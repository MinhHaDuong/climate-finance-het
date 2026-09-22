# Review 5 — fit for purpose against the scientific goals (Opus, 2026-09-22)

Reviewed `docs/jetp-ontology.md` at `94cea95c` (after Astra round 1), against the
programme plan, ticket 0725, the two paper conception notes, the ledger vision,
the Viet Nam pilot report and the AEDIST pipeline pilot. Independent of reviews
1 to 4, which the reviewer was told not to read.

## A. Can the ontology answer the papers' questions?

**A1 — Paper A's central result has no column. SEVERITY: HIGH.**
The measurement paper's whole finding is a *modality* split: budget support (CRS A01/A02) disburses 98.6 % by h=1, project finance (C01) 37.3 % at h=4, and the JETP's one real project loan (Eskom, 472.4 M$) sits at 0.2 % (`courbe-reference-decaissement-2026-09-08.md` § 3; `figure-distribution-decaissement.py` l. 55 filters `instr ∈ {pret, autre_officiel} & modalite == "C01"`). The `agreements` table (ontology § 5) carries `country, instrument, currency, tranche_of, notes` — no modality. Aggregating without it reproduces exactly the "moins de 5 %" artefact the paper exists to refute.

**A2 — No `measure` vocabulary, no flow interval, no gross/net basis. SEVERITY: HIGH.**
`observations` has a free-text `measure`; § 4 closes the vocabulary for line classifications and the three status axes but never for `measure`. The prose uses `count`, `estimate`, `capacity`, `envelope`; § 8 adds "commitment measure". The timing roles (§ 2) are *event, approval, reporting cutoff, register date, report date, planned* — there is no `period_start`/`period_end`, so a quarterly disbursement total cannot state its interval. Backend § 5's disbursement metric depends on exactly that ("movements cover `(t0, t1]`… an adjudicated quarterly total can stand for its covered itemised payments"), and § 8 declares backend § 5 *stands*. It cannot: the interval and the gross/net basis have no home.

**A3 — The accounts and adjudication layer lost its storage. SEVERITY: HIGH.**
Backend § 5 requires `adjudications.csv` (decision types: occurrence membership, flow coverage, perimeter compatibility) and accounts carrying opening/closing, residual, coverage gap, valid cutoff and evidence cutoff. None appears in ontology § 5's table list, and "what disappears" does not say it survives. § 8's claim that sections 5-8 stand is unbacked by the schema.

**A4 — Grant-equivalent and concessional terms are absent. SEVERITY: HIGH for Papers A and B.**
The ledger vision makes "part dons, part équivalent-don" a headline output (`imagine-jetp-ledger-2026-08-10.md` § 2.3), and Paper B anchors a whole section on the 2018-19 DAC grant-equivalent reform (`ancrage-…md` § c). No rate, maturity, grace or grant-element field exists on `agreements`.

**A5 — Conditionalities have no home. SEVERITY: MEDIUM.** The ledger schema sketch lists "conditionnalités déclarées" (AFD 670 M€ ↔ Senelec tariff reform); Paper B § d is conditionality-without-ownership. Nothing in § 2-5 holds it except `notes`.

**A6 — Paper A's Block 1 (absorbability) has no subject kind. SEVERITY: MEDIUM.**
435 rows of GDP, external debt, Eskom debt/EBITDA 13.98×, PLN tariff coverage 77.2 %, FX (`bloc1-absorbabilite-2026-09-08.md`). Observation subjects are project/asset/agreement/party/perimeter/line. A sovereign's GDP fits none; a utility's DSCR fits `party` only by stretching a registry the design says is "minimal, funder and channel roles first" (decision 6). The design never states whether these are in or out of perimeter.

**A7 — What the ontology answers well, and should be credited.** Envelope drift (15.5 → 15.8 → 15.0 Md$, `rapport-pilote-vn.md` § 1) is cleanly a `perimeter` with dated `envelope` observations and supersession. The pledge/commitment distinction — Paper A's "les dénominateurs ne sont pas de même nature", its heaviest limit — is structural here: pledge is a perimeter observation, commitment an IATI flow on an agreement. The opacity map is served by `absence` lines plus `dry-searches`. The physical join (dollars per MW retired) has its path: `finances` → `concerns` → asset state, with GEM's list and `part_of` for unit-level retirement.

## B. Storage

**B1 — § 10's volume claim is wrong by an order of magnitude. SEVERITY: HIGH.**
"About 8 000 rows… the four partnerships publish a few hundred lines a year". But editions are new documents (§ 2), lines are append-only and never renumbered (§ 5), and monthly editions are a committed deliverable (0728). One monthly re-publication of the ZA register (257 rows) is 3 084 lines/year; Indonesia's plan appendices are 1 579 rows per edition pair, and § 11 names a 437 × 1 142 edition-matching problem. Quarterly editions alone reach ~10 k lines/year.

**B2 — `line-fields/<document_id>` contradicts the generated DDL. SEVERITY: MEDIUM.** § 5 gives every document its own table with the publisher's headers verbatim; § 10 says one DDL declares every table and generates the CSV headers. Both cannot hold. Also: 301 documents today → 301 files, growing per edition.

**B3 — CRS/IATI scale is out of reach as specified. SEVERITY: HIGH for the AEDIST/AIRLET prefiguration.** The ledger vision makes CRS/IATI the structured first layer (§ 2.1); the VN pilot pulled 167 MB raw CRS and 485 IATI activities for one country-sector, and the four-country energy extract is already 8 029 CRS rows / 1 791 activities. The programme plan admits comparator countries beyond the four. Practical break points: PR-diff adjudication (the stated reason for CSV-in-git) fails above ~5-10 k rows in a file; per-country chunking postpones it one decade of growth; the in-browser one-JSON-per-table join degrades around 10-20 MB/table. Derived SQLite is the right call and is not the constraint — the *record* format is.

## C. Comparability

**C1 — There is no comparable unit, and the design is honest about not offering one. SEVERITY: MEDIUM.** § 7 forbids adding lines of one document to another or to referents; only lines and referents are countable. The nearest comparable unit to a CRS activity or a WB operation is the `agreement`, and it is honest — money never splits across `tranche_of`, values stay in the publisher's currency. But it is not *sufficient*: without A1 (modality), A2 (measure/basis) and no deflator or FX table anywhere (§ 2 says "conversion is a derivation" and § 12's only derived tables are translations), the constant-2024-USD denominators Paper A needs are uncomputable in-contract. The figure script's hardcoded `2500 * 1.09` EUR→USD is precisely the unsourced conversion the ledger should abolish.

**C2 — The historical reference pool is outside the ontology. SEVERITY: HIGH.** 1 119 World Bank API records / 97 closed energy operations live in `data/jetp/comparison/*.json` with `boardapprovaldate`, `closingdate`, `lendinginstr`, `status`. § 5's "what disappears" never mentions them, no kind admits them, no external-identifier table holds a P-number or a `DONOR_PROJECT_ID`, and no crosswalk maps WB `Closed`/`Dropped` onto the OC4IDS stage axis. The comparator for both papers is unmodelled.

## D. Time

**D1 — As-of reconstruction cannot run. SEVERITY: HIGH.** Backend § 6 step 1 admits "only records with `recorded_at <= K`". `observations`, `timings` and `lines` carry no `recorded_at`, no `reviewed_at`, no `status`, no `supersedes` — only `line-referents` and `relations` do. Ticket 0725's first test ("reproduce a paper result from the exact frozen edition") therefore has no mechanism beyond freezing whole editions. A corrected publication produces a *new* observation with no link revoking the old one.

**D2 — The series exists but is thin, and that is data, not design. SEVERITY: LOW.** Per-agreement disbursement series are expressible once A2 lands. The binding constraint is coverage: 451 timings hold six exact event days and two year-bounded events (`jetp-programme-progress-2026-09-14.md`). The design states this rather than filling it — correct.

## E. Over- and under-served

**E1 — Over-served.** The OC4IDS project-stage axis is fully specified and, by § 4's own admission, populated by *no* country today. `translation_of` + two derived translation tables (§ 12) — self-labelled nice-to-have, no paper needs them. Reconciliation tiers 3-5 are name-only, so cheap; document-dedup tier 4 (LLM on first pages) for 301 documents is over-built.

**E2 — Under-served (no home at all):** modality; measure vocabulary and flow basis; period intervals; grant-equivalent and loan terms; conditionalities; macro-fiscal indicators; external identifiers (CRS/IATI/WB/OECD_ID); FX and deflator provenance; the WB comparator pool; `recorded_at`; the accounts/adjudications layer. Asset `capacity` is promised in § 2 and absent from the `assets` table — recoverable as an observation, but the two sections disagree.

## F. Verdict

**Ontology: fit with named repairs.** The evidence spine (publisher / document / retrieval / snapshot / line, minted identities, verbatim `own_status` + dated crosswalk, perimeter ≠ agreement, defeasible supersession) is the right model and directly serves the honesty constraints both papers are built on. Every gap above is additive, not structural.

**Storage: fit for the JETP ledger as it stands today; not fit as claimed.** CSV-in-git + derived SQLite is correct for ~10 k rows. § 10's steady-state estimate is wrong (B1), it contradicts § 5 (B2), and it does not cover the CRS/IATI ingestion the ledger vision requires (B3).

**Three repairs first:**

1. **Amount semantics pack** — closed `measure` vocabulary, `basis` (gross/net), `modality` on `agreements`, `period_start`/`period_end` date roles, `recorded_at` on `lines`/`observations`/`timings`. Unblocks A1, A2, D1. **2 days.**
2. **External identifiers + comparator admission** — an `external-ids` table (scheme, kind, id) and a written rule admitting WB/CRS/IATI records as lines of an API-response snapshot, with a WB-status crosswalk. Unblocks C2, B3, and the CRS/IATI first layer. **2-3 days.**
3. **Restore the accounts layer and rate provenance into § 5** — map backend § 5-6 constructs onto named tables (adjudications, accounts) and add a derived `fx-rates`/`deflators` table with source assertions. Unblocks A3, C1. **1 day for the contract text, 3 with the validator.**

Then, half a day: correct § 10's row projection and reconcile it with § 5's `line-fields` (B1, B2).
