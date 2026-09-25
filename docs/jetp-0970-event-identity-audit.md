# Indonesia event identity adjudication (0970)

The decision register is `data/jetp/migration/0970-event-adjudications.csv`. It
covers exactly 27 source-backed events left pending by the 0875 identity split:
17 finance events and 10 implementation events. Every row names its original
event, exact source line, referent, support verdict, and promotion decision.
The 28th pending Indonesia event, AfDB without a collected snapshot, remains
with ticket 0926.

## Sources and row identity

The archived *JETP Progress Report 2025* has SHA-256
`74fb460fd09e76607e3cff308f5ba2754f2ebd91b0c9b7613c1a041e7b361162`.
Fifteen new lines in `lines.d/IDN-2026-02.csv` cite printed pages 72–76 and
Tables 4.3-2, 4.3-3, 4.3-4, 4.3-6, 4.3-7, and 4.3-11 down to the funder and
named row. The other three assertions reuse the archived official portfolio
claim lines `idn-portfolio-project-gecs-claim-76` and
`idn-portfolio-project-nagajaya-claim-78`/`claim-79`. The source SHA for each
legacy event is checked against its cited line by
`test_jetp_0970_event_identities.py`.

Six report rows support distinct approved finance agreements: KfW SREAP,
JBIC Muara Laboh Stage 2, Canada/UNOPS ETP, EU/AFD IETF, France/AFD IETF,
and UK/UNOPS-ETP. The ETP and IETF donor rows each retain separate agreement
identities; a shared programme name does not merge them. The report gives the
MUFG commercial-loan amount as TBC, so it supplies no additional approved
amount here. Two portal financing table claims support separate KfW Green
Energy Corridors and Norfund Nagajaya approved financing agreements. None of
these rows alone establishes signature, disbursement, or construction.

Nine Table 4.3-3 rows belong to “Loan and Equity In Process.” Four describe
named projects or interventions: Green Energy Corridors Sulawesi, Nagajaya,
Dieng Units 3 and 4, and the RSCM Kencana/Kiara energy-efficiency work. Five
are a 46-site programme, an E-Taxi service proposal, a multi-project reverse
auction, and two hydro procurement quotas. Those five retain the cited source
row as their referent because the report supplies no single project identity.
The report calls Nagajaya 6 MW while the later portal calls it 6.5 MW; both
reported values remain attached to their own sources.

## Physical-state boundary

Seven implementation claims can be narrowed to the source's actual stage:
Nagajaya preconstruction after its PPA, Eastern de-dieselization procurement,
E-Taxi proposed service, Hijaunesia 2 tender, the two hydro quotas in
procurement, and RSCM preparation after its investment-grade audit. These do
not imply operating capacity or completed works. Three physical claims remain
held: Green Energy Corridors has development/board approval context only;
Dieng has field-development financing context only; and the Nagajaya portal
says it *will install* turbines. The register records `promotion=hold` for
those three rather than projecting physical progress from finance or future
language.

The resulting source-level decision is 24 accepted event referents and three
held physical-state claims. Ticket 0876 consumes these decisions when it
rebuilds the observation view; the legacy served view stays unchanged here.
