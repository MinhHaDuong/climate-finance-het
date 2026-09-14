# Verification record

Scientific review was performed by a separate read-only agent against archived
original JSON/XML and new response bodies, with no additional external units.
It independently reproduced both DVC directory hashes, 2,080 legacy records,
3,277 portal financings, 317 XML financings/225 parents, 223/224 diagnostic
retention, and 19+2+7+13 anomaly rows (41 distinct challenge IDs).

It independently reconstructed all 210 sample ranks and all 12 selected IDs,
checked all 193 legacy/XML first-payment discrepancies, verified all 193 exact
legacy dates remain in events, and reproduced six retained legacy-payment-missing
IDs without XML type-3 entries. It counted 3,296 union financing IDs and 709
regional records without duplicating them into diagnostic countries.

The reviewer initially found three defects: amounts in normalized_date, omitted
raw XML sector/aid classification fields, and unresolved generic XML evidence
references. All were corrected before its second pass. That pass verified all
964 amount rows have empty normalized_date, all 317 XML sector representations
match originals, all raw aid fields match sources, and every anomaly evidence
reference resolves. Five acceptance tests passed. Final scientific verdict:
APPROVED for the bounded NARROW/DEFER feasibility assessment; no approval of
causal identification or merging.

Original metadata checks: resource creation in 2022 does not attest a historical
snapshot; legacy publication conditions include counterparty agreement and an
execution-stage scope. Current dictionaries label a signature field but do not
supply a tested inclusion/retention or payment-aggregation algorithm. The portal
uses C01 throughout despite explicit policy-support content in CAL101901; aid
types are retained raw and never promoted to a validated policy/investment split.

Reproduction used the report's explicit archive-root/output command in a second
output directory. Every one of its 10 output files was byte-identical. Inputs
are hash-checked before parsing; this rerun made no external request.

Acceptance evidence:

- `6dd301cf:tests/test_afd_pilot.py` is the first committed failing contract:
  check-fast reported the expected missing-module collection error.
- `test_cma123501_disappearance_is_not_an_outcome` checks unknown outcome,
  last observed stage and observation snapshot.
- `test_exact_payment_is_preserved_and_no_uncovered_interval` rejects exact XML
  substitution and intervals without earlier completeness.
- `test_value_date_never_imputes_award_and_parent_never_joins` rejects both shortcuts.
- `test_all_193_legacy_exact_payment_dates_survive` checks all audited exact dates.
- `test_amounts_are_not_normalized_as_dates` checks negative-value preservation,
  date-field separation and raw sector-vocabulary retention.

The first fast run also failed two existing document-object tests because this
new worktree lacked their local ignored archive. Linking the already acquired
archive resolved both without changing those tests. Final fast gate: 1,721 passed,
12 skipped. Adherence first caught a script prefix and then a test-import ordering
violation; both received mechanical fixes. Final gate outcomes are recorded below.

DVC replication is outstanding: automatic approval review rejected upload to the
configured SSH remote because ownership/trust and explicit payload authorization
were not established. No upload or workaround occurred. Repository README and
JETP tracking instructions additionally reserve pushes for padme after review.
All generated CSVs and response bodies remain local and hash-addressed. The PR
is reproducible from the existing local source bundles, but remote replication
has not been verified. This limitation is separate from the scientific DEFER.
