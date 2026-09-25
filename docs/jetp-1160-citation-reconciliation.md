# Ticket 1160: legacy event citation reconciliation

Reviewed 25 September 2026. The row-level record is
`data/jetp/migration/1160-citation-decisions.csv`; each accepted row points to a
new line in `data/jetp/lines.d/IDN-2026-03.csv` or `SEN-2026-02.csv`. The line
records give the source snapshot, printed locator and the asserted value and
status. No event was re-sourced: the prior lines belonged to related documents,
while the archived legacy sources supplied 115 of the 120 assertions. Five
claims lack enough evidence in their named source and remain pending.

## Bounded source review

The identity to resolve was each legacy event in
`docs/jetp-0876-citation-mismatches.csv`, not the broader project. Acceptance
required the named source's archived bytes to state the same donor or project
row, financial amount and currency or physical state, with the correct date
role. A common project name alone failed. The review used the 16 source IDs
already in the mismatch register and their existing collection attempts; it
stopped when every row had an exact locator or a specific hold. No new source
retrieval or project identity was introduced.

| Source group | Snapshot SHA-256 | Rows | Decision |
|---|---|---:|---|
| Indonesia JETP Progress Report 2025, printed pp. 72–76, Tables 4.3-2 to 4.3-13 | `74fb460fd09e76607e3cff308f5ba2754f2ebd91b0c9b7613c1a041e7b361162` | 70 | 66 accepted, 4 physical holds |
| Senegal investment plan L4, printed pp. 33, 41–44 | `97c36b242257462f024a934baee6bed3aa02fe0e4917f076d7b865701db65dca` | 32 | 32 accepted; cost rows remain estimates |
| Other 14 source IDs, including original AFD, Senelec, ANER, IFC and operator records | Individual hashes in the decision register | 18 | 17 accepted, 1 missing-snapshot hold |

The Indonesia report's Table 4.3-2 prints Canada's ISLE-1 co-financing as
CAD 64.3 million and approved. The old observation instead cited a World Bank
technical assessment, which does not assert Canada's financing. Table 4.3-3
labels its rows **in process**: the EUR 300 million KfW AICET entry is an
announced pipeline amount, while the same row does not establish physical
preparation. The Singkarak row does describe a 50 MW project temporarily
halted by social opposition, so it supports the separate `suspended` physical
observation. Report prose describes funding status as of November 2025; the
legacy `2025-11-30` timing is a month-end reporting cutoff, not an invented
approval day. The report's table of contents carries an older September 2025
caption, while the body says November; the row citations use the printed body.

The Senegal plan's pp. 41–44 identify projects by their printed **names** and
costs in millions of euros. The legacy `annex-N` identifiers do not always
match the plan's printed project numbers: `sen-plan-cost-annex-03`, for example,
is the briquetting pilot printed as Projet #2 at EUR 0.3 million. Each locator
therefore names the project rather than relying on the legacy ordinal. These
are `need` estimates, not secured financing. The plan's p. 33 Quick Win list
supports three proposed project baselines; their issue dates remain unresolved
in the pending timing register.

For the smaller sources, the AFD Diass factsheet's “Prochaines étapes / impacts”
paragraph gives KfW EUR 18 million and AFD EUR 8 million. Senelec's 20 April
2026 Diass article separately reports KfW EUR 28 million and AFD EUR 8 million
and dates the first-stone ceremony to 31 March 2026. The differing KfW amounts
remain distinct reported observations. Senelec AAO 30/2026 p. 1 confirms a
German allocation without an amount and solicits bids for 11 PV and battery
plants serving 18 Saloum villages. The ANER API snapshots mark the four named
profiles `planned`; the Phase IV lighting profile is API ID 21 but explicitly
specifies the 100,000 lamps of the plan's project. The Ministry's PUELEC article
reports service in three named villages, not completion of the wider programme.

## Holds and limits

- `idn-impl-aicet-2025`: AICET finance in process is not physical preparation.
- `idn-impl-hululais-2025`: JICA funding resuming is not evidence of physical preparation.
- `idn-impl-tanah-laut-2025`: a signed PPA does not establish physical preparation.
- `idn-impl-eib-framework-2025`: a framework loan MOU is not a physical project milestone.
- `idn-impl-cirebon-suspended-2025`: the Reuters retrieval hash is registered, but its archived object is absent in this checkout, so the ministerial statement cannot be checked at source level.

The prior three `0970_physical_state_hold` events and the AfDB
`missing_precise_cited_line` event remain pending. Thus the 451 legacy events
resolve to 442 accepted observations and nine event holds. Unmapped and
ambiguous timing roles remain in `0876-pending.csv`, separate from those nine
event holds. The public four-country legacy views remain authoritative pending
the 0876 switch.

## Verification record

The normalized observations, timings, pending register and timing
reconciliation, plus the four served observation views, were built twice and
had identical SHA-256 hashes. The four **public country views** were also
byte-compared with `origin/t0876-observations-timings` before any 0876 switch:

| View | SHA-256, unchanged |
|---|---|
| ZAF | `1aa267e083b428aabcf200c29b9400690b60df66c45814c73ca3e3697578d487` |
| IDN | `0930f913d0dca4cff41106a4afccd21e276561c3045f8bf5f8ab31315455d6ca` |
| VNM | `0f92fb7557b4e68cd60382973a5bd3489e243c624a6a8fb6cea18039b0f3cd0b` |
| SEN | `acad7df1d7f5e7af7d74346cf0ab6a10fa818e2f66bf1e1ac6dc0095916d92f7` |
