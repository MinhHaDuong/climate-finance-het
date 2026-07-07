# State

Last updated: 2026-07-07T20:58Z

## Current goal

**Œconomia R&R resubmission** — version ladder (v2.0.3 → v2.0.5) gated by tracker tickets.
v2.0.3 (prose-ratchet infra) and v2.0.4 (framing decisions) shipped. **Now: v2.0.5
implementation** (tracker 0156) — the prose pass applying the decisions, then resubmission.

### Roadmap
- **v2.0.5** (0156): base rebuild **0172** (machine-translate the VF, style-anchored on pre-AI prose; reimport VEn evidence) → content 0135/0137/0138/0139/0141 → conclusion **0171** → prose 0134 → em-dash 0162. Parallel: bib 0143, letter 0152, audits 0161/0164. Resubmit 0153.
- Parallel (not R&R): method paper **0026** — `multilayer-detection.qmd`.
- Parallel: Charles Gide conference paper `manuscript-Gide.qmd` — uploaded to colloque website 2026-06-29, sent to A. Missemer and Y. Dosquet, **presented at Vannes 2026-07-02/04**. No RHPE submission: no special-issue call exists, so there is no decision to take (moot, 2026-07-07). Tag `gide-submitted-2026-06-29` (commit 4ac6e3a); record in `papiers/sent/2026-06-29 Charles Gide/`. Follow-up: bib accuracy validation **0164**.

## Status
<!-- generated 2026-07-07T20:58Z -->

**Tickets:** 39 ready · 17 blocked — `erg ready tickets/` for full list
**Recent commits:**
  1d4cff7 Merge pull request #868 from MinhHaDuong/worktree-explore-status
  1f43017 decision update(0172): the VF translation is machine-performed, style-anchored on the author's pre-AI prose
  c688a4b Merge pull request #867 from MinhHaDuong/worktree-explore-status
  0582343 ticket(0172): base rebuild owns step 1 — VF translation + VEn evidence reimport
  22449a4 tickets: propagate the Vannes notes into the v2.0.5 children; open 0171 conclusion rebuild

## Corpus (v1.1.1)

- 6 sources; 42,922 raw → 31,713 refined works, 38,479 embeddings, 968,871 citations
- v1.1.2 being re-generated on padme (GROBID reference extraction + DOI matching)

## Health

Test failures: none (prose-ratchet 41 + 33 adherence). Blockers: none.

## Next actions

- **0172** — v2.0.5 base rebuild; gates all manuscript children (0135/0137/0138/0139/0141/0171→0134→0162).
- Base-independent, ready now: **0143** bib · **0161** stats provenance · **0164** main.bib audit · **0166** lead-lag.
- Background: null-model ribbon 15/18 (G3/G4/G7 no null); bias audit 0071–0078; arch rule 9 (0043/0044).
