# Specification review, wave 2

The second review of the JETP Observer specification ([index](../../jetp-spec.md)),
run on the documents as they stood at commit `d4dd1ef8` on `main` (draft
v0.2, after the wave-1 fixes and the author's decisions of wave 1).

- **Lenses.** The seven lenses of wave 1, with fresh reviewers: within-file
  coherence, cross-file coherence, state of the art, data held, data to
  come, implementation constraints, dead angles. Reviewers ran on Fable.
- **Verifiers.** Each lens report was checked on Sonnet, which confirmed,
  weakened or rejected every finding against the documents and the data.
- **Ledger.** A Fable agent merged 90 verified findings into 57 rows,
  W2-01 to W2-57 (1 blocker, 17 major, 39 minor), each with severity,
  milestone, proposed fix and whether it needs the author (`ledger.json`).
- **External pass.** The draft as one PDF, reviewed through OpenRouter by
  xAI Grok 4.7, Z.ai GLM-5.3 and Qwen3.8-Max, each as a critical reviewer
  ([`external/`](external/README.md)). Moonshot Kimi K3 returned nothing,
  twice, and is not archived.

## How the findings were merged

The author's instruction: "Make sure you merge critically. Design by
committee is tricky." The merge, by a Fable editor, applied these rules in
order:

1. A finding is accepted only if its fix serves a named requirement or
   milestone; a fix that adds machinery without a product need is rejected,
   with the reason.
2. Nothing enters the M2 or M3 slice unless a correct, traceable M2 or M3
   result needs it; otherwise it is tagged M4 or dropped.
3. The author's decisions stand (complete autonomy and no author queue; two
   local readers selected and calibrated on OpenRouter, the arbiter on
   escalation, IPCC terms; Zotero as off-site copy; legal review at
   go-live). A finding that reopens one is rejected.
4. Cut before adding: a contradiction loses one side before a third rule is
   written, and the specification (`docs/jetp-*.md`) must not grow in net
   words. It held 82 773 words before the merge and 82 727 after.
5. Agreement between reviewers is weak evidence; each finding is weighed by
   its argument and its grounding in the documents.

Of the four author questions of the ledger, W2-09, W2-17 and W2-43 were
resolved by the autonomy rule, taking the recommended default that routes
nothing to the author; W2-04 waits for the author, with its options in the
ledger. External findings became rows E2-01 to E2-09 only when new to both
ledgers and passing the rules; the others are listed with their reasons.

## Files

| File | Content |
|---|---|
| [`ledger.md`](ledger.md) | The findings ledger with the outcome of every row, the question for the author, and the external findings not admitted |
| [`ledger.json`](ledger.json) | The 57 rows of batch 1 and the readiness verdict, as the ledger agent produced them |
| [`external/`](external/README.md) | The three external reviews |
