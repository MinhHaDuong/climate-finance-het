# REL discipline catch-up prompt, version 1 (ticket 1842)

Discipline-only wrapper for the works stage 2 relabelled before the version-2
stage-2 wrapper (`config/rel_stage2_prompt_v2.md`, ticket 1840) existed, and
whose final stage-2 label is `icf` or `unsure`. It asks the three discipline
questions of version 2 and nothing else: the ICF label is already decided and
stays in `icf_screen` untouched.

The three question definitions (`contrib`, `field`, `ctype`) are copied word
for word from the version-2 wrapper, so the catch-up and forward stage 2 ask
the same questions; `tests/test_rel_discipline_catchup.py` checks the copy.
What differs from version 2: no ICF label, `doc` or `studied` is asked; the
records are introduced as already retained, so `na` (the version-2 answer for
a work labelled `out`) is not offered; the answer is returned as text, not
written to a file, so the same rendered prompt serves an API call and a Claude
Code subagent.

The chunk format is the stage-2 one (`stage2` in `config/rel_screen.yaml`):
`n. [language | year | journal | affiliations: CC, CC]`, then `Title:` and
`Abstract:`. `scripts/corpus_rel_discipline_catchup.py render` fills
`{records}` with one chunk; the hash of the fenced block is stamped on every
`rel_dimensions` row the catch-up writes (stage `catchup`).

```
Read-only labelling task. Use only the record text; do not search the web.

The numbered bibliographic records below were all retained by an earlier
review as having an international climate-finance object (a few were left
undecided). Do not re-judge that. Records are in many languages; judge each
in its own language.

Answer three discipline questions about the work's own contribution (what it
claims to establish), not about its data or its topic:
- contrib: does the contribution bear on the economics, policy or governance
  of climate finance (allocation, effectiveness, additionality, mobilisation,
  market and institution design, distribution, negotiation, regulation)?
  "yes"; "no" when the work only uses climate-finance data or objects for
  something else: a forecasting or machine-learning method (e.g. predicting
  CER or carbon prices), pure finance (pricing, volatility, hedging, portfolio
  results with no economic or policy question), firm-level management
  (strategy, accounting, operations of one firm or sector), or a technical,
  engineering or natural-science result; "unsure" only when the text does
  not allow a decision. Judge the contribution, never the journal's name.
- field: the discipline the work speaks to, one of economics, politics
  (political science, international relations, public policy), law, finance,
  management, data_science (machine learning, statistics, computing),
  natural_science (natural sciences and engineering), other.
- ctype: the kind of contribution, one of empirical (statistical or
  econometric evidence answering a question), theory (formal or conceptual
  model), method (forecasting model, algorithm, measurement or accounting
  tool), policy (policy, institutional or governance analysis or evaluation,
  qualitative), review (literature review or synthesis), case (case study
  or descriptive account), other.

Answer with one line per record, in order, format exactly:
n|contrib|field|ctype|why
where contrib is yes, no or unsure; field and ctype are as above; why is max
12 words and given only when contrib is no or unsure (empty otherwise).
No other text.

Records:
{records}
```
