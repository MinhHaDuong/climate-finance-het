# M1b: the frozen document catalogue

The Observatory's Projects page links to the [frozen document catalogue](../deliverables/jetp-observatory/index.html#referents).
It covers exactly the M1a inventories: 257 South African register rows,
1,579 Indonesian appendix rows, 279 Vietnamese RMP rows and 49 Senegalese
submission and quick-win rows. These are four inventories across six document
snapshots, not a comparable population of projects. Membership requires the
configured snapshot, document identifier and the corresponding per-document
fields row. Later prose extracted from those same snapshots is outside M1b.

`make jetp-m1b` explicitly replays the historical release: it validates the ledger through its SQLite DDL and writes the
four country catalogues, their decision tables and
`deliverables/jetp-observatory/data/m1b/manifest.json`. The descriptor is the
M1b release record: it pins consumed input hashes, each output hash, the
ontology rows in force and O v1's `ontology_ref`. The O v1 reference is frozen
in `config/jetp-m1b-release.json`; a different ontology or DDL cannot silently
become another O v1. Reproduce this release using its recorded inputs.
Live Observatory builds run `make jetp-m1b-check` instead, validating the
frozen artifact's file hashes without comparing today's ontology with O v1.
Later ontology decisions therefore leave the historical catalogue available.

The reader can open each accepted identity to inspect its record, deciding
method, deciding agent, confidence and cited document lines. Projects,
assets and agreements come from terminal accepted `line-referents` decisions.
Parties come from terminal accepted `party_in` or `role_in` decisions on the
bounded lines and their accepted preferred-name records. A naming source
may be outside M1a. Parties are counted by distinct party identifier in each
country's documentary scope; their home country remains an attribute of
the party. Publisher-only parties are omitted. Pending `same_as` aliases
do not fold these identifiers.

Terminality is computed over the complete decision table before applying the
bounded scope. An accepted row superseded by a candidate or rejection is
therefore absent from accepted counts. Accepted relations retain their
decision and justification line; line-to-line relations also expose both
endpoint lines. Candidate relations can legitimately lack a justification
line, and that absence is displayed rather than filled in.

The review budget for this milestone is the existing recorded decisions.
The append-only `0833-candidate-reviews.csv` records each retained candidate's
reviewer, date and basis, plus the three candidates outside the bounded scope.
No matching tier is rerun and no candidate is promoted. In particular, the
ten Indonesian tier-2 proposals sharing the generic name
“PLTA Sulbagsel (Kuota) Tersebar” remain pending: a repeated quota label
cannot identify which rows represent the same undertaking. Older candidate
document and party aliases relevant to this scope remain visible too.
Candidates are listed and counted by country and relation, separately from
accepted identities. Lines without an accepted or candidate referent remain
explicitly listed as unresolved; headings and unnamed rows receive no
invented identity. Viet Nam's RMP currently has no accepted identity decision
over these 279 lines, which is shown as zero accepted identities and 279
lines without a referent, not as a count of Vietnamese projects.

The 17 coverage identifiers handed over by ticket 1620 each receive an
explicit outcome in `0833-coverage-reviews.json`: fourteen lack a precise
identity line in the inherited decision, two combine multiple contributions
outside M1a, and one combines the separate Talaga2 and Cihaur lines.
The inherited `no_referent` dispositions and 1620 ownership records remain
available alongside these completed bounded-review outcomes.
Later 0970 adjudications and their terminal accepted identity decisions are
cross-referenced with one-to-one or one-to-many mappings. These later lines
are outside the frozen extracts and contribute no M1b identity count; their
presence prevents an unresolved inherited identifier from being mistaken
for an absence of related identity decisions everywhere in the ledger.
They are inspectable in the country catalogue. A legacy coverage identifier
does not itself mint a referent or become a matching proposal, and local
pilot records outside M1a do not enlarge this catalogue.

`tests/test_jetp_m1b_catalog.py` exercises justified duplicates, grouped
components, missing justification, rejected supersessions, party roles and
pending aliases. Its release replay checks byte-identical country views and
descriptor, the exact inventory counts, and unchanged lines, line-fields
and M1a exports. The rendering check verifies that pending decisions are
separate and that accepted identities expose publisher links and snapshot
fingerprints. The reproducibility bundle validates M1b's file hashes and
retains this frozen release when preparing a later candidate bundle.
