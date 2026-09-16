# Roadmap

## North star

Building toward a book on international climate finance between solidarity and profit. This repo is the research infrastructure: a 30K-work corpus, analysis pipeline, and the articles that test each piece of the argument before it becomes a chapter.

## JETP observatory and papers

- [x] Local observatory preview with country synthesis, project evidence and
  historical browsing; scientific date/link/acquisition corrections in PR #1343.
- [x] Prepared, citable four-country data release0726 → local observatory
  acceptance0727 → reviewed monthly-edition/replay handoff0728. Two immutable
  releases replay offline; deployment remains an author decision.
- [x] Historical/bilateral evidence audit 0735 and pilot protocol prepared in PR #1347.
- [ ] Accept selection audit PR #1348; its pinned evidence remains available.
- [x] Run and merge bounded AFD 0737, KfW 0738 and FCDO 0739 feasibility pilots.
  Their synthesis preserves NARROW/DEFER conclusions and rules out a
  single-donor JETP-effect claim.
- [ ] Accept the reviewed 0736 selection audit, 0729 causal DEFER and 0814
  feasibility DEFER from their branches; do not repeat them as open decisions.
- [ ] Execute the author-authorised non-causal JETP measurement programme:
  protocol0816 → source census0817 → country ingestion0818–0821 → frozen
  snapshot0822 → statistics0730/figure0823 and MVP0824 → short paper0732.
  Current framing: `conception/jetp-short-paper-framing-2026-09-15.md`.
  First establish a common operation sample for progression, public/private
  finance and history under 0816; 0823 combines these in three figure panels.
- [ ] JETP data paper0731 after0726; long political-economy paper0733 with Christophe.
  LaTeX scaffolds0711 remain required for the two analytical manuscripts.

See `conception/jetp-observatory-and-papers-plan.md`. A null effect is acceptable;
failed identification returns to an author scope decision. The website and data
paper do not depend on demonstrating acceleration. AEDIST methods pilot remains
Imagine-only, separate from this operational programme.

## Oeconomia manuscript next steps

Submitted to Oeconomia (Varia) on 2026-03-18. Revise-and-resubmit received;
manuscript rebuilt (v2.0.5), response letter drafted (ticket 0152).

- [x] Wait for reviewers feedback
- [ ] Revise and Resubmit — in progress: R1/R2 ledger sign-offs, then 0195 → 0153 (rebuild, deposit, resubmit)
- [ ] Continue Tier 1 reading plan (defence against reviewer questions)

## Data paper manuscript next steps

Submitted data paper to RDJ4HSS (diamond OA).

- [x] Wait for reviewers feedback (R&R received)
- [x] Revise (revision 1 released 2026-07-29: Zenodo v2.0.0, HAL v2, tag `rdj26561-revision1`)
- [x] Resubmit on the journal platform — publication confirmed by the author
  on 2026-09-16.
- [ ] Present at conference

## Charles Gide conference (Vannes, July 2-4)

21st International Colloquium of the Charles Gide Association, theme "Crises". Abstract accepted.

- [x] Write conference paper (due 2026-06-15) — `manuscript-Gide.qmd`, French short version
- [x] Present at Vannes (2026-07-02 to 04)
- [ ] Consider submission to RHPE special issue on "Crises" (call post-conference)

## Next articles

- [ ] **Paper 4 — Multilingual: "Whose evidence shapes climate policy?"** (ticket 0014) — Empirical finding paper. The $300B NCQG was constructed from English-indexed scholarship alone; Chinese (South-South, Belt-and-Road) and Brazilian (deforestation finance) traditions were invisible. Two-axis design (language × geography) disentangles linguistic from epistemic barriers. Blocked on Paper 5 (corpus v2.0). Journals: Global Environmental Change, World Development, Nature Climate Change Analysis. Supersedes the older "epistemic blind spots" framing (multilingual-paper epic on hold per ticket 0001).
- [ ] **Paper 5 — Corpus v2.0** (ticket 0013) — Add CNKI (Chinese) and SciELO (Portuguese/Spanish) to raise non-English share from 7% to 20-30%. Enables Paper 4. Journal TBD; methods-heavy, Scientometrics or QSS if submitted standalone.
- [ ] **Paper 3 — Companion methods paper** (epic 0026) — Multi-layer detection and validation of structural change in text corpora. Lean 6-method panel across 3 layers (embedding / lexical / graph) with permutation Z-scores and transition zones. Wave C in flight, blocked on 0042 pipeline rerun. Journal: Quantitative Science Studies (QSS, chosen).
- [ ] **OECD vs. Oxfam** — How do competing accounting frameworks produce divergent truths from the same financial flows? Contribution: a sociology-of-quantification case study showing how measurement conventions perform political positions on North-South climate debt. Requires document-to-evidence extraction capabilities (cf. [AEDIST](https://github.com/MinhHaDuong/aedist) stage 2). Journals: Accounting, Organizations and Society; Social Studies of Science.
- [ ] **MDB greening pivot** — How did multilateral development banks reframe existing portfolios as "climate finance" without changing what they fund? Contribution: an economization analysis of institutional relabeling as performative category work. Requires document-to-evidence extraction capabilities (cf. AEDIST stage 2). Journals: Review of International Political Economy, New Political Economy.
- [ ] **Carbon markets as failed performativity** — Why did the CDM fail to produce the efficient abatement market it modeled, and is Article 6 repeating the same design flaws? Contribution: a MacKenzie-style analysis of how market devices for North-South carbon transfers failed to perform the world they assumed. Journals: Economy and Society, Journal of Cultural Economy.
- [ ] **Sectoral deals vs. global targets** — Why are sector-by-sector technology cooperation agreements more effective than aggregate financial pledges? Contribution: a comparative policy analysis using the Montreal Protocol as benchmark, arguing the NCQG $300bn target repeats the $100bn's structural failure. Journals: Climate Policy, Global Environmental Politics.

## Milestones

- **Project start (2026-02-18)**: repo created, first commit, manuscript plan, corpus pipeline design
- **v1.0 — Oeconomia submission (2026-03-18)**: tag v1.0, corpus pipeline (6 sources, DVC, teaching scraper), analysis (embeddings, clustering, figures), manuscript (all sections, house style, AI-tell sweep), submission packaging (Zenodo, HAL, cover letter)
- **v1.1 — RDJ4HSS data paper (2026-03-26)**: tag v1.1, data paper drafted and submitted, companion paper outlined, reproducibility archives
- **v1.1.1 — Pipeline refactor (2026-03)**: enrichment split into 4 independent DVC stages (#428), code smell cleanup (#507), agent harness consolidation, script I/O discipline (#547, #549)
- **v1.1.2 — Citation enrichment (in progress)**: GROBID reference parsing (#539), Crossref DOI fallback, circuit breakers (#590, #598), citation hardening (#529)
- **Imperial Dragon harness (2026-04-01)**: workflow renamed from Dragon Dreaming (4 phases) to Imperial Dragon (5 claws), generic harness extracted to ~/.claude/ (#628)
- **v2.0.5 — Œconomia R&R revision (2026-06/07)**: referee reports answered point by point (60-remark ledger, ticket 0152), manuscript rebuilt on the "birth of an aggregate" framing, Gide-Vannes French short version presented (2026-07-02/04)
