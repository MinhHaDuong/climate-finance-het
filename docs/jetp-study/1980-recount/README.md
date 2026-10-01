# Independent recount of the grants register tables (ticket 1980)

Archived verbatim on 2026-10-01 from the scratch directory of session
haduong (`/scratch/tmp/claude-1000/-home-haduong/436e8d97-6d5f-4931-b844-2e5f4f6b461b/scratchpad/recount/`),
which is temporary. The recount compared the overall table and the donor
registers of the South African JET Grants Register with its own extraction,
independently of the parser of ticket 1950 (PR #1675), and found the
relabelled FR block, the cross-edition renumbering and the stale rates that
ticket 1980 records.

The scripts are kept as they ran, not restyled (`pyproject.toml` exempts
them from ruff). They read three local copies of the documents, which are
not archived here because the ledger holds them; the copies are byte
identical to these snapshots (sha256 checked 2026-10-01):

| Local name | Edition | Snapshot sha256 |
|---|---|---|
| `q2.pdf` | `zaf-jet-grants-register-2024-q2` | `8f6fcef78bf9ddb9c67fee3225448e0b6ac6f1d88a6c77cd58a9282cd0ebaf06` |
| `q3.xlsx` | `zaf-jet-grants-register-2024-q3` | `07645661df0c9a4ef97e0a172b8a3f5c92cc5371f992c70a2b3d5420f93c8147` |
| `q1_25.xlsx` | `zaf-jet-grants-register-2025-q1` | `6eae2fffc800f6c82c2d03b21af150ba633bf60992bd8e37a98515808e44d9c0` |

To rerun, copy the three snapshots from `data/jetp/documents/objects/`
under those names next to the scripts (after `make jetp-data`).

| File | What |
|---|---|
| `xl.py` | workbook reader |
| `cmp.py`, `run_xlsx.py` | overall against register comparison for a workbook (`run_xlsx.py q3.xlsx`) |
| `pdfx.py`, `cmp_pdf.py`, `cur_pdf.py` | the same for the 2024-q2 PDF |
| `cur.py`, `sens.py`, `hdr.py` | currency-rate and header checks |
| `q2_extract.json` | the recount's extraction of the 2024-q2 PDF |
