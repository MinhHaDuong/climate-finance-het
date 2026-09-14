# Energy-transition observatories: research methods and reusable tools

## Executive assessment

There is no single examined platform that combines documentary finance
reconciliation, longitudinal project research, policy interpretation and energy
system modelling with the required evidence history. Several projects provide
strong precedents for parts of that system. The useful comparison is therefore
between their research objects, measurement conventions and publication contracts,
rather than between the appearance of their dashboards.

Four families are especially relevant. AidData and Global Energy Monitor show how
documentary research can support structured operation or asset histories. Climate
Policy Radar and Oxford's Climate Policy Monitor show complementary approaches to
finding, classifying and reconciling policy evidence. Our World in Data and Open
Contracting offer publication and revision patterns. Open Energy Platform and the
PyPSA ecosystem provide references for a possible future modelling connection.
The profiles below document both capabilities and limits.

The strongest recommendation is to retain the proposed source archive, reviewed
tables and generated publications, while making research products explicit
consumers of the same evidence. Use external datasets through pinned adapters and
reviewed crosswalks. A common country name, project title or financial stage label
is insufficient to establish semantic equivalence.

For the current JETP observatory, the principal official country report and its
inventories remain the population anchor. External monitors contribute enrichment,
cross-checks and candidate comparison evidence. Their apparent global reach must
not silently replace local definitions, official programme boundaries or missing
national coverage. A complete search of an incomplete dataset is still incomplete
evidence about the underlying transition.

Future whole-transition observation and a PyPSA electricity modelling arm are
considered only for migration compatibility. They do not add requirements to the
present MVP. Their main implication today is to avoid identities and provenance
contracts that make future separation of initiatives, assets, studies and model
components unnecessarily difficult.

## Comparison framework

The comparison distinguishes six questions: what is observed; how evidence becomes
an accepted record; which time and measurement conventions apply; what a research
user can reproduce; which code or interfaces are reusable; and what would be
unsafe to infer from the published data. Public access to a dashboard, an open
methodology, an open dataset and an open software licence are separate properties.

The matrix gives a compact assessment. “Candidate” means worth a bounded technical
evaluation if a relevant need arises; it does not mean installed, benchmarked or
ready for automatic ingestion. Dates in the profiles identify examined editions,
not an assurance that every source has the same information cutoff. The companion
CSV adds access, revision and source columns.

| Project or tool family | Primary object | Most useful transfer | Principal limit |
|---|---|---|---|
| Global Energy Monitor | Physical units and projects | Structured inventories linked to documented histories | Technology thresholds and unit definitions differ[^gemintegrated] |
| AidData TUFF | Financed operations and their documentary histories | Reconstruction protocol and evidence quality | Financing operation is not automatically a physical asset[^tuff] |
| Climate Policy Radar / Project Explorer | Documents, passages and concepts | Source discovery and evaluated annotation | Extracted mention is not a verified economic event[^radar] |
| Climate Funds Update | Multilateral fund flows and projects | Financial-stage and disclosure distinctions | Uneven reporting, especially disbursements[^cfu] |
| CPI Global Landscape | Aggregated climate-finance flows | Perimeter and double-counting discipline | Examined landscape measures commitments[^cpi] |
| Carbon Monitor | Daily estimated sectoral emissions | Transparent high-frequency indicators | Activity-based estimates, with revisions[^carbon] |
| Climate TRACE | Estimated emissions, including assets | Versioned releases and methodological change logs | Estimates and projections need their own interpretation[^trace] |
| Ember | Electricity generation, demand and related series | Country-specific harmonisation documentation | Annual and monthly series can differ[^ember] |
| WRI Climate Watch | Country climate datasets and policy targets | Comparative country exploration | Harmonisation is not causal identification[^wri] |
| Climate Action Tracker | Policy and target assessments | Explicit evaluation dimensions | Normative ratings are derived judgements[^cat] |
| Oxford Climate Policy Monitor | Policy tools and expert assessments | Independent coding, matching and reconciliation | Selected jurisdictions and disclosure limits[^oxford] |
| OECD CAPMF / Climate Policy Explorer | Policy panels and empirical evaluations | Structured covariates and replication packages | Stringency and estimated effects are distinct[^capmf][^explorer] |
| Our World in Data ETL | Versioned datasets and indicators | Snapshot-to-publication dependency chain | Full platform adoption exceeds present needs[^owid] |
| Kausal Watch | Action plans and progress management | Collaborative operational workflows | Administrative progress reporting differs from evidence adjudication[^kausal] |
| Open Energy Platform | Datasets, models and scenario bundles | Research and modelling metadata | Draft data are explicitly volatile[^oepdatabase] |
| PyPSA / PyPSA-Earth | Energy networks and scenarios | Future electricity modelling workflow | Global modelling capability does not validate local inputs[^earth] |
| powerplantmatching | Combined plant databases | Candidate identity matching and model preparation | Harmonised model inputs may transform reported values[^matching] |
| Open Contracting Data Standard | Releases and compiled process records | Journal/status publication pattern | Merge rules do not settle independent-source conflicts[^ocds] |

## Documentary inventories and climate finance

### Global Energy Monitor

GEM's coal tracker combines a unit database with source-referenced plant histories.
Its methodology specifies capacity and historical inclusion thresholds and regular
updates. Status classification can include elapsed-time rules: a long absence of
progress evidence can support a shelved or cancelled classification. Such a label
must not be imported as an exactly dated observed cancellation event.[^gemcoal]

The integrated power tracker federates technology trackers and rolls forward when
its components update. It retains different technology coverage thresholds. An
integrated download is therefore not necessarily one homogeneous census with one
observation date.[^gemintegrated]

**Transfer:** retain inventory rows and identity hierarchies, attach documentary
histories, and publish coverage rules by technology and edition. GEM's public maps
repository also documents data/configuration-driven static publication. That
supports a static interface as a credible pattern, although its dependencies and
licensing would need checking before code reuse.[^gemmaps]

### AidData and TUFF

The fourth TUFF methodology, published in November 2025, sets out reconstruction
of underreported development finance through multiple public sources. Its detailed
manual distinguishes financial records and implementation information and records
evidence quality. It is a closer methodological analogue for a documentary JETP
observatory than a generic project-management application.[^tuff]

One import hazard is date precision. The manual allows some dates with incomplete
day information to be represented using the first day of a month and an estimated
flag. An adapter must preserve that flag and recover supported bounds; the
formatted date alone would create false precision in duration analysis.[^tuffmanual]

**Transfer:** a source hierarchy, explicit acceptance criteria, relationship
crosswalks and quality annotations. Do not adopt its financing unit as the default
unit of physical progress. Its China-focused collection frame also cannot supply
an untreated comparison population merely because records lack a JETP label.

### Climate Policy Radar and Climate Project Explorer

Climate Project Explorer searches documents from the Green Climate Fund, Climate
Investment Funds, Global Environment Facility and Adaptation Fund. Climate Policy
Radar provides a shared document and concept infrastructure behind this and other
products. Its public description offers warehouse access through API/MCP routes
with an access process; anonymous bulk access should not be assumed.[^radar]

The knowledge-graph repository exposes concepts, passage labels and labelling
machinery under Apache 2.0. The methodology describes expert concepts and evaluated
classifiers. Evaluation sampling includes deliberately selected difficult cases;
such samples should not be read as estimates of concept prevalence in the full
corpus.[^radarkg][^radarmethod]

**Transfer:** passage locators, concept identifiers, model/version metadata and
human evaluation. An extraction system should propose assertions with source
spans. It should not infer settlement from approval language or automatically
ratify project identity from a textual similarity score.

### Climate Funds Update

Climate Funds Update draws principally on official fund information and seeks
verification from fund managers, while acknowledging incomplete verification.
Its methodology distinguishes pledges, deposits, approvals and disbursements and
warns that low reported disbursement can reflect inadequate disclosure. Some
background definitions on the methodology page are old, so each definition needs
its own version assessment.[^cfu]

The dashboard describes data for most funds through February 2026 and offers an
Excel download. That is a stated dataset cutoff, not evidence that every financial
stage for every project has that coverage.[^cfudashboard]

**Transfer:** keep the distinction between promised resources, money entering a
fund and subsequent project flows. A page that looks current should never supply
an inferred current disbursement date. Preserve the reporting stage and the
institutional boundary across which money moves.

### CPI Global Landscape of Climate Finance

The examined 2025 methodology measures financial commitments and combines sources
at different levels of detail. Its treatment of financial intermediaries and
source prioritisation addresses double counting. Some granular commercial inputs
have access constraints; published aggregate openness does not guarantee open
record-level reproduction.[^cpi]

**Transfer:** an explicit aggregation perimeter and a documented representation
of the financing chain. A financing commitment can help characterise an investment
pipeline, but it cannot fill a missing disbursement observation. Reconciliation
must check stage, currency, instrument and coverage before comparing totals.

## Emissions and electricity observatories

### Carbon Monitor

Carbon Monitor's foundational data paper describes daily national and sectoral
CO₂ estimates using activity information and conversion methods. Daily resolution
does not mean direct measurement of each daily emission. The paper discusses
uncertainty and limitations in quantifying it at that frequency.[^carbon]

Its live site explains that historical values can change as inputs and methods
improve and asks reusers to identify the release date. The accessible page did not
provide a usable last-data-update value, so this report does not claim a current
daily cutoff or fully verified historical download archive.[^carbonlive]

**Transfer:** publish an indicator's estimation method, vintage and revision
history. High-frequency refresh is useful only where the evidence supports it;
it would not make infrequent financing documents into daily financial observations.

### Climate TRACE

Climate TRACE's March 2025 release explanation describes monthly updates with a
roughly 60-day lag, historical revisions and some explicitly projected values.
It points to archived versions and methodological release notes. The examined
2025 changelog provides concrete examples of revised methods and corrections;
that directory is an example of revision practice, not a claim about the latest
2026 release.[^trace][^tracechanges]

**Transfer:** corrections should state what changed, why and which series or
assets are affected. Preserve estimated and projected status. Asset-level
emissions may support external cross-checks, but an estimate alone cannot prove
that a named JETP investment caused a change or even identify that investment.

### Ember

Ember's electricity methodology documents national source choices and distinctions
between annual and monthly series, including differences in coverage and
measurement. Their totals need not coincide. The retrieved methodology was labelled
version 1.5; an indexed older version illustrates why the downloaded edition must
be pinned.[^ember]

The official API documentation provides a structured access route with signup/key
requirements and states CC BY 4.0 terms. Authenticated access was not exercised for
this comparison.[^emberapi]

**Transfer:** preserve national metadata before producing a common electricity
panel. For future modelling, generation, capacity, demand, imports and time
resolution require distinct fields and conversion rules. Annual totals cannot
provide an hourly load shape without an additional, labelled construction step.

## Policy monitoring and empirical research

### WRI Climate Watch and Climate Action Tracker

WRI Climate Watch brings together country emissions, policy targets and other
climate datasets for comparative exploration. Its value here is the composition
of multiple evidence families within country views. It should be treated as a
source of contextual datasets and metadata, with each underlying series retaining
its own provenance.[^wri]

Climate Action Tracker separately assesses dimensions including policies/action,
targets and fair-share considerations. These ratings are evaluations under an
explicit methodology. They are not raw observations of financing or physical
implementation and should never be imported as an unqualified project status.[^cat]

**Transfer:** a country synthesis can reconcile several evidence streams while
making their roles visible. Keep observation, target, projection and evaluative
judgement separate. Neither platform supplies a causal estimate simply by
placing countries beside each other.

### Oxford Climate Policy Monitor

The 2025 monitor covers 37 jurisdictions with information stated as of August
2025. South Africa, Indonesia and Vietnam appear in its jurisdiction list;
Senegal does not. Participating legal experts identify and describe policy tools,
responses about the same tool are matched, and a central team reconciles them
before evaluation. The method explicitly acknowledges incomplete public
information. Its dataset is CC BY 4.0.[^oxford]

**Transfer:** preserve individual descriptions and the reviewed resolution as
separate objects. Disagreement is useful research material, not merely a cleaning
error to discard. Coverage also needs its own object: the absence of Senegal from
this edition is a coverage boundary, not evidence of absent climate policy.

### OECD CAPMF and the Climate Policy Explorer research

The examined OECD CAPMF explanation describes a harmonised annual policy framework
with adoption and stringency measures; its April 2025 account covers 1990–2023.
The relative scoring and aggregation scheme are part of the measurement definition.
A stringency value is not a direct measure of policy effectiveness.[^capmf]

Stechemesser and colleagues' 2024 study links policy information to detected major
emissions reductions using an empirical design across countries and sectors.
The associated Climate Policy Explorer and replication deposit illustrate how
a policy database can support a separate analytical product. The deposit metadata
identify code for preprocessing, break detection, matching and figures.[^explorer][^replication]

**Transfer:** link a frozen policy panel, outcome panel, method and result package.
Do not transplant its identification design to four JETPs without studying
selection, anticipation, concurrent reforms, spillovers and independent treatment
units. Failure to detect a major emissions break is not evidence of zero effect
on a preparation or financing milestone.

This distinction is central to research integration. An observatory reports what
the evidence supports; a causal study additionally defines an estimand and defends
the counterfactual. Reproducible preprocessing makes that defence inspectable,
but it cannot supply the defence by itself.

## Reusable engineering and modelling approaches

### Our World in Data ETL

OWID documents successive stages from preserved upstream snapshots through
format conversion and harmonisation to publication datasets. Its workflow provides
a concrete model for making derived data depend on identified source inputs.
The ETL repository's inspected licence is MIT.[^owid][^owidlicense]

**Transfer:** borrow the staging, metadata and dependency pattern. Extend the
existing Make/DVC contracts so a new source edition invalidates only the affected
derivations and identifies narratives needing review. Reusing OWID's entire
publication platform would introduce requirements that this observatory does not
currently have.

### Kausal Watch

Kausal Watch's public repository describes an application for managing action
plans, with a Django/PostgreSQL backend, API and a separate frontend. The repository
uses AGPL 3.0 and notes optional private extensions. This is a candidate for a
future operational collaboration need rather than a substitute for independent
documentary research.[^kausal]

**Transfer:** consider collaborative action/progress workflows only if maintainers
need structured contributions from programme owners. An owner-entered progress
report should still enter as an attributed assertion. Adding such a service today
would change deployment and editorial operations without resolving the present
historical-evidence gaps.

### Open Energy Platform

Open Energy Platform uses dataset metadata and scenario bundles to link studies,
publications, models and quantitative inputs/outputs. This is the clearest examined
precedent for connecting a future modelling arm to research provenance.[^oep]

Its database distinguishes reviewed scenario material from a draft area that is
explicitly unversioned and volatile. Simply linking to a table is therefore not
enough to freeze a study dependency. Capture a specific version or immutable
snapshot and record its status.[^oepdatabase]

**Transfer:** study, model, scenario and dataset are distinct objects with explicit
links. Adopt relevant metadata concepts without requiring an OEP deployment or
knowledge-graph service. The Open Energy Ontology is a candidate terminology
source when broader energy-system concepts enter scope.[^oeo]

### PyPSA and PyPSA-Earth

PyPSA-Earth's current repository describes global energy-system workflows including
sector coupling, with open-source inputs and support for custom data. This makes
it a relevant candidate for the future electricity research arm and possible later
extensions. Its advertised geographic reach does not establish validated data
quality for any particular country or study.[^earth]

PyPSA's component and network formats provide an interchange boundary, including
netCDF exports. That boundary would allow model artifacts to remain distinct from
the documentary tables while their manifests link to shared evidence.[^pypsa]

**Transfer, if modelling begins:** use a separate versioned scenario and run
package. Record source editions, conversions, defaults, assumptions, aggregation,
environment and results. A model's representative bus or aggregated generator
need not correspond one-to-one to a source-listed asset.

### powerplantmatching

Powerplantmatching combines and harmonises power-plant databases for energy-system
analysis. Its repository distinguishes MIT software from data licences and
documents operations including capacity scaling to reconcile totals.[^matching]

**Transfer, when needed:** evaluate it as an adapter and candidate-matching tool.
Record the match evidence and retain original external identifiers. A harmonised
capacity belongs to a derived modelling dataset with its transformation history;
it should not replace a source-reported capacity in the observatory. Confidence
in a match must also be separate from confidence in each matched attribute.

### Open Contracting Data Standard

OCDS records collect releases about a contracting process and can provide a
compiled release. This directly addresses the relation between a sequence of
updates and a convenient current representation. Its published schema and merge
rules make that relationship inspectable.[^ocds][^ocdsmerge]

**Transfer:** publish both the supporting history and a derived state with pinned
rules. Our reconciliation problem is harder where several sources disagree about
one occurrence. Compilation must follow explicit adjudication and compatible
measurement coverage; chronology alone is insufficient to determine truth.

## Reuse priorities

The following priorities are recommendations inferred from the comparison, not
claims that integration has already been demonstrated.

| Priority | Reuse target | Practical next step | Decision boundary |
|---|---|---|---|
| Present design | TUFF and Oxford methods | Specify evidence acceptance, independent assertions, reconciliation and coverage | Adapt to JETP questions and local official inventories |
| Present design | IATI, PROV-O, SKOS and OCDS concepts | Write a small versioned semantic profile and lineage contract | No wholesale ontology or platform migration |
| Present design | OWID publication pattern | Put study exports alongside website outputs in the dependency/release model | Keep current stores and build tools |
| Conditional implementation | Climate Policy Radar annotations | Evaluate passage extraction on a small multilingual, manually labelled sample | Promote reviewed assertions, not raw classifier output |
| Conditional data acquisition | GEM, Ember, policy panels | Write pinned adapters and reviewed identity/definition crosswalks | Confirm coverage, rights, vintages and missingness before analysis |
| Future research only | OEP, PyPSA-Earth, powerplantmatching | Evaluate a country-specific modelling package if that work starts | No MVP feature, installation or model build implied |
| Future operational need only | Kausal Watch | Evaluate contributor roles and editing workflow | Adopt a service only for a demonstrated collaboration need |

Access and licensing affect reuse at different layers. Verified examples include
MIT for OWID ETL, Apache 2.0 for the examined Climate Policy Radar knowledge-graph
repository, and AGPL 3.0 for Kausal Watch. Those software licences do not grant
rights to all upstream documents or datasets. A public download route is not a
substitute for recording dataset-specific terms.[^owidlicense][^radarkg][^kausal]

## Implications for the backend and research practice

### Population and observation coverage

The backend needs separate representations of the source inventory, canonical
identity registry, official reporting perimeter and study frame. An inventory row
can be preserved before its identity or financing status is resolved. A frozen
study frame can include operations later cancelled, while a current official
portfolio may legitimately remove them. Neither should overwrite the other.

Document availability is an observation process. A new web publication can reveal
an old milestone; that is not necessarily new implementation progress. Coverage
records should state what was sought and where, and distinguish no report found
from a report stating no progress. Country comparisons must consider different
publication practices, languages and local access routes alongside substantive
differences in transition performance.

### Meaning and measurement

Financial allocation, approval, signature, transfer and expenditure describe
different events or positions. Project, programme, component and physical unit
describe different counting units. A harmonised dictionary should explain the
chosen meanings while retaining each source's words and qualifiers. Ambiguous
source concepts can remain unresolved without blocking publication of a clearly
attributed source position.

Every imported series needs its population, geography, unit, temporal basis,
method and vintage. A measured zero differs from no reported value. An annual
total, cumulative position and period flow require different aggregation rules.
These distinctions are necessary both for an honest country card and for a valid
cross-country dataset.

### Reproducibility and interpretation

Freeze research protocols and their admissible evidence dates alongside analytical
inputs. Study exports should retain inclusion/exclusion reasons, observation
windows and endpoint uncertainty. Released estimates and figures need their code,
configuration and dependency hashes; substantive narrative interpretations need
supporting and contrary evidence links.

Qualitative research should use the same source archive. Coding schemes,
excerpt-level annotations and interpretive revisions can remain lightweight
versioned artifacts. Preserving disagreement makes it possible to study how
institutions define and report progress, as well as whether milestones advance.

Correction handling must reach all products. The relevant question is not just
which country-page number changes, but which study population, estimate, figure
or case interpretation depends on the corrected assertion. An earlier frozen
release remains reproducible; a new analysis or correction receives a new version.

### Future migration

Whole-transition observation would introduce many assets and outcomes outside
JETP programmes, including demand, infrastructure, policy and distributional
effects. Those domains should enter through explicit extensions and external
dataset contracts. Keep country selection independent from website navigation,
and programme affiliation independent from physical identity.

A possible future electricity model should consume a frozen evidence edition and
explicit scenario assumptions. Its generated build, dispatch or emissions results
remain simulated values. An optimisation comparison between scenarios is not
automatically an empirical causal estimate of a policy's effect. The current
design only needs to preserve that conceptual boundary and a migration path.

Small reviewed tables and narrative files can remain in Git, while larger future
arrays, time series and spatial artifacts can be versioned externally with
checksummed manifests. Choosing a database service or a particular large-data
format should follow observed workload needs. Nothing in the comparison requires
such a migration for the present JETP MVP.

## Evidence limits

This comparison assesses documented methods, public interfaces and selected
repository materials. It does not establish runtime performance, complete
cross-country coverage, successful authenticated API access or a working model.
No external dataset has been empirically joined to the JETP registry for this
review, and no replication package or PyPSA scenario has been executed.

The selected cases span finance, assets, emissions, policy, publication engineering
and modelling; they are not an exhaustive census of transition observatories.
Current pages and older methodology editions coexist. The source inventory records
the examined version or date where available, and unresolved access or version
questions remain explicit. The appropriate conclusion is a supported set of
design precedents and candidate adapters, not a claim of ready-made scientific
sufficiency.

## Sources


- Global Energy Monitor. [Global Integrated Power Tracker](https://globalenergymonitor.org/projects/global-integrated-power-tracker). August 2026 citation on examined page.
- AidData. [Tracking Loans and Grants from China Globally: TUFF 4.0 Methodology](https://www.aiddata.org/publications/tracking-loans-and-grants-from-china-globally-4-0-methodology). 2025-11-18.
- Climate Policy Radar. [What we do](https://www.climatepolicyradar.org/what-we-do). Living page; accessed 2026-09-14.
- Climate Funds Update. [Notes and methodology](https://climatefundsupdate.org/about-us/notes-and-methodology/). Undated living page; some historical definitions retained.
- Climate Policy Initiative. [Global Landscape of Climate Finance 2025: Methodology](https://www.climatepolicyinitiative.org/wp-content/uploads/2025/06/Global-Landscape-of-Climate-Finance-2025-Methodology.pdf). 2025; PDF cover July 2025; flow methods pp. 24–26.
- Liu et al. / Scientific Data. [Carbon Monitor, a near-real-time daily dataset of global CO2 emission from fossil fuel and cement production](https://www.nature.com/articles/s41597-020-00708-7). 2020-11-09; Scientific Data 7, 392.
- Climate TRACE. [What to know about Climate TRACE’s monthly data updates](https://www.climatetrace.org/news/what-to-know-about-climate-traces-monthly-data-updates). 2025-03-27.
- Ember. [Electricity data methodology](https://files.ember-energy.org/public-downloads/ember_electricity_data_methodology.pdf). Retrieved document labelled v1.5; country methods and annual/monthly distinctions.
- World Resources Institute. [Climate Watch](https://www.wri.org/initiatives/climate-watch). Living initiative page; accessed 2026-09-14.
- Climate Action Tracker. [CAT rating methodology](https://climateactiontracker.org/methodology/cat-rating-methodology/). Living methodology; accessed 2026-09-14.
- Lecavalier, Gupta, Hale and Wetzer / Oxford Climate Policy Hub. [Climate Policy Monitor methodology](https://climatepolicymonitor.ox.ac.uk/methodology). 2025 edition; information as of August 2025.
- OECD. [The Climate Actions and Policies Measurement Framework (CAPMF)](https://www.oecd.org/en/data/insights/data-explainers/2025/04/the-climate-actions-and-policies-measurement-framework-capmf.html). 2025-04-24 explanation; 1990–2023 coverage in examined edition.
- Stechemesser et al. / PIK publication repository. [Climate policies that achieved major emission reductions: Global evidence from two decades](https://publications.pik-potsdam.de/pubman/faces/ViewItemOverviewPage.jsp?itemId=item_30172_4). Science, 2024; DOI 10.1126/science.adl6547.
- Our World in Data. [ETL workflow](https://docs.owid.io/projects/etl/architecture/workflow/). Living documentation; accessed 2026-09-14.
- Kausal. [Kausal Watch repository](https://github.com/kausaltech/kausal-watch). Project README; accessed 2026-09-14.
- Open Energy Platform. [Database topics](https://openenergyplatform.org/database/). Living page; accessed 2026-09-14.
- PyPSA meets Earth. [PyPSA-Earth repository](https://github.com/pypsa-meets-earth/pypsa-earth). Main branch; accessed 2026-09-14.
- PyPSA contributors. [powerplantmatching repository](https://github.com/PyPSA/powerplantmatching). Project README; accessed 2026-09-14.
- Open Contracting Partnership. [Records reference](https://standard.open-contracting.org/latest/en/schema/records_reference/). OCDS 1.1.5.
- Global Energy Monitor. [Global Coal Plant Tracker](https://globalenergymonitor.org/projects/global-coal-plant-tracker). July 2026 edition cited by project page.
- Global Energy Monitor. [Maps repository README](https://raw.githubusercontent.com/GlobalEnergyMonitor/maps/main/README.md). Main branch; accessed 2026-09-14.
- AidData. [Tracking Chinese Loans and Grants: TUFF 4.0 Methodology](https://docs.aiddata.org/reports/chasing-china/Tracking_Chinese_Loans_and_Grants_TUFF_4_Methodology.pdf). 2025; see date guidance around printed pp. 55–56 and 181.
- Climate Policy Radar. [Knowledge graph repository](https://github.com/climatepolicyradar/knowledge-graph). Main project page; accessed 2026-09-14.
- Climate Policy Radar. [Knowledge graph methodology](https://github.com/climatepolicyradar/methodology/blob/main/knowledge-graph-methodology.md). Main branch; accessed 2026-09-14.
- Climate Funds Update. [Data dashboard](https://climatefundsupdate.org/data-dashboard/). Most funds through February 2026 per page.
- Carbon Monitor. [Carbon Monitor live data site](https://carbonmonitor.org/). Accessed 2026-09-14; current data cutoff not established.
- Climate TRACE Coalition. [Methodology changelogs](https://github.com/climatetracecoalition/methodology-documents/tree/main/2025/CHANGELOG). 2025 directory; accessed 2026-09-14.
- Ember. [API documentation](https://api.ember-energy.org/docs). Living documentation; accessed 2026-09-14.
- Stechemesser et al. / Zenodo. [Replication materials for Climate policies that achieved major emission reductions](https://zenodo.org/records/12773811). 2024 deposit; record 12773811.
- Our World in Data. [ETL licence](https://raw.githubusercontent.com/owid/etl/master/LICENSE). Master branch; accessed 2026-09-14.
- Open Energy Platform. [Scenario Bundles](https://openenergyplatform.org/scenario-bundles/main). Living page; accessed 2026-09-14.
- Open Energy Platform. [Open Energy Ontology](https://openenergyplatform.org/ontology/). Living project; accessed 2026-09-14.
- PyPSA contributors. [Import and Export](https://docs.pypsa.org/latest/user-guide/import-export/). Living documentation; page shows 2026-01-26 update.
- Open Contracting Partnership. [Merging](https://standard.open-contracting.org/latest/en/schema/merging/). OCDS 1.1.5.

[^gemintegrated]: Global Energy Monitor. [Global Integrated Power Tracker](https://globalenergymonitor.org/projects/global-integrated-power-tracker). August 2026 citation on examined page.

[^tuff]: AidData. [Tracking Loans and Grants from China Globally: TUFF 4.0 Methodology](https://www.aiddata.org/publications/tracking-loans-and-grants-from-china-globally-4-0-methodology). 2025-11-18.

[^radar]: Climate Policy Radar. [What we do](https://www.climatepolicyradar.org/what-we-do). Living page; accessed 2026-09-14.

[^cfu]: Climate Funds Update. [Notes and methodology](https://climatefundsupdate.org/about-us/notes-and-methodology/). Undated living page; some historical definitions retained.

[^cpi]: Climate Policy Initiative. [Global Landscape of Climate Finance 2025: Methodology](https://www.climatepolicyinitiative.org/wp-content/uploads/2025/06/Global-Landscape-of-Climate-Finance-2025-Methodology.pdf). 2025; PDF cover July 2025; flow methods pp. 24–26.

[^carbon]: Liu et al. / Scientific Data. [Carbon Monitor, a near-real-time daily dataset of global CO2 emission from fossil fuel and cement production](https://www.nature.com/articles/s41597-020-00708-7). 2020-11-09; Scientific Data 7, 392.

[^trace]: Climate TRACE. [What to know about Climate TRACE’s monthly data updates](https://www.climatetrace.org/news/what-to-know-about-climate-traces-monthly-data-updates). 2025-03-27.

[^ember]: Ember. [Electricity data methodology](https://files.ember-energy.org/public-downloads/ember_electricity_data_methodology.pdf). Retrieved document labelled v1.5; country methods and annual/monthly distinctions.

[^wri]: World Resources Institute. [Climate Watch](https://www.wri.org/initiatives/climate-watch). Living initiative page; accessed 2026-09-14.

[^cat]: Climate Action Tracker. [CAT rating methodology](https://climateactiontracker.org/methodology/cat-rating-methodology/). Living methodology; accessed 2026-09-14.

[^oxford]: Lecavalier, Gupta, Hale and Wetzer / Oxford Climate Policy Hub. [Climate Policy Monitor methodology](https://climatepolicymonitor.ox.ac.uk/methodology). 2025 edition; information as of August 2025.

[^capmf]: OECD. [The Climate Actions and Policies Measurement Framework (CAPMF)](https://www.oecd.org/en/data/insights/data-explainers/2025/04/the-climate-actions-and-policies-measurement-framework-capmf.html). 2025-04-24 explanation; 1990–2023 coverage in examined edition.

[^explorer]: Stechemesser et al. / PIK publication repository. [Climate policies that achieved major emission reductions: Global evidence from two decades](https://publications.pik-potsdam.de/pubman/faces/ViewItemOverviewPage.jsp?itemId=item_30172_4). Science, 2024; DOI 10.1126/science.adl6547.

[^owid]: Our World in Data. [ETL workflow](https://docs.owid.io/projects/etl/architecture/workflow/). Living documentation; accessed 2026-09-14.

[^kausal]: Kausal. [Kausal Watch repository](https://github.com/kausaltech/kausal-watch). Project README; accessed 2026-09-14.

[^oepdatabase]: Open Energy Platform. [Database topics](https://openenergyplatform.org/database/). Living page; accessed 2026-09-14.

[^earth]: PyPSA meets Earth. [PyPSA-Earth repository](https://github.com/pypsa-meets-earth/pypsa-earth). Main branch; accessed 2026-09-14.

[^matching]: PyPSA contributors. [powerplantmatching repository](https://github.com/PyPSA/powerplantmatching). Project README; accessed 2026-09-14.

[^ocds]: Open Contracting Partnership. [Records reference](https://standard.open-contracting.org/latest/en/schema/records_reference/). OCDS 1.1.5.

[^gemcoal]: Global Energy Monitor. [Global Coal Plant Tracker](https://globalenergymonitor.org/projects/global-coal-plant-tracker). July 2026 edition cited by project page.

[^gemmaps]: Global Energy Monitor. [Maps repository README](https://raw.githubusercontent.com/GlobalEnergyMonitor/maps/main/README.md). Main branch; accessed 2026-09-14.

[^tuffmanual]: AidData. [Tracking Chinese Loans and Grants: TUFF 4.0 Methodology](https://docs.aiddata.org/reports/chasing-china/Tracking_Chinese_Loans_and_Grants_TUFF_4_Methodology.pdf). 2025; see date guidance around printed pp. 55–56 and 181.

[^radarkg]: Climate Policy Radar. [Knowledge graph repository](https://github.com/climatepolicyradar/knowledge-graph). Main project page; accessed 2026-09-14.

[^radarmethod]: Climate Policy Radar. [Knowledge graph methodology](https://github.com/climatepolicyradar/methodology/blob/main/knowledge-graph-methodology.md). Main branch; accessed 2026-09-14.

[^cfudashboard]: Climate Funds Update. [Data dashboard](https://climatefundsupdate.org/data-dashboard/). Most funds through February 2026 per page.

[^carbonlive]: Carbon Monitor. [Carbon Monitor live data site](https://carbonmonitor.org/). Accessed 2026-09-14; current data cutoff not established.

[^tracechanges]: Climate TRACE Coalition. [Methodology changelogs](https://github.com/climatetracecoalition/methodology-documents/tree/main/2025/CHANGELOG). 2025 directory; accessed 2026-09-14.

[^emberapi]: Ember. [API documentation](https://api.ember-energy.org/docs). Living documentation; accessed 2026-09-14.

[^replication]: Stechemesser et al. / Zenodo. [Replication materials for Climate policies that achieved major emission reductions](https://zenodo.org/records/12773811). 2024 deposit; record 12773811.

[^owidlicense]: Our World in Data. [ETL licence](https://raw.githubusercontent.com/owid/etl/master/LICENSE). Master branch; accessed 2026-09-14.

[^oep]: Open Energy Platform. [Scenario Bundles](https://openenergyplatform.org/scenario-bundles/main). Living page; accessed 2026-09-14.

[^oeo]: Open Energy Platform. [Open Energy Ontology](https://openenergyplatform.org/ontology/). Living project; accessed 2026-09-14.

[^pypsa]: PyPSA contributors. [Import and Export](https://docs.pypsa.org/latest/user-guide/import-export/). Living documentation; page shows 2026-01-26 update.

[^ocdsmerge]: Open Contracting Partnership. [Merging](https://standard.open-contracting.org/latest/en/schema/merging/). OCDS 1.1.5.
