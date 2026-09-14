# Frozen editions

No public edition is created by this scaffold. Tickets 0726 and 0728 implement
release generation and validation using [the storage contract](../../../docs/jetp-storage.md).

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
