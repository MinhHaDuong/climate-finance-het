# Frozen editions

No public edition is created by this scaffold. Tickets 0726 and 0728 implement
release generation and validation using [the storage contract](../../../docs/jetp-ledger-storage.md).

Each future `<edition_id>/release.json` records:

- edition ID, previous edition, and superseded edition when correcting;
- observation cutoff, publication date and named release reviewer;
- full input Git SHA (an earlier commit), schema and aggregation-policy versions;
- DVC pointer path and pinned object hash from that input commit;
- every public payload's relative path, byte size, SHA-256 and immutable URL;
- dataset reuse terms, exclusions from raw-source redistribution and deposit ID;
- validation/coverage report references and the corresponding editorial note.

A release descriptor pins written bytes; a branch name, a moving URL or a DVC
pointer alone does not identify the public dataset. Public downloads include the
CSV/JSON, dictionary, prose and provenance needed for website reproduction without
access to the internal DVC remote. Large downloadable payloads live in a versioned
release/deposit archive, not as repeated copies of all source PDFs in Git.

The input commit cannot contain its own SHA. Commit inputs first, build and verify
the package, then commit the descriptor. Keep published descriptors and payloads
immutable; issue a new correction edition instead of changing the old files.

## Internal migration baseline

`mvp-baseline-0761.zip` freezes the accepted complete static MVP and small inputs
for offline recovery before migration. It is not a public edition. Its capture
revision, embedded input revision, source-recovery limitations and candidate
workflow are documented in [the recovery note](../../../docs/jetp-mvp-baseline-0761.md).

## Restoration

When a publication fails, restore the last accepted complete package; never
replace a few live files mid-build, and never re-enable a retired writer or
reverse a migration to recover the site. Newer justification and its
ownership are kept. A restored release shows its real cutoff, and a later
correction is a new release. (Carried from the backend implementation plan of
2026-09-14, deleted by ticket 1701.)

## Release identifiers and pinning

Carried from the storage note of 2026-09-13 (deleted by ticket 1701). A
regular monthly release is `YYYY-MM`; a correction is `YYYY-MM-rN`, starting
at r1, and records what it supersedes; the bytes at a published release URL
are never replaced. The current-release pointer advances only after the
complete release passes validation, so a failed update leaves the last good
release available. A paper pins a release and its input SHA, never a moving
current link; its sample selection and code carry their own version
references beside the release.

