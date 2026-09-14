# Independent scientific verification — ticket 0738

Reviewed 14 September 2026 in a separate agent context. Read-only examination of
the calculation, frozen selection, original XML, acquired HTML/PDF and pinned
comparator audit. No external retrieval; units 17–20 remain unused. This is a
scientific verification of measurement and feasibility, not the repository merge
gate or approval of a causal design. The main report was being assembled during
this review; its final prose and repository-wide gates are the author's checks.

## Reproduction and acceptance evidence

The five acceptance tests passed with:

```sh
/tmp/jetp-audit-0735/.venv/bin/python -m pytest tests/test_jetp_kfw_pilot.py -q
```

Evidence IDs are `test_identical_exports_count_distinct_activities`,
`test_quarter_end_and_partial_period_are_not_first_payment_dates`,
`test_identical_starts_do_not_validate_zero_delay`,
`test_negative_entry_is_not_cancellation`, and
`test_sample_round_robin_excludes_challenges_and_retains_all_candidates`.
These test the intended guardrails; the synthetic duplicate test alone does not
prove that two historical endpoint responses were identical. That historical
assertion comes from the archived round-3 endpoint evidence; there is one local
XML object, not two independently observed snapshots.

An independent standard-library calculation parsed the original XML directly
with `ElementTree`, selected participating-org ref exactly `XM-DAC-5-2`, and did
not import the implementation. It checked all country/status counts, all payment
stamp frequencies, challenge IDs, every candidate rank and selected flag, and
summed each country/landmark retrospective coverage cell against source dates.
All checks passed:

| Quantity | Independently reproduced result |
|---|---:|
| Distinct activities / selected XML nodes | 4,036 / 4,036 |
| Status 2 / 3 / 4 | 1,899 / 523 / 1,614 |
| Seven-country activity frame | 521 |
| Regional or multiple allocation stratum | 601 |
| AL / ID / IN / MA / SN / VN / ZA | 68 / 30 / 190 / 87 / 38 / 50 / 58 |
| Identical type-1 and type-2 start labels | 4,036 |
| Type-3 transaction entries / negative entries | 19,072 / 432 |
| Candidate sample after four challenge exclusions | 517 |
| Selected sample | 12 |
| Coverage rows checked | 14,832 (14,076 start-proxy + 756 unsupported stage rows) |
| External acquisition units / reserve unused | 16 / 4 |

The final narrow delta adds 756 rows covering seven countries, 12 landmark
labels, three stages (approval/signature/first payment) and three count kinds.
An independent CSV check confirmed all 756 combinations are unique and every
count/missing count is blank with an explicit unsupported reason. It also
confirmed `xml_document_link_presence = 12`; the clearer key replaces the
ambiguous document-coverage name. All member/pending counts are empty, not zero. All 16 acquisition-log entries
have consecutively numbered units, existing archive objects, matching SHA-256
hashes and byte lengths. Search batches share one archive object but correctly
consume one unit per query. The independent verification script was an ephemeral
review artifact at `/tmp/t0738-independent-check.py`, SHA-256
`ad776369479fca0939174b0ebb0abd3b33bd250bb2bb937133ac2a41e0f2e96a`;
normal reproducibility uses the versioned calculation and explicit archive paths
in the main report, not that temporary script.

Reviewed source fingerprints:

- XML `data/jetp/audit-evidence/0735-round3/kfw/bmz-country.xml`:
  `106dcca9e8cbe791fc0aa933b8c0567aef71f363534f21cffe08a6de9a9d9016`.
- `scripts/analyze_jetp_kfw_pilot.py`:
  `44a1f4fc9ecb13b0950065cc090885f231ec9bcf7234d7145110d4b53e17fd04`.
- `tests/test_jetp_kfw_pilot.py`:
  `da55a7fc71c515a17a0480cfe6f60d98cad93ef0e0142ac859c71242abf1f67e`.
- Frozen `selection.csv`:
  `9b485489139940473bdc169956e660facfe847f6c38bfb55f6bac931a62ebd92`.

## Selection and original-document checks

The independent round-robin produced the exact frozen sample in rank order:
200466276, 200366617, 201968361, 200166785, 200466433, 200866871,
200966358, 199870106, 200266973, 200270538, 200366757, 201870245
(all prefixed `DE-1-`). Mandatory old-start challenges are `DE-1-199170366`
and `DE-1-199370321`, alongside the two explicitly named challenges. There was
no sample substitution. Country/sector/instrument sorting is purposive: these
12 cases cannot estimate population document availability or treatment effects.

All 12 have XML document links. This is link presence, not 12 archived supporting
case documents: the `profile.json` key `xml_document_link_presence` must be read with
that limitation. External sample attempts cover ranks 1–2 only (2/12); rank 1
returned no results and rank 2 yielded one official PDF (1/12 retrieved).
Ranks 3–12 remain not attempted. All four challenge cases were inspected locally
and have a logged external attempt; title similarity is insufficient to close
identity or stage-date gaps.

Original HTML checks, under `data/jetp/audit-evidence/0738-pilot/`:

- `05-2020_scope.html`, project reporting paragraph: KfW's 2020 statement supports
  inclusion of BMZ projects agreed from January 2013 and those already underway
  then. This partially establishes inclusion semantics; it does not certify an
  exhaustive 2018 contract census or continued retention through later snapshots.
- `06-current_scope.html`, Project Database section: since-2013 contract scope is
  stated, with a different scope formulation from the 2020 IATI paragraph.
- `08-catalogue.html`, description and metadata: data are updated and overwritten
  at least monthly. The catalogue's publication date and coverage labels do not
  constitute downloaded historical observations or prove retention.
- `13-DE-1-201366764.html` and `14-DE-1-201365154.html`, project details: official
  project content was retrieved, but no independent exact IATI-ID cross-reference
  or validated signature/first-payment clock was established. The wind project's
  description explicitly involves loans and tranches; an activity is not a loan.
  The MA XML reports an actual end of 2021-12-01 while the retrieved project page
  reports `aktiv`. Preserve this apparent discrepancy: identity and administrative
  scope remain insufficiently resolved to harmonize the lifecycle or infer
  cancellation.

`pdftotext -layout` independently checked `16-DE-1-200366617.pdf`, SHA-256
`4dbafde3373526066ebc7428df77416d83a498cd3b7a7f4407eba3e399ef9ced`.
Page 1 explicitly lists BMZ number 2003 66 617, supporting rank-2 identity.
However, Project A groups it with 1998 65 841 and training components, while
Project B is separate. Page 3's completion years and page 1's aggregate financing
are component/project observations, not automatically dates/amounts for this
single IATI activity. Physical completion is distinct from financial closure.
This document does not establish signature or complete earlier payment coverage.

## Scientific disposition

**NARROW** is defensible for current-snapshot retrospective activity diagnostics
and reporting-stamp patterns. Annual year-end stamps through 2022, quarter-end
stamps thereafter and 315 entries stamped 26 August 2026 are reproduced from the
XML. These are observed stamps, not validated payment intervals: publisher
period semantics and complete earlier coverage remain absent. Negative entries
are retained without imputing cancellation. Identical planned/actual labels do
not identify zero delay or original plans.

**DEFER** historical contract populations, approved-but-unsigned risk sets,
approval/signature delays and first-payment clocks. Inclusion wording partly
exists, but no complete dated MA/IN 2018 roster, retention history or complete
prior payment ledger has been established. Current closed/finalising records
reduce one obvious survival restriction but do not prove absence of removed
records. Unknown disappearance cannot mean cancellation or nonpayment.
The next discriminating evidence is a dated complete 2018 contract register for
MA/IN with stable identifiers and reconciliation to later retained/removed
records; stage-specific dates additionally require official approval/signature
field definitions and a complete transaction history with period definitions.

Comparator constraints were checked against
`docs/jetp-audits/0736/comparators.md` at
`63bb738ef8f8bf7c96db3201a8ce48b717136075`. India is negotiation-exposed;
AL/MA are exposure-unassessed, not cleared controls. Early calendar landmarks do
not establish unexposed baselines; later declaration is not automatic untreated
status. Non-energy spillovers and shared lenders preclude an assumed clean
sector control. A large activity count does not increase the number of
independent treated countries. No causal design is approved by this review.

No pivotal numerical discrepancy was found. Two presentation corrections were
sent to the author: distinguish XML link presence from retrieved-document
coverage, and replace the manifest's freeze-SHA placeholder with the actual
selection-freeze commit before final delivery. The author subsequently supplied
`document-coverage.csv` and resolved the freeze commit as `5a307735`. Acceptance
tests were rerun after the calculation was renamed to
`scripts/analyze_jetp_kfw_pilot.py`: 5 passed. The fingerprints above reflect that
final version. A subsequent wrapper-only diff imports `parse_io_args` and
`validate_io`, keeps explicit `--xml`, requires shared `--output`, validates
paths and forwards the same arguments to `run`; no calculation change was
introduced by that diff. Acceptance tests again passed (5/5). The settings
extracted to `config/analysis.yaml` retain the frozen country list, 12-case size,
participant reference, challenge IDs/cutoff and all landmark dates. The original
freeze is retained by tag `pilot-0738-selection-freeze`; the author records
`467e7fab` as its equivalent after rebase. No implementation edits or git
mutations were made by this reviewer.
