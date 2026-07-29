---
format:
  pdf:
    papersize: a4
    include-in-header:
      text: |
        \pagestyle{empty}
---

# DRAFT — Cover letter to the editor, RDJ-26561 (author sign-off required before submission)

Minh Ha-Duong,
CIRED, CNRS
45 bis avenue de la Belle Gabrielle, 94736 Nogent-sur-Marne, France
minh.ha-duong@cnrs.fr

Dr Cédric Chambru,
Research Data Journal for the Humanities and Social Sciences

Paris, DATE-AT-SIGNATURE

**Re: revised manuscript RDJ-26561**

Dear Dr Chambru,

Please find the revised version of manuscript RDJ-26561, retitled "A
Curated Multi-Source Corpus of Climate Finance Literature, 1990–2024:
Multilingual Retrieval and Institutional Reports." Every point raised has
been addressed. The key changes:

- **The dataset itself changed, not only the paper.** Prompted by the
  referee's remark on institutional coverage, the corpus gains a curated
  layer of UNFCCC and OECD DAC key documents and grows from 42,916 to
  43,179 unified works (30,987 to 33,344 after filtering). The Zenodo
  deposit (same concept DOI, new version) is restructured as you requested
  into code, raw inputs, and final products, with an executable data
  dictionary; every corpus statistic in the paper is regenerated
  by the deposited pipeline.
- **The revision strengthens the paper partly by weakening its claims.**
  The citation-link audit rerun on the new corpus reports 97.0% confirmed
  (previously 99.0%), stated as agreement with Crossref rather than ground
  truth, and the revision measures and discloses a language bias in the
  relevance filter, absent from the submitted version.
- **One referee suggestion is declined with an alternative**: the corpus
  CSV keeps its published layout, and the revision documents the structure
  instead — a generated variables table in the paper and a Frictionless
  `datapackage.json` a reader can execute to verify the file.
- Going beyond the discussion of research directions you asked for, three
  published results were re-tested on the corpus to demonstrate added
  value. The reply notes report them; the paper keeps the growth break in
  Section 4. I will gladly move the other two into the text if you prefer.
- The draft of the companion history-of-thought study built on this corpus
  is enclosed, so the dataset's research potential can be assessed on use.

Thank you and the referee for a report that made both the paper and the
dataset better.

Sincerely,

Minh Ha-Duong
