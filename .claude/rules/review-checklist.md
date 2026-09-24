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
- `.claude/rules/architecture.md` and its scoped siblings (`deliverables.md`, `data-location.md`, `openalex-corpus.md`, `null-model.md`)
- config files

Also:
- On first review cycle, record the risk level in the PR review.
- After build: run `make manuscript` if prose changed.
