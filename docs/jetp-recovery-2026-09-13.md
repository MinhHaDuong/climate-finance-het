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


## Resumed Senegal pass

The next pass adds 22 source routes and 25 manifest observations, including
three retries. Fifteen new documents were collected; ten attempts failed or
were blocked/missing/invalid. The manifest now contains 253 observations and
the canonical pool 210 documents. DVC pushed 16 files (15 objects and the updated
directory). All 210 document objects and the unchanged recovery archive were
read back from the remote and verified by MD5 and SHA-256. Both event schemas
and every collected manifest hash/byte count passed validation.

## Deeper Senegal investigation

The case-analysis pass adds nine collected sources, bringing the canonical pool
to 219 documents (227,940,519 bytes) and the manifest to 262 observations.
DVC directory hash: `26b95713c59f9c4cd22456fe83edef89.dir`. All 219 objects
and the original recovery archive were read back from the padme remote and
verified by MD5 and SHA-256. The financial and physical event tables are
unchanged: new possible identity matches do not create financing milestones.
See `docs/jetp-senegal-case-analysis-2026-09-13.md`.

## Pre-merge review corrections

The subsequent merge review corrected 14 South African financial observations
from approved to announced because their source supplied physical progress
without a signing date or explicit approval. Original amounts and physical
status wording remain preserved. Senegal regeneration now retains reviewed
identity links for unchanged source rows and verifies PDF hashes before parsing.
These corrections leave the 219-document DVC checkpoint unchanged.

## Smaller-model scout checkpoint

The bounded trial adds nine archived documents and one failed retrieval: 270
registered sources, 272 manifest observations and 228 unique documents. The
new documents directory is `d701d514d7fd28f700025dead4a67c6e.dir`
(250,861,262 bytes). All 228 remote document objects and the recovery archive
were read back and checked by MD5 and SHA-256 against local bytes. Every
collected manifest entry and both event schemas validate. One PUELEC component
observation is added; financial events are unchanged. See the
[trial report](jetp-senegal-scout-trial-2026-09-13.md).


## Managed-rounds checkpoint

Rounds 2–4 add 18 registered sources, 19 retrieval observations and 17 unique
archived objects: totals are 288 sources, 291 manifest observations and 245
document objects. The documents directory is
`4dfa34045276bdf14bacc9a002f36178.dir` (256,641,141 bytes).
All 245 remote document objects and the original recovery archive were read
back and verified by MD5 and SHA-256. Every collected manifest observation and
both event schemas validate. Six historical ANER WARC captures additionally
pass their embedded payload-digest checks; original URLs and byte ranges are
preserved in the [capture appendix](jetp-senegal-archive-captures-2026-09-13.md).
Financial and implementation tables are unchanged from the scout checkpoint.
The [managed-rounds report](jetp-senegal-managed-rounds-2026-09-13.md) records
the BOAD approval and procurement discoveries, their attribution limits, and
why exact-identity coverage remains 20 collected / 20 central-only / 3 blocked.


## Document-led checkpoint

The follow-up adds 13 source records, 16 retrieval observations and 12 document
objects: totals are 301 sources, 307 observations and 257 objects. The documents
directory is `d614b74fc598c74dda6fae0dca4f0c1e.dir` (279,613,906 bytes).
All 257 objects were read back from the existing local padme archive and verified
by MD5 and SHA-256; the unchanged recovery archive also passed read-only
verification. This pass copied only public document objects and did not push
the recovery archive. Every collected manifest entry and both event schemas
validate. Financial and implementation tables are byte-identical to the preceding
checkpoint. ANER's final PSD supplies one additional direct identity, making
coverage21 collected /19 central-only /3 blocked. See the
[document-led report](jetp-senegal-document-followup-2026-09-13.md).
