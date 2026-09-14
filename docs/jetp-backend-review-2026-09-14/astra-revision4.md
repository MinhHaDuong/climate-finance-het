# Independent Astra review of backend design revision 4

Reviewed HEAD: `e801442211498a3d9b9f9d467dbcaf49cffc02ce`.
Date: 14 September 2026. Reviewer: GPT-6 Astra.
Phase: Plan, reviewing readiness to plan bounded implementation.

**Verdict: APPROVE for that purpose.** I found no design blocker in the
documentary accounting model or its integration with the present research
programme. One bounded provenance cardinality issue should be settled in the
export-schema ticket. This verdict does not approve an implementation, a release,
or a causal design, and is not a merge-gate result.

I read the design independently. I did not consult earlier Astra/Fable reports,
the four-scope assessment, comparables research, or revision responses. The
design itself names those documents; I did not follow those links. I made no
external requests, spawned no agents, and changed only this report.

## Assessment

The event/position/account separation is coherent. A reported cumulative amount
does not become a payment; a reported completed state does not invent a transition
date. The first financial metric has a bounded subject, original currency,
compatible opening, disjoint movement coverage, and an explicit completeness
decision before an exact closing or residual is available
(`docs/jetp-backend-design.md:283–328`, `:602–647`). It preserves the distinction
between a source error and an economic reversal. The contract permits honest
unavailability when the public record cannot support reconstruction. It does
not require a hidden lender ledger or a general accounting engine.

The identity and temporal rules are sufficient to design executable fixtures.
Typed references protect colliding legacy IDs; relationship rows own parentage;
an agreement can finance several entities without implying financial shares.
Occurrences separate payments from the documents reporting them. Immutable
corrections, admission and review cutoffs, and pending replacement semantics
protect historical queries (`:150–239`, `:285–300`, `:662–729`). The first schema
ticket still has to turn the stated decision-type cardinalities and version
resolvers into concrete contracts. Their absence as implemented columns is
explicitly acknowledged at `:243–257`, and is not evidence of a failed design.

Source management has distinct owners for source identity/revisions, watch
policy, a frozen sweep plan, checks, acquisitions, and discoveries. Check-linked
acquisitions distinguish the target page from a discovered document, while failed
and repeated attempts retain their own identities (`:334–392`, `:428–468`,
`:733–757`). The distinction between publisher authority and claim-level origin
is substantive: an official reprint can be secondary, and an interview can
originate a statement without establishing settlement. Dependencies can remain
unknown or cited-but-unacquired without manufacturing archived evidence
(`:394–424`). This supports bounded monitoring and attributed claims; it does not
pretend that a successful website check establishes national or project coverage.

Quantitative and qualitative research have a place in the same evidence system.
Protocols, historical frame decisions, observation attempts, endpoints, and
external dataset crosswalks are separate from official reporting perimeters.
Codebook revisions, passage annotations, competing codings, and substantive
interpretations also have declared ownership (`:479–567`). Runs and artifacts pin
inputs and methods, and manuscript occurrences extend website provenance rather
than requiring an unrelated research store (`:569–589`, `:865–893`). Those
contracts support source-to-publication replay and correction impact analysis,
subject to the display issue below. A frozen frame is not silently updated by a
new official inventory, and a source correction does not silently rerun a paper.

Standards reuse is proportionate at this stage (`:110–148`). The application
profile requires versioned, directional mappings and leaves evidential concepts
local when equivalence is unjustified. It does not require wholesale adoption or
an RDF service. I assessed this internal contract, not the external standards'
current documentation or eventual mapping conformance. Concept-level mappings
will need their own evidence when implemented.

The migration is compatible with the inspected current readers and headers, but
will require the proposed compatibility readers. The current harvester validates
an exact source header and unique `source_id`; the current exporter joins sources
to their latest manifest row and indexes timing by a bare event ID. Revision 4
explicitly replaces those assumptions rather than suggesting that extended CSVs
can be dropped into those readers unchanged (`:342–351`, `:974–1029`). The
crosswalk and publication-mode rules address duplicate ownership during a partial
migration. Beyond JETPs, the country-keyed partnership convention and local scope
vocabulary have an explicit future migration boundary. Physical assets, broader
transition datasets, and PyPSA remain future work (`:1128–1191`); none is needed
to begin the current bounded implementation.

## Actionable finding

**A4-1 — Medium: a payload location is not a unique display occurrence.**
Classification: bounded export-schema detail; not a blocker to planning the
implementation slices.

- **Evidence:** `docs/jetp-backend-design.md:829–835` gives each display a
  `page_route` and unique `display_id`, but says
  `(payload, json_pointer, rendering role)` identifies one occurrence. The
  generalised uniqueness statement at `:874–878` similarly uses publication,
  artifact, locator, and rendering role. Both omit the rendered route or local
  display instance, while `:834–835` requires finding every affected occurrence.
- **Failure case:** two pages of one website publication reuse
  `data/IDN.json#/country/headline` in a component with rendering role
  `country-card`. Their page routes and display IDs differ; the declared tuple
  is identical. A validator implementing that tuple rejects valid reuse, or a
  deduplicating index loses one rendered occurrence. A correction then cannot
  enumerate both pages from that index. Repeating the same component twice on
  one page exposes the same distinction at a smaller scale.
- **Minimal remedy:** make `(release, display_id)` the occurrence identity and
  allow several occurrences to share a data locator and role. Keep the route
  and, where necessary, a stable rendered-instance locator as occurrence
  attributes. Alternatively, define a composite occurrence key that includes
  those rendered locations. Apply the same identity rule to the website and
  generalised publication contracts; no new store is needed.
- **Discriminating acceptance case:** export two distinct display IDs on two
  routes with the same publication, payload artifact, JSON pointer, and role.
  Both must validate and be returned by reverse traversal after their common
  source assertion changes. Reusing a display ID within that release must fail.
  If one page can render the component twice, the two local instances must also
  remain separately identifiable.

I found no further issue that merits a design revision before bounded planning.
Decisions such as exact enum spellings, parser selection, table partitioning, and
future database capacity should remain with their implementation or research
work unless a fixture exposes a consequential contradiction.

## Scientific and validation limits

This architecture can preserve evidence and make derivations inspectable. It
cannot establish that an inventory is exhaustive, that two countries disclose
comparable milestones, that follow-up supports censoring, or that a comparison
identifies acceleration. Qualitative traceability likewise does not establish
the adequacy of case selection or the strength of an explanation. The separate
scientific gates at `docs/jetp-backend-design.md:1102–1126` are necessary, and the
current plan correctly leaves causal feasibility open.

This was a static design review with read-only inspection of migration surfaces.
I did not run the pipeline or test suite, acquire original sources, inspect
archive objects, or verify the current factual country totals. No implementation
tests can validate these unimplemented schemas. The acceptance cases in the
design and this report are specifications for later executable evidence; a
passing existing suite would not establish that these new contracts work.

## Inspected inputs

All repository paths below are relative to the reviewed worktree. This is the
complete list of repository files whose contents I inspected; file discovery
also listed names without reading them.

Design and existing contracts, read in full:

- `docs/jetp-backend-design.md`
- `docs/jetp-storage.md`
- `docs/jetp-tracking.md`
- `conception/jetp-observatory-and-papers-plan.md`

Migration surfaces:

- `scripts/jetp/build_observatory.py` — lines 1–135 and targeted text matches.
- `scripts/jetp/_observatory_data.py` — lines 1–85 and targeted text matches.
- `scripts/jetp/corpus_harvest_documents.py` — lines 1–235.
- `scripts/analysis/jetp_observatory.mk` — full file.
- `config/jetp_tracking.yaml` — full file.
- `data/jetp/projects.csv` — header only.
- `data/jetp/events.csv` — header only.
- `data/jetp/implementation-events.csv` — header only.
- `data/jetp/event-timing.csv` — header only.
- `data/jetp/sources.csv` — header only.
- `data/jetp/manifest.csv` — header only.
- `data/jetp/project-coverage.csv` — header only.
- `data/jetp/dry-searches.csv` — header only.
- `data/jetp/source-claims.csv` — header only.
- `data/jetp/plan-projects.csv` — header only.

Repository instructions inspected for applicability:

- `AGENTS.md`
- `.claude/rules/architecture.md`
- `.claude/rules/workflow.md`
- `.claude/rules/review-checklist.md`
- `.claude/rules/jetp-research.md`
- `.claude/rules/writing.md`
- `.claude/rules/git.md`

External local instructions inspected:

- `/home/haduong/.claude/rules/workflow.md`
- `/home/haduong/.claude/rules/prose/_all.md`
- `/home/haduong/.claude/rules/lang/en.md`

The explicit read-only review brief took precedence over generic instructions
to fetch, branch, run an implementation workflow, or publish review comments.
