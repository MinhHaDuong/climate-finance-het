# 0152 line-by-line coverage matrix — v2.0.5 rebuilt base

Integration review for sub-tracker 0175 (base 3/3 execute reimports) against the
assembled `content/manuscript.qmd` on `main` (translation of the Vannes VF +
reimports B01–B23 + annexe, tickets 0172/0176/0177/0178/0179). This matrix arms
the author's re-sign of the 60-row response ledger in ticket 0152. It closes no
ticket and edits no manuscript content — verification only.

## Summary

**Addressed 52 / Partial 4 / Not-yet 1 / Needs-resign 3 / Deferred 0** (60 rows).

- Every remark now has a substantive manuscript locus except one bibliographic
  ask (R2.30, Escobar/Mitchell) that is genuinely unmet and one loss-and-damage
  ask (R1.4) that is only half met.
- No orphan gaps: every Partial / Not-yet row is owned by a still-open content
  ticket (0135, 0137, 0138, 0139, 0141, 0143).
- Three rows previously author-signed on the strong "corpus confirms the pre-2007
  separation" reading are now **NEEDS-RESIGN** after the 0182 DEMOTE / 0183 scout
  NO-SIGNAL verdicts — the manuscript wording that supported them still stands on
  `main` (the A.5 rewrite in ticket 0183 is not yet merged; 0183 is open,
  `needs-human`).

Note on appendix letters: the reassembled appendix renumbered its subsections.
The 0152 ledger's "Where" column points at the pre-rebuild letters (E3b→A.3,
E3c/E3d→A.4, E3e→A.5, E3f→A.6). In the manuscript now on `main` the loci are
**A.4** breaks (§252–256), **A.5** co-citation lineages (§258–262), **A.3**
embedding/cleaning (§242–248). Loci below cite the current letters.

## NEEDS-RESIGN — pre-2007 tradition-separation rows

These three rows were signed `MHD 2026-06-19` on the FORTIFIED reading. Ticket
0182 (DEMOTE — the non-circular density-conditioned null is degenerate: outside
environmental economics the a-priori anchor works fall below the pre-2007
co-citation core) and the 0183 scout (`docs/scout-tradition-coupling.md`, verdict
**NO SIGNAL** across three methods — soft-membership coupling, no-scaffold
embedding distance, hard assortativity — none surviving the density/composition
control) downgrade the evidence to *consistent with, not independently confirmed
by* the citation structure. The manuscript must carry the honest
descriptive-consistency wording (0183's proposed A.5 sentence) and the author
must re-sign these rows accordingly.

| Row | Owner | Current locus | Verdict impact |
|-----|-------|---------------|----------------|
| **E3c** | 0136 (closed) | A.5 §260 — "the 250 most-cited references… partitions the network with the Louvain method" | Co-citation rationale + 250-cap stand; the *separation conclusion* they support is downgraded |
| **E3d** | 0136 (closed) | A.5 §262 — Louvain-vs-Leiden + "0.68" drop stand; separation sentence needs rewording | The dropped-0.68 decision is unaffected; the "hardly read one another" close is the re-sign target |
| **R1.2** | 0136 (closed) | §1.5 §102/§104 — burden-sharing divergence read as transmission evidence | The divergence reading stands; the framing that the corpus *confirms* separation is downgraded |

**Current wording on `main` that stands and must be re-signed (quote for the author):**

- A.1 §226: *"The co-citation analysis could have shown the three traditions
  already entangled before crystallization, and did not."*
- §1.5 §102: *"That fragmentation is the empirical point: the three traditions
  occupy separate lineages sharing almost no co-citation edges."*
- A.5 §262 (close): *"the pre-2007 network is scattered into many small, weakly
  connected lineages, and only the governance and accountability lineage persists
  as a distinct community across every window. Before the crystallization, the
  three traditions hardly read one another."*

The manuscript already carries the partial honesty caveat at §104 (the
effort-sharing tradition "left no distinct co-citation footprint"; divergence read
"as evidence about transmission, not as evidence against its existence"). What
0183 requires is that the three framing sentences above stop asserting confirmed
separation and adopt the descriptive-consistency form (0183 proposed sentence:
"…that partition is optimised on the same graph, however, so it corroborates the
reading only weakly… We therefore read the separation as consistent with the
citation structure, not independently confirmed by it."). Wording change lives in
open ticket 0183; author re-sign lives here.

## Full coverage matrix

| Row | Remark gist | Status | Evidence / locus | Serving block / ticket | Notes |
|-----|-------------|--------|------------------|------------------------|-------|
| E1 | Prose: define-by-negation, empty closers | ADDRESSED | Manuscript-wide retranslation, style-anchored (0173); prose adherence tests green | 0134 (open) | Global prose remark; owner 0134 open for final sign |
| E2 | Clarify "economic thought"; value grey-lit | ADDRESSED | §64 "an economics of measurement conventions, more than one of equilibrium models"; §68 "from the model to accounting"; A.2 §238 grey-lit as finding | 0135 (open) | |
| E3 | History↔quant thin; below field standards | ADDRESSED | Appendix A.1–A.6; A.1 §226 role named confirmatory/falsificationist | B16 / 0136 (closed) | Signed |
| E3a | How was the corpus constructed | ADDRESSED | A.2 §236 six sources, four-tier taxonomy, DOI+title/year dedup | B17 / 0136 | Signed |
| E3b | Why these three periods | ADDRESSED | A.4 §252–256 endogenous JS+cosine detection, 2007 robust, 2009 under censoring, no 2015 break, core none | B18 / 0136 | Letter shift: 0152 said A.3 |
| E3c | Why co-citation, why 250 cap | **NEEDS-RESIGN** | A.5 §260 rationale + 250 ceiling | B19 / 0136 | See needs-resign section |
| E3d | Why Louvain not Leiden, 0.68 | **NEEDS-RESIGN** | A.5 §262 Louvain-vs-Leiden + 0.68 drop; tbl-traditions caption | B19 / 0136 | 0.68 drop stands; separation close is the re-sign target |
| E3e | Full-text cleaning procedure | ADDRESSED | A.3 §244 "does not read article full text"; encoding/mojibake/zero-width normalization | B20 / 0136 | Letter shift: 0152 said A.5 |
| E3f | Why k-means, why k, robustness | ADDRESSED | A.3 §248 k-means kept; HDBSCAN 98% noise; Spectral ARI 0.59; k-means ARI 0.98 | B21 / 0136 | Letter shift: 0152 said A.6 |
| E4 | Logical role of quant; directionality; Fig 2 | ADDRESSED | A.1 §226–228 confirmatory; history→data; §228 "A.5 details the method behind the columns" | B16 / 0136 | Signed |
| R1.1 | Economists = policy pros not academics; econ-journal absence; cite Golka | PARTIAL | §157 "policy professionals in international organisations rather than academic theorists"; A.2 §238 econ-journal under-representation "a finding rather than a selection artifact" | B09 / 0135, 0143 (open) | **Golka (2024) not cited** (grep 0 in bib+qmd) — bibliographic gap owned by 0143 |
| R1.2 | Comp analysis weak; burden-sharing divergence | **NEEDS-RESIGN** | §1.5 §102/§104 divergence = transmission evidence; Appendix | B05 / 0136 | See needs-resign section |
| R1.3 | Commensuration/economisation should structure whole analysis | PARTIAL | Deployed §68 (commensuration), §136 + §151 (economisation), A.1 §230 | 0137 (open) | Recurs at several loci but not as the analytic backbone the reviewer asked; 0137 open |
| R1.4 | Loss & damage / insurance actuarial logic challenges thesis; game-theoretic coalition | PARTIAL | §202 + §218 loss-and-damage as a boundary test of the thesis | B14 / 0138 (open) | Insurance/actuarial-logic and game-theoretic coalition-formation opening **not addressed**; inventory marks B14 "R1.4 open, unaddressed" |
| R1.5 | Finance–development nexus; blended finance disconnection; cite King & Levine → Aghion & Bolton | PARTIAL | §155 Hourcade "financial paradox" / public finance as market-failure correction; §134 blended finance / de-risking | 0139, 0143 (open) | **King & Levine 1993 / Aghion & Bolton not cited** (grep 0); financial-deepening lineage owned by 0139/0143 |
| R1.o1 | "models vs accounting" = IAMs vs DAC | ADDRESSED | §68 "from the model to accounting"; §94 IAMs; A.1 §226 | 0141 (open) | |
| R1.o2 | "longer trajectory of climate economics" clarify | ADDRESSED | §68 shift from carbon-price to climate-finance regime; §74 borderline object | 0141 | |
| R1.o3 | Justify corpus boundaries; econ-journal selection effect | ADDRESSED | A.2 §238 grey-lit by design; under-representation "a finding rather than a selection artifact" | B17 / 0136 | Signed |
| R1.o4 | $100bn not from a model | ADDRESSED | §124 "not derived from an economic model or from an estimate of needs; it emerged from last-minute diplomatic bargaining" | B06 / 0141 | |
| R2.g1 | Substantiate central claim (measurable AND contestable) | ADDRESSED | §149 "Controversy … one of its operating conditions"; §190; A.1 §226 | 0134, 0136 | |
| R2.g2 | Analytical concreteness: sites, actors, instruments | ADDRESSED | §153 AGF; §136 OECD Research Collaborative (Jachnik/Caruso); §167 Türkiye case | B07/B09/B11 / 0141 | |
| R2.g3 | Restructure around institutional ruptures | ADDRESSED | Three eras framed by ruptures Bali 2007 / Copenhagen 2009 / Paris 2015 (§70), defended in A.4 | 0142 (closed) | Author kept the chronology but anchored it to ruptures — closed |
| R2.g4 | Formulaic/AI-like prose | ADDRESSED | Manuscript-wide retranslation (0173); adherence green | 0134 (open) | Global prose remark |
| R2.01 | Define Rio markers at first mention | ADDRESSED | §96 "introduced in 1998 to identify projects linked to the … Rio Summit"; §130 three-tier tag | B02 / 0140 (closed) | |
| R2.02 | Jargon: concessional / grant element / face value | ADDRESSED | §96 concessional, grant element (25% threshold), face value vs subsidy | B02 / 0140 | |
| R2.03 | Dev-econ: how reasoning entered negotiations, actors/mechanisms | ADDRESSED | §96 DAC infrastructure; §132 donor/recipient regimes; §153 AGF | 0141 | |
| R2.04 | Replace "not natural categories but historical constructs" | ADDRESSED | §96 "There is nothing natural about these categories, but the effort of transparency is useful…" | 0134 | Reworded concretely |
| R2.05 | Define DAC at first occurrence | ADDRESSED | §96 "The OECD's Development Assistance Committee has tracked official development assistance since the 1960s" | B02 / 0140 | |
| R2.06 | Connect Desrosières quote to empirical case | ADDRESSED | §96 Desrosières/Porter tied to DAC conventions "made progressively objective through use" | 0141 | |
| R2.07 | Name development economists in the OECD case | ADDRESSED | §44/§151 Jan Corfee-Morlot; §136 Raphaël Jachnik, Roberta Caruso | B09 / 0141 | |
| R2.08 | Define the GNI target | ADDRESSED | §96 "0.7% of gross national income (GNI) adopted by the UN General Assembly in 1970" | B02 / 0140 | |
| R2.09 | Why borrowing the aid reporting system is problematic; who drove it | ADDRESSED | §96 inherits ODA "biases and reporting incentives"; §130 biases carried over; §132 donor-designed | 0141 | |
| R2.10 | Article 4.3 transactional language clarify | ADDRESSED | §90 "The logic is transactional: defined and accepted costs are to be reimbursed" | B02 / 0141 | |
| R2.11 | Describe the incremental-cost framework concretely | ADDRESSED | §90 "agreed full incremental costs"; transactional reimbursement logic | 0141 | |
| R2.12 | Evidence the "need for a broader category arose" | ADDRESSED | §90 "gradual abandonment of this initial precision in favour of a broader … category"; §118–122 Bali | 0141 | |
| R2.13 | When/why incremental-cost abandoned | ADDRESSED | §90; §118 Bali "broke with the Convention's incremental-cost logic" | 0141 | |
| R2.14 | Welfare-theoretic transfers not real flows | ADDRESSED | §94 "optimisation or welfare variables, not institutional instruments to be tracked and verified" | 0141 | |
| R2.15 | How the CDM functioned in practice | ADDRESSED | §100 7,500 projects / 105 countries / >$200bn nominal; additionality test | B03 / 0141 | |
| R2.16 | Develop "the concept later migrated…" | ADDRESSED | §100 "would later migrate into climate finance debates, repurposed to ask whether finance was additional" | B03 / 0141 | |
| R2.17 | CDM = carbon accounting not financial accounting | ADDRESSED | §100 "a CER is a unit of carbon accounting, not of financial accounting" | B03 / 0141 | |
| R2.18 | Post-2012 CDM collapse — who generated demand | ADDRESSED | §100 CER prices below €1 after 2012; "a demand that recipient countries and NGOs had pressed since Bali" | B03 / 0141 | |
| R2.19 | What is the Bali Action Plan; what changed | ADDRESSED | §118 "Decision 1/CP.13, the negotiating roadmap … broke with the Convention's incremental-cost logic" | 0140 | |
| R2.20 | "Political legitimacy" introduced suddenly | ADDRESSED | §122 "made countability a condition of political legitimacy" | 0141 | |
| R2.21 | "created a new economic object" too strong | ADDRESSED | §122 overclaim dropped; "narrower and datable" claim | B06 / 0136 | Signed |
| R2.22 | "not just models but accounting infrastructure" too abstract | ADDRESSED | §122; §126 institutional performativity through forms, directives, databases, coefficients | 0141 | |
| R2.23 | Copenhagen context; why $100bn; anecdotal | ADDRESSED | §124 "emerged from last-minute diplomatic bargaining"; not model-derived | B06 / 0141 | |
| R2.24 | Explain the "Barnesian form" | ADDRESSED | §126 "@mackenzie2006 calls a model Barnesian, after … Barry Barnes, when its use reshapes markets…" | 0140 | |
| R2.25 | Define GEF grants | ADDRESSED | §124 "Global Environment Facility (the multilateral fund created in 1991 …)" | 0140 | |
| R2.26 | How climate finance became politically binding | ADDRESSED | §124 "politically binding quantity"; §132 Standing Committee on Finance; §165 Paris Art. 9 | 0141 | |
| R2.27 | Unpack measurement-apparatus/performativity concretely | ADDRESSED | §130 Rio markers three-tier; §136 attribution methodologies; §126–128 institutional performativity | 0141 | |
| R2.28 | Performativity declarative not explanatory | ADDRESSED | §128 "The distinction earns its place by explaining … why the technical methodologies … came to be fought over" | B06 / 0136 | Signed |
| R2.29 | Rio markers role/functioning, by whom, for what | ADDRESSED | §96; §130 three-tier declaration by donors | 0141 | |
| R2.30 | Engage Escobar, Tim Mitchell (not just Desrosières/Porter) | **NOT-YET** | Escobar not in bib+qmd; Mitchell in bib but **not cited** in qmd (grep 0) | B13 / 0143 (open) | Genuine bibliographic gap; owned by open 0143 |
| R2.31 | UNFCCC reporting: to whom, by whom, purpose | ADDRESSED | §132 "accountable to recipient countries, which reported what they had received" | B12 / 0141 | |
| R2.32 | Competing donor vs recipient measurement regimes | ADDRESSED | §132 "Two measurement regimes, each embedded in a different political constituency" | B12 / 0141 | |
| R2.33 | Concluding sentences formulaic; the "particular vision" | ADDRESSED | §138–140 poles stated concretely; §210–218 conclusion direct | 0134 | Prose rewrite |
| R2.34 | §2.3: more examples/sources | ADDRESSED | §136 OECD Research Collaborative + citations; §153 AGF | 0141 | |
| R2.35 | OECD expert groups "set terms of debate" — which experts, methods | ADDRESSED | §136 "Research Collaborative on Tracking Private Climate Finance (2013–2015), coordinated by Raphaël Jachnik and Roberta Caruso" | B08 / 0141 | |
| R2.36 | Concrete examples for accountability-vocabulary crystallisation | ADDRESSED | §138–140 additionality / grant equivalent / double counting; Oxfam 2012 | 0141 | |
| R2.37 | UN Advisory Group composition — does it matter | ADDRESSED | §153 "finance ministers, central bankers and economists … and no climate scientists. The composition mattered" | B09 / 0141 | |

## Genuinely uncovered (real gaps)

All owned by open tickets — no orphans:

- **R2.30** (NOT-YET): Escobar and Tim Mitchell not cited (Mitchell present in
  `main.bib` but unused; Escobar absent). Owner: **0143** (bibliography).
- **R1.4** (PARTIAL): loss-and-damage appears as a thesis boundary-test, but the
  insurance/actuarial-logic-challenges-the-thesis point and the game-theoretic
  coalition-formation opening are unaddressed. Owner: **0138**.
- **R1.1 / R1.5** (PARTIAL): missing citations Golka (2024), King & Levine (1993),
  Aghion & Bolton. Owners: **0143 / 0135 / 0139**.
- **R1.3** (PARTIAL): commensuration/economisation deployed but not structuring
  the whole analysis. Owner: **0137**.

## Build verification (this review)

| Suite | Result |
|-------|--------|
| `tests/test_manuscript_prose.py` + `tests/test_venue_table.py` | **34 passed** |
| `pytest -m adherence` | **33 passed**, 1259 deselected |
| `make check-fast` | **1052 passed, 21 skipped, 1 failed** |

The single `make check-fast` failure is the pre-existing, out-of-scope
`test_script_hygiene.py::TestScriptNaming` — `het_build_corpus.py has
non-conforming prefix`. Known; not fixed here. No manuscript render was run
(verification only).
