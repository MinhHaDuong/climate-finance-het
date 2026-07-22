# Manuscript bibliography vs corpus — coverage probe (ticket 0288)

Empirical basis for the corpus-v2 source extension, proposed by the author
(session 2026-07-22): cross the resubmitted Œconomia manuscript's bibliography
against the v1 refined corpus, and let the *classes* of absent-but-needed
documents bound the extension. The alternative — an a priori list of
institutions — has no natural stopping rule.

Method: `probe_bib_vs_corpus.py` extracts the citation keys used in
`deliverables/manuscript/manuscript.qmd` (v2.0.5, resubmitted 2026-07-21),
resolves them in `deliverables/_shared/bibliography/main.bib`, and matches each
work against `data/catalogs/refined_works.csv` (corpus v1, 31,873 rows) by
normalized DOI, then exact normalized title, then a title-substring pass on the
misses to weed out false negatives.

## Numbers (2026-07-22, corpus v1)

- 81 works cited in the manuscript; 31 matched in the corpus (DOI or title).
- 50 unmatched, of which 1 false negative (Buchner/CPI *Global Landscape of
  Climate Finance*: the series is in the corpus under edition-specific titles).
- The remaining ~49 absences fall into five classes, below.

## Classes of absence

**A. UNFCCC official documents (5 cited, all absent as such).** Bali Action
Plan, Copenhagen Accord, Cancún Agreements, 2014 Biennial Assessment, CDM
Achievements report. The corpus holds *commentary about* these decisions, not
the decisions themselves — and holds the *fifth* Biennial Assessment while
missing the 2014 first edition, so even the flagship accounting series is
covered only incidentally. This is direct empirical confirmation of the UNFCCC
sub-list in ticket 0288, including its emphasis on the BA series.

**B. Other international-institution documents (2).** GEF Evaluation Office
report (*Evaluation of Incremental Cost Assessment*, 2007) — inside 0288's
frame (GCF/GEF/AF reports to COP). AOSIS submission on the NCQG (2024) —
a **party/negotiating-bloc submission**, a sub-class 0288 did not initially
name. Decision (author, 2026-07-22): submissions are INCLUDED.

**C. Negotiation record (2).** IISD *Earth Negotiations Bulletin* summary
(COP15) and a political speech (Clinton at Copenhagen). Decision (author,
2026-07-22): negotiation-record commentary is INCLUDED — session summaries and
statements delivered at COPs join the layer alongside the decisions they
surround.

**D. Pre-crystallization economics ancestry (~11).** Negishi 1960, Weitzman
1974, Ayres–Kneese 1969, Nordhaus 1992, Manne–Richels 1992, Carraro–Siniscalco
1993, Barrett 1994/2006, Aghion–Bolton 1997, King–Levine 1993, Hourcade et al.
2015. Predecessor literature the field cites, predating or exceeding the
"climate finance" scope. Out of corpus scope by design (they appear as
referenced works in `refined_citations.csv`, not as corpus works); no harvest
class here.

**E. HET/STS analytical apparatus (~29).** MacKenzie, Callon, Çalışkan–Callon,
Desrosières, Porter, Power, Merry, Espeland–Stevens, Star, Gieryn, Mitchell,
Escobar, DiMaggio–Powell, North, Finnemore–Sikkink, Marcussen, Claveau–Dion,
Goutsmedt et al., Acosta et al., Lepenies, Cassen–Cointe, Aykut–Dahan, Pottier,
Michalopoulos, and others. The historiographic toolkit of the paper, not the
object of study. Correctly outside the corpus; no harvest class. The two apparent
borderline cases were verified on the documents (2026-07-22) and resolved:
MacKenzie 2009 (*Making Things the Same*) treats commensuration in carbon
markets (the manuscript cites it for the CDM HFC-23 projects), and Golka 2024
(*Epistemic gerrymandering*) treats ESG and impact investing, with no
occurrence of "climate finance" in abstract, keywords, or introduction. Carbon
markets and ESG are deliberate corpus-scope exclusions, so both absences are
by design, not query gaps — the exclusions belong in the paper's scope/bias
section.

## Implication for the 0288 inclusion rule

The probe supports the extension as framed and bounds it: the only document
classes the manuscript actually needed and the corpus lacks are the official
international-institution documents (A, B) plus the negotiation record (C),
which the author folded into the layer (decisions of 2026-07-22: submissions
and negotiation-record commentary included). No open-ended new class emerges —
ancestry (D) and apparatus (E) are correctly out of scope, and carbon markets
and ESG stay deliberate scope exclusions to state in the bias section. The
amended inclusion rule sits in ticket 0288, Action 1.

Caveats: the manuscript bibliography is one author-curated document of 81 works
— a revealed-demand lower bound, not an exhaustive gap analysis; matching is
DOI + title-based, so retitled editions can miss (one caught). Rerun the probe
against corpus v2 after the 0288 harvest as a cheap regression check: classes
A and B should then match.

Reproduce:

```sh
python3 deliverables/data-paper/revision-rdj26561/probe_bib_vs_corpus.py \
  --qmd deliverables/manuscript/manuscript.qmd \
  --bib deliverables/_shared/bibliography/main.bib \
  --corpus data/catalogs/refined_works.csv
```
