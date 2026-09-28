# Independent Astra review — causal map of ICF and CO₂

28 September 2026. Review of `carte-causale-icf-co2.md` v0.4 by GPT-6 Astra.
The reviewer read the complete working document and made no edits. The
consolidated graph was checked mechanically: 56 nodes, 122 arcs, acyclic. This
checks graph syntax, **not** the truth of the causal assumptions. Bibliography
and numerical orders of magnitude were not verified in this review.

## Overall judgment

The A (allocation and measurement), B (electricity), C (land use) modules and
their bridges are a useful **hypothesis map** for a narrow question: effects of
international climate finance on recipient-country CO₂. Substantive changes
are needed before using its arrows as the coding ontology for REL or presenting
them as established mechanisms. The REL bibliometric map is an empirical map
of publications; this DAG is a proposed model of mechanisms. Neither validates
the other by itself.

## What this review has, and has not, established

The findings below address two different objects. Items about outcome
definitions, equations, arrows, suggested designs, and search rules are
**findings about the present working document**. They can be checked directly
against its text. Items about how published studies measure finance, use
regressions, identify effects, or leave questions open are **questions for the
REL reading and coding pass**. Astra did not systematically inspect the
literature, so these are not yet findings about the field.

| Object | What the review can establish now | What REL must test with papers |
|---|---|---|
| Causal hypothesis map | Internal consistency of outcomes, time order, arrows, accounting boundaries, and proposed identification logic | Which mechanisms studies actually posit or investigate |
| Literature map | Whether the proposed coding rules would misclassify types of contribution | How many works study ontology, data, associations, credible effects, or counterfactual models; where they sit in measured bibliometric currents |
| Field-level claim | No prevalence or absence claim follows from this review alone | Search and code a defined sample, record contrary cases and uncertainty, then state bounded conclusions |

The practical bridge is a **crosswalk**, not a merger of the two maps: link
each bibliometrically located work to its question, variables, data, method,
estimand claimed, estimand supported, and any mechanism represented by a DAG
path. A paper may have no corresponding path and still be central to REL.

## Findings, in priority order

1. **High — Outcomes may double-count and mix territorial with consumption
   accounting** (`carte-causale-icf-co2.md:55`, `:388`, `:550`, `:597`). Y2
   includes 1.A.2.f while Y3 adds it for the full construction channel; their
   sum therefore need not be a total. Apparent cement consumption includes
   imports and is not the territorial process-emissions outcome initially
   defined. Define mutually exclusive inventory outcomes first, then map
   channels onto them. If a consumption footprint is useful, name it as a
   separate estimand. See [IPCC cement guidance](https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/3_Volume3/V3_2_Ch2_Mineral_Industry.pdf).

2. **High — The coding system can turn associations into causal arrows**
   (`:15–18`, `:615–623`, `:653`, `:679–680`, `:701`, `:713`). A finance–emissions
   regression does not estimate a direct DAG edge. Even an identified total
   effect runs over paths, not one arrow. The YAML example names an engagement
   arrow while coding disbursements and names Y1 as the outcome while its arrow
   ends at capacity. Separate `question`, `relationship_studied`,
   `estimand_claimed`, `estimand_supported`, and `identification_assumptions`.
   Allow ontology, measurement, descriptive association, effect claim and
   model mechanism as distinct contributions. Papers can occupy several of
   those categories.

3. **High — Some proposed designs do not identify the stated effect**
   (`:539–552`, especially `:546–547`). Commercial and concessional tranches
   within one project differ in risk, seniority, currency, maturity and
   guarantees; the commercial tranche can itself respond to blended finance.
   That comparison decomposes financing terms, not the project's
   no-concessional-finance counterfactual. An IDA threshold also changes other
   assistance. For each design, state intervention, counterfactual, first
   stage, exclusion restriction and competing treatment changes. Replace the
   universal credibility rank with an assessment conditional on assumptions.

4. **High — Negative controls are stated too generally** (`:558–560`).
   Adaptation can affect power demand or resilience; land finance can affect
   electricity through shared budgets and policy; future finance may respond
   to current emissions. Treat leads and cross-module placebos as candidate
   diagnostics, with exclusion and timing assumptions specified for each
   intervention and horizon.

5. **High — Dynamic methods cannot remove latent confounding by themselves**
   (`:48`, `:518–537`, `:667`). Marginal structural models and g-formula methods
   address treatment–confounder feedback under assumptions including adequate
   control of confounding, positivity and consistency. They do not solve the
   admitted latent governance problem. Draw a time-indexed DAG before
   prescribing adjustment; qualify the blanket statements about mediators
   and GDP. See [Hernán and Robins, *What If*](https://www.hsph.harvard.edu/miguel-hernan/wp-content/uploads/sites/1268/2024/04/hernanrobins_WhatIf_26apr24.pdf).

6. **High — NLP recoding cannot reveal 'real finance' on its own**
   (`:146–150`, `:162–181`, `:583–585`). A classifier gives a reproducible
   estimate under a chosen definition. It cannot establish expenditure,
   additionality, climate share or the market subsidy of a financing package.
   Separate classification, valuation, timing and additionality errors;
   validate classifications against reviewed projects and carry uncertainty.

7. **Medium — Budget interventions and additionality need distinct estimands**
   (`:152`, `:166–168`, `:192`, `:198–199`, `:512`). A fixed-envelope shift and
   an increase in total funding answer different questions. A normative
   accounting benchmark is also distinct from the causal substitution response
   of other aid to climate finance. Name each intervention and avoid treating
   contemporary total-envelope conditioning as universally required.

8. **Medium — Physical relations need explicit units and time**
   (`:342–350`, `:378–388`, `:401`). The capacity-to-generation bound needs a
   time conversion. The J-curve formula needs definitions of stock, additions,
   growth and retirements. Construction emissions should follow construction
   flows, not automatically surviving capacity stocks. Separate territorial
   CO₂ from lifecycle CO₂e.

9. **Medium — Direction and magnitude claims outrun assumptions**
   (`:230`, `:370`, `:407`, `:554`, `:572`, `:666`). Earlier land payments may
   influence later outcomes; a lower WACC does not automatically mean more
   investment or lower emissions; fossil-finance omitted-variable bias has no
   universal sign. Time effects absorb homogeneous global changes, not every
   heterogeneous exposure. Remove unsupported order-of-magnitude claims and
   state timing and sign assumptions.

10. **Medium — Search saturation does not establish map completeness**
    (`:679–717`). Searching only from existing arrows can miss whole literatures
    and ontologies. An arc absent from the retrieved set is a corpus gap, not
    necessarily a literature gap. Record searches, dates, exclusions, citation
    tracing and out-of-map works; display disagreement and identification
    assessments separately from study counts.

## Revision order and role in REL

Revise **outcome boundaries → coding ontology → identification claims → search
validation**. Keep the distinctions between commitments and disbursements,
reclassification and additionality, and the attention to spillovers. In REL,
use the diagrams as a transparent lens mainly for the **models** layer and for
checking claims in the **evidence** layer. The full review also requires
ontology and data studies, non-causal statistics, adaptation and other work
outside these CO₂ diagrams. Verify each bibliographic claim before citation.
