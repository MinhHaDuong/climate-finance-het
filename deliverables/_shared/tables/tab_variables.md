::: {#tbl-variables}
```{=latex}
\begin{longtable}{@{}l p{10.4cm}@{}}
\toprule
Variable & Description \\
\midrule
\endfirsthead
\toprule
Variable & Description \\
\midrule
\endhead
\texttt{source} & Primary source catalog for the record's metadata \\
\texttt{source\_id} & Identifier in the primary source (e.g. OpenAlex work ID) \\
\texttt{doi} & Digital Object Identifier, when available \\
\midrule
\texttt{title} & Title of the work \\
\texttt{first\_author} & First author name \\
\texttt{all\_authors} & Full author list, separator-joined \\
\texttt{year} & Publication year \\
\texttt{journal} & Publication venue (journal, publisher, or repository) \\
\texttt{language} & Language code (ISO 639-1), detected and normalised \\
\texttt{keywords} & Keywords, semicolon-separated \\
\texttt{categories} & Subject categories / concepts from the source catalog \\
\texttt{cited\_by\_count} & Citation count (OpenAlex, as of the collection date) \\
\texttt{affiliations} & Author affiliations, when available \\
\midrule
\texttt{from\_openalex} & Provenance flag: found in OpenAlex \\
\texttt{from\_istex} & Provenance flag: found in ISTEX \\
\texttt{from\_bibcnrs} & Provenance flag: found in bibCNRS \\
\texttt{from\_scispace} & Provenance flag: found via SciSpace \\
\texttt{from\_grey} & Provenance flag: institutional reports (Section 2.1) \\
\texttt{from\_teaching} & Provenance flag: teaching canon (syllabi) \\
\texttt{from\_unfccc} & Provenance flag: curated UNFCCC key document \\
\texttt{from\_oecd} & Provenance flag: curated OECD key document \\
\texttt{abstract\_provenance} & Provenance of the abstract, for curated key documents only \\
\texttt{keywords\_provenance} & Provenance of the keywords, for curated key documents only \\
\texttt{language\_provenance} & How the language code was obtained (Section 2.4) \\
\texttt{source\_count} & Number of sources that contributed the record \\
\midrule
\texttt{abstract\_status} & Whether the undistributed abstract was original, reconstructed from an inverted index or fulltext, LLM-summarised, oversized, or missing \\
\texttt{near\_duplicate\_group} & Group identifier for near-identical content published under several DOIs \\
\texttt{semantic\_outlier\_dist} & Distance to the corpus embedding centroid \\
\texttt{in\_v1} & Version tracking: work present in the v1.0 submission corpus \\
\texttt{is\_flagged} & Any quality flag raised; the refined subset is \texttt{df[\textasciitilde{}df[\textquotesingle{}is\_flagged\textquotesingle{}] \textbar{} df[\textquotesingle{}is\_protected\textquotesingle{}]]} \\
\texttt{flag\_reason} & Comma-separated list of raised quality flags; empty when unflagged \\
\texttt{is\_protected} & Protection from removal (key papers kept despite flags) \\
\texttt{protection\_reason} & Why the work is protected (Section 2.2) \\
\bottomrule
\end{longtable}
```

Variables of `climate_finance_corpus.csv`. Horizontal rules separate the four logical groups: record identity, bibliographic metadata, provenance flags, curation metadata. Generated from the deposit column contract (`scripts/_deposit_variables.py`); storage types, allowed values, ranges and measured missingness are in the deposited `datapackage.json`.
:::
