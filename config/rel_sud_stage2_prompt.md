# REL south-and-languages: stage-2 review prompt (ticket 1530)

Used verbatim, 2026-09-29, for each of the 18 chunks of 150 records (2,667
records that the first-pass screen labelled `icf` or `unsure`, minus the 200
pilot records Opus had already judged). One subagent per chunk, model `opus`,
read-only, no web. The rule itself is the `prompt_template` field of
`config/rel_sud_screen.yaml`; only the wrapper below is stage-2 specific.

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

Write one line per record, in order, to <chunk>.opus.txt, format exactly:
n|label|doc|studied|why
where doc is research, institutional or other; studied is the country or
region the work is about (ISO country code or 'global' or '?'), why is max 12
words and given only when the label is icf or unsure (empty otherwise).
No other text in the file. Then reply with only the count of each label.
```

Chunk file format: `n. [language | year | journal | affiliations: CC, CC]`, then
`Title:` (220 characters) and `Abstract:` (650 characters, or `(no abstract)`).
Stage-2 input never shows the first-pass labels.
