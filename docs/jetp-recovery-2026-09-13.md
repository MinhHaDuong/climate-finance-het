# JETP recovery on padme, 13 September 2026

The recovery resumed `t0720-ledger-jetp-senegal` at
`4859aa65ac00f68f08a5949c3e5eec9b36788852`. A fresh fetch confirmed that
this commit includes current main and the South Africa, Indonesia and Viet Nam
country branches. No country PR was open at recovery time. The primary
checkout's untracked `data/book/` was left untouched.

## Archive and reconciliation

The downloaded `jetp-recovery-2026-09-13.tar.gz` is 209,673,532 bytes.
Its SHA-256 matches the handoff:
`8db2ac1ec262365bf894bca422e50a8b1119e164dfa507845d53bdf76822d45b`.
After extraction into an empty directory, every one of the 275 entries in
`SHA256SUMS` passed verification.

`README.txt` and `RECOVERY.json` were read before restoration. The latter
identifies the directory called `t0718-ledger-jetp-indonesie` as a Senegal
checkout and records its earlier HEAD as `2259ac29847c73773c2f84e3b96e3c111f0aac04`.
All its recovered JETP CSVs nevertheless match the saved Git checkpoint
byte for byte. The older recovered canonical CSV rows are subsets of that
checkpoint; no recovered-only observations required appending. The Git
registries were therefore retained unchanged. Separate original manifests,
pilot material, extracts and loose downloads remain in the complete archive.

The canonical manifest has 198 observations referring to 167 distinct document
hashes. Every object was located by SHA-256 across the entire extracted archive,
restored to its manifest path and verified against both hash and byte count.
The resulting document pool contains 177,249,176 bytes. Restoration used content
identity, not checkout directory names.

## Durable storage verification

Two DVC outputs preserve the recovered state:

- `data/jetp/documents.dvc`: the 167 canonical immutable document objects;
- `data/jetp/recovery.dvc`: the complete original archive, including material
  outside the canonical document pool and all original manifests.

On padme the `padme` remote resolves through `.dvc/config.local` to
`/data/projets/dvc/oeconomia-climate-finance`. Both outputs were added and
pushed before new collection. DVC reported 170 files pushed and cache/remote
in sync. Both remote directory objects were then read directly, their MD5
identities verified, and every referenced remote file was checked against its
MD5 and the SHA-256 of the corresponding restored local file. All 168 files
passed. This establishes preservation of document bytes beyond a Git push or
local `dvc add`.

To recover on another checkout, configure access to the `padme` remote and run
`dvc pull data/jetp/documents.dvc data/jetp/recovery.dvc`. The original
archive's `SHA256SUMS` can then verify its extracted contents independently.


## Senegal follow-up checkpoint

After the initial recovery backup, the Senegal review added 30 source
observations: 28 collected documents, one missing brochure and one failed
ASER request. The canonical manifest now has 228 observations and 195 distinct
document objects. The updated DVC directory and its 28 new objects were pushed
(29 remote files), and all 195 documents plus the original archive were read
back from the remote and verified by MD5 and SHA-256. All manifest byte counts
and hashes and both event schemas were checked. The preserved recovery archive
is unchanged.
