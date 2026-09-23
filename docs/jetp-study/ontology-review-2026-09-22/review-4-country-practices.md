# Review 4 — confronted with the four countries' reporting practices (Opus, 2026-09-22)

## 1. Country tables

### South Africa — JET Investment Register, Q1 2026 (257 rows)

| Register object | Draft kind | Mismatch |
|---|---|---|
| Row, keyed `Unique ID` = funder prefix + sequence (`UK034`, `EU018`, `DK010`) | agreement / tranche | Ledger mints one **project** per row (`zaf-register-*`, 259 events, 259 distinct `project_id`, 1 event each) |
| `Project Name` | project | Not an identifier: 166 names for 257 rows; "Municipal Climate Resilience Programme" = 21 rows, 8 funders, 4 portfolios, statuses A+C+D at once |
| `Portfolios` (8 values) | — | Stored as `window` in events.csv; a *funder-line* attribute, not the project's: the 21 "Municipal Climate Resilience" rows sit under Municipalities, Skills, Electricity, Road to Rail |
| `Status` A/B/C/D | implementation state | Discarded — survives only as a notes string `Status=D. Completed`; zero ZAF rows in implementation-events.csv |
| `Purpose` (TA 72, Studies 64, Infrastructure 46) | — | No draft kind; the discriminator for whether an asset exists at all |
| `Implementing Entity`, `Beneficiary`, `Priority Areas` | — | Unmodelled; 85/257 Beneficiary empty |
| `Date of Financing Agreement Signed*`, `End Date` | agreement dates | Agreement-side only; no asset date anywhere |
| — | **asset** | Register has no capacity, no location, no operator field |

`Window` is not a register field. `Funder/Source` is empty in 214/257; the funder is carried by `Funding Partners` and by the ID prefix.

### Indonesia — CIPP 2023 (437 lines) + Progress Report 2025 (1 142) + portfolio (46)

| Reporting object | Draft kind | Mismatch |
|---|---|---|
| CIPP Appendix 10.5 line: technology × system × MW × start year | proposition | Not an intent by a promoter — a **capacity tranche**. "PLTS Dedieselisasi" = 31 lines across 5 systems; 93/437 are `(Kuota) Tersebar` quota lines with no site |
| 37 lines with `capacity_unit = km` | asset? project? | Transmission length, no endpoints, no identity |
| `ruptl` YES 233 / NO 202 | — | A **plan-to-plan membership flag**; the draft has no plan↔plan relation |
| `priority_tier` top_priority 201 / priority 941 | plan ranking | Fine — but the 2025 report renumbers: `ordinal` has 340 distinct values for 1 142 rows |
| Portfolio row: `Modality A`(44)/`B`(2), `financing_type = Grant / TA`, `part_of_jetp_pledge = Yes` | agreement | Correct shape — and already split from project: `idn-grant-jetp-etp` appears twice (Canada Modality A, UK Modality B) |
| AICET/ISLE results-based loans (`idn-fin-*`, 9 rows) | agreement + project | Results-based lending finances a *result*, not a project or asset |

Only 7/437 CIPP lines and 11/1 142 progress lines reach `matched`.

### Viet Nam — RMP 2023 (279) + July 2025 portfolio (24)

| Reporting object | Draft kind | Mismatch |
|---|---|---|
| RMP annex position | proposition | 25 named, **73 programme/task-group, 181 unresolved**; Annex II is "technical-assistance projects/task groups"; `identity_disposition: unresolved_inventory_membership` |
| 3 named July-2025 records | project + asset | They arrive from MOIT/EVN project pages, **not from the RMP** |
| 21 "count slots" (`official_count_slot`) | proposition | Not an object in any source — a cardinality assertion (7 initial, 17 screened) reified to avoid losing a number |
| `reported_financing_envelope` (15), `reported_portfolio_count` (4), `reported_absence_position` (1) | — | No kind; the 15.5/7.75/7.75 bn envelope is a partnership-level pledge, not an agreement |

### Senegal — Investment Plan 2025

| Reporting object | Draft kind | Mismatch |
|---|---|---|
| Annex 2 submission (38, `sen-annex-received-01…38`) | proposition | Yes — the draft's cleanest fit |
| Annex 8 evaluation (34 public proposals) | — | Renumbered; "its ordinals cannot be joined directly to Annex 2 ordinals" |
| Quick win (11) | programme? project? | **A label, not a kind**: QW1 groups Annex 2 #15; QW5/6/7/9/11 = #11/17/19/16/20; QW4/PUELEC is a programme with components |
| "need/estimate" (34) | agreement status `need` | A plan figure with no funder; SEN events.csv = 34 `need` + 5 `announced`, nothing else |

## 2. Findings

**1. The ZAF row is a funder allocation, not a project.** Evidence: `docs/jetp-study/0818-zaf-q1-2026-fields.csv`, IDs `US010` and `US011` — identical name, portfolio, status, amount (300 000 USD), two rows. The identifier is namespaced by funder (`UK`, `EU`, `DK`, `ACTIP`), which is what a grant register numbers. Multi-funder "projects" are therefore not modelled at all: nothing in the register joins UK034 to SW003.

**2. `Project Name` in ZAF is a purpose label.** "Skills Research Programme" carries 13 rows, 9 funders, statuses A/C/D, amounts from 0 EUR (EU010) to 42 000 000 DKK (DK010). Treating it as a programme name (draft's `component_of`) would assert a governance envelope the register never claims.

**3. Only `plan` and `agreement` survive all four.** Every country publishes dated lists with cutoffs (CIPP 2023, RMP 2023, SEN IP 2025, ZAF Q1 2026) and every country publishes funder-side money lines. `Asset` is present only in IDN (`capacity_value`, `system`) and the 3 VNM MOIT records — ZAF has zero implementation events and no capacity field. `Programme` is a ZAF/SEN artefact read into name repetition and quick-win grouping. `Proposition` is a SEN artefact: only Senegal has a named promoter submitting before decision (`promoter=ANER`, `promoter=AEME`).

**4. One word, four objects.** *Project*: ZAF = grant line; IDN = MW tranche ("PLTS Java-Bali (Kuota) Tersebar"); VNM = count slot; SEN = promoter submission. *Programme*: ZAF = row-name collision; SEN = PUELEC's real component structure; VNM = 73 unclassifiable annex rows. *Priority*: IDN = coloured-cell tier; SEN = quick-win label; ZAF = `Priority Areas`, a free-text purpose. *Approved*: ZAF `B. Approved` = physical stage; IDN `approved` = financing decision — 17 ZAF `B. Approved` rows are `signed` in events.csv. *Portfolio*: ZAF = thematic window; VNM = a count of 24.

**5. The status vocabulary is not shared; it is partitioned.** events.csv, `financial_status` × country: ZAF signed 235 / announced 21 / approved 3; IDN approved 62 / announced 19 / mou 1; SEN need 34 / announced 5; VNM **zero**. No country populates two ends of the chronology, and `disbursed` is empty in all 380 events. The ZAF letters cross-tab orthogonally (16 `A. Planned` rows are `signed`), proving they sit on the delivery axis, not the money axis — yet ZAF contributes 0 of 71 implementation events. Each country reports one axis, and the draft's chronology is the union of four disjoint slices, populated only by inference.

## 3. The one change

**Make the plan/register *line* the first-class kind, keyed by (source edition, locator), and demote `project` to a derived identity minted only on reviewed cross-source match.** The four countries never publish a project registry; they publish lists, and each line is one publisher's dated assertion — which is why `plan_only` is 1 561 of 1 628 plan lines, why 21 VNM slots exist, and why 257 ZAF grant lines became 257 "projects". `Proposition`, `programme` and the ZAF register row are not three kinds: they are one kind — a line — under three publishers. Keep `asset` and `agreement` as the two real-world kinds a line may point at; delete `proposition` and `programme` as kinds and carry them as per-line classifications, as `priority_tier` and `technology_group` already are.
