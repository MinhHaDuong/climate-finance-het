# KfW BMZ feasibility: narrow descriptive scope; defer historical stage clocks

14 September 2026. Ticket 0738 was explicitly launched by the author. The pilot
supports **NARROW** for retrospective activity counts and observed transaction
stamps. **DEFER** historical contract populations, approval/signature clocks and
first-payment intervals. No causal design or effect estimate is selected.

## Frozen inputs and population

Audit PR #1347 was merged at live head `137a96160add8ddb8c339ae17eae3853948f45bb`;
this pilot branches from main `7f89c356021cdbd3a10e6b14e6e3106938a846d5`, which
contains that head and the prospective protocol. Selection PR #1348 remains at
`63bb738ef8f8bf7c96db3201a8ce48b717136075`. Input hashes are in
[input-manifest.json](input-manifest.json). Both DVC directory MD5s match the
protocol. Freeze commit `5a307735` precedes new evidence retrieval; it contains
all candidate ranks, selected flags and routes. Tag `pilot-0738-selection-freeze`
preserves that original commit across the subsequent rebase onto main
`0f97bbf6cf1820ed410af82d9764e6c4350b6644`; the rebased equivalent is
`467e7fab`. Moving the identical sampling
constants into config/analysis.yaml is a refactor, not a sample amendment.

The archived Country export has SHA-256
`106dcca9e8cbe791fc0aa933b8c0567aef71f363534f21cffe08a6de9a9d9016`.
Round 3 recorded identical bytes from Country and Region endpoints; the archive
stores that object once. These endpoints are neither two populations nor two
historical snapshots. Exact participating-org ref `XM-DAC-5-2` yields **4,036
unique IATI activities**, not 4,036 loans: raw finance types 110/421/510/520/410
have counts 3,009/822/173/19/13 and remain unharmonized. Mandates outside BMZ are
outside this source population. Present statuses 2/3/4 have 1,899/523/1,614 records.

| Allocation | Activities now observed |
|---|---:|
| AL | 68 |
| MA | 87 |
| IN | 190 |
| SN | 38 |
| ZA | 58 |
| ID | 30 |
| VN | 50 |
| Regional/multiple/ambiguous allocation, separate | 601 |

The seven-country frame has **521 activities**; excluding four mandatory
challenges leaves **517 sample candidates**. The 12-case purposive sample follows
lexicographic country × DAC energy/non-energy/mixed-or-unmapped × raw-instrument
strata, then ID, one per stratum per round. It is not a population document-
availability estimate. Regional allocations are never replicated into countries.
Energy uses explicitly DAC-coded purposes 23000–23999; other vocabularies remain
unmapped. All records, including completed activities and negative transactions,
remain in local profiling.

## What the originals establish

The [dated KfW statement](https://www.kfw-entwicklungsbank.de/International-financing/KfW-Development-Bank/About-us/News/News-Details_593728.html)
(E05, 24 June 2020) describes BMZ projects contracted since 1 January 2013 **or
already underway then**. The [current database description](https://www.kfw-entwicklungsbank.de/International-financing/KfW-Development-Bank/Transparency/)
(E06) abbreviates this to contracts since 2013. These support a published inclusion
rule, but do not demonstrate its completeness or cancelled/withdrawn-project
retention. A dated webpage retrieved today is not a separately observed historical
export. The [BMZ page](https://www.bmz.de/de/ministerium/zahlen-fakten/bmz-transparenzportal)
(E07) describes BMZ financing/cofinancing and monthly publication. The archived
[GovData catalogue](https://data.gov.de/suche/daten/bmz-projektdaten-iati-meldung)
(unit 8) explicitly describes overwritten data. No complete dated official
calendar-2018 financing-contract roster for MA or IN was acquired through the
bounded routes. The denominator is **unknown**, not zero; no roster was invented
from the current-record sample or procurement-contract search results.

There are 19,072 type-3 entries across 3,649 activities: 18,757 quarter-end stamps
(including 12,933 on 31 December), and 315 on 26 August 2026. The distribution
suggests annual/quarterly reporting and a latest partial period; publisher period
boundaries, aggregation policy and earlier coverage were not established.
`events.csv` therefore retains raw stamps without normalizing them into exact
payment days or first-payment intervals. All 432 negative entries are retained as
corrections of undocumented substantive meaning. An absent type-3 entry in 387
activities is missing evidence, not measured zero payment. All 4,036 planned
starts equal actual starts in this snapshot; no original plan or zero-delay
conclusion follows. Approval, signature and first-payment fields remain explicitly
missing; commitment and value dates do not fill them.

## Mandatory challenges and documentary coverage

| Challenge | Original observation | Evidenced disposition |
|---|---|---|
| DE-1-201366764, MA | Start label 2016-08-04; payment stamps 2018/2019/2020 year ends; end label 2021-12-01. | Exact XML-linked KfW detail 32652 downloaded (E13), still reports active. Preserve the status discrepancy; neither source validates contract signature or first payment. Keep Phase III separate. |
| DE-1-201365154, IN | Start label 2015-12-29; annual payment stamps 2017–2022, quarterly stamps beginning 2023. | XML-linked KfW detail 30347 downloaded (E14); no stage-date definitions. Planned end 2026-10-30 is not completion. Annual-to-quarterly transition does not establish complete earlier coverage. |
| DE-1-199170366, MA | Smallest ID with a source start before 2013: 1992-10-26; first visible payment stamp 2012-12-31. | Local XML proves an older surviving record; exact-ID search did not identify an independent original. Earlier payment history and contract date unknown. |
| DE-1-199370321, IN | Smallest ID with a source start before 2013: 1993-12-28; payment stamps begin 2012-12-31; negative 2013 entry. | Older surviving record, with a correction; not evidence of a complete 1993 cohort, first payment in 2012 or cancellation. Exact-ID search unresolved. |

Before new acquisition, all **12/12** selected cases had local XML records and
links, but **0/12** had independently archived case documents in the specified
KfW archive. Generic catalogue/evaluation/tender links are not documents.
External sample attempts were **2/12**, in rank order: rank 1 returned no result;
rank 2 yielded one identity-confirmed evaluation (**1/2 attempted; 1/12 selected**).
The other ten remain explicitly **not attempted** after the historical-
denominator/period-definition stop decision, while preserving the verification
reserve. The four mandatory challenges are outside those denominators: **4/4**
received external attempts; **2/4** yielded XML-linked project pages.

The rank-2 [Albania evaluation](https://www.kfw-entwicklungsbank.de/PDF/Evaluierung/Ergebnisse-und-Publikationen/PDF-Dokumente-A-D_EN/Albanien_Übertragungsleitung_2016_E.pdf)
(E16, p.1) explicitly includes BMZ number 2003 66 617, but combines it with
1998 65 841 and training components under Project A; Project B is a distinct
transmission operation. Combined amounts, completion and implementation duration
cannot be assigned to the sampled activity. Documentary identity is supported;
no new activity-specific stage clock is validated. Physical performance and
financing stages remain separate, and no JETP attribution is inferred.

## Baselines and design-matrix inputs

`coverage.csv` applies all 12 protocol landmarks to each diagnostic country,
including comparator candidates for calendar alignment. It separates currently
reported earlier starts from demonstrated membership and pending status. Annual
cohorts are explicitly **proxy** cohorts; validated stage cohorts are unknown.
Historical membership, pending and lost-visibility counts are empty with reasons,
not zero. No stable pre-period population, absence of payment or disappearance
can be inferred from this single current snapshot.

| Candidate/stage | Verdict | Missing discriminating evidence |
|---|---|---|
| Retrospective activity and raw payment-stamp diagnostics | NARROW | Counts describe the acquired BMZ activity export only; period totals require publisher aggregation definitions. |
| Incumbent-pipeline acceleration | DEFER | Dated retained/cancelled roster and verified pending stage at each landmark; validated event clocks and earlier observation coverage. |
| New financing/signature throughput | DEFER | Complete signed-contract register for calendar 2018 in MA/IN; explicit mapping of commitment/start to signature; comparable retention across years. |
| Approval-to-signature | DEFER | Approval originals and approved-but-unsigned risk set; published inclusion is contract-based. |
| First payment, exact or interval | DEFER | Earlier complete payment coverage plus documented annual/quarterly and 26-August period semantics; contract denominator. |
| Energy/non-energy contrast | DEFER causal; NARROW classification diagnostics | Validated common stage outcome and sector-specific parallel-shock/spillover assessment. |
| Country synthetic control | DEFER | Stable comparable historical series, admissible donors and informative pre-period fit. |
| Support-allocation design | DEFER | Actual eligibility/cutoff/rollout rules, candidate and rejected histories, dated offers. |

India remains negotiation-exposed under pinned 0736; AL/MA are exposure-unassessed,
not cleared controls. Declaration cutoffs do not exclude earlier discussions or
private negotiations. Sector contrasts are relative if non-energy spills over;
matching does not establish exchangeability, and many activities do not create
many independent treated countries. Measurement gaps and counterfactual failures
are separate. These rows feed the coordinator's matrix; primary causal selection
still requires the author's scope decision. No descriptive substitution for the
primary estimand has been made.

## Reproduction and verification

Core tables are DVC-tracked because each exceeds the repository's git size limit;
small selection/evidence/report artifacts are committed directly. New source
bytes are separately DVC-tracked under `data/jetp/audit-evidence/0738-pilot`, with
SHA-256 manifests. No canonical ledger or website total changed.

From the repository root, using a configured project environment:

```bash
PYTHONPATH=scripts:libs/openalex-corpus/src uv run python scripts/analyze_jetp_kfw_pilot.py --xml data/jetp/audit-evidence/0735-round3/kfw/bmz-country.xml --output docs/jetp-pilots/2026-09-15/kfw
uv run python docs/jetp-pilots/2026-09-15/kfw/build_evidence.py --output docs/jetp-pilots/2026-09-15/kfw --bundle data/jetp/audit-evidence/0738-pilot --xml data/jetp/audit-evidence/0735-round3/kfw/bmz-country.xml --config config/analysis.yaml
```

The protocol-approved existing audit interpreter was used in this sandbox.
Reproduction consumes archived bytes only. Acceptance tests are in
`tests/test_jetp_kfw_pilot.py`; first red commit `761c0b72`, green freeze
`5a307735`. The independent [verification](verification.md) reproduces counts,
selection and coverage, checks originals and runs acceptance tests without new
external retrieval. Acquisition is **16/20 units**, with four reserved units
unused; unsuccessful and unattempted cases remain visible. Gates are recorded
in [gate-results.md](gate-results.md).

The exact next documents are: (1) KfW/BMZ's complete, dated MA/IN 2018 financing-
contract register including withdrawn/closed contracts and retention rules;
(2) a publisher transaction-period specification covering annual-to-quarterly
changes, historical opening balances and 26 August 2026; (3) lender evidence
mapping approval, signed agreement and administrative start fields. Further
broad searching is not proposed, and no institutional contact was made.
