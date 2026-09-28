# OECD CRS energy comparator projection

The 80 `crs_<COUNTRY>_<YEAR>_Q.csv` files preserve all 51 source columns of
the archived OECD CRS activity-level response and select `PRICE_BASE=Q`
(2024 constant USD). Their source is the pinned DVC directory
`data/jetp/crs/` (`jetp_pull` in `dvc.lock`, directory MD5
`936675fd267801956b96b404dd181988.dir`). `manifest.csv` records each
compressed source's SHA-256, the projection's SHA-256 and its row counts.
Run `scripts/jetp/build_crs_energy_projection.py` to rebuild the projections from the
DVC bytes; it makes no network request. The source query and its 11-dimension
key are in `scripts/jetp/catalog_crs.py` and the
[OECD CRS Data Explorer](https://data-explorer.oecd.org/vis?df%5Bag%5D=OECD.DCD.FSD&df%5Bid%5D=DSD_CRS%40DF_CRS&df%5Bvs%5D=1.6).

The archived response contains Q and V versions of each row. This ledger
projection retains 8,029 Q rows: 2,716 IDN, 1,356 SEN, 2,486 VNM and
1,471 ZAF. `OBS_VALUE` has `UNIT_MULT=6`, so flow observations express the
published millions in USD units. Q values are already at `BASE_PER=2024`;
no exchange rate or additional deflator is applied. The `deflators` rows
record this no-op representation with value 1, each citing a Q source line.

`MD_ID` identifies one SDMX microdata row and is the external CRS row ID.
`OECD_ID` is retained verbatim in the 51 fields; it repeats across flows and
in 88 cases across different donor project IDs, so it cannot alone be an
external-ID key. `DONOR_PROJECT_ID` is namespaced by `DONOR` for the activity
anchor and `same_as` relation. Blank donor project IDs stay unmatched.

`rio-coefficients-2020.csv` transcribes the EU row of Table 1, printed page
4, of the OECD [2020 Rio marker coefficient survey](https://one.oecd.org/document/DCD/DAC/STAT(2020)41/en/pdf).
The survey describes coefficients applied when reporting 2017–18 data to the
UNFCCC and CBD; these are not universal OECD coefficients. Only the EU's
explicitly reported adaptation, mitigation and biodiversity values are
entered in `marker-coefficients`. A marker observation is a score, never an
amount multiplied by one of these coefficients.
