"""Rebuild the ledger's evidence layer from the legacy registry (ticket 0872).

Step 1 of the migration (``docs/jetp-ledger-migration.md``): "source" stops
naming a URL. ``sources.csv`` becomes ``publishers``, ``documents`` and
``document-publishers``; ``manifest.csv`` becomes ``retrievals`` and
``snapshots``. Nothing is reinterpreted: every document, retrieval and
fingerprint of the old tables is one row of the new ones, and the old tables
stay in place, read only, until ticket 0878 retires them.

Decisions the rebuild takes, each visible in its output:

- A publisher is one distinct publisher label of ``sources.csv``, verbatim.
  Labels that differ only by case or abbreviation are not merged: each such
  pair is a ``same_as`` candidate in ``relations`` (``PUBLISHER_DUPLICATES``),
  pending review and not in force, so no count moves on a guess.
- A publisher carries the ``authority_category`` most of its documents gave
  it; a document that gave another one is named in the publisher's notes.
  Its ``country`` is set only for a national government or a JETP secretariat,
  whose country is the partnership's; for any other category the documents'
  country is where the publisher wrote about, not where it sits.
- A publication's role is ``author``, except for a publisher that only hosts a
  copy (``HOST_PUBLISHERS``). A joint publication is declared by review
  (``JOINT_PUBLICATIONS``); none is derivable from the free text.
- The known mirrors receive a ``same_as`` candidate towards the document they
  copy (``MIRRORS``; storage contract section 4, document deduplication).
- A retrieval's identifier is ``<document_id>:<n>``, its ordinal among that
  document's attempts in registry order, which is the ``row_key`` the
  Documents view already serves. A failed attempt carries no ``sha256``.
- A document's ``language`` is detected from the text of its latest snapshot
  (a seeded ``langdetect`` over the PDF text layer, the visible HTML text or a
  JSON body), kept only when the detector is confident; a document without
  bytes or without a text layer keeps an empty language rather than a guess
  from a title the collector wrote in English.

The output is a record, not a derived view: it is written once, reviewed as a
diff, and from then on edited like any ledger table.
"""

import argparse
import csv
import html
import re
import subprocess
import unicodedata
from collections import Counter
from pathlib import Path

from utils import get_logger

from jetp._ledger_headers import LEDGER_DIR, load_schema, write_table

log = get_logger('jetp.build_evidence_layer')

DECIDED_AT = '2026-09-23'
DECIDED_BY = 'scripts/jetp/build_evidence_layer.py'

# Copies of a document already in the registry: mirror -> original.
MIRRORS = {
    'idn-cipp-2023-cpr-mirror': 'idn-cipp-2023',
    'sen-investment-plan-l4-mirror': 'sen-investment-plan-l4',
    'sen-annex8-project-analysis': 'sen-investment-plan-annex8-official',
}

# Publishers whose documents in the registry are copies they host, not texts
# they wrote.
HOST_PUBLISHERS = frozenset({'Climate Policy Radar', 'Vie-Publique.sn'})

# Joint publications added by review: document_id -> further publisher labels.
JOINT_PUBLICATIONS = {}

# Publisher labels that read as one publisher, left for review: (label, label).
PUBLISHER_DUPLICATES = (
    ('Senelec', 'SENELEC'),
    ('Senelec via AFD dgMarket', 'SENELEC via AFD dgMarket'),
    ('AFD', 'Agence Francaise de Developpement'),
    ('MEPM', 'Senegal MEPM'),
    ('MEPM', 'Ministry of Energy Petroleum and Mines'),
)

# A publisher of these categories speaks for the partnership's country.
NATIONAL_CATEGORIES = frozenset({'national_government', 'jetp_secretariat'})

LANGUAGE_MIN_PROBABILITY = 0.8
LANGUAGE_MIN_CHARS = 300


def slug(label):
    text = unicodedata.normalize('NFKD', label).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def _publisher_ids(labels_by_use):
    """One identifier per label; labels that slug alike are told apart by rank.

    The most used label keeps the plain slug, ties broken by the label itself,
    so the assignment does not depend on registry order.
    """
    ids, taken = {}, Counter()
    for label in sorted(labels_by_use, key=lambda lab: (-labels_by_use[lab], lab)):
        base = slug(label)
        taken[base] += 1
        ids[label] = base if taken[base] == 1 else f'{base}-{taken[base]}'
    return ids


def _publishers(sources, joint):
    uses = Counter(row['publisher'] for row in sources)
    for labels in joint.values():
        uses.update(label for label in labels if label not in uses)
    ids = _publisher_ids(uses)
    categories, countries = {}, {}
    for row in sources:
        categories.setdefault(row['publisher'], Counter())[row['authority_category']] += 1
        countries.setdefault(row['publisher'], set()).add(row['country'])
    publishers = []
    for label in sorted(ids, key=ids.get):
        counts = categories.get(label, Counter())
        category = (min(counts, key=lambda c: (-counts[c], c)) if counts else None)
        notes = []
        for other in sorted(set(counts) - {category}):
            documents = sorted(r['source_id'] for r in sources
                               if r['publisher'] == label and r['authority_category'] == other)
            notes.append(f"sources.csv gave authority_category {other} to "
                         f"{', '.join(documents)}")
        country = None
        if category in NATIONAL_CATEGORIES and len(countries[label]) == 1:
            (country,) = countries[label]
        publishers.append({'publisher_id': ids[label], 'name': label,
                           'authority_category': category or None, 'country': country,
                           'notes': '; '.join(notes) or None})
    return publishers, ids


def _documents(sources, languages):
    return [{
        'document_id': row['source_id'], 'country': row['country'] or None,
        'document_type': row['source_type'] or None,
        'language': languages.get(row['source_id']),
        'title': row['title'], 'url': row['url'] or None,
        'published_date': row['published_date'] or None, 'edition_of': None,
        'active': row['active'] or None, 'notes': row['notes'] or None,
    } for row in sources]


def _publications(sources, ids, joint):
    rows = []
    for row in sources:
        labels = [row['publisher'], *joint.get(row['source_id'], [])]
        for label in labels:
            role = 'host' if label in HOST_PUBLISHERS else 'author'
            rows.append({'document_id': row['source_id'], 'publisher_id': ids[label],
                         'role': role})
    return rows


def _retrievals_and_snapshots(manifest):
    ordinals = Counter()
    retrievals, snapshots = [], {}
    for row in manifest:
        ordinals[row['source_id']] += 1
        sha = row['sha256'] or None
        retrievals.append({
            'retrieval_id': f"{row['source_id']}:{ordinals[row['source_id']]}",
            'document_id': row['source_id'], 'retrieved_at': row['retrieved_at'],
            'status': row['status'], 'http_status': row['http_status'] or None,
            'content_type': row['content_type'] or None, 'etag': row['etag'] or None,
            'last_modified': row['last_modified'] or None,
            'final_url': row['final_url'] or None, 'error': row['error'] or None,
            'sha256': sha,
        })
        if sha is None:
            continue
        snapshot = {'sha256': sha, 'storage_path': row['storage_path'],
                    'size_bytes': row['size_bytes'] or None,
                    'content_type': row['content_type'] or None}
        if snapshots.setdefault(sha, snapshot) != snapshot:
            raise ValueError(f'{sha}: two retrievals describe the same bytes differently')
    return retrievals, sorted(snapshots.values(), key=lambda s: s['sha256'])


def _same_as(from_kind, from_id, to_id, method):
    return {
        'relation_id': f'same_as-{from_kind}-{from_id}--{to_id}', 'from_kind': from_kind,
        'from_id': from_id, 'relation': 'same_as', 'to_kind': from_kind, 'to_id': to_id,
        'status': 'candidate', 'method': method, 'method_version': '1',
        'decided_at': DECIDED_AT, 'decided_by': DECIDED_BY,
    }


def reconstruct(sources, manifest, languages=None, joint_publications=None,
                mirrors=None, publisher_duplicates=None):
    """The evidence tables, as lists of rows keyed by column, from the old two."""
    languages = languages or {}
    joint = JOINT_PUBLICATIONS if joint_publications is None else joint_publications
    mirrors = MIRRORS if mirrors is None else mirrors
    duplicates = PUBLISHER_DUPLICATES if publisher_duplicates is None else publisher_duplicates
    known = {row['source_id'] for row in sources}
    unknown = ({r['source_id'] for r in manifest} | set(mirrors) | set(mirrors.values())
               | set(joint)) - known
    if unknown:
        raise ValueError(f'unknown documents: {sorted(unknown)}')
    publishers, ids = _publishers(sources, joint)
    retrievals, snapshots = _retrievals_and_snapshots(manifest)
    relations = [_same_as('document', mirror, original, 'mirror_review')
                 for mirror, original in sorted(mirrors.items())]
    relations += [_same_as('publisher', ids[a], ids[b], 'label_review')
                  for a, b in duplicates]
    return {
        'publishers': publishers,
        'documents': _documents(sources, languages),
        'document_publishers': _publications(sources, ids, joint),
        'snapshots': snapshots,
        'retrievals': retrievals,
        'relations': relations,
    }


# --- Language of a document, from its bytes -----------------------------------

def snapshot_text(path):
    """The readable text of a snapshot, or '' when it has no text layer."""
    data = Path(path).read_bytes()
    if data[:5] == b'%PDF-':
        result = subprocess.run(['pdftotext', '-l', '5', str(path), '-'],
                                capture_output=True, timeout=120, check=False)
        text = result.stdout.decode('utf-8', 'ignore')
    elif b'<html' in data[:5000].lower() or b'<!doctype' in data[:500].lower():
        page = data.decode('utf-8', 'ignore')
        page = re.sub(r'(?is)<(script|style|noscript)\b.*?</\1>', ' ', page)
        text = html.unescape(re.sub(r'<[^>]+>', ' ', page))
    elif data[:1] in (b'{', b'['):
        text = data.decode('utf-8', 'ignore')
    else:
        return ''
    return re.sub(r'\s+', ' ', text).strip()


def detect_languages(manifest, documents_root):
    """ISO 639-1 language of each document's latest snapshot, when confident."""
    from langdetect import DetectorFactory, detect_langs

    DetectorFactory.seed = 0
    latest = {}
    for row in manifest:
        if row['sha256']:
            latest[row['source_id']] = row['storage_path']
    languages = {}
    for document_id, relative in sorted(latest.items()):
        path = Path(documents_root) / relative
        if not path.is_file():
            continue
        text = snapshot_text(path)
        if len(text) < LANGUAGE_MIN_CHARS:
            continue
        best = detect_langs(text[:30000])[0]
        if best.prob >= LANGUAGE_MIN_PROBABILITY:
            languages[document_id] = best.lang.split('-')[0]
    return languages


def _read(path):
    with Path(path).open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--ledger-dir', type=Path, default=LEDGER_DIR,
                        help='directory holding sources.csv and manifest.csv')
    parser.add_argument('--output-dir', type=Path,
                        help='ledger directory to write the tables to (default: --ledger-dir)')
    parser.add_argument('--documents-root', type=Path,
                        help='snapshot store to read languages from (data/jetp/documents)')
    args = parser.parse_args(argv)
    sources = _read(args.ledger_dir / 'sources.csv')
    manifest = _read(args.ledger_dir / 'manifest.csv')
    languages = detect_languages(manifest, args.documents_root) if args.documents_root else {}
    schema = load_schema()
    for table, rows in reconstruct(sources, manifest, languages).items():
        for path in write_table(args.output_dir or args.ledger_dir, table, rows, schema=schema):
            log.info('%s: %d rows', path, len(rows))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
