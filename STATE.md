# State

Last updated: 2026-07-10T07:22Z

## Current goal

**Œconomia R&R resubmission** — version ladder (v2.0.3 → v2.0.5) gated by tracker tickets.
v2.0.3 (prose-ratchet infra), v2.0.4 (framing), and the v2.0.5 **content pass** have shipped.
Remaining path to resubmit: the reviewer letter (0152, HITL) and the final rebuild + deposit
(0153). Tracker 0156 stays open until resubmitted (closes master tracker 0133).

### Roadmap
- **v2.0.5 content pass — DONE.** Base rebuild 0172, conclusion 0171, title/abstract 0181,
  prose pass 0134, em-dash 0162, bibliography 0143, stats-provenance audit 0161 — all closed.
- **v2.0.5 remaining to resubmit** (tracker 0156):
  - **0152** — response-to-reviewers letter + per-remark traceability (HITL author sign-off).
  - **0195** — regenerate + archive appendix stat tables on the frozen corpus (0161 follow-up).
  - **0153** — final clean rebuild, version bump, Zenodo/HAL deposit, resubmit on platform.
- **Infra (not R&R):** build-split tracker **0163** → children **0207** (render .mk + Quarto
  profile for the 4 remaining papers) + **0208** (evict analysis intermediates out of
  content/tables/). Package extraction 0170 closed; **0211** wires openalex-corpus tests +
  installability guard into host CI.
- **Parallel (not R&R):** method paper **0026** — `multilayer-detection.qmd`.

## Status
<!-- generated 2026-07-10T07:22Z -->

**Tickets:** 6 ready · 37 blocked/deferred (43 open, 160 closed) — `erg ready tickets/` for full list
**Recent commits:**
  d8eac24 ticket(0206): close — re-acquire 3 HTML-not-PDF files via DOIfetch
  eae988a ticket(0211): file follow-up — wire openalex-corpus tests + installability guard into CI
  5c43b48 ticket(0170): close and archive — all moves merged
  9c80891 ticket(0209): close and archive — fabricated DOI purged + class guard
  733348e ticket(0170): delete het_*.py trio + Companion-pipelines doc (Move B+C)

## Corpus (v1.1.1)

- 6 sources; 42,922 raw → 31,713 refined works, 38,479 embeddings, 968,871 citations
- v1.1.2 being re-generated on padme (GROBID reference extraction + DOI matching)

## Health

Tests green: 1128 passed, 21 skipped (`make check-fast` ~93s — over the <30s target, worth a
look but not blocking). Blockers: none.

## Next actions

- **Resubmission critical path (HITL):** 0152 letter rows → 0153 final rebuild + Zenodo/HAL
  deposit + resubmit. Escobar read-later before cite (R2.30) still pending.
- **Ready infra, base-independent:** 0207 render .mk · 0208 evict intermediates · 0211 CI
  wiring · 0195 stat-table regeneration.
