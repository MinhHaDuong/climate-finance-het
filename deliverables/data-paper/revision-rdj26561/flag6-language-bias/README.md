# Flag 6 language bias — study record (2026-07-28)

Diagnostic study behind tickets 0337 (ablation), 0283 (reply-letter
disclosure), and the 0540/0541/0542 corpus-v3 tree. All measurements on
frozen corpus v2 (`extended_works.csv`, 43,179 works); the corpus was not
touched.

## Question

Four external reviewers objected that the relevance filter may remove
exactly the grey and non-English records the corpus claims to add. Does it?

## Part 1 — removal ablation (per stratum)

Flags and protection read from `extended_works.csv` (pre-removal, so
nothing is circular). `removed` = `action == would_remove` (9,434 works;
DOI dedup drops another 401 on the way to 33,344 refined).

| stratum | n | flagged | rescued | removed | % removed |
|---|---|---|---|---|---|
| openalex | 41,138 | 10,627 | 1,405 | 9,222 | 22.4% |
| istex | 748 | 165 | 57 | 108 | 14.4% |
| bibCNRS | 233 | 11 | 1 | 10 | 4.3% |
| scispace | 663 | 44 | 17 | 27 | 4.1% |
| grey | 281 | 84 | 17 | 67 | 23.8% |
| teaching | 622 | 354 | 354 | 0 | 0.0% |
| UNFCCC | 232 | 4 | 4 | 0 | 0.0% |
| OECD | 35 | 4 | 4 | 0 | 0.0% |
| English | 39,537 | 9,603 | 1,718 | 7,885 | 19.9% |
| non-English | 3,577 | 1,585 | 91 | 1,494 | 41.8% |
| unknown lang | 65 | 56 | 1 | 55 | 84.6% |
| has DOI | 34,698 | 10,687 | 1,801 | 8,886 | 25.6% |
| no DOI | 8,481 | 557 | 9 | 548 | 6.5% |

**Verdict on the objection:** refuted on source (curated layers lose 0–24%,
protection catches the teaching/UNFCCC/OECD layers entirely) and inverted on
DOI presence (no-DOI works are removed *less*). Confirmed on one axis the
panel did not name: language.

Flag attribution for the language gap: flag 6 (`llm_irrelevant`) carries
58.9% of non-English removals vs 50.4% of English — the only flag skewed
that way (citation isolation runs lower for non-English, 20.8% vs 28.6%).
Abstract coverage is not the confound: non-English coverage is higher
(88.0% vs 85.7%), and among works with an abstract flag 6 still fires at
29.5% vs 14.4%.

## Part 2 — paired-query experiment

The scorer is `BAAI/bge-reranker-v2-m3` — already multilingual. The
monolingual element is the query string, one English sentence. Each work
scored twice by the same model: deployed English query vs a translation of
it into the work's own language. `paired_query.py`, seed 20260728,
PER_LANG=200, threshold 0.002 (deployed).

**Arm 1** — 1,589 non-English works with abstracts, 14 languages:
pass rate 55.3% (EN query) → 66.8% (own-language query), **+11.5pp**,
Wilcoxon signed-rank p = 3.2e-104. Largest: tr +19.6pp, es +19.0pp,
it +17.9pp, pt +15.0pp, ar +14.5pp, de +14.0pp. Counter-movers: ja (n=6)
−16.7pp, zh (n=23) −17.4pp — samples too small to carry weight and the
translations least certain; reported, not explained away.

**Arm 2 (control)** — 600 English works scored against each foreign query:
pass rate falls 6.5–48.7pp (id −48.7, nl −37.7, fr −35.0). So translated
queries are not simply "better"; the model partly scores query–document
language match.

**Limit:** this shows the *score* is language-sensitive, not that removed
works are relevant. Sizing the false-removal rate needs labels — ticket
0541's panel.

## Context facts pinned during the same session

- The 0.818 human validation sample (0372) is 97/100 English — de facto an
  English-stratum validation.
- The surviving human-labelled batch (`reranker_hitl_review.csv`) is 93
  unique DOIs, all English, 49/45 — the bridge anchor for 0541.
- The batch-1 labels were destroyed by their own generator
  (`compute_reranker_calibration.py:426` blanks `human_label` on re-run) —
  hence 0541's append-only votes invariant.

## Reproduce

```
make data   # in a worktree; DVC checkout, no network
uv sync --extra cu130 --group corpus
PYTHONPATH=scripts:libs/openalex-corpus/src PER_LANG=200 \
  uv run python deliverables/data-paper/revision-rdj26561/flag6-language-bias/paired_query.py
```

~5 min on padme's GPU. Per-work score CSVs land in the chosen `--outdir`
(default `data/derived/`, gitignored); this README carries the summary
numbers, the ticket logs carry the decisions.
