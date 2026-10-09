"""Only an attributed append occurrence loses scientific selection eligibility."""

import csv
import hashlib
import importlib
import io
import json
from pathlib import Path

import _icf_screen as raw
import _rel_view as view
import pytest

pytestmark = pytest.mark.domain_corpus
METHOD = "rel-occurrence-quarantine-v1"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def row_bytes(row, schema=raw.ICF):
    stream = io.StringIO(newline="")
    csv.DictWriter(stream, schema.columns, lineterminator="\n").writerow(row)
    return stream.getvalue().encode()


def label(key, value, run):
    return {"work_key": key, "openalex_id": key.split(":")[1], "stage": "2",
            "labeller": "llm", "model": "native", "prompt_sha256": "abc", "run_id": run,
            "machine": "padme", "label": value, "doc_type": "research", "why": "native evidence",
            "labelled_at": "2026-10-01", "source": "native.jsonl"}


def fixture_registry(tmp_path, schema=raw.ICF):
    name = "icf_screen" if schema == raw.ICF else "rel_dimensions"
    table = tmp_path / (name + ".csv")
    initial = [dict(label("openalex:W1", "icf", "original-A"), contrib="yes", field="finance", contrib_type="empirical"),
               dict(label("openalex:W2", "out", "original-B"), contrib="no", field="other", contrib_type="case")]
    raw.append_new(str(table), [{key: value for key, value in row.items() if key in schema.columns} for row in initial],
                   new_table=True, schema=schema)
    baseline = tmp_path / "baseline.csv"
    baseline.write_bytes(table.read_bytes())
    Path(raw.manifest_path(str(baseline))).write_bytes(Path(raw.manifest_path(str(table))).read_bytes())
    source = raw.read_table(str(table), schema)[0]
    copied = dict(source, work_key="openalex:W2")
    raw.append_new(str(table), [copied], "t1654 exact identity migration", schema=schema)
    target = raw.read_table(str(table), schema)[2]
    events = [json.loads(line) for line in Path(raw.manifest_path(str(table))).read_text().split("\n") if line]
    migration = {"mapping": {"openalex:W1": "openalex:W2"},
                 "tables": {name: {"appended": 1, "skipped": 0}}}
    provenance = tmp_path / "migration.jsonl"
    provenance.write_bytes(canonical(migration) + b"\n")
    mapping = tmp_path / "mapping.json"
    mapping.write_bytes(canonical(migration["mapping"]))
    occurrence = {"source_ordinal": 1, "target_ordinal": 3,
                  "source_work_key": source["work_key"], "target_work_key": target["work_key"],
                  "source_raw_row_sha256": digest(row_bytes(source, schema)), "target_raw_row_sha256": digest(row_bytes(target, schema)),
                  "source_fields_sha256": digest(canonical(source)), "target_fields_sha256": digest(canonical(target)),
                  "baseline_target_multiplicity": 0, "prefix_target_multiplicity": 1,
                  "source_multiplicity": 1, "append_event_ordinal": 2,
                  "append_event_sha256": digest(canonical(events[1])),
                  "migration_record_ordinal": 1, "migration_record_sha256": digest(canonical(migration)),
                  "disposition": "exclude_migration_copy", "reason": "unauthorized_selection_precedence"}
    evidence = tmp_path / "evidence.json"
    evidence.write_bytes(canonical({"method": METHOD, "occurrences": [{"table": name, **occurrence}]}))
    approval = tmp_path / "approval.json"
    approval.write_bytes(canonical({"method": METHOD, "evidence_sha256": digest(evidence.read_bytes()),
                                   "approved_occurrences": [{"table": name, **occurrence}]}))
    artifact = lambda p: {"path": p.name, "sha256": digest(p.read_bytes())}
    registry = {"version": METHOD, "artifact_root": ".", "serialization": "utf8-csv-raw-and-canonical-json-v1",
                "evidence": artifact(evidence), "approval": artifact(approval), "mapping": artifact(mapping),
                "migration": artifact(provenance), "tables": [{"name": name, "path": table.name,
                "schema_columns": schema.columns, "id_column": schema.id_column,
                "baseline": artifact(baseline), "baseline_manifest": artifact(Path(raw.manifest_path(str(baseline)))),
                "prefix": {"bytes": len(table.read_bytes()), "rows": 3, "sha256": digest(table.read_bytes())},
                "manifest_prefix": {"bytes": len(Path(raw.manifest_path(str(table))).read_bytes()),
                                    "sha256": digest(Path(raw.manifest_path(str(table))).read_bytes())},
                "occurrences": [occurrence]}]}
    method_path = Path(importlib.import_module("_rel_selection").__file__)
    registry["method_sha256"] = digest(method_path.read_bytes())
    reg_path = tmp_path / "quarantine.json"
    reg_path.write_bytes(canonical(registry))
    config = {"method": METHOD, "registry": str(reg_path), "registry_sha256": digest(reg_path.read_bytes()), "method_sha256": registry["method_sha256"]}
    return table, registry, reg_path, config


def effective(table, config):
    try:
        module = importlib.import_module("_rel_selection")
    except ModuleNotFoundError:
        return raw.read_table(str(table))
    return module.read_effective_table(str(table), selection=config)


def test_only_proven_migration_occurrence_is_ineligible_and_raw_append_stays_raw(tmp_path):
    table, _, _, config = fixture_registry(tmp_path)
    before = table.read_bytes(), Path(raw.manifest_path(str(table))).read_bytes()
    original = raw.read_table(str(table))
    eligible = effective(table, config)
    assert eligible == original[:2]
    assert view.work_status(original[1:], {})["status"] == "icf"
    assert view.work_status(eligible[1:], {})["status"] == "out"
    assert raw.append_new(str(table), [dict(original[2])]) == (0, 1)
    assert (table.read_bytes(), Path(raw.manifest_path(str(table))).read_bytes()) == before


def freeze_registry(registry, reg_path, config):
    """Re-approve a synthetic hypothesis so a negative test reaches its binding guard."""
    root = reg_path.parent
    declarations = [{"table": table["name"], **row} for table in registry["tables"] for row in table["occurrences"]]
    evidence = root / registry["evidence"]["path"]
    evidence.write_bytes(canonical({"method": METHOD, "occurrences": declarations}))
    registry["evidence"]["sha256"] = digest(evidence.read_bytes())
    approval = root / registry["approval"]["path"]
    approval.write_bytes(canonical({"method": METHOD, "evidence_sha256": registry["evidence"]["sha256"],
                                   "approved_occurrences": declarations}))
    registry["approval"]["sha256"] = digest(approval.read_bytes())
    reg_path.write_bytes(canonical(registry))
    config["registry_sha256"] = digest(reg_path.read_bytes())


@pytest.mark.parametrize('field,value,message', [
    ('source_ordinal', 2, 'identity mismatch'), ('target_ordinal', 2, 'existed in baseline'),
    ('target_ordinal', True, 'ordinal/count'), ('source_raw_row_sha256', '0' * 64, 'row hash'),
    ('target_fields_sha256', '0' * 64, 'row hash'), ('prefix_target_multiplicity', 2, 'multiplicity'),
    ('source_multiplicity', 2, 'multiplicity'), ('append_event_ordinal', 1, 'ordinal/count'),
    ('append_event_sha256', '0' * 64, 'event changed'), ('migration_record_sha256', '0' * 64, 'record changed'),
    ('disposition', 'unresolved', 'disposition'), ('reason', 'wrong-label', 'disposition')])
def test_qualified_occurrence_rejects_false_attribution(tmp_path, field, value, message):
    import _rel_selection as selection

    table, registry, reg_path, config = fixture_registry(tmp_path)
    registry['tables'][0]['occurrences'][0][field] = value
    freeze_registry(registry, reg_path, config)
    before = table.read_bytes()
    with pytest.raises(selection.SelectionError, match=message):
        selection.read_effective_table(str(table), selection=config)
    assert table.read_bytes() == before


@pytest.mark.parametrize('artifact', ['evidence', 'approval', 'mapping', 'migration'])
def test_changed_artifact_cannot_authorize_a_copy(tmp_path, artifact):
    import _rel_selection as selection

    table, registry, _, config = fixture_registry(tmp_path)
    (tmp_path / registry[artifact]['path']).write_bytes(b'{}')
    with pytest.raises(selection.SelectionError, match='artifact changed'):
        selection.read_effective_table(str(table), selection=config)


def test_registry_method_approval_and_prefix_bindings_fail_closed(tmp_path):
    import _rel_selection as selection

    table, registry, reg_path, config = fixture_registry(tmp_path)
    for field in ['registry_sha256', 'method_sha256']:
        bad = dict(config, **{field: '0' * 64})
        with pytest.raises(selection.SelectionError):
            selection.read_effective_table(str(table), selection=bad)
    registry['tables'][0]['prefix']['sha256'] = '0' * 64
    freeze_registry(registry, reg_path, config)
    with pytest.raises(selection.SelectionError, match='prefix changed'):
        selection.read_effective_table(str(table), selection=config)


def test_unapproved_roster_and_duplicate_target_cannot_select(tmp_path):
    import _rel_selection as selection

    table, registry, reg_path, config = fixture_registry(tmp_path)
    registry['tables'][0]['occurrences'][0]['reason'] = 'unapproved'
    reg_path.write_bytes(canonical(registry)); config['registry_sha256'] = digest(reg_path.read_bytes())
    with pytest.raises(selection.SelectionError, match='unapproved'):
        selection.read_effective_table(str(table), selection=config)
    registry['tables'][0]['occurrences'][0]['reason'] = 'unauthorized_selection_precedence'
    registry['tables'][0]['occurrences'] *= 2
    freeze_registry(registry, reg_path, config)
    with pytest.raises(selection.SelectionError, match='duplicate target'):
        selection.read_effective_table(str(table), selection=config)


def test_later_authorized_copy_preserved_prefix_continuation_and_stale_view(tmp_path):
    import _rel_selection as selection

    table, _, _, config = fixture_registry(tmp_path)
    recorded = selection.binding(config)
    original = raw.read_table(str(table))[0]
    # A separately authorized one-to-one copy is not in the exclusion registry.
    authorized = dict(original, work_key='openalex:W3')
    assert raw.append_new(str(table), [authorized], 'authorized independent one-to-one') == (1, 0)
    eligible = selection.read_effective_table(str(table), selection=config)
    assert [row['work_key'] for row in eligible] == ['openalex:W1', 'openalex:W2', 'openalex:W3']
    assert eligible[-1] == raw.read_table(str(table))[-1]
    with pytest.raises(selection.SelectionError, match='stale'):
        selection.require_binding(recorded, config)
    # A completed native import remains resumable/idempotent after raw appends.
    selection.require_binding(recorded, config, allow_append=True)
    assert raw.append_new(str(table), [authorized]) == (0, 1)
    with pytest.raises(selection.SelectionError, match='stale'):
        selection.require_binding(None, config, allow_append=True)


def test_identical_content_occurrence_elsewhere_survives_and_selection_can_stay_same(tmp_path):
    import _rel_selection as selection

    table, registry, reg_path, config = fixture_registry(tmp_path)
    duplicate = raw.read_table(str(table))[2]
    # Historical duplicate occurrences are distinguishable even where a later
    # writer's unique-key guard would refuse introducing another duplicate.
    with table.open('ab') as stream:
        stream.write(row_bytes(duplicate))
    manifest = Path(raw.manifest_path(str(table)))
    event = {'appended_at': '2026-10-02T00:00:00Z', 'rows_added': 1, 'rows_total': 4,
             'bytes': len(table.read_bytes()), 'sha256': digest(table.read_bytes()), 'note': 'independent original occurrence'}
    with manifest.open('ab') as stream:
        stream.write(canonical(event) + b'\n')
    registry['tables'][0]['prefix'] = {'bytes': event['bytes'], 'rows': 4, 'sha256': event['sha256']}
    registry['tables'][0]['manifest_prefix'] = {'bytes': len(manifest.read_bytes()), 'sha256': digest(manifest.read_bytes())}
    registry['tables'][0]['occurrences'][0]['prefix_target_multiplicity'] = 2
    freeze_registry(registry, reg_path, config)
    eligible = selection.read_effective_table(str(table), selection=config)
    assert eligible == raw.read_table(str(table))[:2] + [duplicate]
    assert view.work_status(eligible[1:], {})['status'] == 'icf'
    counts = selection.binding(config)['tables']['icf_screen']
    assert (counts['raw'], counts['eligible'], counts['excluded']) == (4, 3, 1)
    assert counts['excluded_ordinals'] == [3] and counts['eligible_ordinals'] == [1, 2, 4]


def test_field_bytes_and_unicode_separators_are_not_normalized(tmp_path):
    import _rel_selection as selection

    table, registry, reg_path, config = fixture_registry(tmp_path)
    baseline = tmp_path / registry['tables'][0]['baseline']['path']
    source_rows = raw.read_table(str(baseline))
    source_rows[0]['why'] = 'Evidence, "quoted"\nU+2028:\u2028 and U+2029:\u2029'
    target_rows = source_rows + [dict(source_rows[0], work_key='openalex:W2')]
    target_rows[2]['label_id'] = raw.label_id(target_rows[2])
    for path, rows in [(baseline, source_rows), (table, target_rows)]:
        stream = io.StringIO(newline=''); writer = csv.DictWriter(stream, raw.COLUMNS, lineterminator='\n')
        writer.writeheader(); writer.writerows(rows); path.write_bytes(stream.getvalue().encode())
        events = []
        for length, note in [(2, 'baseline'), (3, 't1654 exact identity migration')][:1 if path == baseline else 2]:
            data = io.StringIO(newline=''); w = csv.DictWriter(data, raw.COLUMNS, lineterminator='\n')
            w.writeheader(); w.writerows(rows[:length]); payload = data.getvalue().encode()
            events.append({'bytes': len(payload), 'sha256': digest(payload), 'rows_total': length,
                           'rows_added': length if length == 2 else 1, 'note': note, 'appended_at': '2026-10-01T00:00:00Z'})
        Path(raw.manifest_path(str(path))).write_bytes(b''.join(canonical(event) + b'\n' for event in events))
    entry = registry['tables'][0]; occurrence = entry['occurrences'][0]
    for field, path in [('baseline', baseline), ('baseline_manifest', Path(raw.manifest_path(str(baseline))))]:
        entry[field]['sha256'] = digest(path.read_bytes())
    entry['prefix'] = {'bytes': len(table.read_bytes()), 'rows': 3, 'sha256': digest(table.read_bytes())}
    manifest = Path(raw.manifest_path(str(table)))
    entry['manifest_prefix'] = {'bytes': len(manifest.read_bytes()), 'sha256': digest(manifest.read_bytes())}
    occurrence.update(source_raw_row_sha256=digest(row_bytes(source_rows[0])), target_raw_row_sha256=digest(row_bytes(target_rows[2])),
                      source_fields_sha256=digest(canonical(source_rows[0])), target_fields_sha256=digest(canonical(target_rows[2])),
                      append_event_sha256=digest(canonical(events[1])))
    freeze_registry(registry, reg_path, config)
    eligible = selection.read_effective_table(str(table), selection=config)
    assert eligible[0]['why'] == source_rows[0]['why']
    assert eligible == source_rows


def test_alias_matching_and_native_history_order_remain_unchanged(tmp_path):
    import _rel_selection as selection

    table, _, _, config = fixture_registry(tmp_path)
    eligible = selection.read_effective_table(str(table), selection=config)
    # Original A falls back through its OpenAlex identity; its old key is absent.
    pool = [{'work_key': 'doi:10.example/a', 'all_openalex_ids': 'W1', 'all_dois': '10.example/a'},
            {'work_key': 'openalex:W2', 'all_openalex_ids': 'W2', 'all_dois': ''}]
    matched, unmatched, methods = view.match_labels(pool, eligible)
    assert unmatched == [] and methods == {'openalex_id': 1, 'work_key': 1}
    assert [row['run_id'] for row in matched[0]] == ['original-A']
    assert view.work_status(matched[1], {})['status'] == 'out'
    assert eligible == raw.read_table(str(table))[:2]


def test_registry_enumeration_order_does_not_change_eligibility(tmp_path):
    import _rel_selection as selection

    table, registry, reg_path, config = fixture_registry(tmp_path)
    # A second unapproved copy is attributed to a different original source.
    original_b = raw.read_table(str(table))[1]
    raw.append_new(str(table), [dict(original_b, work_key='openalex:W3')], 't1654 exact identity migration')
    target = raw.read_table(str(table))[3]
    events = [json.loads(line) for line in Path(raw.manifest_path(str(table))).read_text().split('\n') if line]
    migration = {'mapping': {'openalex:W2': 'openalex:W3'}, 'tables': {'icf_screen': {'appended': 1, 'skipped': 0}}}
    provenance = tmp_path / registry['migration']['path']
    with provenance.open('ab') as stream:
        stream.write(canonical(migration) + b'\n')
    registry['migration']['sha256'] = digest(provenance.read_bytes())
    mapping = tmp_path / registry['mapping']['path']
    mapping.write_bytes(canonical({'openalex:W1': 'openalex:W2', 'openalex:W2': 'openalex:W3'}))
    registry['mapping']['sha256'] = digest(mapping.read_bytes())
    occurrence = dict(registry['tables'][0]['occurrences'][0], source_ordinal=2, target_ordinal=4,
                      source_work_key='openalex:W2', target_work_key='openalex:W3',
                      source_raw_row_sha256=digest(row_bytes(original_b)), target_raw_row_sha256=digest(row_bytes(target)),
                      source_fields_sha256=digest(canonical(original_b)), target_fields_sha256=digest(canonical(target)),
                      append_event_ordinal=3, append_event_sha256=digest(canonical(events[2])),
                      migration_record_ordinal=2, migration_record_sha256=digest(canonical(migration)))
    registry['tables'][0]['occurrences'].append(occurrence)
    entry = registry['tables'][0]
    entry['prefix'] = {'bytes': len(table.read_bytes()), 'rows': 4, 'sha256': digest(table.read_bytes())}
    manifest = Path(raw.manifest_path(str(table)))
    entry['manifest_prefix'] = {'bytes': len(manifest.read_bytes()), 'sha256': digest(manifest.read_bytes())}
    freeze_registry(registry, reg_path, config)
    first = selection.read_effective_table(str(table), selection=config)
    registry['tables'][0]['occurrences'].reverse()
    freeze_registry(registry, reg_path, config)
    assert selection.read_effective_table(str(table), selection=config) == first == raw.read_table(str(table))[:2]


def test_scientific_icf_consumers_get_eligible_occurrences_and_raw_guards_stay_raw(tmp_path, monkeypatch):
    from types import SimpleNamespace

    import _icf_chunks as chunks
    import _rel_selection as selection
    import corpus_icf_import as importer
    import corpus_icf_stage1_input as stage1
    import corpus_rel_repec_prefilter as prefilter
    import yaml

    table, _, _, config = fixture_registry(tmp_path)
    monkeypatch.setattr(selection, '_configuration', lambda supplied: supplied if supplied is not None else config)
    cfg = yaml.safe_load((selection.ROOT / 'config/rel_screen.yaml').read_text())
    rule = view.screen_rule(cfg)
    pool = [{field: '' for field in view.POOL_FIELDS} for _ in range(2)]
    for n, row in enumerate(pool, 1):
        row.update(work_key=f'openalex:W{n}', openalex_id=f'W{n}', all_openalex_ids=f'W{n}',
                   title='International climate finance', year='2020', abstract='Complete evidence',
                   sources='catalogue', in_catalogue='true')
    pool_path = tmp_path / 'pool.csv'
    with pool_path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, view.POOL_FIELDS); writer.writeheader(); writer.writerows(pool)
    _, graded = chunks.view(str(pool_path), str(table), rule)
    assert {row['work_key']: row['status'] for row in graded} == {'openalex:W1': 'icf', 'openalex:W2': 'out'}
    summary = stage1.run(str(pool_path), str(table), str(tmp_path / 'stage1.jsonl'), ['catalogue'], rule)
    assert summary['works'] == 0 and summary['assessment_selection']['tables']['icf_screen']['excluded'] == 1
    captured = []
    monkeypatch.setattr(importer, 'agree_rule_rows', lambda checks, model, rows, *args: captured.extend(rows) or [])
    args = SimpleNamespace(cmd='stage2-agree-rule', pool=str(pool_path), checks='', check_model='',
                           relabel_run_id='', run_id='', labelled_at='')
    importer._stage2_rows(args, cfg, str(table))
    assert captured == raw.read_table(str(table))[:2]
    # The experimental Opus reader retains its own model restriction/order.
    assert prefilter.screen_opus_labels(str(table)) == {}
    assert importer.side_table_rows(str(table), pool)[-1]['work_key'] == 'openalex:W2'
    assert len(importer.side_table_rows(str(table), pool)) == 3
    assert len(raw.read_table(str(table))) == 3


def test_cached_request_binding_allows_append_but_not_registry_change(tmp_path, monkeypatch):
    import _icf_chunks as chunks
    import _rel_selection as selection

    table, _, _, config = fixture_registry(tmp_path)
    monkeypatch.setattr(selection, '_configuration', lambda supplied: supplied if supplied is not None else config)
    record = selection.binding(config)
    chunks.write_chunks(str(tmp_path / 'empty'), [], {'chunk_size': 20}, {'kind': 'synthetic'})
    saved = json.loads((tmp_path / 'empty/build.json').read_text())['assessment_selection']
    assert saved == record
    selection.require_binding(saved, config)
    bad = dict(saved, registry_sha256='0' * 64)
    with pytest.raises(selection.SelectionError, match='stale'):
        selection.require_binding(bad, config, allow_append=True)


def test_dimension_readers_and_catchup_presence_honor_occurrences(tmp_path, monkeypatch):
    import _rel_selection as selection
    import corpus_rel_discipline_catchup as catchup
    import corpus_rel_view as corpus_view

    table, _, _, config = fixture_registry(tmp_path, raw.DIMENSIONS)
    monkeypatch.setattr(selection, '_configuration', lambda supplied: supplied if supplied is not None else config)
    original = raw.read_table(str(table), raw.DIMENSIONS)
    assert corpus_view.read_dimensions(str(table)) == original[:2]
    assert catchup.dimension_rows(str(tmp_path / 'unused-icf.csv'), str(table), 'unused-prompt') == original[:2]
    assert original[-1]['contrib'] == 'yes' and original[1]['contrib'] == 'no'
    assert len(raw.read_table(str(table), raw.DIMENSIONS)) == 3


def empty_raw_table(path, schema):
    stream = io.StringIO(newline=''); csv.DictWriter(stream, schema.columns, lineterminator='\n').writeheader()
    path.write_bytes(stream.getvalue().encode())
    Path(raw.manifest_path(str(path))).write_bytes(canonical({'rows_total': 0, 'rows_added': 0,
        'bytes': len(path.read_bytes()), 'sha256': digest(path.read_bytes()), 'note': 'empty snapshot'}) + b'\n')


def test_full_view_routes_native_facets_and_policy_readers_and_records_exclusions(tmp_path, monkeypatch):
    import _rel_facet_io as facets
    import _rel_policy as policy
    import _rel_selection as selection
    import corpus_rel_view as corpus_view
    import yaml

    table, _, _, config = fixture_registry(tmp_path)
    monkeypatch.setattr(selection, '_configuration', lambda supplied: supplied if supplied is not None else config)
    cfg = yaml.safe_load((selection.ROOT / 'config/rel_screen.yaml').read_text())
    pool_rows = []
    for n in [1, 2]:
        row = {field: '' for field in view.POOL_FIELDS}
        row.update(work_key=f'openalex:W{n}', openalex_id=f'W{n}', all_openalex_ids=f'W{n}',
                   title='International climate finance', year='2020', abstract='Complete native text',
                   sources='catalogue', in_catalogue='true')
        pool_rows.append(row)
    pool_path = tmp_path / 'pool.csv'
    with pool_path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, view.POOL_FIELDS); writer.writeheader(); writer.writerows(pool_rows)
    venues = tmp_path / 'venues.csv'
    venues.write_text('work_key,tier,tier_ngo_in_b,tier_ngo_not_b,flags,flagged,excluded,publisher_flag\n'
                      'openalex:W1,A,A,A,,false,false,\nopenalex:W2,A,A,A,,false,false,\n')
    facets_path, policies_path = tmp_path / 'facets.csv', tmp_path / 'policies.csv'
    empty_raw_table(facets_path, facets.SCHEMA); empty_raw_table(policies_path, policy.SCHEMA)
    observed = []
    effective_reader = selection.read_effective_table
    def tracked(path, schema=raw.ICF, **kwargs):
        observed.append((Path(path).name, schema.id_column))
        return effective_reader(path, schema, **kwargs)
    monkeypatch.setattr(selection, 'read_effective_table', tracked)
    window = {'search_date': '2026-09-28', 'year_min': 1990, 'last_complete_year': 2025,
              'partial_year': 2026, 'require_full_date_for_partial_year': True}
    seriousness = corpus_view.rr.seriousness_rule(corpus_view._yaml(corpus_view.VENUE_REGISTRIES), corpus_view._yaml(corpus_view.VENUE_TIERS))
    membership = corpus_view.rr.membership_rule(cfg, view.screen_rule(cfg), seriousness['alpha'])
    result = corpus_view.run(str(pool_path), str(table), str(tmp_path / 'view'), window, view.screen_rule(cfg),
        dims_path=None, venues_path=str(venues), seriousness_rule=seriousness, membership=membership,
        facets_path=str(facets_path), policies_path=str(policies_path))
    assert observed == [('icf_screen.csv', 'label_id'), ('facets.csv', 'facet_id'), ('policies.csv', 'policy_id')]
    assert result['labels']['rows'] == 2 and result['labels']['matched_rows'] == 2
    assert result['assessment_selection']['tables']['icf_screen']['raw'] == 3
    assert result['assessment_selection']['tables']['icf_screen']['excluded'] == 1
    with (tmp_path / 'view/rel_view.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    assert {row['work_key']: row['status'] for row in rows} == {'openalex:W1': 'icf', 'openalex:W2': 'out'}
    assert all(row['mu_international'] == row['mu_climate'] == row['mu_finance'] == '' for row in rows)
    selection.require_binding(result['assessment_selection'], config)


@pytest.mark.parametrize("payload", [b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1,"x":2}'])
def test_nonfinite_and_duplicate_provenance_json_is_rejected(payload):
    import _rel_selection as selection

    with pytest.raises(selection.SelectionError):
        selection._json(payload)


def test_approved_copy_must_preserve_every_assessment_field(tmp_path):
    import _rel_selection as selection

    table, registry, reg_path, config = fixture_registry(tmp_path)
    rows = raw.read_table(str(table))
    target = dict(rows[-1], why="Different native judgment")
    # Re-signing the declared field hash cannot authorize an altered assessment.
    source = rows[0]
    occurrence = dict(registry['tables'][0]['occurrences'][0])
    occurrence['target_fields_sha256'] = digest(canonical(target))
    occurrence['target_raw_row_sha256'] = digest(row_bytes(target))
    with pytest.raises(selection.SelectionError, match='non-key'):
        selection._check_occurrence(occurrence, (source, digest(row_bytes(source))),
            (target, digest(row_bytes(target))), raw.ICF,
            ({occurrence['source_fields_sha256']: 1, occurrence['target_fields_sha256']: 0},
             {occurrence['target_fields_sha256']: 1}), [], [], 'icf_screen')


def test_append_counts_bind_actual_csv_occurrences(tmp_path):
    import _rel_selection as selection

    table, _, _, _ = fixture_registry(tmp_path)
    events = [{'bytes': len(table.read_bytes()), 'rows_total': 2}]
    with pytest.raises(selection.SelectionError, match='actual CSV row count'):
        selection._row_index(table, raw.ICF, {3}, 3, {'openalex:W2'}, events)
