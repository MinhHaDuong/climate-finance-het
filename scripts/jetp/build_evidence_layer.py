"""Rebuild the ledger's evidence layer from the legacy registry (ticket 0872).

Step 1 of the migration (``docs/jetp-ledger-migration.md``): "source" stops
naming a URL. ``sources.csv`` becomes ``parties``, ``party-names``,
``documents`` and ``document-publishers``; ``manifest.csv`` becomes
``retrievals`` and ``snapshots``. Nothing is reinterpreted: every document,
retrieval and fingerprint of the old tables is one row of the new ones, and
the old tables stay in place, read only, until ticket 0878 retires them.

Organisations are under authority control (author's decision of 2026-09-23,
``docs/jetp-ontology.md`` decision 12). Decisions the rebuild takes, each
visible in its output:

- A publisher is a party in a publishing role. Parties are minted from the
  publisher texts of ``sources.csv``; texts that differ only by case,
  diacritics or spacing are one party with several name forms, never two
  parties and a ``same_as`` (storage contract section 4, organisations).
- Every form a document carries is a ``party-names`` row, justified by the
  first document, in identifier order, that carries it, a document printing
  it as its whole publisher text first. The most used form of
  a party is its preferred form, ties going to a form not written in capitals,
  then to alphabetical order; the others are ``spelling_or_case_variant``.
- A publisher text that names two or more bodies (``JOINT_LABELS``) is a
  joint publication: the document is linked to each party, and each part is
  a name form read from that label, in the ``author`` role unless the entry
  tags a part with another one. A part named nowhere else takes its
  authority category and country from review (``PART_ATTRIBUTES``).
- Real variants, an acronym against its expansion or a country-prefixed form,
  are tier-2 ``same_as`` candidates in ``relations``, pending review and not
  in force, so no count moves on a guess. An acronym is detected when a form
  written in capitals is the initials of another party's form, function words
  aside; other pairs are listed by review (``NAME_VARIANT_CANDIDATES``). No
  external identifier ties any two parties yet, so none of these is merged.
- A party carries the ``authority_category`` most of its own documents gave
  it; a document that gave another one is named in the party's notes. Its
  ``country`` is set only for a national government or a JETP secretariat,
  whose country is the partnership's; for any other category the documents'
  country is where the party wrote about, not where it sits.
- A publisher text ``X via Y`` names publisher X and the channel Y it was
  retrieved through, a procurement portal, a mirror or a platform. Y is
  never a party: it is written in the document's notes. A text ``X / Y``
  names publisher X and Y, a consulting firm or a named person who wrote the
  document for X (``WRITERS``, by review). A firm is a party linked to the
  document as ``author``, and X as ``commissioner``; a natural person is not
  a party of the ledger (``docs/jetp-ontology.md`` section 6) and is written
  in the document's notes instead. A slash text whose second part is not a
  reviewed writer, and both parts are organisations with nothing in the text
  marking one a consultant, is a joint publication instead (``JOINT_LABELS``,
  below), each part a party in the ``author`` role; one review found split
  three ways, a commissioner ministry between a hosting publisher and the
  firm it commissioned (``Senegal EITI / MEPM ENERCAP``). A slash text
  matching neither stays one party. The registry's text of a split label is
  kept in the document's notes (author's decision of 2026-09-23).
- A publication's role is ``author``, except for a party that only hosts a
  copy (``HOST_PUBLISHERS``) and the publisher that commissioned the writer
  of an ``X / Y`` text. Further joint publications may be declared by
  review (``JOINT_PUBLICATIONS``).
- The known mirrors receive a ``same_as`` candidate towards the document they
  copy (``MIRRORS``; storage contract section 4, document deduplication).
- A retrieval's identifier is ``<document_id>:<n>``, its ordinal among that
  document's attempts in registry order, which is the ``row_key`` the
  Documents view already serves. A failed attempt carries no ``sha256``.
- A document's ``language`` is detected from the text of its latest snapshot
  (a seeded ``langdetect`` over the PDF text layer, the visible HTML text or a
  JSON body), kept only when the detector is confident; a document without
  bytes or without a text layer keeps an empty language rather than a guess
  from a title the collector wrote in English. A name form's language is left
  empty: the rebuild does not guess it from the form.

The output is a record, not a derived view: it is written once, reviewed as a
diff, and from then on edited like any ledger table.
"""

import argparse
import csv
import html
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from utils import get_logger

from jetp._evidence_layer_rules import (
    DECIDED_AT,
    DECIDED_BY,
    HOST_PUBLISHERS,
    JOINT_LABELS,
    JOINT_PUBLICATIONS,
    MIRRORS,
    NAME_VARIANT_CANDIDATES,
    NATIONAL_CATEGORIES,
    PART_ATTRIBUTES,
    WRITERS,
    initials,
    is_acronym,
    name_key,
    slug,
    split_label,
)
from jetp._ledger_headers import LEDGER_DIR, load_schema, write_table

log = get_logger('jetp.build_evidence_layer')

LANGUAGE_MIN_PROBABILITY = 0.8
LANGUAGE_MIN_CHARS = 300


def _printed_forms(sources, joint_labels, joint, writers):
    """``(row, form, origin, role)`` for every party name a document carries.

    ``origin`` is ``None`` for a form that is the document's whole publisher
    text, ``(text, how)`` for a form read out of a longer text (``how`` is
    ``joint``, ``via``, ``slash`` for the publisher of an ``X / Y`` text or
    ``writer`` for its Y), or ``'review'`` for a joint publication added by
    review. ``role`` is the publication role, ``None`` for the default.
    """
    for row in sources:
        label = row['publisher']
        if label in joint_labels:
            for part in joint_labels[label]:
                name, role = part if isinstance(part, tuple) else (part, None)
                yield row, name, (label, 'joint'), role
        else:
            publisher, writer, channel = split_label(label, writers)
            how = 'slash' if writer else 'via' if channel else None
            yield row, publisher, ((label, how) if how else None), (
                'commissioner' if writer else None)
            if writer and writers[writer] == 'firm':
                yield row, writer, (label, 'writer'), 'author'
        for extra in joint.get(row['source_id'], ()):
            yield row, extra, 'review', None


def _own(origin):
    """Whether a form names the party that published the document."""
    return origin is None or (isinstance(origin, tuple) and origin[1] in ('via', 'slash'))


def _preferred(uses):
    return min(uses, key=lambda form: (-uses[form], form.isupper(), form))


def _parties(sources, joint_labels, joint, part_attributes, writers):
    printed = list(_printed_forms(sources, joint_labels, joint, writers))
    uses = defaultdict(Counter)       # key -> form -> documents carrying it
    first_document = {}               # form -> first document carrying it
    origins = defaultdict(set)        # form -> origins it was read from
    categories = defaultdict(Counter)  # key -> category -> own documents
    countries = defaultdict(set)
    documents = defaultdict(list)     # key -> own documents, for the notes
    for row, form, origin, _ in printed:
        key = name_key(form)
        uses[key][form] += 1
        # A document printing the form as its whole publisher text justifies
        # it before one printing it inside a longer text.
        justification = (origin is not None, row['source_id'])
        first_document[form] = min(first_document.get(form, justification), justification)
        origins[form].add(origin)
        if _own(origin):
            categories[key][row['authority_category']] += 1
            countries[key].add(row['country'])
            documents[key].append(row)
    ids, taken = {}, Counter()
    order = sorted(uses, key=lambda k: (-sum(uses[k].values()), _preferred(uses[k])))
    for key in order:
        base = slug(_preferred(uses[key]))
        taken[base] += 1
        ids[key] = base if taken[base] == 1 else f'{base}-{taken[base]}'
    parties, names = [], []
    attributes = {name_key(form): value for form, value in part_attributes.items()}
    for key in sorted(ids, key=ids.get):
        party_id, preferred = ids[key], _preferred(uses[key])
        counts = categories[key]
        notes = []
        if counts:
            category = min(counts, key=lambda c: (-counts[c], c))
            country = None
            if category in NATIONAL_CATEGORIES and len(countries[key]) == 1:
                (country,) = countries[key]
            for other in sorted(set(counts) - {category}):
                cited = sorted(r['source_id'] for r in documents[key]
                               if r['authority_category'] == other)
                notes.append(f"sources.csv gave authority_category {other} to "
                             f"{', '.join(cited)}")
        elif all(isinstance(o, tuple) and o[1] == 'writer'
                 for form in uses[key] for o in origins[form]):
            category, country = None, None
            notes.append('named only as the writer of a document its publisher '
                         'commissioned; no authority category of the list fits a '
                         'consulting firm')
        else:
            category, country, note = attributes.get(key, (None, None, None))
            notes.append('named only in a joint publication; authority category and '
                         'country set by review')
            if note:
                notes.append(note)
        parties.append({'party_id': party_id, 'authority_category': category or None,
                        'country': country, 'notes': '; '.join(notes) or None})
        forms = sorted(uses[key], key=lambda form: (form != preferred, form))
        for number, form in enumerate(forms, start=1):
            read_from = sorted(o for o in origins[form] if isinstance(o, tuple))
            note = None
            if None not in origins[form]:
                note = ('; '.join(f"read from the joint publisher text '{text}'"
                                  if how == 'joint' else
                                  f"read from the publisher text '{text}'"
                                  for text, how in read_from)
                        or 'added by review as a joint publisher')
            names.append({
                'name_row_id': f'{party_id}.name.{number}', 'party_id': party_id,
                'name': form,
                'form_type': 'preferred' if form == preferred else 'spelling_or_case_variant',
                'language': None, 'document_id': first_document[form][1], 'line_id': None,
                'recorded_at': DECIDED_AT, 'decided_by': DECIDED_BY, 'status': 'accepted',
                'supersedes': None, 'notes': note,
            })
    return parties, names, printed, ids


def _label_notes(label, joint_labels, writers):
    """What a split publisher text says beyond its parties, for the notes."""
    if label in joint_labels:
        return []
    _, writer, channel = split_label(label, writers)
    if not (writer or channel):
        return []
    notes = [f"publisher text in the registry: '{label}'"]
    if channel:
        notes.append(f'retrieved through {channel}, a channel and not a party')
    if writer and writers[writer] == 'person':
        notes.append(f'written by {writer}, a natural person, not held as a party '
                     '(docs/jetp-ontology.md section 6)')
    return notes


def _documents(sources, languages, joint_labels, writers):
    return [{
        'document_id': row['source_id'], 'country': row['country'] or None,
        'document_type': row['source_type'] or None,
        'language': languages.get(row['source_id']),
        'title': row['title'], 'url': row['url'] or None,
        'published_date': row['published_date'] or None, 'edition_of': None,
        'active': row['active'] or None,
        'notes': '; '.join(([row['notes']] if row['notes'] else [])
                           + _label_notes(row['publisher'], joint_labels, writers))
                 or None,
    } for row in sources]


def _publications(printed, ids, names):
    """One row per document and party, naming the form the document prints."""
    form_rows = {name['name']: name['name_row_id'] for name in names}
    rows, seen = [], set()
    for row, form, _, role in printed:
        pair = (row['source_id'], ids[name_key(form)])
        if pair in seen:
            continue
        seen.add(pair)
        rows.append({'document_id': pair[0], 'party_id': pair[1],
                     'role': 'host' if form in HOST_PUBLISHERS else role or 'author',
                     'name_row_id': form_rows[form]})
    return rows


def _name_candidates(names, reviewed):
    """Tier-2 ``(party, party, method)`` pairs: acronyms, then reviewed pairs."""
    forms = defaultdict(set)
    for name in names:
        forms[name['party_id']].add(name['name'])
    by_initials = defaultdict(set)
    for party_id, party_forms in forms.items():
        for form in party_forms:
            acronym_letters = initials(form)
            if acronym_letters:
                by_initials[acronym_letters].add(party_id)
    pairs = {}
    for party_id, party_forms in sorted(forms.items()):
        for form in sorted(party_forms):
            if is_acronym(form):
                for other in sorted(by_initials.get(form.strip(), set()) - {party_id}):
                    pairs.setdefault((party_id, other), 'normalised_label')
    party_of = {name_key(n['name']): n['party_id'] for n in names}
    for a, b in reviewed:
        pair = (party_of[name_key(a)], party_of[name_key(b)])
        if pair[0] != pair[1]:
            pairs.setdefault(pair, 'label_review')
    return sorted((a, b, method) for (a, b), method in pairs.items())


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
                mirrors=None, joint_labels=None, name_candidates=None,
                part_attributes=None, writers=None):
    """The evidence tables, as lists of rows keyed by column, from the old two."""
    languages = languages or {}
    joint = JOINT_PUBLICATIONS if joint_publications is None else joint_publications
    mirrors = MIRRORS if mirrors is None else mirrors
    joint_labels = JOINT_LABELS if joint_labels is None else joint_labels
    reviewed = NAME_VARIANT_CANDIDATES if name_candidates is None else name_candidates
    part_attributes = PART_ATTRIBUTES if part_attributes is None else part_attributes
    writers = WRITERS if writers is None else writers
    known = {row['source_id'] for row in sources}
    unknown = ({r['source_id'] for r in manifest} | set(mirrors) | set(mirrors.values())
               | set(joint)) - known
    if unknown:
        raise ValueError(f'unknown documents: {sorted(unknown)}')
    parties, names, printed, ids = _parties(sources, joint_labels, joint, part_attributes,
                                             writers)
    retrievals, snapshots = _retrievals_and_snapshots(manifest)
    relations = [_same_as('document', mirror, original, 'mirror_review')
                 for mirror, original in sorted(mirrors.items())]
    relations += [_same_as('party', a, b, method)
                  for a, b, method in _name_candidates(names, reviewed)]
    return {
        'parties': parties,
        'party_names': names,
        'documents': _documents(sources, languages, joint_labels, writers),
        'document_publishers': _publications(printed, ids, names),
        'snapshots': snapshots,
        'retrievals': retrievals,
        'relations': relations,
    }


# --- Language of a document, from its bytes -----------------------------------

def snapshot_text(path):
    """The readable text of a snapshot, or '' when it has no text layer."""
    # Sniff the format from the head: pdftotext reads a PDF itself, so its
    # bytes, the bulk of the store, are never loaded here.
    with Path(path).open('rb') as handle:
        head = handle.read(5000)
    if head[:5] == b'%PDF-':
        result = subprocess.run(['pdftotext', '-l', '5', str(path), '-'],
                                capture_output=True, timeout=120, check=False)
        text = result.stdout.decode('utf-8', 'ignore')
    elif b'<html' in head.lower() or b'<!doctype' in head[:500].lower():
        page = Path(path).read_bytes().decode('utf-8', 'ignore')
        page = re.sub(r'(?is)<(script|style|noscript)\b.*?</\1>', ' ', page)
        text = html.unescape(re.sub(r'<[^>]+>', ' ', page))
    elif head[:1] in (b'{', b'['):
        text = Path(path).read_bytes().decode('utf-8', 'ignore')
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
    # Deliberate script-io exception: this writes seven named tables into one
    # directory, not one file to one path, so the single --output contract of
    # script_io_args.parse_io_args/validate_io does not fit. Same multi-output
    # precedent as build_0730_descriptives.py.
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--ledger-dir', type=Path, default=LEDGER_DIR,
                        help='directory holding sources.csv and manifest.csv')
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='ledger directory to write the tables to (data/jetp to '
                             'rewrite the committed record)')
    parser.add_argument('--documents-root', type=Path,
                        help='snapshot store to read languages from (data/jetp/documents)')
    args = parser.parse_args(argv)
    sources = _read(args.ledger_dir / 'sources.csv')
    manifest = _read(args.ledger_dir / 'manifest.csv')
    languages = detect_languages(manifest, args.documents_root) if args.documents_root else {}
    schema = load_schema()
    for table, rows in reconstruct(sources, manifest, languages).items():
        for path in write_table(args.output_dir, table, rows, schema=schema):
            log.info('%s: %d rows', path, len(rows))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
