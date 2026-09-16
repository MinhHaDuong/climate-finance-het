# 0818 — ZAF Q1-2026 register reconciliation

## Result

The retained `zaf-register-q1-2026` snapshot yields **257** material register rows, exactly the manifest target.  Every row is retained as an unadmitted source candidate; none is admitted to an account or used as payment, signature, or transition evidence.

## Evidence and boundary

- Source: `zaf-jet-investment-register-q1-2026`; SHA-256 `5b5d6442da4e9e57b3c83b7bfc04a19135b2c5bf750c2480685d9d084dc093f4`.
- Locator: `Overall - Data, Unique ID <official id>` for each row.
- The Q1 edition and the field labelled `Date of Financing Agreement Signed*` are retained source wording. They do not establish an independently verified event date.
- `Amount: Pledged`, currencies, reported USD/ZAR, funder, instrument and implementation status are source positions; they are not summed across perimeters and are not payments.

## Dispositions

- `unadmitted_candidate`: 257
- duplicate / excluded / unavailable / lost_visibility: 0 within this retained table; those dispositions belong to the country census outside this bounded extraction.

## Register implementation labels

- `A. Planned`: 23
- `B. Approved`: 18
- `C. Implementation Phase`: 128
- `D. Completed`: 88

## Handoff

The reconciled CSV is a replayable source-layer input for 0822. A later review may link candidates to operations only with explicit evidence; it must preserve this table's identifiers and must not infer payments or causality from register status.
