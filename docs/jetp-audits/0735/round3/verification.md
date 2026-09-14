# Third-pass verification record

14 September 2026. Independent read-only reviews checked AFD against original
payloads and the synthesis against provider profiles and originals. This is
scientific verification of the evidence audit, not the full PR merge gate.

AFD review reproduced the 224 legacy-country denominator, 223 retained IDs,
225 parents, 317 financings, exact field comparisons and period-end clustering.
Corrections applied: distinguish one missing signature proxy from one changed
date; distinguish historical zero payments from current payment status; explain
frozen modified metadata and separate 2026 data-processing timestamps.

Synthesis reviewer independently recomputed JICA, FCDO and USAID pivotal counts.
Corrections applied: observed payment state replaces claims of known unpaid
status; stage outcomes remain candidates subject to definitions and coverage.
No substantive blocker remained in either review. Neither reviewer selected a
causal design or claimed disclosure completeness.

Parent separately recomputed BMZ/KfW counts using the exact agency reference,
JICA dates/transaction types, FCDO hierarchy/status counts, USAID temporal range,
and AFD joins; read original JICA PDF milestone tables and FCDO structured
transactions; checked the US dictionary's accounting-period definition.
Original payloads are identified by SHA-256 in source-byte-manifest.json.

The planning/scout briefs in this round were written after initial discovery;
the recorded sequence is not a prospective preregistration. Future rounds should
freeze the named questions, acceptance criteria and budgets before retrieval.

Local gates: `make check-fast` passed (1,549 passed, 12 skipped); `make lint`
passed (330 passed, 15 skipped). All audit JSON/CSV parse, all 33 archive hashes
and sizes match, and the specific DVC bundle status is clean. The full pipeline
suite is not required for this documentation/provisional-data-only diff.

The DVC push failed with connection refused at 127.0.1.1:22. All 34 new cache
objects, including directory metadata, were copied and hash-verified in the
primary checkout cache. Remote replication is pending under 0726.
