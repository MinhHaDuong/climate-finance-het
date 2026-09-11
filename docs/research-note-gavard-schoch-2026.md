# Do climate-finance transfers reduce emissions? Reading Gavard and Schoch (2026)

## Source note

### Citation and status

Claire Gavard and Niklas Schoch, "International climate finance and emission
reductions: what do the last twenty years tell us?", *Environment and
Development Economics*, First View, 9 September 2026, pp. 1--24.
<https://doi.org/10.1017/S1355770X26100679>.

Peer-reviewed journal article. The published PDF is paywalled. This note is
therefore based on the publisher's abstract and metadata, checked against the
authors' public preprint, replication archive and estimation code. It does not
claim to summarize changes made between the archived manuscript and the
accepted article that are absent from those sources.

Author preprint: Gavard and Schoch, *Climate Finance and Emission Reductions:
What Do the Last Twenty Years Tell Us?*, ZEW Discussion Paper No. 21-014,
February 2021; manuscript dated 18 March 2021.
<https://ftp.zew.de/pub/zew-docs/dp/dp21014.pdf>.

Replication archive: Gavard and Schoch, "Dataset and simulation file associated
with the paper...", deposited 5 October 2022, Zenodo.
<https://doi.org/10.5281/zenodo.7149667>.

### The result, stated carefully

The authors compare three transfer measures rather than estimating one generic
effect of climate finance. In the 2021 preprint, a transfer commitment of $10
million per million tons of a recipient's lagged national CO2 emissions is
associated over the following six years with:

- a cumulative **4.7% increase** in emissions for Rio-marker adaptation finance
  (95% confidence interval 0.93--15.78%);
- a cumulative **1.86% increase** for Rio-marker public mitigation finance (95%
  confidence interval 0.75--4.21%); and
- no statistically significant cumulative response to CDM investment over the
  full six-year horizon. The coefficient on the sixth annual lag alone is
  negative: about **0.29% lower emissions in year six**, but years one to five
  and the six-year cumulative response are not significant.

The cleanest verbal summary is therefore: *recorded public climate-finance
commitments are followed by higher territorial emissions in this sample, while
the CDM proxy supplies only weak evidence of a delayed reduction*. It is too
strong to say that CDM transfers "produce" a reduction after five years.

This does **not** establish that a genuine mitigation project raises emissions.
It shows that three accounting and delivery systems labelled as climate finance
do not behave as interchangeable treatments. Rio-marker flows may contain
ordinary development projects relabelled as climate-related, and adaptation
projects may finance energy-intensive infrastructure. CDM projects are selected,
registered and measured through a different institutional process.

For the climate-finance history project, this distinction is more informative
than the sign of any single coefficient. The categories used to count finance
also define the empirical object whose effectiveness is estimated.

### Data construction

The publisher reports an unbalanced panel of 164 non-OECD countries for
2000--2017. The public archive documents the following sources:

- OECD DAC External Development Finance Statistics, recipient perspective, for
  project-level Rio-marker mitigation and adaptation flows;
- the UNEP DTU CDM pipeline, restricted to registered projects;
- Global Carbon Atlas/Our World in Data for territorial carbon emissions;
- World Bank GDP, population, political-stability, industry-share and forest-area
  indicators;
- the ND-GAIN vulnerability index;
- US inflation data used to express flows in 2016 dollars.

Project-level finance is aggregated to country-years with Excel pivot tables.
The archive says that country names were harmonized manually and intermediate
tables were copied into the final panel. The resulting Stata file and estimation
do-file are public, but the spreadsheet remains a substantial part of the data
pipeline.

### Estimation design

The outcome is the first difference of log carbon emissions. The released code
estimates Gaussian generalized estimating equations with year indicators,
country-panel structure, robust standard errors and an autoregressive working
correlation. It includes six annual lags of each finance measure, separately and
jointly, and plots cumulative responses through year six.

Controls include changes in log population, log GDP, industry share and
vulnerability. The timing design limits direct feedback from current emissions
to earlier transfers: future transfers cannot cause past emissions. It does not
remove donor selection based on lagged emissions, growth prospects, policy
capacity or persistent trends. The estimates are therefore dynamic conditional
associations under a timing restriction, not effects identified by an external
shock or instrument.

The causal requirement is sequential exogeneity: after conditioning on country
and year effects and observed controls, changes in transfers must be unrelated
to current and future innovations in emissions. That is demanding. Donors can
target commitments in response to a recipient's expected growth, project
pipeline, policy reforms, administrative capacity or prior emissions trend.
Those same factors can change future emissions. First differencing removes
time-invariant country heterogeneity; lagging finance prevents future finance
from causing past emissions. Neither operation removes this forward-looking
selection. Nor does an autoregressive working-correlation matrix create
identification; it changes how residual dependence is modelled.

The paper describes the estimates as intent-to-treat because the Rio variables
are commitments rather than disbursements. That label is useful for the exposure
margin but should not be confused with randomized-assignment ITT: commitment is
still endogenously assigned. The positive coefficients can consistently capture
several mixtures: causal construction emissions, economic activity enabled by
infrastructure, relabelling of ordinary development finance, finance targeted at
countries already on high-emissions trajectories, or failure to observe actual
disbursement and implementation.

### What is strongest

1. **The treatment is disaggregated by accounting regime.** Pooling Rio-marker
   flows and CDM activity would conceal their opposite dynamic patterns.
2. **The response is allowed to develop over time.** The delayed CDM result would
   be missed by a contemporaneous regression.
3. **The evidence is unusually broad.** The panel spans most recipient countries
   and almost two decades, with a public replication dataset and code.
4. **The null hypothesis becomes institutional.** If recorded mitigation finance
   fails to reduce emissions, the question shifts toward classification,
   additionality, disbursement and project composition.

### Main identification and replication cautions

- **No exogenous finance shock.** Lagging transfers addresses one direction of
  simultaneity but not endogenous allocation or time-varying omitted variables.
- **The measures are not commensurate.** Rio-marker development-finance records
  and registered CDM projects arise from different selection, reporting and
  verification systems. Their coefficients cannot be treated as a horse race
  between otherwise equivalent financial instruments.
- **Old outcome window.** The sample ends in 2017. It excludes the post-Paris
  scaling of MDB finance, new OECD accounting rules, JETPs and the recent rise of
  adaptation and loss-and-damage finance.
- **Manual data operations.** Excel pivots, copied tables and manual country-name
  harmonization weaken provenance and make unnoticed changes harder to audit.
- **Country-count discrepancy.** The 2026 publisher abstract reports 164
  non-OECD countries; the 2022 replication README says 168 countries remain for
  estimation. The archive may predate the accepted-paper sample.
- **Code-label discrepancy.** Variables named `CDMperGDP`, `MitiperGDP` and
  `AdaptperGDP` are divided in the released code by lagged emissions, not GDP.
  Interpretation should follow the executed formula rather than the variable
  names. The estimation heading also says `ar(4)` while the command specifies an
  AR(7) working correlation.
- **Publication lag.** The archive was deposited in October 2022, almost four
  years before First View publication. Until the published tables are compared
  with a rerun of the archive, exact replication of the accepted version is
  unconfirmed.

### How this paper fits the project

The paper belongs most directly in the REL review's controversy over accounting
boundaries and the consequences of classification. Its empirical contribution
supports a precise claim: estimates of climate-finance effectiveness depend on
which reporting system defines the treatment. It should not be cited as evidence
that "climate finance increases emissions" without preserving the distinction
between Rio-marker mitigation, Rio-marker adaptation and CDM transfers.

For the history-of-economics argument, the paper is evidence that measurement
choices remain active after the climate-finance aggregate has crystallized. A
counting convention does not merely describe financial effort. It determines
which projects enter an effectiveness test and can change the estimated sign.

The article appeared after the project's 1990--2024 corpus window and after the
current Oeconomia revision was submitted. It is best treated as a forward-looking
source for the REL review and later work, rather than silently inserted into an
already-submitted text.

### Could JETPs provide climate-finance shocks?

Not at the country-announcement level. The four early JETPs were negotiated with
countries selected precisely for coal dependence, policy opportunity and
geopolitical salience. Announcements were anticipated, bundled finance with
domestic policy commitments, and were followed by country-specific investment
plans. Headline packages combine grants, concessional and market-rate debt,
guarantees and expected private finance; commitment, financial close and
disbursement occur on different dates. With only a handful of heterogeneous
country treatments, an announcement-date event study would confound finance
with selection, anticipation, contemporaneous power-sector reform and common
energy-price shocks.

JETPs are more promising as sources of *within-country allocation rules* than as
country shocks. A credible design would use the earliest irreversible financing
event available and exploit predetermined exposure:

1. map each project from the investment plan to approval, financial close and
   disbursement, separating genuinely additional funds from relabelled or
   previously programmed finance;
2. define treatment at plant, utility, province or eligible-project level rather
   than assigning the entire country on the announcement date;
3. exploit a published eligibility threshold, scoring rule or donor-side budget
   discontinuity where one exists; otherwise use matched pipeline projects and a
   transparent event study as suggestive rather than causal evidence;
4. test pre-trends and report effects on direct outcomes first (financing terms,
   closure, dispatch, renewable connection and grid investment), before national
   emissions; and
5. treat the JETP's policy conditions as co-treatments, not controls that can be
   innocently partialled out.

For Viet Nam in particular, the December 2022 political declaration overlaps
with PDP8 development and its May 2023 approval, subsequent implementation
planning, tariff and market changes, post-pandemic demand recovery and grid
constraints. The December 2023 Resource Mobilisation Plan is another negotiated
milestone, not a random finance arrival. Project-level disbursement or a sharp
eligibility rule could yield a design; the declaration alone cannot.

### Reproduction and update effort

Approximate effort for one researcher already comfortable with Stata and the
source datasets:

| Deliverable | Researcher time | What drives it |
|---|---:|---|
| Run the archived code and reproduce archived tables | 2--4 days | Stata setup, package versions, table/figure reconciliation |
| Forensic replication of the accepted article | 5--10 days | Obtain published PDF; reconcile 164/168 countries, 2022/2026 versions, AR(4)/AR(7), coefficients and samples |
| Mechanical data extension using the old spreadsheet workflow | 1--2 weeks | Download later vintages, harmonize country-years, repeat manual pivots; quick but fragile |
| Scripted, auditable update through the latest common year | 4--7 weeks | Rebuild OECD/CDM/World Bank/ND-GAIN ingestion, commitments versus disbursements, country concordance, tests and robustness |
| Publication-grade JETP causal extension | 3--6 months minimum | Project-finance genealogy, additionality coding, actual disbursement dates, plant/utility outcomes, design and pre-trend validation |

The efficient sequence is: spend one week on exact replication and discrepancy
resolution; stop if the accepted results cannot be recovered; then budget about
one month for a scripted update. A JETP extension should be a separate paper, not
an extra robustness table, because treatment construction and identification
are the core research contribution.

### Checks before substantive citation

1. Obtain the published PDF through CNRS/Cambridge access and record the exact
   cumulative coefficients, confidence intervals and sample for each model.
2. Determine whether the Rio variables use commitments or disbursements and how
   "principal" and "significant" markers enter the totals.
3. Compare the published tables with a rerun of the 2022 Stata archive; reconcile
   164 versus 168 countries and AR(4) versus AR(7).
4. Inspect whether results survive country-specific trends, alternative scaling
   of transfers, large-recipient exclusions and separate pre-/post-Paris windows.
5. Separate four explanations for positive coefficients: misclassification,
   development-induced emissions, energy-intensive adaptation and endogenous
   allocation toward rising emitters.

### BibTeX record

```bibtex
@article{gavard_schoch_2026_climate_finance_emissions,
  author  = {Gavard, Claire and Schoch, Niklas},
  title   = {International climate finance and emission reductions: what do the last twenty years tell us?},
  journal = {Environment and Development Economics},
  year    = {2026},
  pages   = {1--24},
  doi     = {10.1017/S1355770X26100679},
  url     = {https://doi.org/10.1017/S1355770X26100679}
}
```
