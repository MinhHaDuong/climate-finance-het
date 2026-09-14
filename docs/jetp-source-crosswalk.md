# Source and evidence migration candidate

Ticket 0763 inventories the legacy JETP CSV inputs and produces one compressed
JSON handoff. It does not change their write ownership, admit historical claims,
refresh sources, migrate country observations or select website publication.
The existing MVP compatibility reader remains authoritative.

Run from an isolated checkout with the existing environment and DVC cache:

```sh
UV_NO_SYNC=1 make data
UV_NO_SYNC=1 PYTHONPATH=scripts:libs/openalex-corpus/src uv run python \
  scripts/jetp/build_source_crosswalk.py --input . \
  --output data/jetp/releases/source-crosswalk-0763.json.gz
```

An optional `--source-root CHECKOUT` locates existing source bytes or authenticated
DVC objects without collecting any URL. The output is a single deterministic
artifact: JSON without wall-clock generation timestamps, compressed with a zero
mtime. Its input inventory records file hashes, exact headers and row counts.
Mappings preserve row content and duplicate occurrences; appended retrievals do
not change earlier acquisition IDs. Every input row has a mapping or a retained
owner disposition. Coverage, failed searches, news leads and country observations
remain recoverable with their original fields and meaning.

The `source-crosswalk/1` document is a migration staging contract. It retains
unknown historical admission and source-origin fields explicitly. It is not a
`jetp-core-v1` admitted record graph: that graph additionally requires real
recording metadata, valid typed domain targets and review decisions. A resolved
byte tuple is therefore not an accepted financial assertion. Country migration
and subsequent review supply those requirements at their actual dates.

Evidence resolution requires the exact acquisition, logical edition, source hash,
extraction and locator. Missing historical components remain in the unresolved
report; a source ID or the latest retrieval is never a substitute. Catalogue
metadata does not prove which revision an old acquisition consulted. Matching
bytes share a support group, including mirrors, without asserting independent
confirmation or automatic logical-edition equivalence. Official publisher status
does not establish claim-level primary origin.

The writer validates the candidate before atomic replacement. Canonical inputs,
source bytes, the current static website and frozen ZIP releases are protected.
A failed candidate leaves the preceding candidate artifact and accepted MVP
unchanged. No renderer output changes, so the existing browser remains outside
this ticket's change surface.

## Reconciliation evidence

The committed candidate and its measured inventory are recorded below after the
migration and local gates complete. Unknowns are retained findings, not a claim
that archival evidence has been recovered.

Input Git revision: `687ba6257a23f6677865abd7a3242f61a3e28c3b`.
The pinned CSV hashes and `documents.dvc` hash are in the candidate.
The complete 2,027,014-byte candidate is stored through
`data/jetp/releases/source-crosswalk-0763.json.gz.dvc`, with DVC object
`13f72044595edd3e6ce0ce5368cfa812` and SHA-256
`6c8b244f61b73f5f6935434213bec89537fbd83c9f776a561b157af75f07d007`.
Retrieve only this handoff with `uv run dvc pull
data/jetp/releases/source-crosswalk-0763.json.gz.dvc`; the pointer and checksum
identify the bytes independently of any moving branch. This is an internal
migration artifact, not a public edition.

| Input | Rows | Disposition |
|---|---:|---|
| sources | 301 | Source revisions; historical admission/origin unknown |
| manifest | 307 | Distinct acquisition attempts |
| vnm-pilot-manifest | 66 | Distinct pilot acquisition attempts; snapshot day retained separately |
| events / implementation-events | 380 / 71 | Legacy assertion owners, staged evidence |
| source-claims / project-source-links | 149 / 315 | Legacy claim/link owners, staged evidence |
| plan-projects | 1,628 | Inventory owner retained, staged evidence |
| idn-portfolio / vnm-pilot observations | 46 / 46 | Country-observation owners retained, staged evidence |
| authority-coverage / project-coverage | 64 / 141 | Coverage owners retained |
| dry-searches / news-leads | 109 / 18 | Search and lead owners retained |
| projects / event-timing | 404 / 451 | Existing domain owners retained |

Total: **4,496 rows, 4,496 mappings and 4,496 retained originals** across 16
CSV inputs. The 373 attempts include 266 with verified available material,
54 collected pilot rows without a recoverable declared storage path, 27 blocked
attempts and 26 failed attempts. The 54 pilot gaps are preserved, not resolved by
borrowing a newer acquisition. This inventory does not claim that their original
bytes are globally unavailable.

All 2,635 evidence projections remain explicitly unresolved because their input
rows lack exact acquisition, edition and extraction IDs. Of these, 513 also lack
an exact hash and 46 lack both a source ID and locator. No logical editions or
extractions were invented. These gaps accompany retained originals for the
country migrations and later review; they do not alter the currently accepted
MVP or withdraw its legacy displays.

The shared `_contracts.validate_evidence_tuple` checks acquisition/extraction
hash equality, locator membership and edition snapshot membership in both the
core store and complete migration tuples. Its regression test passes tuples
without admission timestamps; the full core graph still rejects absent recording
metadata. This separates byte integrity from historical admission explicitly.

The first failing fixture was committed as `5deaa178` before implementation.
`test_refresh_keeps_original_bytes_and_distinct_attempts` covers changed bytes,
mirror acquisition, identical retrieval timestamps, a failed attempt and stable
old evidence. Additional fixtures cover duplicate legacy rows, unknown origin,
cross-source mismatch, missing/corrupt bytes, preserved search outcomes,
deterministic compressed writes, input aliases and failed-candidate restoration.

MVP verification ran the existing compatibility, bundle and source-recovery tests
alongside the core/crosswalk fixtures: **147 passed**. This includes all six public
payload views and the existing interruption/restoration checks. A real candidate
rerun produced identical compressed bytes. The frozen baseline archive and all
ten archived static site files remain byte-identical. No new browser exercise
was run: neither the renderer nor its output changed.
