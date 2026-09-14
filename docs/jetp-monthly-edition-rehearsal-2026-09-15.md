# JETP monthly-edition rehearsal — 15 September 2026

This rehearsal exercised the release-diff fixture required by ticket 0728,
without changing a JETP fact or fabricating a second real edition. It compared a
frozen `2026-09` snapshot to a synthetic `2026-10` candidate with one unchanged
record, a source-backed amount correction, a report of an older event, a blocked
refresh and a retracted claim.

The report classifies the cases as unchanged, correction, late report, failed
refresh and retraction. It retains all IDs from the previous edition, so a
failed retrieval cannot erase a project. `tests/test_jetp_monthly_editions.py`
records this fixture and verifies the classification.

The release owner is the named JETP release reviewer. On the first working day
after a monthly cutoff, the owner freezes reviewed registry and editorial inputs,
creates an isolated candidate, runs the release comparison and reviews every
scientific change with source, reviewer and rationale. The review cutoff is the
last day of the month at 18:00 Europe/Paris; a routine edition is prepared by
the tenth day of the following month. A correction uses `YYYY-MM-rN`, never
replaces the preceding archive, and is published only after the same review.

Recorded rehearsal effort: 35 minutes for fixture review, report inspection and
offline archive/recovery checks. Unresolved coverage remains the existing
blocked or unavailable source-byte records and the 21 Viet Nam identity slots.
No unattended scheduler or external publication was exercised.
