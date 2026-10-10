# REL citation chaining as an intake lane (t1654-citations)

Ticket 2061, child of 1654. Stage S1 of `docs/rel-pipeline-redesign-2026-10-10.md`.

Citation chaining is one more harvesting lane under `docs/rel-intake-contract.md`.
It screens nothing: its records stay unscored until the redesign's scorer exists
(tickets 2060, 2071). The staged screening that the 1654 branch built around it is
retired (author decision of 2026-10-10, ticket 2062) and does not land.

## Code

- `scripts/_rel_chaining.py`: resumable OpenAlex collector. Backward (references)
  and forward (citations) queries per seed, cursor resume, raw page archive, shared
  budget ledger, intake export (`records.csv`, `edges.csv`, `excluded.csv`,
  `registry.csv`, `manifest.json`).
- `scripts/catalog_rel_citation_chaining.py`: CLI (`seeds`, `harvest`, `export`,
  `aliases`, `restore-cache`, `identities`, `rekey`).
- `tests/test_rel_citation_chaining.py`: offline tests; no network.

The round-one budget ledger (`data/rel_chaining/2026-10-08/budget.sqlite`) is
frozen. A new round needs a new authorization and a new ledger.

## Round one (2026-10-08), from the archive

Deliveries `data/rel_intake/t1654-citations/2026-10-08` (titled records) and
`2026-10-09` (177 titleless records with exact-DOI metadata). Both pass
`scripts/qa_rel_intake.py`.

| Quantity | Count | Source |
|---|---|---|
| Seeds | 19,956 | checkpoint `seeds` |
| Query units completed | backward 183/183, forward 183/183, references 1,388/1,388, archive 48/48 | checkpoint `queries` |
| Edges, backward (references) | 284,522 (138,733 distinct works) | `edges.csv` |
| Edges, forward (citations) | 255,428 (152,313 distinct works) | `edges.csv` |
| Distinct edge candidates | 272,964 = 138,733 + 152,313 - 18,082 found both ways | derived |
| Records delivered | 270,647 titled (incl. 10,080 seed metadata updates) | manifest |
| Excluded | 119,242 duplicate in lane, 235 not retrievable (titleless) | manifest |
| Unresolved | 12,434 references, 1,657 seed identities, 80 seed metadata | checkpoint `unresolved` |

Merge on dedup version 1 (`merge_report.json`, 2026-10-09): of the 270,306
works in the 2026-10-08 delivery (270,647 - 341 duplicates within delivery),
18,221 match the catalogue, 44,020 another lane only, and 208,065 are new to
the pool (18,221 + 44,020 + 208,065 = 270,306); the 2026-10-09 delivery adds 177.
Pool: 597,494 works against a baseline of 389,291, a net 208,203. The 39 between
208,242 gross and 208,203 net are not reconciled here. New works are not
admissible works: none has been scored.
