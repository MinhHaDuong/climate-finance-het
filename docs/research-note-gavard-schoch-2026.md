# Do climate-finance transfers reduce emissions? Reading Gavard and Schoch (2026)

## Source note

### Citation and status

Claire Gavard and Niklas Schoch, "International climate finance and emission
reductions: what do the last twenty years tell us?", *Environment and
Development Economics*, First View, 9 September 2026, pp. 1--24.
<https://doi.org/10.1017/S1355770X26100679>.

Peer-reviewed journal article. The published PDF is paywalled. This note is
therefore based on the publisher's abstract and metadata, checked against the
authors' public replication archive and estimation code. It does not claim to
summarize parts of the article that are absent from those sources.

Replication archive: Gavard and Schoch, "Dataset and simulation file associated
with the paper...", deposited 5 October 2022, Zenodo.
<https://doi.org/10.5281/zenodo.7149667>.

### The result, stated carefully

The authors compare three transfer measures rather than estimating one generic
effect of climate finance. OECD Rio-marker public mitigation finance is followed
by higher recipient-country emissions. Public adaptation finance is followed by
an even larger increase. Transfers recorded through the Clean Development
Mechanism (CDM) produce a modest emissions reduction after about five years.

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
