"""panel-rule-v1: alignment, agreement and the sealed split (ticket 1895).

Rows are the members' proposals whose locators resolved (``_panel_layer``).
Two rows of different members are one item when their spans overlap on the
same page and their classifications match; two quotes of one sentence by
different spans therefore align as one item. Pairs are joined greedily by
decreasing overlap (intersection over union), and an item never holds two
rows of one member.

Within an item, rows agree when their verbatim fields are equal after
whitespace and Unicode normalisation, an empty field equal to an absent one;
a difference of span only is agreement, and the shortest agreeing span is
kept. The item's stance comes from the largest agreeing group: 3 members,
confidence high; 2, medium; otherwise the item is excluded from the
reference and counted. A change of rule is a new rule version and a new
reference set version.

The split assigns each kept item to the tuning or the held-out part by a
recorded seed, stratified by country, language and statement shape.
"""

import hashlib
import random
from collections import defaultdict

from jetp._panel_layer import normalise

RULE = 'panel-rule-v1'


def _overlap(a, b):
    if a['page'] != b['page']:
        return 0.0
    inter = min(a['end'], b['end']) - max(a['start'], b['start'])
    if inter <= 0:
        return 0.0
    union = max(a['end'], b['end']) - min(a['start'], b['start'])
    return inter / union


def field_key(row, fields):
    return tuple(normalise(row['fields'].get(name) or '') for name in fields)


def dedupe(rows, fields):
    """One row per member, span, classification and field values."""
    seen, kept = set(), []
    for row in rows:
        key = (row['member'], row['page'], row['start'], row['end'],
               row['classification'], field_key(row, fields))
        if key not in seen:
            seen.add(key)
            kept.append(row)
    return kept


def align(rows):
    """Items: lists of rows, at most one per member, from one document."""
    parent = list(range(len(rows)))
    members = [{rows[i]['member']} for i in range(len(rows))]

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    pairs = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            if a['member'] == b['member'] or a['classification'] != b['classification']:
                continue
            score = _overlap(a, b)
            if score > 0:
                pairs.append((-score, i, j))
    for _, i, j in sorted(pairs):
        ri, rj = find(i), find(j)
        if ri == rj or members[ri] & members[rj]:
            continue
        parent[rj] = ri
        members[ri] |= members[rj]
    groups = defaultdict(list)
    for i in range(len(rows)):
        groups[find(i)].append(rows[i])
    return sorted(groups.values(),
                  key=lambda g: min((r['page'], r['start']) for r in g))


def stance(item, fields, panel_size=3):
    """``(confidence, kept_row, agreeing_members)``; confidence None = excluded."""
    groups = defaultdict(list)
    for row in item:
        groups[field_key(row, fields)].append(row)
    best = max(groups.values(), key=lambda g: (len(g), -min(r['end'] - r['start'] for r in g)))
    agreeing = sorted(r['member'] for r in best)
    kept = min(best, key=lambda r: (r['end'] - r['start'], r['member']))
    if len(best) >= panel_size:
        return 'high', kept, agreeing
    if len(best) == panel_size - 1 and panel_size >= 3:
        return 'medium', kept, agreeing
    return None, kept, agreeing


def split(items, seed, heldout_share):
    """``{line_id: 'heldout' | 'tuning'}``, stratified by country, language, shape."""
    strata = defaultdict(list)
    for item in items:
        strata[(item['country'], item['language'], item['shape'])].append(item['line_id'])
    rng = random.Random(seed)
    part = {}
    for key in sorted(strata):
        ids = sorted(strata[key])
        rng.shuffle(ids)
        cut = round(len(ids) * heldout_share)
        for n, line_id in enumerate(ids):
            part[line_id] = 'heldout' if n < cut else 'tuning'
    return part


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b''):
            digest.update(chunk)
    return digest.hexdigest()
