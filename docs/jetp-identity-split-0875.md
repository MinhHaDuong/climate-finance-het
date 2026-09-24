# Ticket 0875: identity split report

The frozen input is `data/jetp/migration/0875-projects-legacy.csv` (404
rows). `scripts/jetp/build_reconciliation.py --write` generates the identity
tables and two disposition reports deterministically. The old identifiers have no new
public routes; the existing 1,907 M1a line routes remain for inventory
exports only.

| Disposition | Old rows | Target assigned | Pending |
|---|---:|---:|---:|
| Agreement | 310 | 306 | 4 |
| Project | 66 | 53 | 13 |
| Asset | 1 | 1 | 0 |
| Line only | 6 | 3 | 3 |
| Perimeter count slot | 21 | 21 | 0 |

"Target assigned" includes a line or the common perimeter and does not mean
that every old row minted a new identity. Six source-defined component parent
projects and one plan-defined asset
(Pelabuhan Ratu) bring the identity tables to **59 projects, 2 assets and
306 agreements**. The 21 count slots point to one Viet Nam portfolio
perimeter; its count observations belong to ticket 0877. Eighteen pending old
rows have no precise source line. Two more old programme labels (ETP and
IETF) each point to two distinct grant lines, so neither is silently turned
into one agreement. These 20 rows have no minted identity. Their IDs and
reasons are in `data/jetp/migration/0875-dispositions.csv`. The accepted
identity rows have 367 `line-referents`; the SQLite validator rejects any
project, asset or agreement without one.

The three line-only dispositions mint no identity. One Indonesia monitoring
label covers two separate printed plan lines; the disposition lists both
line IDs rather than silently selecting one.

The South African register's `Funding Instrument` is copied verbatim to
`instrument`. It does not identify an OECD type of aid, so `modality` is
explicitly `unknown`; the portfolio label remains a verbatim sector until a
published sector crosswalk provides a narrower classification.

The South African register has 257 accepted `party_in` funder roles, 10
channel roles and 126 `role_in` implementing-entity roles. The latter use
only individually named organisations on the printed register line; the
remaining composite and placeholder cells are not treated as organisations.
The touched register cells contain no IATI organisation, ROR, LEI or Wikidata
identifier, so no external-ID tier 1 party merge was possible here. Exact
previously published party-name forms are reused; an acronym alone remains a
candidate.
The 11 reviewed project-page components are `component_of` relations. A
parenthetical acronym yields one candidate `same_as` between parties, with
no authority-record merge. The current financial event register contains
60 distinct funder strings (the migration plan's earlier estimate was 61):
22 resolve to an existing party name, 30 are composite strings, three need
authority review, and five do not name a party. Each is recorded in
`data/jetp/migration/0875-funder-strings.csv`. Event-specific party roles
remain pending their source-line migration in step 5; the report does not
pretend a register line justified an unrelated event.

## Tier 2: repeated Indonesia hydro quota label

Method version 1 in `config/jetp-matching.json` proposes exact normalized
labels within one country and technology group. It yielded ten candidate
`same_as` relations between five CIPP 2023 Appendix 10.4 rows and two 2025
Progress Report Appendix 1 table 3 rows. No relation was accepted from a
label match.

The frozen CIPP PDF, SHA-256
`747283facac512780ad757313c493d1080c39705824e72c4b231e87ecb4102b5`,
prints rows 8, 10, 26, 27 and 43 with 400/350/200/200/80 MW and
2024/2025/2026/2025/2027 estimated starts. The frozen 2025 Progress
Report, SHA-256
`74fb460fd09e76607e3cff308f5ba2754f2ebd91b0c9b7613c1a041e7b361162`,
prints rows 101 and 139 with 200 MW and 2028/2030 estimated starts.
The latter's ledger line ID ends in `hydro-149`: its locator records
`printed row 139, normalised physical row 149`.

On 2026-09-24, `claude-sonnet-5` reviewed only those seven bounded source
rows, after a first response had correctly flagged that the supplied
excerpts were from the wrong pages. Its adjudication found no supported
exact pair: the repeated quota label identifies several allocations even
within the CIPP, capacity 200 MW occurs twice in each document, and no
capacity/start-year pair repeats. The four 200 MW cross-pairs remain
indeterminate; the other six have conflicting capacities. This is evidence
against accepting any match, not evidence that all ten pairs are distinct
real-world assets. A PLN/RUPTL project code, named site, or a published
cross-edition allocation reconciliation would discriminate them. All ten
relations therefore remain candidates for ticket 0833's review.
