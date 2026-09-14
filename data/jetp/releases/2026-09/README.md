# JETP observatory 2026-09 — prepared release

`jetp-observatory-2026-09.zip` is the frozen, offline package prepared from
input commit `fba8e63ff6a8ad44076cd054871e60d99db6bd3f`. `release.json` is its
byte inventory and policy descriptor; `validation.json` records the archive
hash and acceptance checks.

The package covers South Africa, Indonesia, Viet Nam and Senegal. It includes
the static site, country downloads, provenance sidecar, dictionary, coverage
report and reuse terms. It deliberately excludes raw source documents and needs
no Git, DVC remote, database or network connection to render after extraction.

The release is **prepared**, not externally deposited or hosted. Its
`publication_date` is therefore `null`; `release_prepared_date` and the
observation cutoff are separate date roles. A later public deposit must preserve
these bytes and use the recorded SHA-256 rather than replacing this edition.
