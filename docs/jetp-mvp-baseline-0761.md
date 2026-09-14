# Recoverable MVP baseline — ticket 0761

The accepted website is frozen in
[`data/jetp/releases/mvp-baseline-0761.zip`](../data/jetp/releases/mvp-baseline-0761.zip).
This is an internal migration baseline, not a published edition or deployment.
The archive preserves the matching HTML, JavaScript, CSS, six JSON downloads,
small corpus inputs and an exact-byte manifest. Restoration needs neither the
source-document store nor Git, DVC or a network connection.

The accepted output checkout is `9568989284688e8acbc99db6bc863076d609c150`.
Its embedded exporter input revision is
`e35988a7065c628dc75dddde4df18d6658701b40`; the input bytes recorded by that
exporter still match the accepted checkout. Both identities are retained.
Capture reads the existing files without invoking the exporter. The JSON
[inspection report](jetp-mvp-baseline-0761.json) records the archive hash, sizes,
input/output hashes, CSV headers and counts. The archive's `manifest.json` also
retains every row locator, candidate identifier, duplicate row/key, 400 routes,
six downloads and source-recovery status. Historical build inputs reference
identical archived corpus bytes; differing historical bytes get their own entry.

Freeze requires a fresh destination: existing files, symlinks (including dangling
ones) and hardlinks are rejected before capture. Publication never replaces an
entry that appears while the archive is being built or validated. Deliberate
recapture therefore uses a new filename; candidate archives retain their explicit
replacement behavior.

All 16 CSV registries are inventoried, including failed searches, coverage,
country observations and Vietnam pilot tables. A repeated identifier is recorded,
not deduplicated or interpreted as another asset. Source-document hashes and
recovery locations are recorded separately from website restoration; raw source
documents are not embedded in this compact bundle. Unavailable source bytes stay
explicit gaps and no remote-recovery success is inferred from a DVC pointer.
Of 307 source records, all 266 with collected hashes were verified: 228 from the
working tree and 38 from the local DVC cache. Those 38 records retain their
missing-working-tree status and the exact cache-object recovery path. The pinned
DVC directory index and cached objects were authenticated before verifying each
source SHA-256. The other 41 records have no collected hash. No remote fetch or
source restoration was performed.

The accepted ZAF download is **508002 bytes**, leaving **3998 bytes** below the
repository's **512000-byte** file constraint. The baseline does not split or
regenerate that download. Future compatibility/chunking changes belong to the
later publication ticket.

## Restore and preview

From a checkout with the project environment installed:

```bash
export PYTHONPATH=scripts:libs/openalex-corpus/src
uv run python scripts/jetp/build_observatory_bundle.py --mode restore \
  --input data/jetp/releases/mvp-baseline-0761.zip --output /tmp/jetp-restored
uv run python -m http.server 8765 --bind 127.0.0.1 --directory /tmp/jetp-restored
```

The destination must not exist. Restoration validates every archived payload
before creating the complete site directory. Serve `/tmp/jetp-restored` directly;
no build is needed. With only the ZIP and Python's standard library available,
`python -m zipfile -e BUNDLE.zip NEW_DIRECTORY` also extracts a `site/` directory
that can be served; use the project restoration command when hash verification
is required.

## Build and inspect a candidate

Candidate construction is explicit and separate from the existing legacy Make
writer. These commands do not invoke `make jetp-observatory`, regenerate canonical
registries, transfer ownership, or publish anything:

```bash
export PYTHONPATH=scripts:libs/openalex-corpus/src
uv run python scripts/jetp/build_observatory_bundle.py --mode candidate \
  --input data/jetp/releases/mvp-baseline-0761.zip --output /tmp/jetp-candidate.zip
uv run python scripts/jetp/build_observatory_bundle.py --mode diff \
  --input data/jetp/releases/mvp-baseline-0761.zip /tmp/jetp-candidate.zip \
  --output /tmp/jetp-diff.json
uv run python scripts/jetp/build_observatory_bundle.py --mode restore \
  --input /tmp/jetp-candidate.zip --output /tmp/jetp-candidate-site
```

All six candidate views are built in a temporary directory. The single complete
archive replaces its candidate destination atomically after validation. A failed
build leaves the accepted site, baseline archive and any previous candidate
archive intact. Candidate output cannot be the accepted archive or a path inside
the canonical site, corpus registries, configuration or exporter inputs, including
symlink and hardlink aliases. Difference reports protect both compared archives
and canonical inputs, and replace their destination only after the complete
report is written. Restore does not overwrite an existing
site; publication switching is outside this ticket.

The difference report compares rendered JSON values and asset bytes, and lists
route additions/removals. Route and download declarations must match the verified
payloads. Boolean, integer and floating-point values remain distinct, including
`true` versus `1` and `1` versus `1.0`, even inside lists or objects.
Only the named build-provenance fields are treated as
metadata. Scientific fields, dates, amounts, source targets, wording and unknown
changes remain `unexplained`. To record an intentional scientific change, pass
`--intentional decisions.json` with an exact reported path as the key and
`source`, `reviewer`, and `rationale` strings as its value. This records supplied
review evidence; the tool does not grant approval. For example:

```json
{
  "site/data/ZAF.json/country/headline": {
    "source": "official-report, page 4",
    "reviewer": "named reviewer",
    "rationale": "Corrected reported allocation; not a payment"
  }
}
```

The frozen input inventories remain available for later table migration. This
report covers the website comparison, not an automatic scientific reconciliation
of unpublished corpus rows.

## Validation evidence

The red fixture is commit `b4948966`,
`tests/test_jetp_observatory_bundle.py::test_interrupted_candidate_preserves_accepted_and_restores_offline`.
It interrupts after the first output, compares the complete canonical site and
archive bytes, then restores while subprocess/network entry points are forbidden.
The fast semantic red fixture is `b38de840`. Additional tests check tampered
archive rejection, duplicate-row preservation and positive controls for all three
difference categories.

The existing Chromium exercise, `tests/browser/jetp_observatory.py`, passed against
both restored accepted and candidate sites. It verifies country/project navigation,
filters, 97 historical records, all six complete JSON downloads and mobile layout,
with external requests blocked. The first candidate has no scientific differences
and no route changes; its only differences are two Git revision metadata fields.
