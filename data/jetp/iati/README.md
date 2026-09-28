# IATI energy comparator slice (ticket 0886)

Frozen 28 September 2026 from the [Code for IATI Datastore Classic API](https://datastore.codeforiati.org/docs/api/).
Each compressed JSON file contains the exact query URLs, SHA-256 hashes of API
responses, reported page totals, and a compact projection of the returned
activities. The collector is `scripts/jetp/catalog_iati_energy.py`; the ledger
adapter is `scripts/jetp/build_iati_comparators.py`.

| Country | API hits | Admitted activities | Ledger flow observations |
|---|---:|---:|---:|
| Indonesia | 433 | 344 | 4,233 |
| Senegal | 370 | 241 | 1,254 |
| Viet Nam | 485 | 411 | 1,618 |
| South Africa | 410 | 305 | 736 |
| **Total** | **1,698** | **1,301** | **7,841** |

The query selects recipient country and any of the 19 energy sector codes used
in the Viet Nam pilot. The API matches country and sector independently, so
397 hits do not establish a same-activity or same-transaction DAC energy and
country match and are not admitted. Sector codes are interpreted under their
IATI vocabulary: DAC 5-digit (1, also the default when omitted) or DAC 3-digit
(2). Identical numeric codes in another vocabulary, such as NAICS, are not DAC
energy codes ([IATI sector rule](https://reference.iatistandard.org/en/iati-standard/203/activity-standard/iati-activities/iati-activity/sector/)).

A matched activity becomes one comparator line for each country in which it
appears. A transaction uses its own country and sector when reported, otherwise
the activity-level values. When these indicate multiple recipient countries or
a mix of DAC energy and non-energy sectors, its full amount has no defensible
country-energy allocation and is withheld from flow observations. The compact
projection records 3,291 country-ambiguous and 3,833 sector-ambiguous
transaction appearances in the admitted activities, plus each activity's full
source transaction count. These counts are appearances in country snapshots,
not distinct global transactions.

The ledger assigns the first line for each exact IATI identifier to
`external-ids`; 94 additional country appearances have `same_as` links to that
line. Every line also carries the identifier as its locator. The activity's
reporting organisation remains a source field; the dataset edition's publisher
in the ledger is the International Aid Transparency Initiative. These external
activities are never partnership projects. The adapter also records GEM IDs
from `other-identifier` when present; none occur in this frozen slice.

Transaction types 2/11/C (commitment), 3/D and 7 (disbursement), 4 (expenditure),
and 12 (pledge) map to the ledger's existing flow types, following the
[IATI TransactionType codelist](https://codelists.codeforiati.org/TransactionType/).
Another 4,913 country-energy transactions have other source codes and are
counted by the adapter but are not promoted to a shared flow type. The six
standard activity statuses map through `status-crosswalk`. Dates and amounts
remain source assertions. There is no currency conversion or reconciliation
with partnership finance.

The API data changes over time. Rebuilding the committed ledger from these
snapshots is deterministic; rerunning the collector creates a new edition and
may produce different counts. The full 831 MB IATI corpus remains outside this
repository and is queried only when needed.
