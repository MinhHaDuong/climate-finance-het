"""Preserve historical evidence identities during candidate source migration."""

import csv
import hashlib
import json
from pathlib import Path

import pytest
from jetp import build_source_crosswalk as builder
from jetp._source_crosswalk import migrate_sources


def table(root, name, rows):
    path = root / 'data/jetp' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def saved(root, content):
    digest = hashlib.sha256(content).hexdigest()
    path = Path('objects') / digest[:2] / f'{digest}.txt'
    target = root / 'data/jetp/documents' / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return digest, str(path)


def attempt(source, identity, digest='', storage='', edition='edition-original'):
    return dict(source_id=source, acquisition_id=identity,
                retrieved_at='2026-09-01T12:00:00Z', status='collected' if digest else 'failed',
                sha256=digest, storage_path=storage, report_edition_id=edition,
                final_url=f'https://example.test/{source}', error='' if digest else 'timeout')


def fixture(root):
    old, old_path = saved(root, b'Original report')
    table(root, 'sources.csv', [dict(source_id='official', url='https://example.test/report',
                                   title='Report', publisher='Ministry', authority_category='government'),
                               dict(source_id='mirror', url='https://mirror.test/report',
                                    title='Report', publisher='Mirror')])
    rows = [attempt('official', 'a-old', old, old_path)]
    table(root, 'manifest.csv', rows)
    table(root, 'events.csv', [dict(event_id='old-assertion', source_id='official',
                                  document_sha256=old, locator='p1', acquisition_id='a-old',
                                  report_edition_id='edition-original', extraction_id='extract-old',
                                  parser_version='fixture/1')])
    return old, old_path, rows


def test_refresh_keeps_original_bytes_and_distinct_attempts(tmp_path):
    old, old_path, rows = fixture(tmp_path)
    before = migrate_sources(tmp_path)
    changed, changed_path = saved(tmp_path, b'Revised report')
    rows.extend([attempt('official', 'a-new', changed, changed_path, 'edition-revised'),
                 attempt('mirror', 'a-mirror', old, old_path), attempt('official', 'a-fail')])
    table(tmp_path, 'manifest.csv', rows)
    after = migrate_sources(tmp_path)
    evidence = after['evidence'][0]
    assert evidence['status'] == 'resolved'
    assert evidence['document_sha256'] == old
    assert evidence['acquisition_id'] == 'a-old'
    assert evidence['extraction_id'] == 'extract-old'
    assert evidence['evidence_id'] == before['evidence'][0]['evidence_id']
    assert len(after['acquisitions']) == 4
    assert len({row['acquisition_id'] for row in after['acquisitions']}) == 4
    assert all(row.get('check_id') is None for row in after['acquisitions'])
    assert all(row.get('sweep_id') is None for row in after['acquisitions'])
    assert evidence['report_edition_id'] == 'edition-original'
    assert json.dumps(after, sort_keys=True) == json.dumps(migrate_sources(tmp_path), sort_keys=True)


def test_legacy_unknowns_and_each_input_row_survive(tmp_path):
    old, path, rows = fixture(tmp_path)
    rows.append(attempt('official', 'second-same-hash', old, path))
    table(tmp_path, 'manifest.csv', rows)
    table(tmp_path, 'source-claims.csv', [dict(claim_id='legacy', source_id='official', section='p1')])
    table(tmp_path, 'implementation-events.csv', [dict(implementation_event_id='ambiguous',
          source_id='official', document_sha256=old, locator='p1')])
    for name, row in {
        'authority-coverage.csv': dict(authority_id='ministry', verdict='no_match', checked_at='2025-01-01'),
        'project-coverage.csv': dict(project_id='project', review_status='not_found'),
        'dry-searches.csv': dict(search_id='dry', outcome='blocked', query_or_route='archive'),
        'news-leads.csv': dict(lead_id='lead', evidence_role='unknown', url='https://news.test'),
        'vnm-pilot-observations.csv': dict(observation_id='obs', legacy_status='cancelled'),
        'idn-portfolio-observations.csv': dict(project_id='idn', reconciliation_status='unresolved'),
    }.items():
        table(tmp_path, name, [row])
    result = migrate_sources(tmp_path)
    assert len(result['mappings']) == sum(1 for p in (tmp_path / 'data/jetp').glob('*.csv')
                                         for _ in csv.DictReader(p.open()))
    assert all(row['disposition'] for row in result['mappings'])
    assert len({row['row_id'] for row in result['mappings']}) == len(result['mappings'])
    assert len(result['unresolved']) >= 2
    assert all(row.get('recorded_at') is None for row in result['evidence'])
    assert all(row.get('intelligence_role') in (None, 'unknown') for row in result['evidence'])
    encoded = json.dumps(result)
    for word in ('cancelled', 'blocked', 'no_match', 'not_found', 'archive', 'reconciliation_status'):
        assert word in encoded


def test_missing_or_corrupt_bytes_never_resolve(tmp_path):
    _, path, _ = fixture(tmp_path)
    source = tmp_path / 'data/jetp/documents' / path
    source.unlink()
    assert migrate_sources(tmp_path)['evidence'][0]['status'] == 'unresolved'
    source.write_bytes(b'Corrupted bytes')
    assert migrate_sources(tmp_path)['evidence'][0]['status'] == 'unresolved'


def test_identical_legacy_attempt_rows_remain_distinct_on_rerun(tmp_path):
    old, path, _ = fixture(tmp_path)
    row = attempt('official', 'unused', old, path)
    del row['acquisition_id']
    table(tmp_path, 'manifest.csv', [row, row])
    first = migrate_sources(tmp_path)
    ids = [r['acquisition_id'] for r in first['acquisitions']]
    assert len(set(ids)) == 2
    assert first == migrate_sources(tmp_path)
    table(tmp_path, 'manifest.csv', [row, row, attempt('official', 'failed')])
    assert [r['acquisition_id'] for r in migrate_sources(tmp_path)['acquisitions']][:2] == ids


def test_candidate_write_is_deterministic_and_protects_inputs(tmp_path, monkeypatch):
    fixture(tmp_path)
    output = tmp_path / 'candidate.json.gz'
    builder.write_crosswalk(tmp_path, output)
    accepted = output.read_bytes()
    builder.write_crosswalk(tmp_path, output)
    assert output.read_bytes() == accepted
    baseline = tmp_path / 'data/jetp/releases/mvp-baseline-0761.zip'
    baseline.parent.mkdir(parents=True)
    baseline.write_bytes(b'accepted frozen package')
    for protected in (baseline, tmp_path / 'data/jetp/sources.csv'):
        before = protected.read_bytes()
        with pytest.raises(ValueError):
            builder.write_crosswalk(tmp_path, protected)
        assert protected.read_bytes() == before

    def interrupted(*args, **kwargs):
        raise ValueError('candidate validation failed')

    monkeypatch.setattr(builder, 'migrate_sources', interrupted)
    with pytest.raises(ValueError, match='candidate validation failed'):
        builder.write_crosswalk(tmp_path, output)
    assert output.read_bytes() == accepted


@pytest.mark.parametrize('alias_kind', ['symlink', 'hardlink'])
def test_candidate_cannot_write_through_input_alias(tmp_path, alias_kind):
    fixture(tmp_path)
    source = tmp_path / 'data/jetp/sources.csv'
    alias = tmp_path / 'alias.json'
    if alias_kind == 'symlink':
        alias.symlink_to(source)
    else:
        alias.hardlink_to(source)
    before = source.read_bytes()
    with pytest.raises(ValueError):
        builder.write_crosswalk(tmp_path, alias)
    assert source.read_bytes() == before


def test_tuple_cross_source_and_origin_are_not_inferred(tmp_path):
    old, path, rows = fixture(tmp_path)
    rows.append(attempt('mirror', 'mirror-attempt', old, path))
    table(tmp_path, 'manifest.csv', rows)
    table(tmp_path, 'events.csv', [dict(event_id='misjoined', source_id='official',
          document_sha256=old, locator='p1', acquisition_id='mirror-attempt',
          report_edition_id='edition-original', extraction_id='extract-old', parser_version='fixture/1',
          intelligence_role='secondary', origin_rationale='Quotes lender', upstream_status='cited_not_acquired')])
    result = migrate_sources(tmp_path)
    evidence = result['evidence'][0]
    assert evidence['status'] == 'unresolved'
    assert 'acquisition_source_mismatch' in evidence['reasons']
    assert evidence['intelligence_role'] == 'secondary'
    assert evidence['origin_rationale'] == 'Quotes lender'
    assert evidence['upstream_status'] == 'cited_not_acquired'
    assert result['acquisitions'][0]['support_group_id'] == result['acquisitions'][1]['support_group_id']
    assert result['acquisitions'][0]['independence'] == 'unknown'


@pytest.mark.parametrize('filename', ['source-crosswalk-0763.json.gz.dvc', 'README.md',
                                      '.gitignore', 'release.json', 'edition-1/release.json'])
@pytest.mark.parametrize('alias_kind', ['direct', 'symlink', 'hardlink'])
def test_candidate_preserves_release_recovery_metadata(tmp_path, filename, alias_kind):
    fixture(tmp_path)
    metadata = tmp_path / 'data/jetp/releases' / filename
    metadata.parent.mkdir(parents=True)
    metadata.write_text('{"release_id": "accepted"}\n')
    output = metadata
    if alias_kind != 'direct':
        output = tmp_path / 'candidate-alias.json'
        if alias_kind == 'symlink':
            output.symlink_to(metadata)
        else:
            output.hardlink_to(metadata)
    before = metadata.read_bytes()
    with pytest.raises(ValueError):
        builder.write_crosswalk(tmp_path, output)
    assert metadata.read_bytes() == before


@pytest.mark.parametrize('suffix', ['.json', '.json.gz'])
def test_existing_release_candidate_remains_replaceable(tmp_path, suffix):
    fixture(tmp_path)
    output = tmp_path / 'data/jetp/releases' / ('candidate' + suffix)
    builder.write_crosswalk(tmp_path, output)
    before = output.read_bytes()
    builder.write_crosswalk(tmp_path, output)
    assert output.read_bytes() == before


def test_crosswalk_preserves_unrelated_existing_output_outside_releases(tmp_path):
    fixture(tmp_path)
    output = tmp_path / 'unrelated.json'
    output.write_text('{"release_id":"accepted"}')
    before = output.read_bytes()
    with pytest.raises(ValueError, match='recognized'):
        builder.write_crosswalk(tmp_path, output)
    assert output.read_bytes() == before
