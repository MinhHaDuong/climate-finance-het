# JETP scout brief

Use this brief for one bounded evidence gap. Fill it before searching; adapt it
after each round's adjudication. Several project IDs may share an assignment
only when the same named document can distinguish them. Solo researchers use
the same brief and separate discovery from verification.

## Assignment template

- **Identity and gap:** country, canonical project ID, current coverage verdict,
  and the specific unknown. List known aliases and nearby projects that must
  remain distinct. Read the existing coverage and source links first.
- **Document sought:** title or document type, issuer, date range and known
  identifiers. State what it must disclose: for example, a contract cover and
  annex, village schedule, signed loan instrument or original project fiche.
  If no identifier is known, make discovering one the bounded first task.
- **Routes:** ordered primary repositories, operator/funder catalogues and
  archival fallbacks. List previously exhausted routes from the dry-search log;
  retry only with a changed endpoint, new identifier or other stated reason.
- **Acceptance criteria:** the combination of distinctive attributes that would
  join the canonical identity: promoter or legal vehicle, beneficiary scope,
  component/site schedule and explicit cross-reference as applicable. State
  what would contradict the match. Distinguish an exact identity from a related
  component or predecessor. Budget similarity alone is insufficient.
- **Separate questions:** what, if anything, could this document establish about
  financial status, physical progress and JETP/IPG attribution? Each requires
  its own evidence even after identity is confirmed.
- **Budget and stop:** maximum tool calls or elapsed time, counted consistently
  for this assignment. Stop at that limit, when the acceptance evidence is
  obtained, or when the listed routes are exhausted. Report an overrun; do not
  silently reset the budget. A blocked route may end in a precise document
  request draft under existing authorization.
- **Return and ownership:** report findings to the parent with no shared ledger
  edits. Specify any separately authorized retrieval/archive work and output
  location. Do not send messages to institutions without authorization.

## Required return

1. **Verdict:** exact match proposed, related component/predecessor, conflicting
   evidence, or unresolved. Explain which acceptance criteria are met and missing.
2. **Evidence:** issuing institution, original URL, document title and date,
   page/section/table locator, and a short supporting passage or faithful
   paraphrase. Include retrieval date and archive path/hash when bytes were
   collected. Label OCR, search snippets and third-party mirrors; a snippet or
   mirror label alone cannot confirm the original document's claim.
3. **Limits:** alternative identities, contradictory sources, uncertain dates,
   and the claims the evidence cannot establish. Keep an approval distinct from
   signature, a payment order from settlement, and a component from a programme.
4. **Search record:** routes and identifiers tried, retrieval outcomes and
   calls/time used. Distinguish no matching result, access failure and missing
   disclosure. An unsuccessful search is not evidence that a project is absent.
5. **Next discriminating step:** name the document or field still required and
   its likely custodian; otherwise recommend stopping this public-search route.

## Adjudication and another round

The parent reads the original pages, checks provenance and challenges the join
against nearby identities. A solo researcher repeats these checks in a separate
verification pass. Only then may the responsible editor update
`data/jetp/project-source-links.csv`, `project-coverage.csv`, `source-claims.csv`
or the financial and implementation event tables. Retain provisional/context
links where identity remains unresolved; do not count them as direct coverage.
Record attempted retrievals in `data/jetp/manifest.csv` where applicable and dry
searches in `data/jetp/dry-searches.csv`, following their existing schemas.

Record each round's accepted identities, useful contextual documents and rejected
joins in a dated research report. Continue only when a new identifier, document,
route or discriminating question justifies the next budget. Otherwise stop that
route and name the remaining gap. Describe saturation only within the routes,
dates and questions actually tested; retain unresolved identities as unresolved.

The [Senegal document follow-up](jetp-senegal-document-followup-2026-09-13.md)
illustrates the distinction: ANER's strategic plan confirmed a programme identity
while its conditional budget established no funding agreement. The
[managed-round report](jetp-senegal-managed-rounds-2026-09-13.md) records why a
thematically related charging study did not establish the exact project join.
