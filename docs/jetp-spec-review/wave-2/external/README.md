# Specification review, wave 2: external pass

- **Draft reviewed.** The specification assembled into one PDF, draft v0.2
  (not archived: it is the documents at `d4dd1ef8` on `main`).
- **Models.** xAI Grok 4.7 (`x-ai/grok-4.7`), Z.ai GLM-5.3
  (`z-ai/glm-5.3`) and Qwen3.8-Max (`qwen/qwen3.8-max-0902`), reached
  through OpenRouter on 2026-09-30. Moonshot Kimi K3
  (`moonshotai/kimi-k3`) returned an empty answer on two attempts.
- **Persona.** Each model reviewed once, as a critical reviewer
  (`grinchy`), under the brief of wave 1: an experienced data architect
  and methodologist covering internal coherence, fitness for purpose, state
  of the art, implementation realism and dead angles, ending with a verdict
  and five priority changes. The brief still described "a sampled human
  review", which the author's autonomy rule had removed; the three reviews'
  common call for item-level human review answers that sentence.
- **Merge.** The findings new to the wave-1 and wave-2 ledgers that passed
  the merge rules are rows E2-01 to E2-09 of [`../ledger.md`](../ledger.md);
  the others are listed there with the reason they were not admitted.

| File | Content |
|---|---|
| [`review_x-ai_grok-4.7_grinchy.md`](review_x-ai_grok-4.7_grinchy.md) | Grok 4.7, critical reviewer |
| [`review_z-ai_glm-5.3_grinchy.md`](review_z-ai_glm-5.3_grinchy.md) | GLM-5.3, critical reviewer |
| [`review_qwen_qwen3.8-max-0902_grinchy.md`](review_qwen_qwen3.8-max-0902_grinchy.md) | Qwen3.8-Max, critical reviewer |
