# JETP tracking decisions

This file records human adjudications that change how observations are coded.
Do not use it as a run log. Each entry must name the affected identifiers,
state the evidence considered and give the date and author of the decision.

The unresolved Vietnam pilot arbitrations remain in
`conception/jetp/papier-3-ledger/pilote-ledger-vn/feuille-arbitrage.md` until
ticket 0719 migrates them.

## 2026-09-11 — copies de conservation des plans indonésien et sénégalais

Author: Codex, draft for Minh's review.

Affected sources: `idn-cipp-2023`, `idn-cipp-2023-cpr-mirror`,
`sen-investment-plan-l4`, `sen-investment-plan-l4-mirror`.

- The Indonesia Secretariat URL returned HTTP 403 to the harvester. Climate
  Policy Radar exposes a preserved PDF with the same official source URL in
  its document metadata. Its advertised MD5
  `111dabc5e962ec140a6080232a0bb367` matches the collected 334-page object.
  The object is accepted as a preservation copy of the 2023 CIPP; the source
  row remains `secondary_source`, and the blocked official observation stays
  in the manifest.
- The Senegal EITI-hosted URL returned repeated HTTP 502 responses. The
  Vie-Publique.sn copy is a 354-page Ministry/ENERCAP report whose title and
  version table identify it as Livrable L4. It is provisionally accepted for
  document extraction, but identity with the official-host copy remains an
  explicit recheck. The mirror page labels the document 2025-04-02 while the
  embedded revision table continues into May and prints an anomalous
  `28/05/2024` for v5; no version date is inferred from that conflict.

This decision authorizes extraction from the preserved bytes. It does not
upgrade an archive or mirror into a primary authority for event-level claims:
locators must cite the government-authored document, while provenance retains
both the document publisher and the delivery host.

## 2026-09-29 — items below the tier threshold, ticket 1620

Author: claude-fable-5-1 (tier 4 adjudication), for Minh's decision. Each
item scored below `matching.llm_adjudication.accept_threshold` (0.8,
`config/jetp_tracking.yaml`) and stays pending in
`data/jetp/migration/0876-pending.csv` with owner `author`. The row-level
record is `data/jetp/migration/1620-register-dispositions.csv`.

### 1. The Senegal plan's own date (42 timing rows, confidence 0.7)

Affected: the 42 `event-timing` rows citing `sen-investment-plan-l4-mirror`
(`sen-qw2-plan-need-2025`, `sen-qw3-plan-need-2025`, the 29
`sen-plan-cost-annex-*`, `sen-plan-allocation-qw-04/08/10`,
`sen-project-qw-02/03-proposed-2025-04-02`,
`sen-project-annex-11/17/19-plan-proposal`, `sen-project-qw-04/08/10-plan-proposal`).

Evidence: the legacy date 2025-04-02 is the mirror host's label and the plan
file name (`20250402-ENERCAP-Livrable-L4-v5-clean-1.pdf`); it is printed
nowhere in the document. The version table (PDF p. 2) prints 05/02/2025 v1,
21/03/2025 v2, 04/04/2025 v3, 09/05/2025 v4 and 28/05/2024 for v5, a year
that contradicts the sequence. The annexes' own version table (17/03/2025)
matched their legacy date and was accepted at 0.9.

Reading: v5 is the delivered version and the anomaly is a typo for
28/05/2025. Recommended answer: record `report_date` 2025-05-28 (day
precision) for the 42 observations, citing a minted version-table line, and
note the typo; if the author declines the chronological reading, the rows are
terminal (`no supported document date`).

### 2. A bid deadline as a date role (1 row, confidence 0.7)

Affected: `sen-project-annex-16-procurement-2026-09-09` (observation
`observation-sen-project-annex-16-procurement-2026-09-09`, state
`procurement`).

Evidence: AAO 30/2026 (`sen-senelec-saloum-tender-2026`) p. 3 fixes bid
submission "au plus tard le MERCREDI 09 SEPTEMBRE 2026 à 09h30mn GMT"; the
Senelec notice index (`sen-senelec-procurement-2026`, not extracted) lists
the notice under 09/09/2026 in a column headed "Date limite"; the notice
itself carries no issue date (it refers to the AGPM in Le Soleil of
24 December 2025).

Reading: 2026-09-09 is the bid deadline, a date the publisher plans for the
procurement, not the launch day. Recommended answer: `planned` 2026-09-09
(day), or a new `date_role` term `deadline` if the author prefers the
publisher's word; either needs the index line that 1502 will extract.

### 3. An implementation period on a money amount (1 row, confidence 0.7)

Affected: `zaf-eepbip-maf-approved-2018` (observation
`observation-zaf-eepbip-maf-approved-2018`, EUR 20.1 million `approved`,
subject the line `zaf-eepbip-maf-claim-49`).

Evidence: the MAF profile (`zaf-eepbip-maf`) prints "Funding volume provided
EUR 20.1 million", "Project duration 05/2016-01/2018 (Appraisal);
08/2018-12/2026 (Implementation)", "Status Active".

Reading: the legacy `other_milestone` date 2018-08-01 is the first day of the
implementation period; `period_start` and `period_end` are interval roles of
a flow, and this observation is an amount state. Recommended answer: no
timing on the amount; once the EEPBIP project is a referent, one
`project_stage` observation `implementation` with `period_start` 2018-08 and
`period_end` 2026-12 (month precision), citing the same line.

### 4. Does "in the financing phase" satisfy `preparation`? (3 rows, confidence 0.5 to 0.6)

Affected: `idn-impl-green-corridors-2025` (0.6), `idn-impl-dieng34-2025`
(0.6), `idn-impl-nagajaya-portal-2026` (0.5); with them the four 1160
rejections recorded today on the author's decision (`idn-impl-aicet-2025`,
`idn-impl-hululais-2025`, `idn-impl-tanah-laut-2025`,
`idn-impl-eib-framework-2025`) and the accepted
`observation-idn-impl-nagajaya-2025`.

Evidence: the ledger term `project_stage.preparation` reads "The project is
being designed, appraised and prepared for funding and procurement"
(OC4IDS exact match). Progress Report 2025, Table 4.3-3 (printed pp. 72-73,
PDF pp. 73-74): Green Energy Corridors Sulawesi "approved by KfW Board,
currently waiting for PLN Board Approval" (p. 72); Dieng 3,4 "currently in
the financing phase for field development" (p. 73); Nagajaya "PPA has been
signed, with COD expected by mid 2027" (p. 72), while the portal profile
only says the plant "will install two Francis turbines"; Hululais "funding
was halted ... but is now back on track" (p. 72); Tanah Laut "PPA was signed
in May 2023" (p. 73). The 0970 and 1160 reviews read `preparation` as a
physical state and held or rejected on that reading, which the author
endorsed on 2026-09-29 for the four 1160 rows; 0970 nevertheless accepted
Nagajaya's report row as `preparation` on the signed PPA, the same fact 1160
rejected for Tanah Laut.

Reading: the ledger's own definition and the physical reading give different
answers, and the four rows of one table cannot be split between them:
under the definition, Green Energy Corridors, Dieng 3,4, Hululais and Tanah
Laut are all "prepared for funding"; AICET (a results-based lending
programme) and the EIB framework MOU fail either way, having no project
subject. Recommended answer: choose one reading for the whole table.
(a) Definition reading: accept the four as `project_stage` `preparation`
with `reporting_cutoff` 2025-11-30 citing their Table 4.3-3 lines, which
reopens the two 1160 rejections of Hululais and Tanah Laut; reject the
portal duplicate for Nagajaya, already covered by the report row.
(b) Physical reading, as endorsed today: the three holds become terminal
rejections and `observation-idn-impl-nagajaya-2025` is revoked for
consistency. Either way the term's definition should say which reading it
carries.
