# Review 1 — internal consistency and fit to the data (Opus, 2026-09-22)

**1. The ZAF register line is a funder tranche, not a project. [blocks]**
`projects.csv`: 257 `zaf-register-*` rows whose id prefix is a funder code (`uk`×70, `gr`×43, `us`×35, `nl`/`eu`/`fr`×20, `dk`×17, `sw`, `can`, `afdb`, `idc`, `sp`, `fp`, `actip` — 14 codes). Each has exactly one event in `events.csv` (257 of 257; none with 0 or >1). Only **166 distinct `canonical_name`**, and even (name, funder) gives only 206 pairs: "Municipal Climate Resilience Programme" is 21 rows across 5 funders, 11 of them US. The same rows appear in `deliverables/jetp-observatory/data/m1a/ZAF.json` as `record_type=register_row` carrying funder, USD amount, start and end date. A register line is *one funder's tranche against a programme*; the programme it names has no identity row.

**2. "Proposition BECOMES project" is the minority path into projects.csv. [blocks]**
350 of 404 project rows (87%) are matched by no plan line: all 263 ZAF, all 24 VNM, 63 of 74 IDN. `plan-projects.csv` contains zero ZAF and zero VNM rows; 1 561 of 1 628 lines are `plan_only`, 67 `matched`. The dominant entry paths are a funder register (ZAF) and a donor portfolio table (IDN `idn-grant-*`), neither of which passes through a proposition.

**3. The Cirebon `matched` link joins an asset to a project, not a proposition to a project. [blocks]**
`idn-cipp-coal-retirement-002` = "PLTU Cirebon-1", 660 MW, `natural_retirement_year=2042`, `estimated_retirement_year=2035` → `canonical_project_id=idn-pipe-cirebon-1-retirement` ("Cirebon-1 early retirement"). The plan line names the **plant**; the project row names the **closure undertaking**. `reconciliation_status=matched` therefore does not mean what the draft says it means.

**4. Assets without any project already exist in the data. [blocks the "Asset lives nowhere" claim]**
`idn-cipp-coal-retirement-001` "PLTU Pelabuhan Ratu", 1 050 MW, retirement 2045→2037, `canonical_project_id` empty. Also transmission lines identified by their endpoints ("Transmission PLTU Pelabuhan Ratu ke Pelabuhan Ratu Baru"). Asset attributes are in `plan-projects.csv` (`capacity_value`, both retirement years), not only in `implementation-events.capacity_mw`.

**5. Retirement inverts the shared implementation vocabulary. [blocks]**
`idn-impl-cirebon-suspended-2025`: `implementation_status=suspended`, note "early retirement was described as unlikely to proceed". Here `suspended` means the plant **keeps running**; on a build project the same token means the opposite. One status vocabulary cannot serve both an asset's life and a retirement's progress.

**6. Count slots are cardinality assertions stored as entities. [should fix]**
21 VNM rows `verification_status=official_count_slot`, 0 events, 0 implementation events, 0 plan lines, 7 source links for the whole country. The observatory already discloses "383 named records and 21 unnamed slots", yet `COUNT(projects.csv)=404` is wrong by construction for any reader who does not read the README.

**7. `need` is not an agreement state. [should fix]**
34 `need` events, all SEN, **32 with an empty `funder`** (the other 2 say "Proposed financing mix"); notes: "Plan cost estimate, sometimes rounded; not secured funding. Date unresolved." The draft's agreement is defined by funder/instrument/amount/counterparty; a need has none. It is an estimate carried by a plan line, not the first state of an agreement.

**8. Partnership-level finance has no representation. [blocks]**
`source-claims.csv`: `zaf-annex25-finance-aggregate` — "USD 10bn current IPG pledge; USD 13.7bn including MDBs; USD 3.8bn allocated", `matched_project_ids` empty; likewise `idn-progress25-approved-aggregate` (USD 3.1bn). The site's headlines ($6.12bn allocated / 42.6 % of a revised $14.36bn pledge; ≈$3.1bn approved) live hard-coded in `config/jetp_observatory.yaml`, with `signed_on` and `pledge_label` per country. ZAF events sum to **$4.318bn**, not $6.12bn. The pledge is an agreement whose counterparty is a country; the ontology cannot express it, so it leaked into prose and YAML.

**9. `component_of` has no storage and currently lives on the wrong axis. [should fix]**
It is encoded as a *source*-link relationship: `project-source-links.relationship=project_page_component` (11 rows), e.g. `zaf-register-gr002/gr003/gr006` → `source_id=zaf-project-sagen-germany`. The containing programme SAGEN exists only as a source row. A project↔project relation is being carried by a project↔source table.

**10. Plan-as-source-only breaks cross-edition tracking. [blocks]**
Two IDN editions: CIPP 2023 (437 lines, 276 distinct names, cutoff 2023-11-21) and Progress 2025 (1 142 lines, 843 names, cutoff 2025-11-30) — **literal name intersection: 3**. No predecessor field exists. SEN: Annex 8 renumbers 34 public proposals, so its ordinals cannot join Annex 2's 38. Rankings are in the data (212 `top_priority`, 1 378 `priority`). "Plans succeed one another" is asserted and unimplementable.

**11. A plan line can itself be a programme. [note]**
VNM M1a RMP 2023: 279 positions typed `programme` 73, `named` 25, `unknown` 181. Those 279 lines are in the M1a inventory only, never in `plan-projects.csv` — the same kind has two incompatible storages.

**12. Missing kinds, each with live rows. [should fix]**
*Party/funder*: 61 free-text funder strings conflating funder and channel ("Canada via World Bank and ADB", "European Union via KfW"). *Policy measure*: `idn-fin-pbl-aset` (policy-based loan to the state), instrument `Policy Loans` ×3 in ZAF incl. `zaf-register-gr031` at $864m, `idn-grant-perform` (fiscal reform), `idn-grant-ipdf`. *Contractor*: `sen-scout-claim-sen-scout-ouarkhokh-par`, a CNTIC EPC contract — a party that is not a funder. *Site*: `sen-project-annex-31` "100 000 lampadaires", annex-05 "350 villages", annex-20 "2000 forages" (the plan itself says 1 000 elsewhere) — one row, N sites. *Perimeter*: `idn-pipe-hydro-quota-sumatra` is a 250 MW procurement quota. *Disbursement*: **0 `disbursed` events** of 380; 235 `signed`. Commitment and payment are not distinguished because nothing reaches the last state.

**13. Most damaging ambiguity, and the cheapest fix. [blocks]**
`events.project_id` is one foreign key pointing at three different subject types — a funder tranche (257), a donor facility or programme (≈35 `idn-grant-*`, 4 `official_programme`), and a physical undertaking (≈60). Consequently no count and no sum in the ledger states its unit, and 443 of 451 `event-timing` rows are `event_precision=unknown` with 257 `date_role=register`, so the dates do not disambiguate either.

Cheapest fix: **do not build the asset and agreement tables yet — add one required `subject_kind` column to `projects.csv`.** `verification_status` already partitions the file almost exactly along the needed lines (257 `official_register` → tranche, 21 `official_count_slot` → count slot, 43 `official_plan` → proposition, 4 `official_programme` → programme, remainder → project), so the column is derivable today by a deterministic mapping and reviewable row by row. It forces every published count to name its unit, and it is the precondition for splitting tranches out later without re-adjudicating 404 identities.
