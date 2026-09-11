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
