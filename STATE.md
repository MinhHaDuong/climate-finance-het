# State

Last updated: 2026-07-10T20:48Z

## Current goal

**Œconomia R&R resubmission.** v2.0.5 shipped. Critical path: **0152** letter
(DRAFT v3 done 2026-07-10: first-person, A4, 60-row ledger filled, all 14
Editor rows author-signed; **R1/R2 sign-offs next session**) → **0195** stat
tables → **0153** final rebuild + Zenodo/HAL deposit + resubmit. Tracker 0156
stays open until resubmitted (then closes 0133).

### Also open
- **0244** — verify 4 AI-generated techrep includes (phantom ref caught in §11);
  vet `cop-topic-structure.md` before the letter goes out (it backs E3f).
- **0245** brief entries · **0243** Fable style alignment · **0026** method paper.
- **0246/0247** — harness: make-check exit-0 bug; shared venv missing bibtexparser.

## Status
<!-- generated 2026-07-10T20:48Z -->
**Tickets:** 5 ready · 43 blocked — `erg ready tickets/` for full list
**Recent commits:**
  76f6ca8 Merge pull request #1008 from MinhHaDuong/t-roar-file-tickets
  fc6ef2d Merge pull request #1007 from MinhHaDuong/t152-response-letter
  50927b8 manuscript(0152): drop the false pre-2007 co-citation paragraph

## Corpus (v1.1.1)

- 6 sources; 42,922 raw → 31,713 refined works, 38,479 embeddings, 968,871 citations
- v1.1.2 being re-generated on padme (GROBID reference extraction + DOI matching)

## Health

check-fast 932 + lint 149 green. Full suite on doudou: 1388 passed, 21 failed + 4
errors, all data/env-dependent (no local corpus data; C2ST timeouts; bibtexparser
→ 0247), none from the merged diff. `make check` exited 0 despite failures → 0246.

## Next actions

- **HITL:** 0152 R1/R2 sign-offs → 0195 → 0153 (rebuild, deposit, resubmit).
