# South Africa: gross-disbursement account unavailable (0768)

- **Review date:** 2026-09-14
- **Metric:** `gross_disbursement_original_currency_v1`
- **Subject proposed:** a single financing agreement or tranche
- **Result:** unavailable; no reconstructed closing or residual is published.

The bounded South African migration intentionally retains no payment candidate:
`config/jetp-zaf-migration.json` has `payments: []`. Its retained register is a
pledge/allocation inventory and its Q1 report has aggregate tables with different
perimeters. The migration policy says that register dates are not payment dates,
that original pledged amounts do not establish payment, and that report/register
disagreement remains unresolved. See the `register dates`, `register amounts`,
`report perimeters`, and `register/report discrepancy` entries in `source_regime`.

Consequently the source set supplies none of the reviewed inputs required by the
first account: a specific agreement or tranche, an accepted original-currency
gross-disbursement opening, accepted dated disbursement occurrences or a wholly
covering flow, and a reviewed complete-coverage decision. It cannot support a
subtotal labelled as a payment total either. The reported ZAF pledge/allocation
positions remain available in their original perimeters; this result neither
changes their meaning nor selects anything for the observatory's canonical
publication.

A later account must add the required evidence and decisions, then invoke
`scripts/jetp/_reconciliation.py`. Until then, this document is the reviewed
country-level unavailability record for ticket 0768.
