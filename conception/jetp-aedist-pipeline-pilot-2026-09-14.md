# Imagine: JETP as a pilot of the AEDIST data pipeline

14 September 2026. Report only: no pilot implementation, new tickets, upstream
changes or automated research campaigns are launched by this note.

JETP can be a demanding production pilot of AEDIST's method: turn fragmented
sources into persistent, revisable, auditable statistical knowledge. The website
is one consumer and a public inspection surface. The experiment is the evidence
pipeline that feeds it, alongside the academic papers.

## What the upstream projects actually support

The original [AEDIST repository](https://github.com/MinhHaDuong/aedist) exposes
query → extraction → reconciliation/evaluation against an expert inventory.
Its upstream README and repository metadata were inspected on September 14;
its last reported push is April 2, 2026. Its plant-versus-unit distinction is
especially relevant to JETP's programme/component/asset problem. Its global
matching design separates identity matching from attribute-error measurement.
That is a useful principle, not a ready-made financial-project crosswalk.

The [technical-report masterplan](https://github.com/MinhHaDuong/aedist-technical-report/blob/660f26fa1f03bec3431e2d69b6f6bd29995b4a29/MASTERPLAN.md)
was read from current upstream, together with STATE. It treats the method as
the whole acquisition, extraction, reconciliation and verification chain, with
the model one parameter. It proposes incremental fusion, a master/provenance pair,
source triage, changed-cell verification and human-ratified reusable rules.
The specification explicitly limits v0 fusion to tables; scalar facts and richer
event histories remain future extensions. JETP should test these extensions,
not claim their transferability is already established by the thermal-plant
benchmark. The older local August JETP Imagine note was too categorical in
saying the architecture and fragment taxonomy transfer unchanged.

The technical report's phase-boundary policy is another strong import:
[acquire, consolidate, render, write](https://github.com/MinhHaDuong/aedist-technical-report/blob/660f26fa1f03bec3431e2d69b6f6bd29995b4a29/docs/pipeline-phases.md).
Preserve each phase's handoff so rebuilding a figure does not trigger new
acquisition or paid model calls. The current JETP offline export already moves
in this direction.

**AIRLET remains an unresolved source in this assessment.** Public-repository,
web and local CNRS searches found no identifiable project specification. Two
local notes mention it, but neither is an authoritative AIRLET design document.
A repository/path clarification has been requested. The user's statement that
these projects share a way of thinking is the premise; I cannot yet attribute
particular mechanisms or findings to AIRLET.

## The shared idea, and the useful challenge

My interpretation of that shared thinking is a research process with durable
state: goals direct observation; observations propose changes; explicit checks
and human judgment admit or reject them; recorded decisions guide the next
observation. The same pattern can describe this collaboration, an extraction
benchmark, or a maintained statistical observatory. A conversational agent's
agreement is not evidence that the loop works: its proposals and evaluations
also need recorded inputs, reproducible checks and independent adjudication.

JETP is a particularly good stress test because plausible mistakes are subtle:
a programme is confused with a component, a conditional budget with financing,
a publication day with an event day, or a shared location with a legal entity.
The latest Senegal work supplies concrete examples of all four. Finding more
sources is not enough; the pilot must measure whether it preserves those
boundaries as sources accumulate.

## A bounded first pilot

Use Senegal's 43 reconciled identities as the operational cohort. Freeze the
pre-#1332 corpus and ledger, then replay the newly merged documents as an update
batch. The known result, including the ANER identity promotion and unresolved
Linguère vehicle join, is a development fixture, not a held-out accuracy test:
we have already inspected it. Reserve genuinely unseen later documents and
human-adjudicated cases for evaluation before tuning the extraction method.

The pilot question is: **can a new document produce a justified, inspectable
change to the ledger, with fewer serious errors and less human work than the
current assisted process?** It is not whether a model can regenerate a plausible
43-row list.

Candidate acceptance cases include:

- ANER Annex 23 gains confirmed identity support; its conditional budget remains
  a need and does not duplicate an existing amount.
- Linguère's BOAD approval remains attached to its documented operation; shared
  geography does not silently promote the Champions Nationaux/JETP join.
- PUELEC's three-village report stays component-scoped, with observation timing
  separate from the unknown individual commissioning dates.
- Failed retrievals remain access observations; an unreceived document cannot
  prove inactivity or non-financing.
- Replaying an accepted source causes no duplicate facts. A correction produces
  an explicit supersession/conflict record and an intelligible monthly delta.

## What to import, adapt and measure

| Mechanism | JETP adaptation | Pilot evidence |
|---|---|---|
| Incremental master + fragment updates | Preserve append-only claims/events; derive a current view without erasing disagreements | Replay/idempotence, correction handling, order-sensitivity probe |
| Cell provenance and atomic validation | Every published factual field points to a source snapshot, passage, transformation and decision | Grounding coverage and independent passage checks |
| Source triage | Separate discovered, retrieved, accepted-for-use and rejected/contextual records | No candidate source silently becomes validated evidence |
| Human-ratified rules | Typed aliases, unit conversions, date roles and identity boundaries with scope and rationale | Rule acceptance, false matches, escalation and minutes per accepted change |
| Gold-reference benchmarking | Adjudicated document-to-claim cases plus a held-out update batch | Claim precision/recall, attribute errors and mistaken entity joins |
| Phase handoffs and run records | Frozen raw documents/replies → candidate claims → adjudicated ledger → published edition | Offline rebuild and source-to-figure trace |

Do not literally copy the masterplan's one-authoritative-source-per-cell rule
into the evidence layer: financial documents can make compatible claims at
different scopes, and contradictory claims need to survive. A selected current
value can have one decision provenance, while the supporting/opposing claims
remain a many-to-many history. Also, maintain a discovery registry outside the
accepted-source vocabulary: JETP needs to publish blocked and unresolved routes.

Use identifiers and typed relations before considering a graph database. The
current CSV/Markdown/DVC arrangement can express this pilot; SQLite would be a
derived query convenience, not a solution to the epistemic problem. Reuse small
contracts/helpers only after checking their interfaces and licensing, rather
than transplanting the plant schema or entire benchmark package.

Measure the complete method against the current human-assisted baseline on the
same frozen material. Record exact model/tool versions, prompts, inputs, retries,
latency, expenditure and human minutes. Repeat stochastic runs. Report uncertainty
with document/project clustering where observations share sources; do not count
hundreds of cells from one table as hundreds of independent trials. Distinguish
failure to retrieve, failure to extract, false linkage and incorrect adjudication.
A cited claim can still be wrong, and agreement between agents is not a gold label.

Thresholds should be chosen before held-out evaluation, with a stricter policy
for unsupported approvals/payments and false entity merges than for missing
optional descriptions. On uncertainty, preserve an unresolved value. A single
weighted score must not hide a critical attribution failure behind cheap gains
in formatting or completeness.

## Options and publication value

**Recommended, high feasibility:** instrument the existing JETP pipeline and
run the Senegal replay plus one genuinely new update. This yields evidence on
transferability and maintenance effort without delaying the observatory.

**Medium feasibility:** implement a shared claim/adjudication contract across
JETP and AEDIST after the pilot exposes stable common requirements. The payoff
is reusable evaluation and provenance, but financial scopes differ from plant
attributes and premature unification would obscure that distinction.

**Low near-term feasibility:** begin with a universal autonomous knowledge graph
and multi-agent planner. This would test infrastructure before establishing the
scientific acceptance rules. Keep it an architectural hypothesis until the
bounded experiment shows which failure modes require it. These feasibility
judgments are qualitative assessments, not measured probabilities.

The JETP data paper can describe coverage, provenance and maintenance; an AEDIST
methods paper can test cross-domain transfer and the cost of reliable updates.
The substantive acceleration paper remains a separate question, requiring
comparable early-stage endpoints and an uncensored historical sampling frame.
Better extraction cannot manufacture its counterfactual. AIRLET's contribution
should be added after its actual design is available.
