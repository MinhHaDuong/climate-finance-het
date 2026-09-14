# Astra independent backend design review

Model: `gpt-6-astra`, effort high. Reviewed commit:
`962f4bb1ef65eaee564fa1f27cde1e8116c153f9`. Independent read-only review;
no Fable report supplied. Reviewer response preserved below.

---

Astra independent design review of commit `962f4bb1`. **Verdict: REVISE before implementing the reconciliation engine.** The architecture fits the intended product and existing backend. The principal gaps concern historical query semantics and accounting periods; they require design decisions, not a database replacement.

1. **High — Evidence cutoffs do not yet govern every input that changes an account.**
   References: `docs/jetp-backend-design.md:109`, `:153`, `:231`, `:274`, `:285`.

   Assertions have `recorded_at`, and adjudications have `reviewed_at`, but relationships carry only world-validity dates. Review metadata may change in place. The note does not define which timestamp establishes evidence eligibility, when supersession becomes effective, or how historical queries select identity mappings, occurrence assignments and reviews.

   **Failure scenario:** two payments are treated as distinct in August. September review identifies them as duplicate reports of one payment. Rebuilding from current tables with an August evidence cutoff can inherit September’s relationship or review state and change the historical total. A frozen August package remains reproducible, but that is a different capability from the promised two-cutoff account query.

   **Minimum repair:** define one historical selection algorithm covering assertions, adjudications and consequential relationship/review changes. Specify availability versus approval time, supersession eligibility at the selected cutoff, competing supersession branches, and retrospective correction treatment. Store consequential changes as dated revisions or adjudications rather than mutable metadata. Explain how migration represents unknown historical recording times. Add a test where September duplicate adjudication changes September’s account while preserving August’s result.

2. **High — Reporting-cutoff uncertainty and flow coverage share insufficient temporal fields.**
   References: `docs/jetp-backend-design.md:170`, `:184`, `:189`, `:247`.

   Positions support `period flow`, but expose only `as_of_start`, `as_of_end` and precision. These fields also represent an uncertain cutoff, such as “June.” A coverage interval and uncertainty about a point in time have different accounting meanings.

   **Failure scenario:** a report published in September states EUR 5m paid during April–June. Another states EUR 20m cumulative at June-end. Encoding both through the same interval convention leaves a consumer unable to distinguish the flow period from cutoff uncertainty. A payment whose possible date straddles the opening balance date also cannot safely be assigned wholly before or after it.

   **Minimum repair:** distinguish reporting cutoff bounds from flow coverage dates, with explicit boundary conventions. Define eligibility for movements whose timing overlaps the opening or closing boundary; unresolved overlap must not yield an exact reconstruction. Add fixtures for a quarterly flow, a month-precision cumulative position and an uncertain payment crossing the opening boundary.

3. **Medium — Source-edition mapping is required by the design but remains optional and lacks cardinalities.**
   References: `docs/jetp-backend-design.md:186`, `:205`, `:211`, `:386`, `:406`.

   Positions, perimeters and evidence require `report_edition_id`, yet the edition/snapshot index is introduced “if needed.” The existing catalogue identifies curated URLs; its publication metadata cannot represent successive editions at one URL. The proposed evidence row also repeats source, edition, acquisition and hash references without declaring their consistency rules.

   **Failure scenario:** an annual-report URL is refreshed to a corrected PDF. An evidence row combines the old document hash with the new acquisition or edition. Every individual identifier can resolve while the resulting provenance chain is false. A selected principal reference identified only by source ID also does not identify which report snapshot was selected.

   **Minimum repair:** make the edition/snapshot contract mandatory for snapshot-backed assertions. Define the relationships among logical publication, snapshot hash, source URL and acquisition attempt, including mirrors and unchanged retrievals. Require validators to check the complete tuple, with explicit handling for acquisitions that have no document. Bind principal/news selections to the selected edition or evidence record while preserving source IDs for compatibility.

4. **Medium — Typed subject keys depend on a classification that the migration permits to change.**
   References: `docs/jetp-backend-design.md:78`, `:84`, `:91`, `:199`, `:450`.

   The registry permits `entity_type=unknown`, but observation subjects must use `project`, `programme` or `component` and match that classification. There is no valid subject type for an unresolved legacy entity. Later reclassification can also invalidate existing assertions.

   **Failure scenario:** a legacy “project” is established to be a programme containing several components. Updating its registry type causes historical `subject_type=project` references to fail validation, despite the promise to retain assertions and stable IDs. Conversely, leaving it `unknown` prevents its observations from entering the proposed typed contract.

   **Minimum repair:** separate stable registry identity from revisable classification—for example, reference a registry entity and validate classification separately—or define versioned classification semantics. Specify how count slots remain addressable legacy records without becoming observation subjects representing inferred projects. Test unknown-to-programme classification and preservation of existing references and routes.

5. **Medium — Display provenance needs an explicit one-to-many location model.**
   References: `docs/jetp-backend-design.md:350`, `:357`, `:414`.

   The proposed index is keyed by stable `display_claim_id`, with one payload and JSON pointer. The same reviewed claim can appear on the homepage, country page, project page and download. The illustrative entry supports only one location, while the requirement is bidirectional traceability for every display.

   **Failure scenario:** the Indonesian headline appears in both overview and country JSON. Reusing its claim ID can overwrite one location; independently allocating IDs can split the dependency graph and leave one display outside correction detection.

   **Minimum repair:** choose either one semantic claim with multiple output locations, or distinct display occurrence IDs that reference one semantic claim. Make uniqueness and reverse lookup explicit. Test a correction that identifies both homepage and country-page uses, including an authored sentence supported by that claim.

Several choices are particularly sound:

- CSV and Markdown remain authoritative; SQLite and public JSON are disposable outputs. This uses the existing harvester and static exporter without introducing unnecessary operational infrastructure.
- Source assertions, underlying occurrences and generated accounts are distinguished. Preserving contrary evidence and publishing unresolved residuals is appropriate for documentary accounting.
- Agreement-to-project relationships are many-to-many, and hierarchy does not authorize allocating money. This avoids a major source of double counting.
- Original-currency decimals, explicit conversion provenance, separate financial and physical states, and protection against invented commissioning dates are well chosen.
- Country cards retain their sole principal-reference link while summaries draw on all reviewed evidence. The proposed compatibility alias acknowledges the current frontend without treating that link as exhaustive support.
- The migration preserves IDs, source rows and legacy crosswalks. Frozen input commits followed by descriptor commits also avoid the self-referential release hash problem.

Before assigning implementation tickets, the author should settle three further decisions:

- **The first account metric.** Select one narrow example, such as gross original-currency disbursement for an agreement. Its executable definition should specify opening-balance requirements, movement eligibility, cancellation/refund treatment, rounding or uncertainty, and perimeter compatibility. Currency equality and a shared perimeter label are necessary but insufficient evidence of comparability.
- **Occurrence and relationship ownership.** Decide whether occurrence membership is generated entirely from adjudications or stored canonically. Likewise, choose one owner for tranche parentage: it currently appears both in `parent_agreement_id` and `tranche_of` relationships. Derived duplicates are acceptable with enforced consistency.
- **The migration publication boundary.** State whether releases during migration expose reconciled accounts only for migrated subjects or temporarily support both representations. The ownership switch must prevent the legacy event and its new position from appearing as two independently counted observations.

The design is not fundamentally overengineered: most proposed structures support explicit research requirements. Avoid turning its generic adjudication and metric concepts into a general-purpose rule engine before demonstrating one complete account. Resolve the two high-severity temporal issues and tighten the key contracts above, then implement the proposed bounded slices.
