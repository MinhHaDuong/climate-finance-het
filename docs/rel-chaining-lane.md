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
  `aliases`, `restore-cache`, `identities`).
- `scripts/_rel_chaining_reuse.py`: offline reuse of completed directions from an
  archived round (split for the module size cap; it imports `_rel_chaining`, not the reverse).
- `tests/test_rel_citation_chaining.py`: 44 collected tests (26 test functions,
  some parametrized). One is an `integration` import check run in a subprocess;
  the rest are offline, with no network.

The 1654 branch's screening and label-rekey code (Stage 1 batch parser, screening
transport, label migration) does not land; nothing on the collector path used it.

The round-one budget ledger (`data/rel_chaining/2026-10-08/budget.sqlite`) is
frozen. A new round needs a new authorization and a new ledger.

Known limits, no code change here:

- Cost: when OpenAlex reports credits rather than USD, `reported_oa_cost` converts
  them at `meta.cost * 0.0001` USD per credit. That rate is an assumption, not a
  published price.
- Cursor restart: a query stopped on a repeated cursor or a short count stays
  incomplete and resumes from its stored cursor. There is no path to restart it
  from the first page.
- The manifest's `ticket` is hard-coded to `"1654"`.

## Round one (2026-10-08), from the archive

Two deliveries, both passing `scripts/qa_rel_intake.py`:

- `data/rel_intake/t1654-citations/2026-10-08` (titled records) was produced by
  `export_delivery` in this collector at commit 9bbdfe2d. That is the `head` in
  `data/rel_chaining/2026-10-08/producer/checkpoint.json` and the manifest's
  producer commit.
- `2026-10-09` (177 titleless records with exact-DOI metadata) was not produced by
  this code: `export_delivery` excludes blank titles. Its producer is the one-off
  script
  `data/rel_chaining/2026-10-08/operations/titleless177-exact-doi-metadata/prepare-delivery.py`
  (sha256 `402b3b244ecacf6fdcd11112a0ddc0754798212bca774cbe2f5c1bf8975eb4dd`, the
  manifest's `producer.source_sha256`; commit 4ae045da). It stays in the archive and does not land.

| Quantity | Count | Source |
|---|---|---|
| Seeds | 19,956 | checkpoint `seeds` |
| Query units completed | backward 183/183, forward 183/183, references 1,388/1,388, archive 48/48 | checkpoint `queries` |
| Edges, backward (references) | 284,522 (138,733 distinct works) | `edges.csv` |
| Edges, forward (citations) | 255,428 (152,313 distinct works) | `edges.csv` |
| Distinct edge candidates | 272,964 = 138,733 + 152,313 - 18,082 found both ways | derived |
| Records delivered | 270,647 titled (incl. 10,080 seed metadata updates) | manifest |
| Excluded | 119,242 duplicate in lane, 235 not retrievable (titleless) | manifest |
| Unresolved | 14,171 = 12,434 `reference` + 1,657 `seed` + 80 `seed_metadata` | checkpoint `unresolved`; the manifest's `incomplete` list has the same 14,171 entries |

The 235 titleless exclusions and the 177 titleless records of the 2026-10-09
delivery are different counts:

- The 1654 branch checkpoint doc splits the 235 into 199 citation candidates and
  36 seed metadata records.
- The 2026-10-09 delivery covers the frozen roster of 177 titleless candidates
  that matched exactly by DOI (`titleless-roster.json`, 177 entries).
- The other 22 candidates (199 - 177, derived) and the 36 seed records were not
  delivered.
- The 199/36 split is quoted from that doc, not re-measured here.

The 10,080 seed metadata updates are the seeds' own works, returned by the
backward, references and archive queries that read their reference lists. This
is inferred from `export_delivery` and was not traced record by record.
`export_delivery` attributes each work to its first citation query. `put_work` is
first-wins (`INSERT OR IGNORE`), so each record carries the first payload
retrieved. These records come from the seed queries themselves, not from a later
refresh of the `works` table.

The unresolved counts sum three kinds. Round one ran before the
`reference_evidence` kind existed, so there are no rows of that kind. Under the
landed code, a forward work without a usable `referenced_works` field gets two
unresolved rows: one `reference_evidence` and one `edge`. A future round's
unresolved total is therefore not a count of works.

Merge on dedup version 1 (`merge_report.json`, 2026-10-09):

- The 2026-10-08 delivery holds 270,306 works (270,647 - 341 duplicates within the
  delivery). Of these, 18,221 match the catalogue, 44,020 match another lane only,
  and 208,065 are new to the pool (18,221 + 44,020 + 208,065 = 270,306).
- The 2026-10-09 delivery adds 177, for 208,242 gross.
- Pool: 597,494 works against a baseline of 389,291, a net 208,203.

The 39-work gap between gross and net was settled read-only on the archived pools
(`data/rel_pool/pool.csv` and `data/rel_chaining/2026-10-08/baseline/pool.csv`,
using the pool's own `work_key`):

- 208,242 merged works have the chaining lane as their only source and no
  catalogue row. The gross figure is therefore real: every one of these works is new.
- The 389,291 baseline works now sit in 389,252 merged works. Chaining records
  carried identifiers that joined formerly separate baseline works, which absorbed
  39 of them: 208,242 - 39 = 208,203.
- Keys also moved. 211,753 merged keys are absent from the baseline and 3,550
  baseline keys are gone (211,753 - 3,550 = 208,203):
  - 3,392 gone keys were renamed to a new key, for example when a chaining record
    supplied an OpenAlex id that now keys the work;
  - 145 were merged into a surviving baseline key;
  - 13 had members split across two merged works.
  Net is not "gross minus matches".

Mapping: `docs/rel-chaining-key-mapping-v1.csv`, sha256
`9e291cf5b7219344a2351459cbb4124d80076347c31523b2b64a88f42be8df1d`.

- One row per gone baseline key, 3,550 rows: 3,392 `renamed` + 145 `merged` +
  13 `split` = 3,550.
- Columns: `old_work_key`, `disposition`, `new_work_keys` (`;`-separated for
  `split`), `old_member_record_ids`, `old_sources` and `members_not_found` (empty
  in every row).
- It was derived read-only from the two archived pools by following each
  baseline member record to the merged work that holds it.

**Labels keyed on version-1 work keys no longer join for these 3,550 works until
this mapping is applied.**

New works are not admissible works: none has been scored.
