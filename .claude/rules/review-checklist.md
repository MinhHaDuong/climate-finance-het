---
paths:
  - "scripts/**"
  - "config/**"
  - "deliverables/**"
---

# PR review — doc propagation checklist (project-specific)

When `/review-pr` triggers doc propagation, trace references in these project files:
- `deliverables/technical-report/technical-report.qmd`
- `deliverables/data-paper/data-paper.qmd`
- `deliverables/manuscript/manuscript.qmd`
- `deliverables/*/*-vars.yml`
- `docs/`
- `README.md`, `STATE.md`, `ROADMAP.md`
- `.claude/rules/architecture.md`
- config files

Also:
- On first review cycle, add a risk label to the PR:
  - Trivial → `review:trivial` (merge gate requires 1 cycle)
  - Standard or above → `review:standard` (merge gate requires 2 cycles)
- After build: run `make manuscript` if prose changed.
