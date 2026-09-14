# KfW: a verified bulk comparison pool, with coarsened transaction dates

14 September 2026. **A concrete all-sector, multi-country KfW data source was acquired. It supports a portfolio and reporting-period feasibility pilot; exact first-payment timing and a pre-signature population are not established.** No causal design is selected.

## Acquisition and identity

The [official GovData BMZ dataset](https://data.gov.de/suche/daten/bmz-projektdaten-iati-meldung) describes monthly overwritten data covering ongoing, completed and newly committed measures. It links original [Country XML](https://teamwork.bmz.de/pub/bscw.cgi/2018133/DE-1-BMZ-RecipientCountry.xml) and [Region XML](https://teamwork.bmz.de/pub/bscw.cgi/2018133/DE-1-BMZ-RecipientRegion.xml). Both downloaded successfully after the web reader rejected XML. **Both delivered exactly the same 322,808,758 bytes and SHA-256**, so they must not be concatenated. The root generation timestamp is 2 September 2026; catalogue metadata dated July is not the current payload timestamp.

There are 34,735 BMZ activities. Selecting activities with a participating organisation exactly `XM-DAC-5-2` yields **4,036 unique KfW-linked IATI activity IDs**. KfW appears as accountable/extending agency; do not describe all BMZ records as KfW operations or equate every activity with an independent loan. The [profile](profile.json) records raw counts, code domains and byte hashes; [examples](examples.json) preserve exact IDs and source fields.

| Property of delivered KfW subset | Verified count |
|---|---:|
| Distinct IATI activity IDs | 4,036 |
| Implementation / finalisation / closed status codes 2/3/4 | 1,899 / 523 / 1,614 |
| Planned start / actual start fields | 4,036 / 4,036 |
| Planned end / actual end fields | 4,017 / 2,137 |
| Activities with type-3 disbursement entries | 3,649 |
| Type-2 outgoing commitment entries | 4,036 |
| Type-3 disbursement entries | 19,072 |
| Negative type-3 entries | 432 |
| Distinct recipient-country / sector codes | 95 / 140 |

Country codes include territories; regional entries are also present. Broad sector domains include education, health, water, transport, energy, forestry and governance. Finance-type codes are retained separately: 110 (3,009), 421 (822), 510 (173), 520 (19), 410 (13). Instrument harmonisation needs a separate codebook; this is not a 4,036-loan pool.

## The timing finding that matters

All 4,036 planned starts equal the corresponding actual starts in this snapshot. That does not establish zero start delay: plans may be overwritten or these labels may share an administrative source. No approval, signature or effectiveness field has been independently validated.

Of 19,072 type-3 entries, 18,757 are stamped on quarter ends (12,933 on 31 December); the other 315 use 26 August 2026. This distribution strongly suggests reporting-period aggregation and a latest partial period, **an inference pending publisher definitions**. Earliest positive transaction date is not an established first-payment day. There are 432 negative entries, and missing type-3 entries do not prove zero payment. Nor should negative corrections be mistaken for cancellation events.

The [IATI transaction codebook](https://iatistandard.org/en/iati-standard/203/codelists/transactiontype/) distinguishes a written outgoing commitment from funds placed at a recipient's disposal, including transfers between reported activities. These definitions alone do not equate the published commitment timestamp with lender Board approval or loan signature. The [Bundestag's March 2026 account of the government response](https://www.bundestag.de/presse/hib/kurzmeldungen-1155384) explicitly explains that BMZ's IATI publication does not have a project decision-date field. The BMZ FAQ returned only a JavaScript application shell, so institution-specific date and aggregation semantics remain unresolved.

## Two exact-ID observations beyond JETP beneficiaries

Examples were chosen as the first lexicographic ID at or above `DE-1-2013` within fixed countries Morocco and India, without selection on dates or speed. The ID prefix is a selection rule, not an inferred approval year. Each is verified within the publisher's XML; linked KfW detail pages failed to open and provide no additional verified evidence.

| Activity | Recorded start and commitment date | First type-3 entry | Interpretation |
|---|---|---|---|
| `DE-1-201366764`, Morocco Wind Programme (IKLU), Phase III, sector 23240 | 2016-08-04 | 2018-12-31, EUR 12,876,923.08 | Source reports three annual disbursement entries through 2020; date is not accepted as first-payment day. Phase III remains separate from other wind phases. |
| `DE-1-201365154`, Himachal Pradesh Forest Ecosystems Climate Proofing Project, India, sector 41010 | 2015-12-29 | 2017-12-31, EUR 51,463.39 | Non-energy comparison lead; annual entries followed by quarterly entries. Planned end 2026-10-30 is not actual completion. |

Exploratory checks also retained older Morocco and India studies/expert funds, with starts in 1992/1993 and transactions beginning at 2012-12-31. These show older surviving records, not complete histories from the 1990s. They were not used to select the two newer examples.

## Inclusion and historical retention

[KfW's current transparency page](https://www.kfw-entwicklungsbank.de/International-financing/KfW-Development-Bank/Transparency/) describes its project database as contractually agreed projects since 2013. Its [2020 IATI disclosure statement](https://www.kfw-entwicklungsbank.de/International-financing/KfW-Development-Bank/About-us/News/News-Details_593728.html) additionally includes BMZ projects already underway on 1 January 2013. This supports left-truncation concerns and a BMZ-mandate scope; it does not establish coverage of every KfW own-account or other-ministry financing.

Actual closed and finalising records demonstrate that this is not only a current active-project list. However, no pipeline, cancelled or suspended status code occurs in the KfW subset. Absence of those codes is not proof that there were no such operations, or that all completed contracts are retained. Monthly overwriting also means the current planned dates cannot be treated as original plans. A historical snapshot comparison and inclusion/removal specification remain necessary.

## Next discriminating pilot

Proceed with a **KfW/BMZ activity-universe and reporting-period pilot** alongside AFD. Freeze this original export, define the KfW agency filter, distinguish instruments and regional activities, and match a small fixed-country/all-sector cohort to legal/project documents. Ask the data documentation to resolve commitment versus signature, actual-start semantics, annual-to-quarterly aggregation, pre-2013 opening balances and 26 August partial-period entries. Seek older official snapshots and ascertain withdrawn/cancelled and closed-project retention. No external inquiry was sent.

If definitions confirm annual/quarterly flow periods, these may support interval-censored payment-stage or period-total analyses rather than day-level delay estimates. Earlier lifecycle stages would need additional originals. Tender and award links in the XML are a separate promising route, but generic GTAI links do not yet establish project-level procurement events.

## Scope, limits and artifacts

The exact acquisition budget was **20/20 external units**, counting each search query, open/click or HTTP download; see [log](acquisition-log.csv). The [brief](brief.md) candidly records that it was written after the first 11 discovery units. There is no saturation claim. Errors distinguish reader limitations from missing public disclosure.

Raw payloads and derived operation extracts remain in `/tmp/jetp-round3-kfw/`; they have not been claimed as remotely archived. Both bulk XML hashes are in the profile. The local profiling script is retained there as an audit computation, not installed in the production pipeline. No canonical ledgers, website totals, scripts or tickets were changed by this scout. Parent adjudication must precede any source-coverage promotion.
