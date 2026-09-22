# Review 3 — does the backend design implement the ontology, and is it sound (Opus, 2026-09-22)

## Mapping

| Draft kind | Design construct | Verdict |
|---|---|---|
| **Asset** | None. No `asset` in `subject_type` (L163–171) or the 35 record kinds (L248–257). Deferred to §12 (L1165). Yet §3 legislates "Asset counts exclude unknown and count-slot rows" (L227–229) and §10 tests "asset totals" (L1080) | **Absent, but already assumed.** Contradiction inside the design |
| **Project** | `entity` → `projects.csv`; classification = dated assertion `measure=entity_type` (L155–158) | Sound |
| **Programme** | Same entity kind, value `programme`, plus `component_of` in `entity-relations.csv` (L195–198) | Sound; draft agrees |
| **Proposition** | Split, never named: money side → `agreements.csv` ("a named financing proposal before signature", L183); project side → a reported position with `basis`=inventory membership (L50, L333) | Partially represented; **no landing place when no entity exists** |
| **Plan** | No table. = source edition (`source-editions.csv`) + `perimeters.csv` + inventory-membership positions; `plan-projects.csv` demoted to legacy staging (L82, L1006) | Sound, and matches the draft's own "not an entity" |
| **Agreement** | `agreements.csv` + `tranche_of` + `finances` (L179–200) | Sound as a registry; unusable as an event subject today (finding 2) |

## Findings

**1. The first executable metric has zero eligible rows. (gap, hardest)** §5 L615 starts with `gross_disbursement_original_currency_v1` "for one agreement or tranche". `events.csv` `financial_status` distribution today: signed 235, approved 65, announced 45, need 34, mou 1, **disbursed 0**. There is also no agreement column. So the metric's subject does not exist and neither does its movement class. §9 L1002 says "leave unidentifiable agreements unresolved" — consistent, but it means 0768 can only run on evidence not yet collected. The design never states that precondition.

**2. Draft "event is about an agreement" vs. design `subject_type`. (contradiction — the design is right, the draft is right about the metric)** Design allows entity/agreement/perimeter/country subjects (L163–171); `events.csv` keys to `project_id`. Forcing agreement subjects would fabricate an agreement per event, which L1002 forbids. But L615 then defines the flagship metric over a subject class no event uses. Resolution: keep the polymorphic subject, and say explicitly that an event becomes metric-eligible only once an accepted `finances`/`tranche_of` relation or an agreement subject exists.

**3. Draft "proposition becomes project" vs. stable identity. (contradiction — the design is right)** L155–157: classification is dated and "does not change observation keys". A proposition is not a pre-state of an identity; it is an assertion *about* one. But the design leaves the mechanism unsaid for `plan-projects.csv`'s 67 `matched` rows: `canonical_project_id` is exactly the draft's BECOMES, and neither `alias_of` nor `same_as` fits a plan line. It needs a named `identity` adjudication (the type exists, L601) crosswalked from that column. Unstated in §9 L1006.

**4. Propositions without an entity have nowhere to go. (gap)** 1 561 `plan_only` rows, Senegal's 38-submission/34-proposal conflict, Viet Nam's 21 count slots. L160 forbids count slots as subjects; L1079 forbids inventing entities; `subject_type` has no `inventory_row`. The only offered home is an aggregate against a perimeter (L160–161) — which **loses the per-row record `plan-projects.csv` keeps today**, and directly blocks ticket 0860 action 2 (descend from the 21 slots to their coverage lines).

**5. The 263 ZAF registry rows are unresolved. (gap)** The draft says these are closer to tranches. The classification vocabulary is `project|programme|component|unknown` (L157) — no `agreement` value — and L154 mandates preserving every `project_id` and route. So a row that is really a tranche can be neither reclassified nor moved. §9 is silent.

**6. Asset attributes are already in the data. (gap)** `implementation-events.csv` carries `capacity_mw` (15 rows) and retirement statuses keyed to `project_id`; `plan-projects.csv` carries `natural_retirement_year`/`estimated_retirement_year`. §12's "when those domains enter research scope" (L1165) is already past tense.

**7. ~29% of the new model serves the first metric. (over-engineering)** ~21 new CSV tables + ~8 YAML/JSON stores against 16 existing, for ~4 500 rows and one maintainer. The metric (L615–656) and the first fixture (L1054–1059) need agreements, perimeters, reported-positions, occurrences, adjudications(+members), evidence-links — 6. Unexercised: the editions triple (L448–450), watches/sweeps/checks/discoveries, `evidence-dependencies`, `entity-relations` half-open intervals (L190) for a parentage nobody has observed changing, the `same_as`/`alias_of` chain rules (L203–207) over a `projects.csv` that already has an `aliases` column, all 8 research stores (L482–592) for work §11 L1145 may DEFER, and the concept-mapping profile (L113–141) with no named consumer.

**8. §8's provenance index re-creates what ticket 0858 deleted. (contradiction with the served-view principle)** L836–838 mandates "an exported provenance index keyed by `claim_id`, with assertion IDs" and L840–852 a display-occurrence table with `json_pointer`/`page_route`. That is `by_source_id` one level up — the 874 kB materialised join 0858 removed by author decision. Reverse traversal over rendered HTML cannot be a read-time filter over served tables. Also L177 and L587 keep asking for SQLite indices that 0858 deferred to M2.

**9. Servable as-is / not. (sound, with two cautions)** Entity, agreements, perimeters, positions, events, event-timing, evidence-links, adjudications, editions all map one-file-one-table. Two break: the provenance/display index (above), and the "generated, validated cache" `review_status` columns (L283, L362) — a derived column copied onto another table. Volume: `ZAF.json` is 497.4 kB against a 512 000-byte cap; 1 628 plan lines yield ~3 100 positions before evidence links. Chunking one table across files (impl. plan L51–53) stays normal-form; say so.

**10. §9 omits three tables. (gap)** `news-leads` (18), `authority-coverage` (64), `vnm-pilot-manifest` (66) have no row in the migration table, though protocol step 1 (L107–109) requires their enumeration. Also: `need`, `announced` and `mou` (80 rows) have no named target `measure`; L307 names only signing/approval/disbursement.

## Three changes first

1. **Decide the entity-registry split before 0762.** Give each `projects.csv` row a migration disposition: entity, agreement/tranche (the ZAF register), or perimeter-count position (the 21 slots), behind route-preserving redirects — and add an `inventory_row` subject type so a proposition survives without an invented entity.
2. **Cut the MVP surface by half.** Drop from slices A–D: the editions triple (use an `edition_key` on the acquisition), `same_as` and chain-flattening, `evidence-dependencies`, the concept-mapping profile, and the display-occurrence contract. Keep the research stores as prose only; write no fixture for them.
3. **Reconcile §8 with 0858 explicitly.** State that the provenance index is a build-time validation artifact, never a served file, and that the site's climb stays a read-time filter over served tables — otherwise 0769 rebuilds the join the author just removed.
