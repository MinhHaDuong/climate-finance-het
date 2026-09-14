# South African register and report migration candidate

Ticket 0765 stages source observations beside the legacy writer. It does not
admit financial events, change canonical CSVs, or publish new website data.
The implementation recipe starts at commit `977096ec`; the artifact records
exact input, policy and parser hashes.

## Reproduction and recovery

```sh
UV_NO_SYNC=1 make data
UV_NO_SYNC=1 PYTHONPATH=scripts:libs/openalex-corpus/src uv run python \
  scripts/jetp/build_zaf_positions.py --input . \
  --output data/jetp/releases/zaf-migration-0765.json
```

The optional `--source-root CHECKOUT` reads saved source bytes from another
checkout. No retrieval is performed. The 5,728,079-byte JSON is a separate DVC
sidecar, object `45ed9fa8f6d35cbe5565b2b30dc365b4`, SHA-256
`fc0e483facf3ff93dc25684112f77e6a8b93f602133a07c3953bddadbceabc59`.
Retrieve it with `uv run dvc pull data/jetp/releases/zaf-migration-0765.json.dvc`.
An independent repository with an empty cache recovered identical candidate
bytes and the pinned document directory from the local project archive.
Both selected source hashes were checked after recovery:

| Source | Acquisition (UTC) | SHA-256 |
|---|---|---|
| Q1 2026 investment register | 2026-09-12 05:26:22 | `5b5d6442da4e9e57b3c83b7bfc04a19135b2c5bf750c2480685d9d084dc093f4` |
| Q1 2026 quarterly report | 2026-09-12 05:33:00 | `1b62a65fd70c70b0234379fcc4fcda064e9175fc9aee21a37c97b283e1b8dc13` |

## Inventory boundary and source meaning

The complete selected population is 257 register records and 82 data rows from
report Tables 1–11 (physical pages 4 and 12–21). Every row retains its original
fields or table headers/cells, locator, source role, perimeter and validated
acquisition/extraction/edition evidence tuple. Table extraction requires the
pinned source hashes, parser version and complete table dimensions.
Tables 12–14 are explicitly excluded from this financial-position inventory:
outcome indicators, definitions, and a nonrepresentative 24-project indicator
snapshot. Other figures, prose and historical editions remain source history.
The candidate retains the report page text alongside extracted cells.

Register agreement/start/end labels remain source fields; they do not establish
transaction dates. The report cutoff of 31 March 2026 is not a proven publication
date or historical admission date. New extraction provenance is recorded on
14 September 2026; historical admission remains unknown.

Pledged, allocated, instrument and programme totals retain their labels and
currencies. Reported USD and ZAR columns are not new conversion evidence.
The report's USD 6.12 billion instrument allocation and USD 4.32 billion portfolio
allocation have different perimeters and are not summed or reconciled into a
payment. The register has 128 implementation and 88 completed records; report
Table 5 has 129 and 87, respectively. Both have 257 total records. This source
disagreement remains visible.

No selected real row establishes a payment event. The first regression supplies
a separately evidenced payment on the same project and produces only that
payment candidate, while preserving the register funding position separately.
Even that candidate remains ineligible for an account pending later occurrence
reconciliation and admission.

## Legacy reconciliation and public boundary

All 1,084 exactly country-linked legacy rows receive explicit retained-authority
dispositions: 263 projects, 259 events, 259 timing rows, 79 project-source links,
69 manifest rows, 61 sources, 46 claims, 21 authority-coverage rows, 18 news leads,
and 9 failed-search rows. Original wording, missing evidence and uncertainty
survive. Event timing joins through exact financial or implementation event IDs;
duplicate occurrences remain separate. Unmatched timing rows remain in the
global crosswalk and are not assigned a country from an ID prefix. Vietnam's
227-row legacy slice remains unchanged.

Each of the 257 register records joins its existing project only through the
original register key and matching retained source wording. The six supplementary
legacy projects remain present. Repeated programme names keep distinct IDs;
uncertain identity or component relationships remain unresolved rather than
being collapsed or treated as disjoint funding. Existing references and routes
remain in the unchanged legacy views.

All six MVP payloads equal the legacy reader output, including all four country
views. The South African payload remains 508,002 bytes, below 512,000. The large
detailed sidecar is not loaded by the website. Publication and writer ownership
remain legacy. The 16 original workspace hashes and frozen baseline ZIP hash
`dbdc45b8f6d5dccce1c378b15a3d92a766f87ad26231751fca7ebf963716f574`
were verified unchanged.

Writer tests reject accepted metadata, malformed predecessor objects, and final
file symlink/hardlink aliases before building. Valid candidate reruns succeed;
a builder interruption preserves the previous bytes. Focused evidence includes
`test_zaf_candidate_reconciles_inventory_legacy_and_unchanged_views`,
`test_interruption_preserves_previous_candidate`, and the register/payment
fixture in `tests/test_jetp_zaf_positions.py`.
