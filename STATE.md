# State

Last updated: 2026-06-23T09:20Z

## Current goal

**Œconomia R&R resubmission** — major revision via a version ladder (v2.0.3 → v2.0.5)
gated by tracker tickets. **v2.0.3 (prose-ratchet infrastructure) shipped today**:
harness + editorial brief + LLM-judge guards live, ratchet initialized over the
manuscript. Next: v2.0.4 decisions, then v2.0.5 implementation (prose pass +
resubmission).

### Roadmap
1. ~~**DONE — v2.0.3 prose ratchet** (0147 harness, 0148 brief+guards, 0149 inventory; tracker 0154).~~ PRs #825/#826/#827/#828 merged.
2. **NOW — v2.0.4 decisions** (tracker 0155): framing/thesis decisions 0150, 0151 (+ 0142 restructure).
3. **THEN — v2.0.5 implementation** (tracker 0156): prose pass 0134 (define-by-negation, 20), em-dash density 0162, content tickets 0135/0137/0138/0139/0141/0143, response letter 0152, resubmission 0153.

Parallel track (not R&R): method paper **0026** — narrative/figures/prose for `multilayer-detection.qmd`.

## Status
<!-- generated 2026-06-23T09:20Z -->

**Tickets:** 31 ready · 22 blocked — `erg ready tickets/` for full list
**Recent commits:**
  ff4bca8 Merge pull request #828 (ticket 0154 close)
  1e0b5fa ticket(0154): close v2.0.3 ratchet tracker — integration review green
  e57b58f Merge pull request #827 (ticket 0149)

## Corpus (v1.1.1)

- 6 sources; 42,922 raw → 31,713 refined works, 38,479 embeddings, 968,871 citations
- v1.1.2 being re-generated on padme (GROBID reference extraction + DOI matching)

## Known test failures

None. Prose-ratchet suite green (41 tests + 33 adherence).

## Blockers

None.

## Next actions

- **0150 / 0151** — v2.0.4 framing/thesis decisions (now unblocked by 0154 close); I draft decision options.
- **0134** — R&R prose pass: eliminate define-by-negation (20 `not X but Y`); ratchets the ceiling down.
- **0162** — reduce em-dash density toward 2/paragraph (filed from the 0149 inventory).

Background: method paper 0026; null-model ribbon 15/18 methods live (G3/G4/G7 have no null model); bias audit 0071–0078; re-land arch rule 9 (0043/0044).
