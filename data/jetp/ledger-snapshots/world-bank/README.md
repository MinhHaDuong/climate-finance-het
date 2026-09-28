# Historical comparison: frozen World Bank source fields

The four JSON files project public Projects & Operations API responses onto the
fields needed to select and describe the historical reference pool. Retrieved
13 September 2026. They preserve all returned project records in each country,
not only selected successes, and record pagination totals and raw-response hashes.

| Source code | Country | API records retained |
|---|---|---:|
| ID | Indonesia | 593 |
| VN | Viet Nam | 262 |
| ZA | South Africa | 48 |
| SN | Senegal | 216 |

The public MVP selects status `Closed`, approval before the country's JETP
announcement, and a source sector label containing `energy`, `power` or
`electric` (case-insensitive). Result: 97 closed energy-related operations:
38 Indonesia, 32 Viet Nam, 10 South Africa, 17 Senegal. Approval years span
1951–2021. Includes mixed-sector, policy and additional-financing operations;
the interface exposes instrument/vintage filters and labels additional finance.

These are administrative operations, not necessarily unique physical projects
or verified completed assets. The reported closing field is not independently
verified as the actual physical completion date. Status in the API can be older
than retrieval. A closed-only pool is subject to selection on completion and
cannot estimate an acceleration effect. No JETP-versus-historical speed estimate
is published by this MVP.

This pool is separate from canonical JETP identities. It supports exploratory
context and the feasibility audit in 0729, not the matched design in 0730 yet.
Keyword selection may omit energy-related operations with absent or different
sector labels. The preserved projections permit inspection of exclusions.

Rebuild a snapshot from downloaded API response pages using
`scripts/jetp/build_wb_snapshot.py --input <pages...> --country <ISO2>
--retrieved-on <date> --output <snapshot.json>`; pagination must match the API's
country total. Page query URLs and hashes are retained in each snapshot. This is
a lossless projection of declared fields, not an archive of all API fields.

Source: [World Bank Projects & Operations](https://projects.worldbank.org/).
Records retain direct project URLs. Raw source-document redistribution is not
part of the website bundle.
