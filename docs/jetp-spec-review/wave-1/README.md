# Specification review, wave 1

The first review of the JETP Observer specification ([index](../../jetp-spec.md)),
run on the ten documents as they stood at commit `7f3368b5` on `main`.

- **Lenses.** Seven reviewers, each on one lens: within-file coherence,
  cross-file coherence, state of the art, relevance to the data held (a paper
  walkthrough of real documents), relevance to data to come, implementation
  constraints, and dead angles. Reviewers ran on Sonnet.
- **Skeptics.** Each lens report was checked by one skeptic on Fable, which
  confirmed, weakened or rejected every finding against the documents and the
  data.
- **Ledger.** A Fable agent deduplicated the verified findings into one
  ledger of 71 rows, each with severity, milestone, proposed fix and whether
  it needs an author decision.
- **Prototype.** The report of a throwaway prototype (branch
  `spike-spec-prototype`, `spike/REPORT.md`) was an input to every lens.
- **External pass.** The cross-vendor pass (OpenAI GPT-5.5 and Mistral
  Large, each as a critical and a sympathetic reviewer) could not run with
  the lens review, for lack of OpenRouter credit; it ran later the same day
  on the fixed documents, and its 31 findings are batch 2 of the ledger
  ([`external/`](external/README.md)).

## Files

| File | Content |
|---|---|
| [`ledger.md`](ledger.md) | The findings ledger, human-readable, with the outcome of each row |
| [`ledger.json`](ledger.json) | The same rows as data, as the ledger agent produced them |
| [`agent-results.json`](agent-results.json) | Raw outputs of the lens reviewers and their skeptics |
| [`external/`](external/README.md) | The four external reviews and their synthesis (batch 2) |

The **Outcome** line of each row in `ledger.md` records whether the fix was
applied and in which commit, or why it waits for the author.
