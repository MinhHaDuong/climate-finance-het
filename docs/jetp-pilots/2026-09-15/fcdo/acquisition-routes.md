# Frozen FCDO acquisition routes

Ticket 0739; user explicitly launched this pilot on 14 September 2026.
Scope: exact GB-GOV-1 programme IDs, explicit related components, stage documents.
Budget: at most 20 requests including failures and redirects. No outreach.
Stop at decisive evidence, route exhaustion or the cap. Verification reuses originals.

1. Retention/status tranche (up to 6): inspect acquired DOCX first; request official
   DevTracker about, IATI ActivityStatus definition, FCDO publisher dashboard.
   Seek historical downloadable snapshots/inclusion policy, not current timestamps.
2. Documentary tranche (up to 10): inspect three archived structured records first.
   Query uninspected pipeline IDs in lexical order for structured document links,
   then sample IDs in frozen rank order. Each query is a unit. Follow exact stage
   document links if present in order: business case/approval, procurement, start.
   A document pointer is not retrieval or validation. Failed requests remain rows;
   never replace sample members. No procurement portal search without contract ID.
3. Reserve 4: inspect exact document links uncovered above in the same case order,
   prioritizing pipeline cases then sample rank; inspect a linked programme only
   with an explicit relation. Any unused earlier tranche may move forward.

Acceptance: an original must identify the exact programme/component and explicitly
record a decision/procurement event or actual start at that unit. A draft business
case, planned date, activity status or budget alone cannot establish approval,
signature, settlement or actual execution. Related component dates remain separate.
Document date and retrieval date remain separate from event dates. Contradictory
starts and expenditure preceding transfers are retained.

The frozen catalogue lacks sector vocabulary and raw finance type; these are
mixed-or-unmapped and missing respectively, throughout selection. Single-country
programme candidates in AL/MA/IN/SN/ZA/ID/VN enter without status/date filtering.
Regional/multi-country records remain in the full profile, outside this frame.
No new external research requests have preceded this freeze. GitHub PR metadata
preflight is administrative and is not a research acquisition unit.
