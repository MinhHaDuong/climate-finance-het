---
paths:
  - "deliverables/jetp-observatory/**"
  - "docs/jetp-observatory-presentation.md"
  - "scripts/jetp/build_observ*.py"
---

# JETP observatory: structure and labels (project-specific)

Before changing the site's navigation, page structure or labels, read
`docs/jetp-language.md`, then `docs/jetp-ledger-migration.md`.

- **The navigation menu follows the data pipeline and the ontology** (author,
  2026-09-24). The paper trail is a viewer on the CSVs of steps D1–D4. The
  tallies hold everything narrative, comparative or derived: one page for each
  country, one page for each theme (ticket 0956).
- **Design for the migrated tables, not the legacy ones the site still
  serves.** `events.csv` and `project-source-links.csv` are on their way to
  `observations` and `line-referents`, so a structure read off the legacy
  tables encodes a pipeline that no longer exists.
- **Labels use the ontology's words, with no step codes.** D1–D4 are for
  documents and data attributes, never for a reader-facing label.
