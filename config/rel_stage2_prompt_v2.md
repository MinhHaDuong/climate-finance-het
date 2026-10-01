# REL stage-2 review prompt, version 2: ICF label plus discipline (ticket 1840)

Successor of `config/rel_sud_stage2_prompt.md` (version 1, ticket 1530), which
stays frozen: its wrapper hash is stamped on the 4,752 historical t1530 Opus
rows (`t1530_stage2_prompt` in `config/rel_screen.yaml`). Version 2 is the
wrapper `stage2.prompt` points to from 2026-10-01 on, for every stage-2 and
audit chunk written after that date.

Same use as version 1: one subagent per chunk of 150 records, model `opus`,
read-only, no web. The ICF rule is the `prompt_template` field of
`config/rel_sud_screen.yaml`. The ICF part of the wrapper is word for word
the version-1 text, so the ICF label stays comparable across versions. What
version 2 adds is three separate fields after `studied` and before `why`: the
parser keeps any further `|` inside `why`, so new fields can only go before
it.

The added fields carry the author's discipline decision of 2026-10-01 (ticket
1830): a work enters the economic literature review only if its contribution
bears on the economics, policy or governance of climate finance. Machine
learning or data science (for example CER price forecasting), pure finance
(pricing with no economic or policy question) and firm-level management
science that merely exploit climate-finance data are excluded. The journal
alone never decides.

```
Read-only labelling task. Do not run git commands; do not edit any file other
than the one output file named below.

Read the screening rule in config/rel_sud_screen.yaml (the `prompt_template`
field: the ICF definition and the labels, ignore the answer-format sentence and
the Records placeholder). Then label the numbered bibliographic records in
<chunk file>. This is a second-stage review of records a cheaper model flagged
as ICF or unsure, so be strict: use "icf" only when the record's own title or
abstract shows an international climate-finance object; "aux" for
related-but-not-ICF; "out" for unrelated; "unsure" only when the text truly
does not allow a decision. Records are in many languages; judge each in its own
language. Use only the record text; do not search the web.

Then, for every record labelled icf, aux or unsure, answer three discipline
questions about the work's own contribution (what it claims to establish),
not about its data or its topic:
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
For a record labelled out, write na in all three fields.

Write one line per record, in order, to <chunk>.opus.txt, format exactly:
n|label|doc|studied|contrib|field|ctype|why
where doc is research, institutional or other; studied is the country or
region the work is about (ISO country code or 'global' or '?'); contrib, field
and ctype are as above; why is max 12 words and given only when the label is
icf or unsure, or when contrib is no or unsure (empty otherwise).
No other text in the file. Then reply with only the count of each label.
```

Chunk file format: unchanged from version 1 (`n. [language | year | journal |
affiliations: CC, CC]`, then `Title:` (220 characters) and `Abstract:` (650
characters, or `(no abstract)`)). Stage-2 input never shows the first-pass
labels.

## Where the answers go

`scripts/corpus_icf_stage2.py parse` reads a version-2 answer file, appends
the ICF label to `icf_screen` (unchanged 17 columns) and the three discipline
fields to `rel_dimensions` (`dimensions_table` in `config/rel_screen.yaml`),
an append-only table with the same guards, keyed like `icf_screen` by
`(work_key, stage, model, run_id)`. An out-of-vocabulary value is stored as
`unknown` and counted in the parse report; it never refuses the chunk. A
version-1 answer file still parses (the t1530 import re-reads them) and writes
no dimension rows. Works labelled under version 1 get the discipline fields
from the catch-up wrapper `config/rel_discipline_catchup_prompt.md` (ticket
1842), which copies the three definitions above word for word.

## Test before launch (2026-10-01)

Results and archive path: `conception/rel-stage2-prompt-v2-test.md`.
