# JETP backend design: assessment under four research scopes

## Overall judgement

**Retain the architecture; revise its scientific contract.** The design's separation
of event assertions, reported positions and derived reconciled accounts is sound.
Git for reviewed tables and interpretation, the existing DVC archive for source
bytes, and generated publication artifacts remain proportionate to the present
programme. The comparison does not justify replacing them with an operational
database service or a knowledge-graph platform.

Revision 2 is a credible observatory design. It is only partly integrated as a
research backend: several requirements for the already agreed papers occur solely
in section 11, outside the main storage, release and dependency contracts. Its
future expansion path also needs clarification because country, partnership and
reporting scope are currently coupled. These are design revisions to discuss
together, rather than grounds for extending the MVP.

| Review scope | Verdict | Proposed disposition |
|---|---|---|
| Existing open ontologies and standards | Relevant reusable standards exist; no single examined standard covers this entire evidence problem | Define a small application profile and explicit mappings |
| Integration of present research needs | Compatible architecture, incomplete integration | Bring protocols, frames, observation coverage and research outputs into the main contracts |
| Comparable projects and tools | Strong precedents support the architecture and expose methodological risks | Borrow selected methods and interfaces; avoid adopting a whole platform |
| Future whole-transition coverage and PyPSA | Evolution is plausible, but not demonstrated by the present schemas | Document extension boundaries and migration triggers only |

The reviewed baseline is [backend design revision 2](../jetp-backend-design.md).
The supporting [comparison report](comparables.md) separates documented capabilities
from recommendations. Recommendations below are architectural judgements; they
are not claims that the proposed contracts have been implemented or tested.

## 1. Existing open ontologies and standards

The right approach is an **application profile**: a small local vocabulary with
documented links to established concepts. An exchange standard, a terminology
system and a formal ontology solve different problems. Calling all three an
ontology would obscure what can actually be reused.

| Source | Useful contribution | Boundary of reuse |
|---|---|---|
| IATI Activity Standard | Activities, participating organisations, budgets, transactions, dates and related activities | An XML exchange standard; a publisher's activity need not equal a physical asset or our research unit[^iati] |
| W3C PROV-O | Entities, activities, agents and derivation relations for provenance | Describes lineage; does not itself decide whether an economic claim is true[^prov] |
| W3C SKOS | Concept identifiers, labels and mappings between vocabularies | Mapping strength must be reviewed; similar words do not establish equivalence[^skos] |
| W3C OWL-Time | Temporal instants, intervals and relations | Our bounds for uncertain event dates still need an explicit local interpretation[^time] |
| Open Contracting Data Standard | Successive releases and a compiled record for one contracting process | A close journal/status precedent; publisher update merging cannot adjudicate conflicting independent sources[^ocds] |
| Open Energy Ontology | Energy-system and modelling terminology | Relevant to future sector coverage; select terms as needed rather than importing its whole structure[^oeo] |
| FIBO | Formal financial concepts | Consult for specific instrument semantics when needed; full adoption is disproportionate here[^fibo] |

The profile should record `local_term`, definition, value type/unit where relevant,
external concept or code, external version, mapping relation, explanation and
review status. Pin the actual external identifier during implementation; a link
to an ontology's homepage is not a field-level mapping. Keep original source
terminology alongside the normalised term. A Vietnamese allocation label and a
South African register category may remain related but non-equivalent concepts.

The most important local extensions concern evidential status: an assertion about
a payment, a reported cumulative position, an adjudicated occurrence, an unresolved
overlap and an observation gap. A financial transaction definition cannot erase
those distinctions. In particular, official inventories should remain the starting
point for JETP membership even when an external database supplies useful enrichment.

**Proposed revision:** add the profile to sections 2–4 and its version to release
descriptors. Map only terms already used by the MVP. Make linked-data export
possible later; no RDF store, ontology reasoner or broad financial ontology is
needed now. The explanatory glossary on the website should derive from the same
reviewed definitions, with simpler display wording where appropriate.

## 2. Integration of the current research programme

The concern about section 11 is substantiated by the document's structure.
[Section 2](../jetp-backend-design.md#2-stores-formats-and-authority) lists the
authoritative stores without study protocols, frames or analysis products.
[Section 8](../jetp-backend-design.md#8-full-traceability-to-the-web-page) ends its
trace at website claims. Section 9 calls research frames and exposures a separate
extension. Section 11 then specifies useful contracts, but does not integrate
their ownership and dependencies into these earlier sections.

The remedy is more than moving paragraphs. The scientific products need the same
explicit ownership and change rules as the public account:

| Contract | Authoritative input | Derived product and dependency |
|---|---|---|
| Study definition | Versioned protocol with question, unit, eligibility, endpoints and evidence policy | Every study export identifies the exact protocol revision |
| Historical population | Frame definition plus reviewed inclusion/exclusion decisions and evidence | Frozen membership export; current project status cannot silently change eligibility |
| Observation process | Search/coverage attempts, routes, sought evidence and outcomes | Defensible observation windows and documented gaps |
| Quantitative analysis | Frozen inputs, transformation definitions, run configuration and environment | Episodes, estimates, tables and figures retain input IDs and output hashes |
| Qualitative analysis | Versioned codebook, excerpt annotations and source-backed interpretive claims | Case narratives and comparative tables retain contrary evidence and coding revisions |
| Research publication | A release descriptor referencing all relevant dependencies | Paper claims and exhibits resolve to a frozen dataset and its source evidence |

The qualitative row matters for the existing political-economy paper. Section 11
is dominated by duration and causal analysis. The longer paper also needs
traceable thematic coding, competing explanations and case selection. That can
use Markdown interpretation, excerpt locators and typed links in the existing
architecture. It does not require installing qualitative-analysis software or
creating a second document corpus.

The central dependency should be stated once:

> Saved source → extraction → assertion → reviewed identities and decisions →
> frozen evidence edition → publication-specific derivation → published claim.

For the observatory, the final derivation produces an account or narrative and a
display occurrence. For a study, it produces a frame, episodes or coded cases,
then analytical results and manuscript exhibits. Both branches must support
reverse impact tracing. Correcting a source should identify affected studies and
figures; an already released paper package must remain reproducible under its
original evidence and policy versions.

Three distinctions must survive this integration. An official reporting perimeter
is different from a study's eligible population. A milestone date is different
from the date it became observable. A correction of historical evidence is
different from an amendment of the research protocol. Store the reason and
version for each change instead of relying on a Git diff to explain its meaning.

**Proposed revision:** move the research store definitions, typed references,
update rules and output lineage into sections 1–9. Retain a shorter final section
on scientific feasibility and go/no-go decisions. No estimator should be chosen
by the backend design. A causal interpretation remains conditional on evidence,
comparability and identification assumptions; reproducing an estimate does not
establish its validity.

Integration is needed in the design now. Implementation can remain staged:
capture the source and observation information that would be costly to reconstruct
later, and implement study-specific exports with the relevant research tickets.
The website release need not wait for a completed causal analysis.

## 3. Lessons from comparable projects and tools

The [comparison matrix](comparison.csv) covers 18 project/tool families. Their
usefulness differs by task; a single overall ranking would be misleading.

**For reconstructing documentary evidence,** AidData's TUFF methodology is the
closest research precedent. It formalises reconstruction from fragmented public
sources. Global Energy Monitor adds a useful distinction between structured
asset inventories and documented histories. These support ingesting complete
official inventories and enriching them, rather than equating readily found
project webpages with the empirical population.[^tuff][^gemcoal]

**For adjudication,** Oxford's Climate Policy Monitor provides a particularly
clear precedent: independent descriptions of the same policy are matched and
reconciled before evaluation. Climate Policy Radar contributes passage-level
annotation and evaluated concept extraction. Automated discovery should therefore
feed candidate assertions; accepted identity, financial and physical findings
remain separate reviewed decisions.[^oxford][^radarkg]

**For finance,** Climate Funds Update and CPI show why the accounting boundary
must be explicit. The examined CPI landscape tracks commitments; Climate Funds
Update separates several fund-flow stages and warns about incomplete disbursement
information. Their numbers cannot be interchangeable entries in one JETP progress
ladder.[^cpi][^cfu]

**For publication engineering,** Our World in Data's staged ETL is the closest
pattern: preserved source snapshots feed harmonised datasets and publication
outputs. Open Contracting supplies a useful release/record model. Neither requires
copying its complete software stack to adopt the principle.[^owid][^ocds]

**For future energy-system work,** Open Energy Platform connects studies,
scenarios, models and datasets. PyPSA-Earth is a relevant candidate workflow,
whose current documentation includes sector coupling as well as electricity.
These are future integration references, not additions to the present delivery
plan.[^oep][^earth]

The comparison also exposes a recurring research risk: apparently harmonised
datasets carry different units, coverage rules and measurement conventions.
Ember, for example, documents differences between annual and monthly electricity
series. No automatic join should convert the presence of a common country code
and unit into evidence that two measures are comparable.[^ember]

**Proposed revision:** add a short precedent-and-reuse rationale to the design,
backed by the separate research note. Prefer vocabulary mappings, adapters,
quality checks and release patterns. Evaluate a larger service only when a
concrete operational need exceeds the current workflow.

## 4. Future expansion beyond JETPs

The future question is the whole energy transition across a defensible set of
comparable countries, with a possible PyPSA electricity modelling arm. It includes
physical systems, demand, policy, finance and social consequences. An expanded
financing register would cover only part of that question. An electricity model
would also cover only part of it.

The present architecture can evolve in that direction, but three assumptions
should be marked as JETP-specific before they become permanent identity rules:

1. Section 3 resolves a `partnership` subject to a country code. A country can
   contain several initiatives, while an initiative or physical system can cross
   borders. Future initiative IDs and jurisdiction links must be separable;
   existing country routes and IDs can survive through explicit crosswalks.
2. The two permitted `scope` values describe current JETP research boundaries.
   Keep them as a profile, not the universal vocabulary for future energy data.
   Programme affiliation is a sourced, dated relationship, not a condition for
   the existence of an asset, policy or observation.
3. The current entity registry accommodates projects and programmes but does not
   explicitly distinguish every physical unit, site, financing operation and
   analytical unit. Future types must extend the registry without reinterpreting
   existing project identifiers as generators or model components.

These provisions do not require adding empty registries now. The revision should
name the assumptions, explain the crosswalk strategy and reserve schema-versioned
extension. Selecting comparable countries remains study-specific; present-day
income labels or JETP participation should not silently define every future sample.

### The future PyPSA boundary

PyPSA supports component tables, time-dependent attributes and network exports,
including netCDF. Its import documentation also notes that omitted values can
receive defaults. Consequently, a future importer would need an explicit
assumption record whenever source evidence is missing; an import default must
not become an apparent observation.[^pypsa]

A possible future modelling package would identify its evidence edition, network
construction and aggregation rules, input series, weather and demand assumptions,
cost basis, scenario constraints, code/environment and solver configuration,
termination status, and result artifacts. A many-to-many crosswalk would link
observed assets to model components. These are requirements to revisit if that
research starts, not fields to add to today's MVP.

Observed, externally estimated, scenario-assumed and simulated values need distinct
roles. A model's cost-optimal build is neither a reported investment commitment
nor a causal estimate of JETP acceleration. Model results can inform a new
interpretation, but must not overwrite documentary facts. Powerplantmatching's
capacity harmonisation is a useful example of a legitimate modelling transformation
that belongs downstream of preserved source values.[^matching]

### Storage and scale

Keep reviewed metadata and small documentary tables in Git. A future time-series
or spatial workload may justify columnar, array or geospatial artifacts in a
versioned object store, with manifests pointing to them. NetCDF is a candidate for
PyPSA networks; specific formats for other data should follow actual workloads.
A database for concurrent editing or larger queries can later implement the same
logical contracts, with one declared source of authority during migration.

Do not promise scale from the logical diagram alone. Revisit storage when measured
build times, file sizes, memory use, collaborative write conflicts or access needs
make the current arrangement inadequate. Static website payloads can remain small
even when their underlying research datasets become large. No numerical capacity
claim is supported by this review because no workload benchmark was performed.

## Consolidated revision package

| Proposed change | Design sections | Timing |
|---|---|---|
| State observatory and present research products as consumers of one evidence base | 1 | Next design revision |
| Add the minimal standards profile and mapping/version rules | 2–4, 6 | Next design revision; only used concepts implemented |
| Integrate protocol, frame, observation-process and qualitative contracts | 2–4, 6–7 | Design now; implementation follows research tickets |
| Extend traceability and frozen releases through study exports, results and paper claims | 7–8, 10 | Design now; validate with each output implementation |
| Revise migration ordering so research-critical history is preserved during ingestion | 9 | Next design revision |
| Retain scientific go/no-go conditions in a shorter final research section | 11 | Next design revision |
| Document separation of country, initiative, physical asset and research unit | 3, 9, future-extension subsection | Migration provision only |
| Describe future external datasets and modelling artifacts, including PyPSA | Future-extension subsection | Migration provision only; no present implementation |

The most discriminating future implementation checks are substantive examples:
a changed official inventory leaves a frozen historical study population intact;
a source correction identifies both affected website claims and manuscript
exhibits; a changed concept mapping is versioned without altering original labels;
and a modelling assumption can never enter a reported-finance aggregate.
The modelling example is a conceptual extension check today, not an MVP test task.

**Sufficiency assessment:** the revised contracts would provide a coherent backend
for the present observatory and research programme, subject to implementation and
empirical coverage. They would preserve a credible migration route to broader
transition research. They would not establish causal identification, guarantee
cross-country data comparability or constitute a validated electricity model.

## Sources


- IATI. [Activity Standard](https://iatistandard.org/en/iati-standard/203/activity-standard/). 2.03.
- W3C. [PROV-O: The PROV Ontology](https://www.w3.org/TR/prov-o/). 2013-04-30 Recommendation.
- W3C. [SKOS Simple Knowledge Organization System Reference](https://www.w3.org/TR/skos-reference/). 2009-08-18 Recommendation.
- W3C. [Time Ontology in OWL](https://www.w3.org/TR/owl-time/). Living page; accessed 2026-09-14.
- Open Contracting Partnership. [Records reference](https://standard.open-contracting.org/latest/en/schema/records_reference/). OCDS 1.1.5.
- Open Energy Platform. [Open Energy Ontology](https://openenergyplatform.org/ontology/). Living project; accessed 2026-09-14.
- EDM Council. [Financial Industry Business Ontology](https://spec.edmcouncil.org/fibo/). Living project; accessed 2026-09-14.
- AidData. [Tracking Loans and Grants from China Globally: TUFF 4.0 Methodology](https://www.aiddata.org/publications/tracking-loans-and-grants-from-china-globally-4-0-methodology). 2025-11-18.
- Global Energy Monitor. [Global Coal Plant Tracker](https://globalenergymonitor.org/projects/global-coal-plant-tracker). July 2026 edition cited by project page.
- Lecavalier, Gupta, Hale and Wetzer / Oxford Climate Policy Hub. [Climate Policy Monitor methodology](https://climatepolicymonitor.ox.ac.uk/methodology). 2025 edition; information as of August 2025.
- Climate Policy Radar. [Knowledge graph repository](https://github.com/climatepolicyradar/knowledge-graph). Main project page; accessed 2026-09-14.
- Climate Policy Initiative. [Global Landscape of Climate Finance 2025: Methodology](https://www.climatepolicyinitiative.org/wp-content/uploads/2025/06/Global-Landscape-of-Climate-Finance-2025-Methodology.pdf). 2025; PDF cover July 2025; flow methods pp. 24–26.
- Climate Funds Update. [Notes and methodology](https://climatefundsupdate.org/about-us/notes-and-methodology/). Undated living page; some historical definitions retained.
- Our World in Data. [ETL workflow](https://docs.owid.io/projects/etl/architecture/workflow/). Living documentation; accessed 2026-09-14.
- Open Energy Platform. [Scenario Bundles](https://openenergyplatform.org/scenario-bundles/main). Living page; accessed 2026-09-14.
- PyPSA meets Earth. [PyPSA-Earth repository](https://github.com/pypsa-meets-earth/pypsa-earth). Main branch; accessed 2026-09-14.
- Ember. [Electricity data methodology](https://files.ember-energy.org/public-downloads/ember_electricity_data_methodology.pdf). Retrieved document labelled v1.5; country methods and annual/monthly distinctions.
- PyPSA contributors. [Import and Export](https://docs.pypsa.org/latest/user-guide/import-export/). Living documentation; page shows 2026-01-26 update.
- PyPSA contributors. [powerplantmatching repository](https://github.com/PyPSA/powerplantmatching). Project README; accessed 2026-09-14.

[^iati]: IATI. [Activity Standard](https://iatistandard.org/en/iati-standard/203/activity-standard/). 2.03.

[^prov]: W3C. [PROV-O: The PROV Ontology](https://www.w3.org/TR/prov-o/). 2013-04-30 Recommendation.

[^skos]: W3C. [SKOS Simple Knowledge Organization System Reference](https://www.w3.org/TR/skos-reference/). 2009-08-18 Recommendation.

[^time]: W3C. [Time Ontology in OWL](https://www.w3.org/TR/owl-time/). Living page; accessed 2026-09-14.

[^ocds]: Open Contracting Partnership. [Records reference](https://standard.open-contracting.org/latest/en/schema/records_reference/). OCDS 1.1.5.

[^oeo]: Open Energy Platform. [Open Energy Ontology](https://openenergyplatform.org/ontology/). Living project; accessed 2026-09-14.

[^fibo]: EDM Council. [Financial Industry Business Ontology](https://spec.edmcouncil.org/fibo/). Living project; accessed 2026-09-14.

[^tuff]: AidData. [Tracking Loans and Grants from China Globally: TUFF 4.0 Methodology](https://www.aiddata.org/publications/tracking-loans-and-grants-from-china-globally-4-0-methodology). 2025-11-18.

[^gemcoal]: Global Energy Monitor. [Global Coal Plant Tracker](https://globalenergymonitor.org/projects/global-coal-plant-tracker). July 2026 edition cited by project page.

[^oxford]: Lecavalier, Gupta, Hale and Wetzer / Oxford Climate Policy Hub. [Climate Policy Monitor methodology](https://climatepolicymonitor.ox.ac.uk/methodology). 2025 edition; information as of August 2025.

[^radarkg]: Climate Policy Radar. [Knowledge graph repository](https://github.com/climatepolicyradar/knowledge-graph). Main project page; accessed 2026-09-14.

[^cpi]: Climate Policy Initiative. [Global Landscape of Climate Finance 2025: Methodology](https://www.climatepolicyinitiative.org/wp-content/uploads/2025/06/Global-Landscape-of-Climate-Finance-2025-Methodology.pdf). 2025; PDF cover July 2025; flow methods pp. 24–26.

[^cfu]: Climate Funds Update. [Notes and methodology](https://climatefundsupdate.org/about-us/notes-and-methodology/). Undated living page; some historical definitions retained.

[^owid]: Our World in Data. [ETL workflow](https://docs.owid.io/projects/etl/architecture/workflow/). Living documentation; accessed 2026-09-14.

[^oep]: Open Energy Platform. [Scenario Bundles](https://openenergyplatform.org/scenario-bundles/main). Living page; accessed 2026-09-14.

[^earth]: PyPSA meets Earth. [PyPSA-Earth repository](https://github.com/pypsa-meets-earth/pypsa-earth). Main branch; accessed 2026-09-14.

[^ember]: Ember. [Electricity data methodology](https://files.ember-energy.org/public-downloads/ember_electricity_data_methodology.pdf). Retrieved document labelled v1.5; country methods and annual/monthly distinctions.

[^pypsa]: PyPSA contributors. [Import and Export](https://docs.pypsa.org/latest/user-guide/import-export/). Living documentation; page shows 2026-01-26 update.

[^matching]: PyPSA contributors. [powerplantmatching repository](https://github.com/PyPSA/powerplantmatching). Project README; accessed 2026-09-14.
