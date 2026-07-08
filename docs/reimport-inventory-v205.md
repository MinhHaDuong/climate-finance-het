# Reimport inventory — VEn evidence blocks absent (or thinner) in VF

Ticket: 0174 (child of tracker 0172, base rebuild v2.0.5). Read-only inventory —
compares `content/manuscript.qmd` (current VEn, source of the evidence) against
`content/manuscript-Gide.qmd` (VF, what the translated base will contain), and
maps each gap to the rows it serves in `tickets/0152-…`'s 60-row traceability
table. Nothing here is a decision; the "Décision auteur" field is left empty
for author sign-off, block by block.

**Prepared:** 2026-07-08. **Source line ranges** refer to the manuscript.qmd
and manuscript-Gide.qmd revisions as of this reading (pre-0173 state).

## Structural map (for orientation)

**VEn (`manuscript.qmd`, 327 lines, English, `number-sections: true`)**
Intro (§sec-intro) → Before 1990–2006 (§sec-before: 3 tradition subsections +
"why it didn't exist yet" + Corpus evidence + tbl-traditions) → Crystallization
2007–2014 (§sec-crystallization: Copenhagen moment + statistical infrastructure
+ emergence of key concepts + economists as architects + Corpus evidence +
fig-composition) → Established Field 2015–2024 (§sec-established: anatomy of a
transaction §sec-transaction + Paris/transparency + four controversies +
$100bn/$300bn transition + Corpus evidence + tbl-venues) → Conclusion →
Appendix A.1–A.6 (unnumbered: logical role, corpus construction, break
detection, co-citation, text embedding, clustering).

**VF (`manuscript-Gide.qmd`, 233 lines, French, `lang: fr`)**
Intro (§sec-intro) → **Méthode** (no VEn equivalent as a standalone section;
folds fig-bars + fig-breaks in early, more compact) → Avant 1990–2006
(§sec-before: one paragraph per tradition + tbl-traditions, no separate
"corpus evidence" subsection) → Cristallisation 2007–2014 (§sec-crystallization:
Copenhagen/performativity, OCDE/CAD infrastructure, deux pôles + tbl-poles; no
"economists as architects", no separate corpus-evidence subsection) →
Controverses 2015–2025 (§sec-controverses: cas Türkiye §sec-transaction with
tbl-turkiye — compact but present — + quatre controverses, one compact
paragraph on computational corroboration) → Conclusion → Annexe A.1–A.5
(unnumbered: intro, corpus, ruptures dans le temps, filiations de citation,
polarisation efficacité/redevabilité + venue table + reproducibility
paragraph — **five** subsections, different topic split than VEn's six; no
equivalent of VEn's A.5 text-cleaning/embedding-model justification or A.6
clustering-method justification).

## Summary table

| ID | Location (VEn) | Serves (0152) | Recommendation |
|----|----|----|----|
| B01 | §1.1 Environmental economics, L88–95 | none found | merge |
| B02 | §1.2 Development econ / aid categories, L96–105 | R2.08 (open) | merge |
| B03 | §1.3 Burden-sharing / CDM, L106–113 | R2.15, R2.16, R2.17, R2.18 (open) | merge |
| B04 | §1.4 "Why climate finance did not yet exist", L114–118 | none found | drop |
| B05 | §1.5 Corpus evidence (Act I) + tbl-traditions caption, L120–134 | R1.2 (signed off), E3d (signed off) | keep |
| B06 | §2.0 Copenhagen moment / performativity, L142–155 | R2.21 (signed off), R2.28 (signed off) | keep |
| B07 | §2.1 Building statistical infrastructure, L156–167 | R2.32-adjacent (open, indirect) | merge |
| B08 | §2.2 Emergence of key concepts, L168–179 | R2.35 (open), R1.5 (open) | merge |
| B09 | §2.3 Economists as architects (AGF/Stern/Hourcade), L180–187 | R1.1 (open), R2.37 (open) | keep |
| B10 | §2.4 Corpus evidence (Act II), L188–195 | none found (E4 adjacent) | merge |
| B11 | §3.1 Anatomy of a single transaction (Türkiye), L208–219 | none found directly | merge (reconciliation — see note) |
| B12 | §3.2 Paris and transparency framework, L220–227 | R2.31 (open), R2.32 (open) | keep |
| B13 | §3.3 Four controversies after Paris, L228–241 | R2.30 (open) | merge |
| B14 | §3.4 $100bn claim / $300bn transition + loss-and-damage, L242–249 | **R1.4 (open, unaddressed)** | keep |
| B15 | §3.5 Corpus evidence (Act III), L250–263 | R1.2-adjacent (signed off, indirect) | merge |
| B16 | Appendix A.1 Logical role / falsificationist framing, L288–292 | E3 (signed off), E4 (signed off) | keep |
| B17 | Appendix A.2 Corpus construction boundaries, L294–298 | E3a (signed off), R1.o3 (signed off) | keep |
| B18 | Appendix A.3 Break detection methodology, L300–304 | E3b (signed off) | keep |
| B19 | Appendix A.4 Co-citation methodology, L308–312 | E3c (signed off), E3d (signed off) | keep |
| B20 | Appendix A.5 Text embedding / cleaning methodology, L314–316 | E3e (signed off) | keep |
| B21 | Appendix A.6 Clustering justification, L318–322 | E3f (signed off) | keep |
| B22 | Conclusion limitations paragraph, L280 | none found (adjacent to E-series honesty concerns) | merge |
| B23 | Intro reflexive-note paragraph, L74 | none found | drop |

**Counts:** 23 blocks — keep 11 (B05, B06, B09, B12, B14, B16–B21), merge 10
(B01–B03, B07, B08, B10, B11, B13, B15, B22), drop 2 (B04, B23).

## Décisions auteur (2026-07-08, session R+R)

- **Keep confirmé** : annexes B16–B21 (famille 4), B09 (economists as
  architects), B14 (loss & damage / R1.4).
- **Merge confirmé** : famille 1 (B01–B03) — réinjecter le détail
  CDM/GNI/additionnalité dans la base traduite.
- **B23 : drop validé** (auteur, 2026-07-08) — « c'est un point de méthode,
  pas d'intro ». L'idée (notre méthode est elle-même une commensuration,
  Espeland & Stevens) migre en annexe A.1 / point de méthode, au service du
  fil commensuration de 0137. Ne pas réintroduire dans l'intro.
- **B04 : drop validé avec pont narratif** (auteur, 2026-07-08) — l'acte I ne
  peut pas se terminer sur l'item 3 d'une énumération, il faut une
  résolution. Garder une clôture courte portant l'argument d'intersection
  (engagement politique × infrastructure statistique × logique de défaillance
  de marché → Copenhague), sans restaurer la sous-section récapitulative.
  À exécuter en 0175 ; vérifier d'abord si la Cristallisation VF porte déjà
  ce pont.
- Autres blocs (B05–B08, B10–B13, B15, B22) : recommandations non contestées,
  décision au fil de la revue de la PR t0174.

---

## Family 1 — §1 "Before" tradition subsections (concrete detail VF compressed into one table)

VF replaced VEn's three prose subsections with one paragraph each plus
`tbl-traditions`. That compression is fine as *narrative economy*, but it also
deleted concrete material that several **still-open** ticket-0141 remarks
(R2.09–R2.19, the largest single remark block at 29 items) are asking for.
This is the most consequential finding not spelled out by name in ticket
0172's family list ("§2 concretizations" — §1 has an equally large gap).

### B01 — §1.1 Environmental economics concrete detail
- **Location:** `manuscript.qmd` §sec-before, subsection "Environmental
  economics and the externality framework", L88–95.
- **Description:** Pigou→Ayres&Kneese "materials balance", cap-and-trade
  lineage (1990 Clean Air Act, EU ETS), "when-and-where flexibility" doctrine,
  Stern Review's "1% of GDP" figure as an aggregate-cost (not a flow) example.
- **Serves:** none found directly in the 0152 table (VF's compact version at
  L95 already covers the core authors; this is texture, not a targeted
  remark-response).
- **Recommendation:** merge — fold the "1% of GDP" contrast and the
  cap-and-trade lineage into VF's paragraph; a full reimport would restore
  the prose bulk VF deliberately shed.
- **Décision auteur:**

### B02 — §1.2 Development economics / aid categories concrete detail
- **Location:** L96–105.
- **Description:** DAC ODA tracking since the 1960s; grant element / face
  value / concessionality definitions (with the forward cross-reference to
  §sec-transaction); the 0.7% GNI target (1970 UNGA); the EU Structural and
  Cohesion Funds analogy (climate earmarking imposed 2021); Rio markers
  (1998) as self-assessed, unverified.
- **Serves:** R2.08 (open — "Define the GNI target") maps directly onto the
  0.7% GNI sentence here; VF's compact paragraph (L97) has no GNI figure at
  all.
- **Recommendation:** merge — the GNI-target sentence and the grant-element
  definition are load-bearing for R2.08/R2.02; the EU-Structural-Funds
  analogy is a nice-to-have, not required.
- **Décision auteur:**

### B03 — §1.3 Burden-sharing / CDM concrete detail
- **Location:** L106–113.
- **Description:** Negishi weights; Article 4.3's transactional language;
  CDM statistics (7,500+ projects, 105 countries, >$200bn nominal
  investment per UNFCCC Secretariat); the "additionality" concept's origin in
  CDM and its later migration into climate-finance debates; CER price
  collapse below €1 post-2012.
- **Serves:** R2.15 (open — "how the CDM functioned in practice"), R2.16
  (open — "additionality... migrated... develop with examples"), R2.17
  (open — CDM carbon-accounting vs financial-accounting distinction), R2.18
  (open — "post-2012 CDM collapse — who generated the demand for
  budget-based accounting?"). All four are currently unanswered (dash in the
  Response column) and are owned by ticket 0141.
- **Recommendation:** merge — this is the single highest-value block in
  Family 1: it directly answers four open remarks that ticket 0141 has not
  yet executed. Reimporting this passage (even lightly translated/adapted)
  would let 0141 close four rows nearly for free.
- **Décision auteur:**

### B04 — §1.4 "Why climate finance did not yet exist" synthesis
- **Location:** L114–118.
- **Description:** Closing synthesis paragraph: the three traditions had
  "remarkably little contact" before the late 2000s; Copenhagen as the
  moment of intersection.
- **Serves:** none found — this is narrative bridging, not evidence.
- **Recommendation:** drop — VF's closing paragraph of the same section
  (L101) already performs this synthesis function; reimporting would
  duplicate rather than add.
- **Décision auteur:**

### B05 — §1.5 Corpus evidence (Act I) + tbl-traditions caption
- **Location:** L120–134 (prose) + table caption L134.
- **Description:** Co-citation fragmentation among the three pre-2007
  traditions (Louvain on top-250 pre-2007 references); the Negishi-vs-
  North/DiMaggio/Finnemore divergence between intellectual-history anchors
  and co-citation anchors — explicitly why `tbl-traditions` keeps two
  separate anchor columns instead of one.
- **Serves:** R1.2 (**signed off** MHD 2026-06-19, commit 248c9f0 — "Divergence
  read as evidence about transmission, not against the tradition") and E3d
  (**signed off** MHD 2026-06-19, commit b6eb935 — this remark's "Where"
  field explicitly lists "§1.5 (§118); tbl-traditions caption" alongside
  Appendix A.4).
- **Recommendation:** keep — dropping this passage reopens two
  already-closed, author-signed-off remarks. VF's `tbl-traditions` (L103–109)
  has the anchor columns but not the explanatory prose that justifies keeping
  them separate; the prose is the part that answers R1.2/E3d, not the table
  alone.
- **Décision auteur:**

---

## Family 2 — §2 "Crystallization" concretizations

### B06 — §2.0 Copenhagen moment / institutional performativity
- **Location:** L142–155 ("The Copenhagen moment").
- **Description:** Bali Action Plan quote; the "Bali and Stern did not by
  themselves bring a new object into being" qualifying paragraph; MacKenzie's
  Barnesian-performativity distinction (Black–Scholes example) contrasted
  with "institutional performativity" (accounting directives, not market
  pricing); the explanatory link "why methodologies were fought over as
  bitterly as the political target."
- **Serves:** R2.21 (**signed off** MHD 2026-06-19, 248c9f0 — narrowed the
  overclaim to a datable claim) and R2.28 (**signed off** MHD 2026-06-19,
  248c9f0 — "institutional performativity made explanatory... §3 confirms").
- **Recommendation:** keep — same reasoning as B05: two closed remarks
  depend on this exact prose. VF's version (L113–116) states the core
  Callon-performativity point but has no MacKenzie/Barnesian contrast and no
  explicit "why fought over as bitterly" bridge — reimporting is required to
  avoid silently reopening R2.21/R2.28.
- **Décision auteur:**

### B07 — §2.1 Building statistical infrastructure
- **Location:** L156–167.
- **Description:** Rio markers' 1998→mid-2000s three-tier redesign; the
  Japan/UK divergent-interpretation example; the parallel UNFCCC Standing
  Committee on Finance (est. COP16 Cancún 2010) and its first Biennial
  Assessment (2014, $340–650bn range) contrasted with DAC donor-side
  reporting; the "battle for the operational definition" framing.
- **Serves:** no exact-ID match found; adjacent in spirit to R2.31/R2.32
  (open — UNFCCC reporting practices, competing donor/recipient regimes),
  which are more squarely served by B12.
- **Recommendation:** merge — the $340–650bn Biennial Assessment range and
  the Japan/UK example are concrete illustrations worth folding into VF's
  shorter infrastructure paragraph (L117–119), which currently asserts the
  Rio-marker ambiguity without a quantified example of its consequence.
- **Décision auteur:**

### B08 — §2.2 Emergence of key concepts
- **Location:** L168–179.
- **Description:** Post-Copenhagen vocabulary (mobilised private finance,
  leverage ratios, blended finance, de-risking, crowding-in); the OECD
  Research Collaborative on Tracking Private Climate Finance (2013–2015,
  named coordinators Jachnik and Caruso), its committee-level attribution
  debates (volume-based vs instrument-based, commitment vs disbursement);
  Stadelmann's eight baseline options for additionality (2011); Oxfam's
  first climate-finance shadow assessments (2012).
- **Serves:** R2.35 (open — "OECD expert groups 'set the terms of debate'
  too vague — when/where/which experts/what methods/what debates") maps
  directly onto the Research Collaborative detail here; R1.5 (open — finance–
  development nexus, situate blended finance/de-risking) is partly served by
  the vocabulary-origin discussion.
- **Recommendation:** merge — the committee detail (named coordinators,
  dates, the volume-vs-instrument attribution split) is exactly the
  concreteness R2.35 asks for and is currently open; VF's `tbl-poles`
  (L123–128) states the two vocabularies conceptually but has zero
  institutional-history detail behind them.
- **Décision auteur:**

### B09 — §2.3 Economists as architects (AGF, Stern, Hourcade)
- **Location:** L180–187 (entire subsection).
- **Description:** The UN Secretary-General's High-Level Advisory Group on
  Climate Change Financing (AGF, 2010) — co-chairs Zenawi/Stoltenberg,
  Stern's membership, the sources/instruments/governance analytical
  framework, the carbon-pricing-as-source ambiguity left unresolved; Jean-
  Charles Hourcade's "financial paradox" argument (CIRED).
  **This entire subsection has no counterpart anywhere in the VF.**
- **Serves:** R1.1 (open — "'Economists' claim under-specified: named
  figures are policy professionals, not academics... cite Golka (2024)") —
  this subsection is precisely the concrete naming R1.1 asks for, just
  missing the Golka citation and the explicit "policy professional, not
  academic" framing. R2.37 (open — "UN Advisory Group composition [...] —
  does it matter for the argument?") is answered nowhere else in either text.
- **Recommendation:** keep — the largest single concretization gap found in
  this inventory. It is a complete, self-contained subsection that VF simply
  does not have, and it is the most direct existing material answering R1.1,
  the editor/R1's central complaint about under-specified "economists."
  Ticket 0172's family list ("§2 concretizations") undersells this: it is not
  a thinning, it is a total absence.
- **Décision auteur:**

### B10 — §2.4 Corpus evidence (Act II)
- **Location:** L188–195.
- **Description:** Vocabulary shift sharply dated to 2007–2008; publication
  ecology of the crystallization core (OECD/IEA Climate Change Expert Group
  papers, CPI's *Global Landscape of Climate Finance*, first published 2012);
  the finding that the *most-cited* works show thematic stability 2005–2020
  (vocabulary drift is driven by an influx of lower-cited scholarship, not a
  reorientation of influential works).
- **Serves:** no exact-ID match; thematically adjacent to E4 (signed off —
  Figure 2's role) and to the Appendix A.3/A.4 methodology already kept
  (B18/B19).
- **Recommendation:** merge — the "most-cited-works are thematically stable"
  finding is a strong, falsifiable-style result worth folding into VF's
  Annexe A.3 (which currently doesn't distinguish core-subset from
  full-corpus stability at this granularity); the publication-ecology detail
  is optional color.
- **Décision auteur:**

---

## Family 3 — §3 "Established Field" concretizations and the worked transaction

### B11 — §3.1 Anatomy of a single transaction (Türkiye/World Bank)
- **Location:** VEn §sec-transaction, L208–219 (5 footnotes). VF counterpart:
  §sec-transaction, L137–160 (2 footnotes + `tbl-turkiye`).
- **Description — granularity comparison (per ticket 0172's specific ask):**
  VEn narrates the three-instrument breakdown as continuous prose ending in
  two open questions (*additionality*, *specificity*); VF organizes the same
  case around an explicit table (`tbl-turkiye`) plus three separately-labeled
  controversies (concessionality, qualification climatique, additionality).
  VEn's footnotes derive the grant-element discount rate explicitly (OECD DAC
  6% for upper-middle-income Türkiye = 5% base + 1% margin) and name the
  Joint MDB Methodology for climate finance as the parallel scheme to Rio
  markers; VF's footnotes instead cite a dated press release (4 August 2025)
  and a Project Information Document (PID PIDIA01318, 28 April 2025) as
  primary sourcing. **Numerical discrepancy:** VEn states "some fifteen
  gigawatts of additional wind and solar capacity"; VF states "1,7 gigawatt"
  (1.7 GW) for the same project (P508354) — an order-of-magnitude difference
  that is a reconciliation matter, not a translation choice.
- **Serves:** no exact 0152-row match (the transaction case is illustrative
  throughout §3, not tied to one remark ID).
- **Recommendation:** merge, with an explicit flag — VF's version is the
  one going forward (tracker 0172 already routes Türkiye reconciliation to
  child 0175, "downgraded to reconciliation, both texts primary-sourced").
  This inventory's contribution: pull VEn's more precise discount-rate
  derivation and the "Joint MDB Methodology" naming into VF's footnotes if
  0175 judges them additive, and **surface the 15GW vs 1.7GW discrepancy to
  0175 explicitly** — it was not visible as a discrepancy until this
  side-by-side read.
- **Décision auteur:**

### B12 — §3.2 Paris and the transparency framework
- **Location:** L220–227.
- **Description:** Enhanced Transparency Framework (ETF) reporting formats
  negotiated through SBSTA, drawing on OECD DAC categories; face-value-vs-
  grant-equivalent deferral (both allowed); multilateral development banks'
  joint climate-finance methodology (from 2011, project-level activity-based,
  contrasted with DAC's policy-marker approach); the Green Climate Fund's own
  investment framework; the International Development Finance Club (IDFC,
  27 national/regional development banks, largely Global South) and its
  Green Finance Mapping. **Entirely absent from VF.**
- **Serves:** R2.31 (open — "UNFCCC reporting practices: to whom are flows
  reported, by whom, for what institutional purpose?") and R2.32 (open —
  "Describe the competing donor vs recipient measurement regimes explicitly")
  are the closest matches; this passage is the concrete institutional
  material both remarks are asking for.
- **Recommendation:** keep — a complete institutional layer (MDB joint
  methodology, GCF, IDFC) that VF's controverses section does not mention at
  all, and that directly supplies the concreteness R2.31/R2.32 (both still
  open, owned by 0141) are asking for.
- **Décision auteur:**

### B13 — §3.3 Four controversies after Paris (detailed citations)
- **Location:** L228–241.
- **Description:** VEn's version of the same four controversies VF also
  covers (L162–172), but with additional citations and cases: Michaelowa's
  "audit failure" framing via Power (1997); Oxfam Shadow Reports' specific
  quantified adjustments; Skovgaard (2017) on finance-ministry framing to
  avoid new budgetary commitments; Steckel et al. (2016) proposing to dissolve
  the climate-finance/development-finance boundary (rejected as gaining
  "little traction"); the observation that China, Gulf states, and other
  non-Annex-I upper-middle-income countries complicate the frozen 1992
  Annex binary; Paris's "in light of different national circumstances" as a
  deliberate retreat from binary classification.
- **Serves:** R2.30 (open — "Desrosières/Porter may not be the best refs for
  biased aid architectures — engage Escobar, Tim Mitchell") is adjacent: this
  passage is where alternative/critical citations would be added, though
  Escobar/Mitchell themselves are not yet present in either text.
- **Recommendation:** merge — fold the Steckel2016/Skovgaard2017/China-Gulf
  material into VF's compact four-controversies section; these are citations
  and cases VF's version lacks outright, not just compression.
- **Décision auteur:**

### B14 — §3.4 The $100bn claim and the $300bn transition (incl. loss & damage)
- **Location:** L242–249.
- **Description:** OECD's 2022 announcement of $115.9bn (exceeding the
  $100bn target); Oxfam's quantified counter-estimate ($21–24bn "climate-
  specific net assistance" against OECD's reported $60–80bn in the same
  years — less than a third); COP27's loss-and-damage fund (2022) as a
  category that "potentially disrupts the crystallization-era framework...
  neither mitigation nor adaptation... raises questions of liability the
  existing accounting system was designed to avoid"; COP29/Baku NCQG
  ($300bn/2035); China's bilateral development finance (China Development
  Bank, FOCAC) as invisible to the OECD DAC accounting infrastructure.
  VF's equivalent is a single footnote citing the $115.9bn figure and a
  footnote citing the Baku decision (L172) — **no loss-and-damage discussion,
  no Oxfam quantified breakdown, no China Development Bank/FOCAC point.**
- **Serves:** **R1.4 (open, unaddressed — no response in the 0152 table)** —
  "Loss & damage / insurance (actuarial) logic sits outside crystallisation-
  era categories — challenges the 'disputes within established categories'
  thesis." This is the single clearest match in this entire inventory between
  an open, currently-unanswered remark and existing VEn material that VF
  dropped. Ticket 0138 owns R1.4 and has not yet executed it (dash in
  Response/Where/Commit/Sign-off columns).
- **Recommendation:** keep — this passage is the closest existing draft
  answer to a live open remark. Losing it in the VF-based rebuild would mean
  ticket 0138 has to reconstruct this argument from scratch; reimporting it
  gives 0138 a running start (though the remark still needs full resolution,
  since VEn itself only raises loss-and-damage as an open question rather
  than resolving it).
- **Décision auteur:**

### B15 — §3.5 Corpus evidence (Act III)
- **Location:** L250–263.
- **Description:** Six-cluster decomposition of the post-2015 literature;
  the two-pole (efficiency/accountability) structure detected across both
  thematic and lexical analyses, attenuated but detectable in the most-cited
  core; venue ecology detail (*Review of Financial Studies*, *JFE*, *Energy
  Economics* for the efficiency pole vs *Global Environmental Politics*,
  *Climatic Change*, *WIREs Climate Change* for the accountability pole,
  with *Climate Policy* as shared ground); a Herfindahl–Hirschman venue-
  concentration check (0.07 in 1998 → 0.003 by 2024, no spike at either
  structural break, ruling out editorial-consolidation as an artifact
  explanation); asymmetric growth analysis (efficiency-pole publications
  multiplying faster, accountability pole diversifying rather than thinning).
- **Serves:** no exact-ID match; indirectly related to R1.2's "computational
  analysis weakly connected, large footprint / low returns" concern (signed
  off via the Appendix justification, not this passage specifically).
- **Recommendation:** merge — the HHI concentration check and the venue-
  ecology detail are strong, specific evidence for the two-pole thesis that
  VF's one-paragraph equivalent (L176) does not carry; recommend folding the
  HHI check and the venue table's in-text elaboration in, while trimming the
  asymmetric-growth paragraph as lower-priority.
- **Décision auteur:**

---

## Family 4 — Appendix A.1–A.6 (methods justification, all author-signed-off)

Every block in this family answers a remark from the editor's methods
critique (E3/E3a–f/E4, ticket 0136, 13 of the 60 atomic remarks — **the
single largest remark concentration in any one ticket after 0141**), and
every one of those remarks is **already signed off** (MHD 2026-06-19, mostly
commit 248c9f0, with E3d at b6eb935). Dropping any of these six blocks
silently reopens a closed, author-approved remark. VF's own Annexe (A.1–A.5,
a different five-way split) covers the same three empirical tests at a much
shallower level of methodological defense and has no equivalent at all to
VEn's A.5 (text-cleaning/embedding) or A.6 (clustering-method comparison).

### B16 — Appendix A.1: The logical role of the quantitative analysis
- **Location:** L288–292.
- **Description:** States the falsificationist framing explicitly — each of
  the three corpus findings is presented as an "attempted refutation the
  narrative survives," not evidence used to discover the narrative;
  directionality (history → data) stated plainly, tied to why
  `tbl-traditions` keeps intellectual-history and co-citation anchors in
  separate columns.
- **Serves:** E3 (signed off — "Methods justification brought into the paper
  as a new Appendix (A.1–A.6)... quant role named confirmatory") and E4
  (signed off — "Role named confirmatory; directionality stated").
- **Recommendation:** keep.
- **Décision auteur:**

### B17 — Appendix A.2: Corpus construction and its boundaries
- **Location:** L294–298.
- **Description:** Six sources, four-tier keyword taxonomy (eight languages),
  DOI + normalized title/year dedup; two boundary choices stated and
  defended — (1) grey literature included deliberately because the category-
  making happened in OECD/UNFCCC/institutional documents, not journals; (2)
  core-economics-journal under-representation framed as a finding about
  where the intellectual work was done, not a selection artifact.
- **Serves:** E3a (signed off — "Corpus construction documented") and R1.o3
  (signed off — "Boundary criteria justified... framed as a finding, not a
  selection artifact").
- **Recommendation:** keep.
- **Décision auteur:**

### B18 — Appendix A.3: Why three periods, and how the boundaries were detected
- **Location:** L300–304.
- **Description:** Jensen–Shannon divergence + cosine distance, z-scored
  across candidate years 2005–2023, three window widths; strongest break at
  2007 with a second at 2013; under 2-year censoring only 2009 (Copenhagen)
  survives; Paris (2015) shows only a marginal JS rise, not a rupture; the
  core (highly-cited) subset shows no break at all 2005–2020.
- **Serves:** E3b (signed off — "Endogenous JS+cosine break detection; 2007
  break robust, Copenhagen 2009 dominant under censoring, no 2015 break; core
  shows none").
- **Recommendation:** keep.
- **Décision auteur:**

### B19 — Appendix A.4: Co-citation communities
- **Location:** L308–312.
- **Description:** 250-reference ceiling rationale (load-bearing references,
  computationally trivial); edge-weight threshold; Louvain-vs-Leiden
  justification (negligible difference at ≤250 nodes); modularity discussion
  — the unverifiable "0.68 / 10 communities / three clusters" claim was
  explicitly **dropped** from the main text per author decision, deferred to
  the companion technical report, replaced with the qualitative "fragmented
  into many small, weakly connected lineages" statement.
- **Serves:** E3c (signed off — "Co-citation rationale + 250-ref ceiling
  justified") and E3d (signed off — "Louvain-vs-Leiden justified...
  unverifiable claim dropped... per author decision").
- **Recommendation:** keep — note E3d's fix (dropping the 0.68/10-communities
  claim) must travel together with B05 (§1.5/tbl-traditions caption), since
  E3d's "Where" field spans both locations.
- **Décision auteur:**

### B20 — Appendix A.5: What is embedded, and how the text is cleaned
- **Location:** L314–316.
- **Description:** No full-text processing — title + abstract (if >20 chars)
  + keywords only; Unicode/mojibake/zero-width-character normalization before
  embedding; `BAAI/bge-m3` multilingual sentence-transformer (1024-dim,
  L2-normalized, 8192-token context); a direct test showing the model does
  not segregate texts by language (English/non-English split is
  anti-clustered, silhouette −0.01). **No equivalent anywhere in VF.**
- **Serves:** E3e (signed off — "Premise corrected: no full text used;
  embeds title+abstract+keywords after normalization").
- **Recommendation:** keep.
- **Décision auteur:**

### B21 — Appendix A.6: Clustering — why k-means, why six, how robust
- **Location:** L318–322.
- **Description:** k=6 matched to the six co-citation communities (not an
  optimum read off the data); near-zero silhouette at every k disclosed
  candidly (climate finance is a continuum); HDBSCAN rejected (~98% flagged
  as noise); spectral clustering rejected (unstable, ARI 0.59 across
  snapshots, cubic scaling); k-means's stability under corpus growth (ARI
  0.98 between snapshots) and its one known weakness (reshuffled partition
  boundaries ~1-in-10 re-clusterings, now contained by fixed reference
  centroids); the three representation spaces (semantic/lexical/citation)
  are nearly independent (ARI 0.06–0.22), which is why traditions are read
  from co-citation and not from embedding clusters. **No equivalent anywhere
  in VF.**
- **Serves:** E3f (signed off — "k-means/k=6 justified... robustness ARI
  0.98; HDBSCAN/Spectral rejected with reasons").
- **Recommendation:** keep.
- **Décision auteur:**

---

## Family 5 — Conclusion and minor passages

### B22 — Conclusion: "Several limitations point to further research"
- **Location:** L280.
- **Description:** Corpus remains English-dominated despite multilingual
  intent; the developed/developing binary frozen in 1992 "remains one of the
  most consequential yet least examined constructions"; the economists-as-
  architects account "rests on published outputs rather than archival
  records or interviews... claims about individual motivations remain
  conjectural"; professional financial media (*The Economist*, *FT*,
  Bloomberg) explicitly out of scope; Article 4.3→NCQG "deserves a dedicated
  legal-institutional history." VF's conclusion has its own, differently
  scoped "chantiers" paragraph (L188: archivistic, geographic, legal,
  loss-and-damage-as-test) — not a subset or superset of VEn's, a genuinely
  different list.
- **Serves:** none found by remark ID; thematically adjacent to the E-series
  methodological-honesty concerns (E3/E4 family) but not a direct match.
- **Recommendation:** merge — VEn's "rests on published record, not
  interviews/archives" caveat is a methodological-honesty admission worth
  keeping regardless of translation base (it matches this project's
  "cite only pipeline numbers traceable to an archived output" norm); the
  English-dominance caveat duplicates Appendix A.2 (already kept via B17) so
  is lower priority; recommend a light fold rather than wholesale reimport
  since VF's own chantiers paragraph is substantive and should not simply be
  replaced.
- **Décision auteur:**

### B23 — Introduction: reflexive-note paragraph
- **Location:** L74 ("A reflexive note is warranted...").
- **Description:** The paper's own method (embeddings, statistical pattern
  detection) is itself framed as "an act of commensuration in Espeland &
  Stevens's sense" — a one-paragraph reflexive aside.
- **Serves:** none found.
- **Recommendation:** drop — no remark depends on it, and VF's Méthode
  section (L75, "objet-limite... produit d'une économie pratique de la
  mesure") already carries comparable reflexivity in different words; adding
  VEn's paragraph on top would be redundant rather than additive.
- **Décision auteur:**
