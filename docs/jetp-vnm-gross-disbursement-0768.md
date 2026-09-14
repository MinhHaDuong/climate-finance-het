# Viet Nam: gross-disbursement account unavailable (0768)

- **Review date:** 2026-09-14
- **Metric:** `gross_disbursement_original_currency_v1`
- **Subject proposed:** a single financing agreement or tranche
- **Result:** unavailable; no reconstructed closing, residual, or payment subtotal is published.

The VNM migration retains financial claims and positions in
`config/jetp-vnm-migration.json`, but it does not admit them as dated
original-currency gross-disbursement occurrences for one agreement. Its retained
source dispositions explicitly say that reported valuation/cost/mobilised
positions do not make payment dates; proposals and announced facilities are not
upgraded to payments; lender history has a wider, mixed-stage perimeter; and a
source-reported absence does not establish a zero payment history or complete
coverage. Those rules occur in `legacy_observations` (including the entries for
`vnm-pilot-observation-012`, `vnm-pilot-observation-013`,
`vnm-pilot-observation-014`, and `vnm-pilot-observation-017`).

There is therefore no reviewed account-opening decision supported by an exact
source locator, edition, acquisition and extraction; no accepted occurrence
membership for a dated payment; no disjoint period-flow cover; and no explicit
complete-coverage decision. A reported zero would not repair this absence.

Legacy VNM headlines and their source-defined positions stay available through
the migration crosswalk. This unavailability record changes neither their values
nor canonical observatory ownership. A later account needs evidence and the
account-specific decisions validated in `scripts/jetp/_contracts.py`, then must
be derived by `scripts/jetp/_reconciliation.py`.
