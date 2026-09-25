# 0876 event evidence gaps: bounded snapshot audit

Checked on 2026-09-24 against the archived bytes, without collecting new
sources or changing ledger identities. The input is the 27
`missing_precise_cited_line` rows in `data/jetp/migration/0876-pending.csv`.
The separate AfDB row has no snapshot and was not reviewed here.

| Archived document | SHA-256 | Pending events | Exact places checked | Result |
|---|---|---:|---|---|
| JETP Progress Report 2025 | `74fb460fd09e76607e3cff308f5ba2754f2ebd91b0c9b7613c1a041e7b361162` | 24 | Printed pp. 72–76, Tables 4.3-2, 4.3-3, 4.3-4, 4.3-6, 4.3-7 and 4.3-11 | The two approved loan rows, four grant rows and nine in-process finance rows are printed separately. The nine linked implementation rows need individual review: “finance in process” alone is not physical progress. |
| Official GECS project profile | `efe51d479eb32608cafe1006ecb5a7e01796ca0590c4861df4295df0991900ed` | 1 | `#financial-info`, Modality A | The KfW EUR 300m financing row is present. Existing ledger line `idn-portfolio-project-gecs-claim-76` already cites the financial claim; the unresolved issue is the subject identity. |
| Official Nagajaya project profile | `ac5d3eb835fb55acddca3cae5864743e476972476bebe5cb5b3d458a14afb0c6` | 2 | `#financial-info`, Modality A; General Information | The Norfund USD 1.26m row and 6.5 MW/two-turbine description are present in existing lines `idn-portfolio-project-nagajaya-claim-78` and `-claim-79`. Future-tense “will install” does not by itself establish a physical implementation state. |

The Progress Report’s Muara Laboh footnote says MUFG’s portion awaits
confirmation; only the JBIC USD 138m row supports the current numeric event.
The report describes the nine Table 4.3-3 entries as finance **in process**.
It does not make each financing row an approved agreement, and its project
descriptions must not automatically become a common physical `preparation`
observation. The ETP and IETF labels each occur in more than one distinct
grant row; do not merge them into one agreement by acronym.

## Next decision and ownership

The 0875 dispositions deliberately leave the target identity blank for these
27 events. Therefore adding a source line alone does not make an 0876
observation valid. Ticket 0970 resolves the source-row identities and separate agreement
rows, using the exact printed rows above and the
existing portal lines. Review each physical-state claim against its own text.
Until then, the 27 events remain pending and the legacy served view remains
authoritative. The blocked AfDB source belongs to the acquisition path of
ticket 0926; a failed retrieval does not imply that the claimed approval is
absent.

## 1120 update (2026-09-25)

Retrieval `zaf-murp-afdb-2026:2` now supplies the publisher HTML, SHA-256
`a9385e879af5f88511324674b8b12345cea23bc3dd0fbc8eae3b02a11e57cf33`.
Article `#node-95536`, body paragraph 1, states that AfDB approved a USD 400
million loan to South Africa for the Mpumalanga Municipal Utility Reform
Programme. Body paragraph 5 states the UK FCDO guarantee. The named borrower,
programme and amount identify a distinct agreement from register AFDB004,
which is the USD 474.64 million IGGGP policy loan.

The article labels 16 July 2026 as its publication date and gives no approval
day in the body. The [AfDB MapAfrica catalogue](https://new-mapafrica.afdb.org/en/projects)
lists project `P-ZA-K00-009` with a 15 July 2026 approval date. This catalogue
finding has not been archived as a ledger snapshot, so the legacy event's
16 July event-day timing is
held pending a collected, cited catalogue line. The accepted observation is
approval only; neither signature nor disbursement is evidenced.
