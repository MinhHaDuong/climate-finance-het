# Specification review, wave 1: external pass

The cross-vendor pass of wave 1, run on 2026-09-30 after the lens review
([`../README.md`](../README.md)) and its fixes had landed on `main`.

- **Draft reviewed.** The ten documents of the specification assembled into
  one PDF, draft v0.1 (`jetp-observer-spec-v0.1.pdf`, not archived: it is
  the documents on `main` after the wave-1 fixes and before the author's
  decisions on the autonomy of machine judgement and on the prose statement
  shape).
- **Models.** OpenAI GPT-5.5 (`openai/gpt-5.5`) and Mistral Large 2512
  (`mistralai/mistral-large-2512`), both reached through OpenRouter.
- **Personas.** Each model reviewed twice: as a critical reviewer
  (`grinchy`) and as a sympathetic one (`student`), under the same brief: an
  experienced data architect and methodologist covering internal coherence,
  fitness for purpose, state of the art, implementation realism and dead
  angles, ending with a verdict and five priority changes.
- **Cost.** About USD 0.7 for the four reviews.
- **Synthesis.** A Fable agent read the four reviews against the wave-1
  ledger and listed 31 new findings, X-01 to X-31, with document, severity,
  milestone and a one-line fix. Its abbreviation G0 names an earlier single
  GPT-5.5 critical run, used only to note agreement and not archived; its
  paths `wave1/external2/` are this directory.

## Files

| File | Content |
|---|---|
| [`review_openai_gpt-5.5_grinchy.md`](review_openai_gpt-5.5_grinchy.md) | GPT-5.5, critical reviewer |
| [`review_openai_gpt-5.5_student.md`](review_openai_gpt-5.5_student.md) | GPT-5.5, sympathetic reviewer |
| [`review_mistralai_mistral-large-2512_grinchy.md`](review_mistralai_mistral-large-2512_grinchy.md) | Mistral Large 2512, critical reviewer |
| [`review_mistralai_mistral-large-2512_student.md`](review_mistralai_mistral-large-2512_student.md) | Mistral Large 2512, sympathetic reviewer |
| [`external-synthesis.md`](external-synthesis.md) | Verdicts, convergent themes, the findings X-01 to X-31 and the points discarded |

The findings and their outcomes are the section "Batch 2: external review"
of the [ledger](../ledger.md).
