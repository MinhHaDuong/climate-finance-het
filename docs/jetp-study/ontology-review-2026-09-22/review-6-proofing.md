# Review 6 — real-world proofing: 12 documents, 36 random pages, and the CRS / World Bank slurp (Opus, 2026-09-22)

Reviewed `docs/jetp-ontology.md` at `7d4fcc8b` (after decision 9). Seeded page selection, 470 information items classified. Independent of reviews 1 to 5.

# Proofing the JETP ontology against real documents

## PART 1 — Twelve documents, 36 pages

Selection seeded with `random.Random(20260922)`; page picks drawn in the table's order.

| # | source_id | Country | Publisher | Type | Fmt | Pages | Pages read | Lang |
|---|---|---|---|---|---|---|---|---|
| 1 | idn-cipp-2023-cpr-mirror | IDN | Climate Policy Radar (mirror) | investment_plan | PDF | 334 | 53, 185, 260 | EN |
| 2 | idn-jetp-progress-report-2025 | IDN | JETP Indonesia Secretariat | annual_report | PDF | 226 | 2, 20, 131 | EN/ID |
| 3 | idn-portfolio-project-hululais | IDN | JETP Indonesia Secretariat | project_page | HTML | 38 260 B | full + @2544, @34037 | EN |
| 4 | vnm-rmp-2023-vi | VNM | GoV + IPG | investment_plan | PDF | 248 | 17, 188, 241 | VI |
| 5 | vnm-decision-458-2026 | VNM | Government of Viet Nam | implementation_plan / approval | PDF | 23 | 15, 20, 22 | VI |
| 6 | vnm-evn-kfw-tri-an-2025 | VNM | Vietnam Electricity | official_news | HTML | 70 778 B | full + @7908, @54351 | EN |
| 7 | zaf-jet-grants-register-2024-q2 | ZAF | JET PMU | project_list | PDF | 33 | 10, 14, 33 | EN |
| 8 | zaf-jet-quarterly-2025-q3 | ZAF | JET PMU | progress_update | PDF | 28 | 17, 18, 28 | EN |
| 9 | zaf-jetp-political-declaration-2021 | ZAF | Germany (+5 co-signatories) | political_declaration | PDF | 4 | 1, 3, 4 | EN |
| 10 | sen-investment-plan-l4-mirror | SEN | Vie-Publique.sn (mirror) | investment_plan | PDF | 354 | 88, 149, 199 | FR |
| 11 | sen-aeme-report-2023 | SEN | AEME | annual_report | PDF | 52 | 7, 17, 20 | FR |
| 12 | sen-boad-linguere-loan-2026 | SEN | BOAD | approval_document | PDF | 4 | 2, 3, 4 | FR |

**Doc 5 has no text layer** — a 1-bit CCITT scan; pages were rendered to image and transcribed.

### Tally — 470 information items over 36 pages

| | (a) simple | (b) awkward | (c) not representable |
|---|---|---|---|
| Docs 1–3, 5 | 14 (10%) | 91 (63%) | 39 (27%) |
| Docs 4, 6–8 | 29 (17%) | 111 (65%) | 32 (19%) |
| Docs 9–12 | 32 (21%) | 87 (56%) | 35 (23%) |
| **All 36 pages** | **75 (16%)** | **289 (61%)** | **106 (23%)** |

The (a) share is concentrated: a heading, a locator, a named plant with an operator and a capacity, an instrument, a perimeter membership, a register row with an ID and a status letter. Two pages of CIPP governance (185, 260) produced **zero** clean fits between them.

### Ranked recurring awkward patterns

**1. CROSS-DOC-REFERENCE (22).** `refers_to` ranges over project/asset/agreement/party/perimeter — never over a *document* or a line in one. Every document in the set points at documents the ledger does not hold.
> "Recueil des recommandations et décisions prises aux réunions du Conseil d'Administration de la BOAD tenues en 2025" (doc 12, p4)
> "Currently, there are 45 grants related to skills registered in the JET Investments Register, totalling USD 140.25 mn" (doc 8, p18)
> "Nghị quyết số 10 NQ/TW; Quyết định số 888/QĐ-TTg ngày 25/7/2022" (doc 4, p188)

**2. Mandate, responsibility and role (18).** `party_in` binds a party to an *agreement*; these documents assign duties where no agreement exists. Roles observed and absent from the list: lead agency, coordinating agency, guarantor, host, endorser, standards body, counterparty.
> "Các Bộ trưởng, Thủ trưởng cơ quan ngang bộ … chịu trách nhiệm thi hành Quyết định này" (doc 5, p15)
> "Letters of endorsement were secured from the IDC, the dtic, and the Department of Electricity and Energy." (doc 8, p17)

**3. Target / commitment / policy intention (21).** `estimate` sits under the *money* axis, so a physical or social target has no measure at all.
> "Porter la part des énergies renouvelables en capacité installée à 40% de son mix électrique d'ici 2030" (doc 10, p199)
> "the IPG will aim to mobilize US$10 billion out of the US$20 billion over the next 3-5 years" (doc 1, p260)

**4. Conditionality and legal clause (14).** Measure `condition` is an observation *on an agreement* with a `concerns` party; the conditions observed attach to pledges, footnotes and normative acts.
> "Subject to concurrence on the investment framework, and in line with budgetary procedures" (doc 9, p3)
> "*Subject to the availability of budget funds" (doc 7, p10 — a footnote conditioning all 257 rows)

**5. Aggregates, derived statistics and nested scopes (14).**
> "approvals had been granted for five programs, four projects, and forty-four grants representing a combined value of USD 3.1 billion" (doc 2, p2)
> "The average grant size per project is approximately USD 3.2 mn" (doc 8, p18 — "per project" contradicts the register's actual unit)

**6. Locator undefined, especially for HTML (11).** §5 requires `(sha256, locator)` unique and refuses one "too coarse", but defines no syntax. Printed folio ≠ PDF page (docs 4, 5); most HTML byte offsets address no assertion; one amount sits at three locators in doc 3 (headline, table, chart series) with no `same_as` between lines.

**7. Counts whose unit the contract forbids (10).** §5 permits three units — lines, referents, perimeter observations. Observed: locomotives, scholars, certificates, farmers, SMMEs, officials, companies, households.
> "Chuyển đổi, thay thế 244 đầu máy, 80 toa xe phát điện" (doc 4, p188)
> "88 municipal officials trained in gender-responsive e-mobility planning" (doc 8, p28)

**8. Party strings, aliases and consortia (10).** Exactly the conflation the `party` table exists to fix — but §5 also demands the cell be kept verbatim and forbids semicolon lists. The two rules collide on every `Implementing Entity` cell.
> "Multiple partners; Eskom, Eskom employees, local communities, municipalities, province, knowledge institutes" (doc 7, p14)

**9. Multi-currency printing and publisher-supplied conversion (7+).** §5: "a monetary conversion cites a `rates` row; a script never carries a rate." Publishers convert first, at unstated rates.
> "Montant approuvé : 200 millions d'euros, soit 131,2 milliards FCFA." (doc 12, p2)
> "JPY 29,156,000,000 | USD 183,682,800" (doc 3, financing table)

**10. Publisher method notes (7).** They change the meaning of every value on the page and land in `notes`.
> "All figures are pro-rated from November 2021 and reflect the support provided from COP26 onwards." (doc 7, p33)
> "The average exchange rate from October 2022 to June 2024 using Oanda has been applied" (doc 7, p33)

**11. Ranges and open bounds (9).** `value` is a scalar; bounds exist only on `timings`. "approximately $8.5 billion", "1 400–1 500 construction jobs", "53 000+ people", "299 167 USD maximum".

**12. Multi-country / multi-site rows (9).** `lines.country` and `assets.location` are single-valued; observed: OMVS hydro in Mali counted in Senegal's mix, a Thái Bình–Nam Định pilot, six schools in four towns, a Uganda+South Africa grant.

### Not representable — what is lost

Global or sector-level subjects (no sector dimension exists on any kind). Emissions, jobs, people, generation (GWh), emission factors, tonnage, hectares, dwellings. Institutional events: a body founded, launched, staffed, merged. Party→party relations (SMI's role in forming IIF; consortium membership). Chart-only values, including one percentage present in **no byte** of the snapshot — defeating §2's "what was read can be re-read". Natural persons: signatories, delegated signature ("KT. THỦ TƯỚNG"). Distribution lists, seals, embedded PKI signatures. A document as a *subject* — doc 2 p131 asserts throughout what the PPA Regulation says and where it is silent, and has no subject. Recurrence ("Hàng năm") and dates deferred to another plan's schedule. Liability-side finance: BOAD's own bond issue, its programme budget.

### Two internal inconsistencies surfaced

- §6 maps the ZAF register's status letter to `own_status` **axis delivery**; §4 declares only project stage, asset state and money. `delivery` is undefined — on the most-populated status column in the corpus (257 rows).
- §12 files all translation as derived text outside the system of record, but doc 2 p20's Indonesian→English glosses are *publisher-authored*, inside the evidence; and for doc 5, a scan, the **label itself** is a transcription with no provenance column.

## PART 2 — Slurping CRS and the World Bank as comparator records

### Numbers

| Dataset | Rows | Bytes | Cols | Source |
|---|---:|---:|---:|---|
| CRS all sectors, all recipients | ~6.6 M **(derived, weak)** | 1.18 GB parquet / 296 MB reduced | 51 | sdmx.oecd.org `DSD_CRS@DF_CRS,1.6` |
| CRS energy (230xx), all recipients | 154 602 | 101 MB CSV | 51 | same, measured |
| CRS energy, IDN+VNM+ZAF+SEN | **9 337** | **5.9 MB** | 51 | same, measured (IDN 3 179, VNM 2 870, ZAF 1 748, SEN 1 540) |
| CRS all sectors, four countries | 401 269 | 265 MB | 51 | same, measured |
| WB Projects API v3, all | 28 140 | — | 45 | search.worldbank.org/api/v3/projects |
| WB projects, four countries (already pulled) | 1 119 | 514 KB JSON | 9 projected | `data/jetp/comparison/*.json` |
| IDA + IBRD statements, latest | 20 965 | — | 32 / 35 | financesone.worldbank.org DS00001, DS00047 |
| …historical monthly snapshots | 3 176 764 | — | same | DS00976, DS00975 |
| IATI bulk | 929 947 activities / 13 941 datasets | 831 MB zip | — | bulk-data.iatistandard.org |

All CRS counts are conditioned on `PRICE_BASE=Q`, `MD_DIM=DD`; years returned 1995–2024. Legacy purpose codes 23010–23082 return `NoRecordsFound` — OECD back-applied the 2016 nomenclature.

### (2) What fits CSV-in-git

**The threshold is already set by the repo, not by taste:** `.githooks/pre-commit` caps a staged file at **512 000 bytes**. Combined with review-by-diff, the working rule is: **CSV-in-git when the whole table is ≤ ~10 MB and ≤ ~25 000 rows** (≤ 512 KB per chunk, ≤ ~50 chunks — a wave a human can still read).

- **Fits:** four-country energy CRS (9 337 rows, 5.9 MB → 120 chunks of ~50 KB at country/year, or 40 at country/quinquennium); the 1 119 WB projects, already in git; a four-country IATI energy slice (~1 800 activities).
- **Does not fit:** all-recipient energy CRS (101 MB), full CRS (~6.6 M rows), WB historical statements (3.2 M rows), IATI bulk (831 MB). These must be **API snapshot bytes under DVC, manifest-only in git, lines materialised in the derived SQLite** — exactly §10's bulk path.

### (3) What CRS needs that the ontology lacks

1. **The activity-year row is not a line of a document** — it is a cell of a cube. `line_id = <document_id>-<table>-<ordinal>` works only if the dataset edition is the document and the SDMX key is the locator. Declare that.
2. **Commitment vs disbursement is not two columns** — it is `FLOW_TYPE ∈ {C,D}` × `OBS_VALUE`. One activity-year yields two lines. `flow_type` maps cleanly (commitment, disbursement); state it in the crosswalk.
3. **The same activity across years** needs `same_as` between *lines*, which §3 does not offer. Join key must be `(DONOR, DONOR_PROJECT_ID)` — `OECD_ID` is year-prefixed and stable for only 13.3% of activities (the pilot measured this).
4. **`MODALITY` collides.** §2 pins `modality` to DAC type-of-aid; JETP Indonesia publishes its own scheme whose first value is literally "Modality A". Namespace it.
5. **Rio markers** — four columns (`CLIMATE_MITIGATION`, `CLIMATE_ADAPTATION`, `BIODIVERSITY`, `DESERTIFICATION`), coded 0/1/2/blank. Blank ≠ 0, and the ontology's `absence` cannot say so. Needs a marker measure with a screened/not-screened distinction.
6. **Purpose codes and channel codes** need the sector dimension Part 1 found missing everywhere.
7. **Currency/deflator**: `PRICE_BASE=Q` means the value is *already* deflated by OECD. `rates`/`deflators` must record that the deflation was the publisher's, not the ledger's — the same PUBLISHER-SUPPLIED-CONVERSION gap Part 1 ranked ninth.

### (4) Recommended scope

- **Slurp fully:** four-country energy CRS (9 337 lines), the 1 119 WB projects already held, four-country IATI energy activities. CSV-in-git, chunked country/year.
- **Slurp filtered, DVC + manifest:** four-country all-sector CRS (401 k rows) as snapshot bytes, lines materialised only in SQLite; IDA/IBRD *latest* statements for the four countries.
- **Leave on demand:** full CRS, WB historical statements, IATI bulk, all-recipient CRS. Query by API at analysis time; never ingest.

### (5) Effort

| Work | Days |
|---|---|
| Comparator-line contract (dataset edition as document, SDMX key as locator, flow_type crosswalk, activity `same_as`) | 3 |
| CRS ingestion + `line-field-specs` for 51 columns + external-ids | 4 |
| Rio markers, purpose/channel codes, sector dimension | 3 |
| WB projects re-ingestion under the contract (45 fields, not 9) | 2 |
| IATI four-country slice | 2 |
| DVC bulk path + manifest review + SQLite materialisation | 4 |
| Validator, chunking, tests | 3 |
| **Total** | **21 days** |

**Verdict.** The comparator-record design is sound and the four-country energy slice is genuinely small — 9 337 rows is smaller than the plan appendices already in the ledger. The blockers are not volume; they are the three vocabulary gaps (sector, marker, modality namespace) and the missing line-to-line `same_as`. Fix those before ingestion, not after.
