# Fable independent backend design review

Model: `claude-fable-5-1`, effort high. Reviewed commit:
`962f4bb1ef65eaee564fa1f27cde1e8116c153f9`. Independent review of the
approved document packet; no Astra report supplied. Tools disabled.
Reviewer response preserved below.

---

# Design review — `docs/jetp-backend-design.md` @ 962f4bb1

Scope: the note as a plan, checked against the storage and tracking contracts, the current CSV headers, the exporter and the harvester. I did not run anything.

## Findings, by priority

### F1 — `report_edition_id` is a foreign key to a table that may not exist (High)

Lines 124, 186, 213 make `report_edition_id` a field of `perimeters.csv`, `reported-positions.csv` and `evidence-links.csv`. Line 206 says "introduce an edition/snapshot index **if needed**". Three tables reference an optional entity, and the "unknown typed references fail validation" gate (L500–502) then has nothing to resolve against.

The same rows also carry `source_id`, `acquisition_id` and `document_sha256` (L213–214). Those four overlap: an acquisition already fixes source and hash; an edition fixes source and publication date. Nothing says which one is the anchor when they disagree. Concrete case: a `not_modified` manifest row copies `sha256` and `storage_path` from the prior material row (harvester L307–317). An evidence link pointing at that acquisition, plus a mirror `source_id` with the same bytes, yields two evidence IDs, two acquisitions, one hash and possibly one or two editions — and L367 wants the independence count to be one.

**Repair.** Make the edition index a required table in slice 1 (`source-editions.csv`: `report_edition_id, source_id, publication_date, publisher, document_sha256, derived_from_edition_id`). Declare `document_sha256 + locator` the evidence anchor; `acquisition_id` is provenance context, validated to be a manifest row with that hash; `report_edition_id` is resolved from `(source_id, sha256)` and validated, not free-entered. `acquisition_id` can be assigned deterministically today as `(source_id, retrieved_at)`: the harvester uses one timestamp per run and visits each source at most once (L394–406), so the key is unique without renumbering.

### F2 — Period flows sit in positions but are the movements that quarterly reports actually supply (High)

`basis` lists "period flow" as a position (L189). The account reconstructs closing = opening + "documented movements" from the event journal (L241–242, L247–250). Most official reporting gives "disbursed USD 12m in Q2" and no individual payments. Under the note as written that flow is never a movement, so every quarter-report-only country is permanently non-reconstructible, while a country with both a flow and three itemised payments in the same interval double-counts if a later reader treats the flow as a movement.

**Repair.** In the metric dictionary, define a period-flow position whose `[as_of_start, as_of_end]` lies inside the account interval as an eligible movement, and require an adjudication (`decision_type = flow_covers_occurrences`) whenever the same interval also contains occurrences of the same measure. Add this pairing to the first test fixture (L482–485), which currently covers two sources of one payment but not flow-versus-itemised overlap.

### F3 — Timing and evidence keys share one column across ID namespaces (High)

`event-timing.csv` is keyed by `event_id` and the exporter accepts either an `event_id` or an `implementation_event_id` in that column (`build_observatory.py` L28). Line 454 extends timing to positions and recording history. Nothing makes the three ID spaces disjoint: a position or implementation event whose ID equals an event ID silently steals or merges its timing row (`unique_rows` only rejects *differing* rows with the same key, L35–43). The note already uses `record_kind + record_id` for evidence links (L217); timing must do the same.

**Repair.** Either key timing by `(record_kind, record_id)`, or mandate a prefix per table (`evt-`, `imp-`, `pos-`, `agr-`) enforced by the validator and add "cross-table ID uniqueness" to the L500–502 list. Prefer prefixes: cheaper, and they make every `record_id` self-describing in provenance exports.

### F4 — "Evidence-availability cutoff" is not pinned to a recorded timestamp (Medium)

Line 238 generates accounts at an evidence-availability cutoff; L274–277 describe the axis as "when that evidence became available to this system". Two candidates exist: acquisition `retrieved_at` and assertion `recorded_at` (L153). A document retrieved in July and coded in September gives different July accounts under each reading, so L494–495 ("account at an earlier evidence cutoff remains reproducible") is untestable. Worse, `review_status` is a mutable field under "narrowly controlled changes" (L285–286) with no timestamp, so a status flip from rejected to accepted is invisible to any cutoff except by mining Git — which L287 says should not be necessary.

**Repair.** Define the cutoff as `recorded_at` of the assertion (a document not yet coded is not system knowledge); `retrieved_at` stays available for "could have known" analysis. Make `recorded_at` immutable. Make review-status changes adjudication rows (they carry `reviewed_at`, L232) and treat the assertion's `review_status` as a validator-checked cache. Also forbid supersession forks: two live assertions superseding the same parent.

### F5 — `occurrence_id` on the event row duplicates the duplicate-occurrence adjudication (Medium)

Line 163 puts an `occurrence_id` on the assertion; L234 says duplicate occurrences are decided in `adjudications.csv`. That is one fact in two editable places, which L471 forbids, and it mutates an append-only evidence row (L285). There is also no occurrence table, so an occurrence has no key of its own and cannot be referenced by the account's "contributing occurrence IDs" (L244) without depending on a column that reconciliation rewrites.

**Repair.** Occurrence = adjudication of type `duplicate_occurrence`; `occurrence_id` is the `decision_id`, members are the assertions. Drop the column from events, or declare it a generated cache the validator regenerates.

### F6 — Perimeter identity is coupled to a report edition (Medium)

`perimeters.csv` carries `report_edition_id` (L124). If that is part of identity, the South Africa "implementing/completed register" perimeter gets a new ID each quarter and "compatible perimeter" (L247–248) is undefined between quarters; every Q1→Q2 comparison needs a human adjudication of perimeter compatibility, which defeats the purpose of stable IDs.

**Repair.** State that `perimeter_id` is edition-independent; `report_edition_id` records where the definition was first published. Same ID ⇒ presumed compatible; divergence in a later edition is a `perimeter_compatibility` adjudication (already listed at L235) plus a new perimeter with `successor_of`.

### F7 — Currency conversion has no record type, and mixed-currency perimeters are then never reconstructible (Medium)

Accounts are generated "for a currency" (L237); conversions need "rate, date, source and rounding rule" (L257) — but no table or assertion type holds a rate, and L501 fails incompatible currencies. South Africa's USD allocations against EUR/ZAR tranche disbursements are the normal case, not the exception.

**Repair.** Slice 1: accounts are single-currency and computed in original currency only; converted figures (legacy `amount_usd`, `conversion_method`) are retained as reported observations excluded from sums, as the tracking contract already says (L188–189). If cross-currency accounts are wanted later, an exchange rate is a reported position (`measure = fx_rate`, subject `partnership`, with evidence link), and the conversion is a derivation citing that position ID. Do not add a rates service.

### F8 — No magnitude rule for canonical money (Medium)

Money is "a decimal string plus currency" (L61–62); counts have a declared unit (L149); the worked example says "EUR 20m" and the derivation `format-money-billions` (L423) implies raw values in full units — but nothing states it. Extraction from a table headed "USD million" will produce `3.92` next to a hand-coded `3920000000`.

**Repair.** One sentence: canonical `value_decimal` for money is in whole currency units; scale is a display derivation; `value_qualifier` covers rounded source figures. Add a migration check on legacy `amount_original`.

### F9 — `same_as` is symmetric; routing needs a direction (Medium)

L114 lists `same_as`; L118 wants old IDs retained as aliases/redirects; L78 preserves public routes. A symmetric relation gives the exporter no canonical target, and chains A→B→C plus B→A pass an acyclicity check on `successor_of` but not on `same_as`.

**Repair.** Use `alias_of` (directed, single canonical target, target never itself an alias). Keep `same_as` only as a review-stage hypothesis that must be resolved to `alias_of` or `overlaps` before release.

### F10 — Derivative-source relationships have no store (Low)

L368 requires derivative reports to retain their upstream relationship and L208 admits mirrors. `sources.csv` has no such field; `entity-relations.csv` targets subjects only (L84–92). The F1 repair (`derived_from_edition_id` on the edition index) closes this; a `source` from/to type in relations is the alternative.

### F11 — `perimeter_id` is required on every assertion (Low, proportionality)

L142 requires `perimeter_id` on each event or position, including a single tranche payment or a component's status. Membership is supposed to be relation rows (L129), so this duplicates data and forces migrating several hundred legacy events with a field they cannot honestly carry. Require it only for `partnership`/`perimeter` subjects; keep `scope` for attribution on project- and agreement-level assertions.

### F12 — `parent_agreement_id` and `parent_perimeter_id` duplicate `tranche_of`/`parent` relations (Low)

L100, L123 versus L114 and L63 ("use relationship rows"). Pick one; I would keep the column on `agreements.csv` (tranche→agreement is 1:1 and cheap) and drop `tranche_of` from relations, or the reverse — not both.

### F13 — Three classification axes on money events without a cross-validation table (Low)

`financial_status` (legacy vocabulary), `measure` and `amount_basis` (L176–180) can contradict each other (`disbursed` + `agreement_face_value`). The metric dictionary should carry the allowed triples and state which `amount_basis` values feed which account.

## Sound choices

- CSV + Markdown + DVC with SQLite as disposable export (L11–15) is the right size; no new service.
- Two evidence layers with positions distinct from events (L17–27), "opening + movements only for compatible measure and perimeter" (L247–250), the EUR 5m residual (L252–256) and the SA 257/257 example (L260–265) are exactly the right documentary stance.
- Adjudications as records, `unresolved` as publishable (L231–235, L297–300).
- Editions never rewritten, descriptor in a later commit (L328, L380–381); the provenance index must not hash itself, which the current wording allows.
- `record_kind + record_id` polymorphic evidence links (L217), `support_role` including contradicting evidence.
- Principal/news source-role split surviving the JSON handoff (L386–412) and the compatibility alias for `headline_source`.
- Retaining `not_modified` and failed acquisitions; deterministic acquisition keys exist for free (see F1).

## Open author decisions

1. Default aggregation level for counts and stage tallies when programmes, components and `unknown`-typed rows overlap (L80–82, L131, L496–497): count `project` + `programme` and exclude components, or require an explicit level per export?
2. Cross-currency accounts at all (F7), or original-currency only for the first editions?
3. Deterministic ID composition for extracted positions: `(sha256, locator, measure)` orphans rows when a parser fix moves a locator; acceptable via supersession, or hash the source row content instead?
4. Whether `adjudication-members` needs a fixed role vocabulary now (L234 names "roles" without listing them).
5. Slice 1 ordering: build the L482 fixture with hand-written rows *before* mass crosswalks, so the schema is proven on a dozen rows rather than discovered during Vietnam RMP ingestion.

## Verdict

**REVISE.** The architecture is correct and proportionate; the defects are schema-level and cheap to fix in the note: F1–F3 change primary/foreign keys that every later slice depends on, F4–F6 decide what "as of" and "same" mean. With those seven items resolved in text, the note is ready to seed the 0726–0728 handoffs. F8–F13 can be folded into the same edit or deferred to the metric dictionary.
