# Vietnam inventory and legacy-position candidate

Ticket 0764 stages the complete selected English RMP inventories and preserves
every Vietnam legacy row. Publication and write ownership remain **legacy**.
The artifact is `country-migration/1`, an unadmitted staging contract, not an
admitted `jetp-core-v1` graph or a reconciled financial account.

## Reproduction and recovery

```sh
UV_NO_SYNC=1 make data
UV_NO_SYNC=1 PYTHONPATH=scripts:libs/openalex-corpus/src uv run python \
  scripts/jetp/build_vnm_positions.py --input . \
  --output data/jetp/releases/vnm-migration-0764.json
```

The optional `--source-root CHECKOUT` reads already recovered source PDFs from
another checkout. It performs no source refresh. The importer selects exactly
the English acquisition at `2026-09-11T20:39:00Z`, not the latest acquisition.
The subsequent unchanged retrieval and all earlier pilot searches survive.

The 2,554,708-byte JSON is DVC-managed through
`data/jetp/releases/vnm-migration-0764.json.dvc`, object
`180429d7c6b882fdc2871b9fa6fbf003`, SHA-256
`ef7538d2af534d31877634bd42f28c5fae1c20b192e6647fc030146a7492eb34`.
It is not compressed into Git. Recovery was performed from the local DVC cache:
after removing the generated candidate, `dvc checkout` restored byte-identical
content. Both principal PDF hashes were independently checked after recovery:

| Source | SHA-256 |
|---|---|
| English RMP | `b145af2e7f4a441dc87d7ec2d99a29e1e6d7b265406d398dd64013dd4560733c` |
| Vietnamese RMP | `d1a306394a19acd576b39e34d0ba8cf7a947fc1cefa07550f35217a943927959` |

The candidate records every input CSV's hash/header/count, source pointer hash,
parser and importer hashes, policy hash, pdfplumber version, exact acquisition,
new edition-snapshot association, extraction output hash and every row locator.
Its extraction recipe was recorded on 14 September 2026. Historical admission
remains unknown; this is not a claim that these assertions were admitted in 2023
or that the September extraction repairs the August pilot's evidence gaps.
`validate_evidence_tuple` checks the exact byte/edition/extraction/locator tuple.

## Selected population and exclusions

| Inventory | Physical PDF pages | Printed pages | Rows |
|---|---|---|---:|
| Annex I.1: masterplan/programme investment proposals | 155–158 | 139–142 | 37 |
| Annex I.2: partner proposals outside those masterplans/programmes | 159–174 | 143–158 | 181 |
| Annex II: technical-assistance projects/task groups | 175–186 | 159–170 | 61 |

These are **279 source rows**, not 279 newly identified projects. Each has an
inventory-position ID, complete decoded source cells and wrapped row wording,
physical and printed page locators, ordinal, classification and disposition.
The extractor uses ruled-cell geometry in the rotated PDF, so “80 generator
cars” inside I.1 row 36 cannot become an invented ordinal. PDF character decoding
and whitespace reconstruction are not a facsimile; the saved PDF is authoritative.
The pinned extractor requires pdfplumber 0.11.9 and rejects other source bytes,
missing/duplicate ordinals and unsupported continuation structure.

The initial classification is conservative: 25 named proposals, 73 programme or
task-group rows, and 181 rows with entity type unresolved. These categories are
not accepted entity classifications. All 279 retain unresolved identity
membership; no new public entity IDs are minted. No exact mapping to one of the
three existing named Vietnam records was established in these selected rows.
The reusable crosswalk supports explicit one-to-many mappings, requiring the
exact extracted wording, existing target IDs and a rationale.

The policy file records explicit exclusions with full physical/printed ranges:
body Tables 5, 8–10, 12–14; Annex III policy actions; Annex IV's ten concept
notes; Annex V political declaration/end matter. These mix alternatives,
priorities, conceptual summaries and finance frameworks and are not silently
added to the selected population. The saved Vietnamese counterpart is retained
without invented English/Vietnamese row or edition equivalence.

Identity decisions preserve two contrary cases: I.1 row 22, **KN Tri An Floating
Solar Farm**, is not the Tri An hydropower expansion; I.2 row 43's **BWID DPPA
solar** proposal is not the Binh Duong/Dong Nai transmission project. I.2 row 1's
“3-4 suitable coal-fired power plants” remains one unnamed programme description.
It creates neither four named plants nor financing events. Planned commissioning
and programme periods remain source wording, never inferred transition dates.

## Legacy reconciliation and writer-transfer report

| Legacy table | Vietnam rows | Disposition |
|---|---:|---|
| projects / project-coverage | 24 / 24 | IDs, routes, count-slot identity uncertainty and coverage retained |
| project-source-links | 7 | Discovery links retained, not assertion-level evidence repairs |
| sources / manifest | 34 / 20 | Source metadata and all attempts retained |
| authority-coverage / dry-searches | 2 / 4 | Coverage and failed/partial search history retained |
| vnm-pilot-manifest | 66 | Original acquisition fields retained |
| vnm-pilot-observations | 46 | Original cells plus explicit semantic dispositions |
| events / implementation-events / event-timing | 0 / 0 / 0 | Empty Vietnam slices remain empty |
| plan-projects / source-claims / news-leads | 0 / 0 / 0 | Empty Vietnam slices remain empty |

All **227 legacy rows** retain their shared source-crosswalk row ID, original
table and row number, original fields, prior owner and pending review state.
The 46 pilot observations receive explicit policy classifications: 15 envelopes,
nine proposals, seven event assertions pending evidence, five financial
positions, four portfolio counts, three cumulative positions, one programme
position, one reported absence and one withdrawal assertion pending evidence.
Original status/date/amount/currency, verification verdicts and contradictory
observations remain intact. None is eligible for a reconstructed account.

The 53 legacy evidence projections remain unresolved. In particular, 54 pilot
“collected” acquisitions lack recoverable declared storage paths, pilot source
066's earlier failure to locate the RMP remains history, and Decision
1929/QĐ-BCT's partial full-text search remains partial. Recovery here proves
availability of the principal saved PDFs, not the missing pilot originals.

The July 2025 portfolio remains seven initial plus 17 newly screened proposals,
24 in total; it is distinct from the later 50-project portfolio. USD 5.52 billion
belongs to the 17 proposals, not the USD 7.04 billion total portfolio. All 21
unnamed slots retain their IDs; inventory membership cannot fill those slots.
Cancellation, withdrawal and the reported absence of disbursement are retained
without invented payments, reversals or a complete observation history.

**Transfer decision: none.** The existing CSVs remain the only writable domain
authority. Candidates are regenerated from pinned inputs and await review;
existing publication/release tickets continue to own publication. Acceptance of
any later bounded combination must reconcile intervening legacy edits, resolve
its dependencies and transfer its writer once. This ticket does not authorize
a whole-country switch or an aggregate account.

## Candidate differences and validation

The artifact's `mvp_views` contains all six existing compatibility payloads.
The inventory sidecar adds 279 observations and 46 classified legacy candidates;
public project IDs, counts, financial events and website semantics change by zero.
The three other country views remain unchanged. No renderer changes or live
files are required to inspect or download the candidate JSON.

The writer validates before atomic replacement, protects accepted site/input
files and every release descriptor/pointer, rejects final-file aliases before resolution, and replaces only
a structurally complete previous Vietnam candidate; identifying markers alone
do not permit replacement. A failing build preserves its preceding
candidate. Tests exercise direct, symlink and hardlink targets and interruption.

First RED commits after rebasing are `85db49e9` (missing page, explicit mapping,
unnamed count) and `4186e0b7` (complete PDF extraction). Implementation began in
`d36835b5`. Discriminating tests include:

- `test_official_rows_without_pages_exact_mapping_and_unnamed_count`
- `test_tri_an_solar_does_not_join_hydropower_by_place`
- `test_wrapped_count_is_not_an_ordinal_or_named_asset`
- `test_saved_rmp_has_all_279_rows_without_solar_hydro_identity_join`
- `test_real_candidate_covers_inventory_legacy_and_all_country_views`
- `test_writer_preserves_accepted_files_and_aliases`
- `test_interruption_preserves_previous_candidate`

The real candidate rerun is byte-identical. The 16-file primary-workspace
preservation snapshot still matches, including unrelated `data/book/` files and
all accepted site assets. Local gate and browser results accompany the PR.

The round-2 regressions `test_recognized_candidate_alias_is_rejected_before_build`
and `test_malformed_candidate_markers_are_not_replacement_permission` exercise
recognized symlink/hardlink targets and malformed marker/record/view shapes before
builder entry. Replacement uses the shared release-safety guard from ticket 0771;
legitimate candidate reruns through symlinked parent directories remain allowed.

Final artifact generation used input/code Git revision
`9deed983b6cb46f70f9da03839e20681c3c7dd09`. Reproduce at that revision for
byte-identical Git provenance. Relative to the earlier candidate, only the
overview’s `input_git_sha` and `build_base_git_sha` change within MVP payloads;
all scientific fields and the four country payloads remain identical.
