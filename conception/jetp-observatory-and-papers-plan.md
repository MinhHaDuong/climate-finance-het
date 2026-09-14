# JETP observatory and academic programme

Decision agreed with Minh, 13 September 2026. Phase: Plan.

## Shared question and two tracks

**Where do JETPs stand, and have they accelerated energy-transition projects?**

Track one is a public, source-backed observatory for South Africa, Indonesia,
Viet Nam and Senegal. Readers explore country portfolios, individual projects,
essential features, references, progress timelines and meaningful totals.
Monthly editions make changes visible and preserve the previous state.

Track two is academic publication: a JETP data paper and the two analytical
papers discussed with Christophe Cassen. The short paper compares project
progress against regular pre-JETP energy projects. The long paper investigates
why the observed trajectories differ. Papers analyse frozen observatory releases;
the observatory remains useful regardless of the analytical result.

This decision supersedes the disbursement-only framing and predetermined
mechanism claims in `jetp-papier-court-mesure.md` and
`jetp-papier-long-economie-politique.md`. Those notes and the September 8 meeting
record remain historical inputs, not agreed conclusions. LaTeX remains the
chosen format for the two analytical manuscripts (0711). No journal change is
decided here.

## Storage decision (13 September 2026)

Markdown dossiers and small CSV registries stay in Git; binary evidence stays in
the existing DVC archive. The website renders static HTML with release-bound
JSON/CSV, without a live SQLite backend. SQLite may later be a derived export.
See [storage contract](../docs/jetp-storage.md) and `data/jetp/README.md`.

## Track one: the observatory

- Country pages: pledge history, portfolio composition, financing stages,
  coverage and observation dates.
- Project pages: stable identity, purpose, technology, location, promoter,
  funders, instruments, original-currency amounts and linked source locators.
- Timelines distinguish event date, publication date and retrieval date;
  approximate dates and status-only observations remain explicit.
- Filters cover country, technology, funder and stage. Initial visualisations
  show portfolio composition, preparation/financing stages and monthly changes.
- Every total exposes its constituent records, perimeter, stage, currency
  treatment and cutoff. Programme/component overlap and repeated financing
  observations must not inflate totals. Unknown is not zero.
- Monthly releases include a change log, correction history, versioned downloads,
  coverage report and source archive references. Start with a documented reviewed
  release process; do not introduce an unattended publication scheduler by default.

Physical milestones may appear when actually documented, but construction,
commissioning and retirement comparisons are not prerequisites for this programme's
first analytical release. An agency's generic implementation label is not a
construction date. Public access to source references does not imply permission
to redistribute every archived document; specify release terms explicitly.

## Track two: three academic contributions

| Paper | Question | Evidence and deliverable |
|---|---|---|
| JETP data paper | How can partnership progress be observed consistently? | Versioned dataset, schema, provenance, identity decisions, coverage, validation and uncertainty; distinct from the repository's existing non-JETP data paper. |
| Short paper | Are JETP projects progressing faster than comparable pre-JETP energy projects? | Preparation and financing intervals, milestone attainment and historical benchmarks, selected after a feasibility audit. |
| Long paper with Christophe | What explains the observed trajectories? | Comparative process evidence on instruments, institutions and negotiations; explicit rival explanations and negative cases. |

The short paper considers formal identification to approval, approval to
signature, and signature to effectiveness or first payment. Disbursement remains
one possible outcome, not the sole measure. Construction is too early for the
comparative question at this stage.

The comparator is ordinary pre-JETP energy projects, preferably within the same
country, lender, instrument and broad technology. A political pledge is not a
project commitment. Partnership announcement dates do not substitute for each
project's lifecycle origin. Record projects' pre-existing maturity when they
enter JETP; do not credit the partnership with their entire preparation history.

Retain pending, withdrawn and cancelled proposals where observable. Distinguish
right-censoring, unknown dates, interval-known transitions and reporting delays.
Do not compare only successful completed transitions. Approval databases alone
cannot identify the probability or speed of approval among all proposals.

Historical comparisons establish relative speed, not automatically a causal
JETP effect. Instrument substitution, absorption constraints and ownership
arrangements are hypotheses to investigate, not findings to manufacture. A null or mixed effect remains publishable under a credible design. If causal
identification is unavailable, return the short-paper scope decision to the author
rather than automatically substituting a descriptive paper.

## Feasibility decision before scaling analysis

Audit 10–15 named JETP investment projects selected by explicit lender/project-type
rules, alongside a defined historical candidate cohort. Include stalled proposals
where sources expose them; document selection and unavailable histories. This is
a coverage diagnostic, not a powered effect estimate or a representative sample.

For each stage record both endpoints, source precision and historical-comparator
availability. Prefer comparable lender records, including World Bank and ADB
records where relevant, without silently excluding bilateral finance. Deliver a
stage-by-stage go/narrow/defer decision. If pre-approval histories cannot be
reconstructed, keep pipeline descriptions and restrict duration inference to the
financing transitions that are supported. Observatory publication must not wait
for complete four-country causal analysis.

## Delivery plan and dependencies

Tracker 0725 governs integration. It reuses the collection programme 0715 and its
children, especially 0721 (CRS/IATI reconciliation) and 0722 (refresh guidance).
Physical-asset work 0723 remains a separate extension, not an analysis blocker.

| Ticket | Deliverable | Prerequisites |
|---|---|---|
| 0726 | Public dataset release and auditable totals | Existing corpus; bounded reconciliation within release scope |
| 0727 | Observatory website ready for public release | 0726 |
| 0728 | Reviewed monthly release process and edition comparison | 0726, 0727; reuse 0722 and existing harvester |
| 0729 | Lifecycle/comparator feasibility pilot | Existing corpus; coordinate matching with 0721 |
| 0730 | Historical comparison dataset and reproducible analysis | 0729 go/narrow decision; reuse 0713 and 0721 |
| 0731 | JETP data-paper manuscript | 0726 |
| 0732 | Reimagined short comparative manuscript and figure | 0730, 0711 |
| 0733 | Reimagined comparative political-economy manuscript | 0726, 0729, 0711; incorporate 0730 when available |

First wave: release preparation and feasibility pilot. Second wave: website,
comparison dataset and data paper. Third wave: monthly operation and analytical
manuscripts. This is dependency ordering, not a promise of publication dates.
Each ticket specifies its first test or falsifiable documentary acceptance check.
Implementation runs in separate ticket contexts with the repository's usual gates.
Hosting, public URL and recurring release ownership are resolved in the website
and monthly-process tickets using a concrete preview; no deployment occurs in
this planning task. Journal submission remains a separate action.

## Integration acceptance

The programme is delivered when the website and a repeatable monthly release
process are live, a citable dataset release exists, and the three manuscripts are
reviewable with reproducible evidence. Scientific scope may narrow after the
pilot, with the decision recorded; positive acceleration is never an exit criterion.
Close the tracker only after reviewing the integrated child deliverables, not
merely because their individual tickets are closed.

## Public planning tracker

[GitHub issue #1333](https://github.com/MinhHaDuong/climate-finance-het/issues/1333)
links the eight implementation and publication issues (#1334–#1341).

## Comparator extension considered on 14 September 2026

The feasibility audit will also examine a synthetic (pooled or weighted) reference
of other beneficiary countries with comparable pre-treatment conditions, rather
than restricting the candidate universe to the four JETP countries. The author confirms pre-JETP country income, financing eligibility and
energy-sector conditions, plus project matching by lender, instrument and
technology. Pre-entry maturity remains an additional baseline characteristic.
The protocol must specify indicators, reference years and matching tolerances;
matching uses baseline characteristics, not financing choices induced by JETP.
Within-country comparisons remain a useful
sensitivity reference, not an exclusive constraint. Tickets 0729/0730 now carry
the expanded pool and a separate causal-identification audit. A project-support
effect and a country-wide partnership effect require different treatments and
sampling frames. No formal synthetic-control design or causal interpretation is
automatically adopted by widening the pool.

## Short-paper decision, 14 September 2026

The author now targets a **causal short paper**. Ticket 0729 selects and audits
identification alongside endpoint availability; 0730 implements the frozen viable
design; 0732 writes the causal argument and central figure. Stronger comparative
coverage alone is insufficient. The treatment may be partnership-wide or a more
limited project-support intervention, but that choice must precede estimation.
A broader beneficiary-country pool is a candidate comparator strategy, not a
predetermined synthetic-control method. If no credible design is supported, the
audit returns to the author for an explicit decision. The observatory, monthly
editions and data paper remain useful and can proceed regardless of that outcome.

## Additional comparator option: non-energy sectors

The author proposes non-energy projects as a possible comparator. Tickets 0729/0730
now audit within-country sector contrasts and a possible triple-difference design
(energy/non-energy × JETP/comparator countries × pre/post). This is a candidate,
not a selected estimator: sector-gap counterfactual trends, project comparability
and JETP spillovers into other sectors must be assessed first. A relative sectoral
effect must not be presented as total energy-project acceleration.
