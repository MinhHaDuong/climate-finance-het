| Source | Raw | Refined | Unique | %non-EN | %DOI | %Abstract | %Refs |
|:-------|----:|--------:|-------:|--------:|-----:|----------:|------:|
| OpenAlex | 41,138 | 31,544 | 30,815 | 6% | 76% | 88% | 61% |
| ISTEX | 748 | 635 | 443 | 2% | 100% | 97% | 96% |
| bibCNRS | 233 | 219 | 200 | 8% | 10% | 5% | 1% |
| SciSpace | 663 | 618 | 238 | 1% | 83% | 90% | 66% |
| Institutional reports | 281 | 210 | 103 | 0% | 95% | 97% | 32% |
| Teaching canon | 622 | 618 | 549 | 9% | 100% | 31% | 55% |
| UNFCCC key documents | 232 | 230 | 225 | 0% | 0% | 94% | 0% |
| OECD DAC key documents | 35 | 33 | 33 | 0% | 12% | 94% | 6% |
| **TOTAL** | **43,179** | **33,344** | **32,606** | **6%** | **76%** | **87%** | **61%** |

: Works counts and key fields presence by source. *Raw*: records with `from_*` provenance flag before filtering (a record in multiple sources is counted once per source). *Refined*: after quality filtering. *Unique*: found only in that source (`source_count = 1`); *Refined* less *Unique* = 738 works appearing in two or more sources. The TOTAL row is the deduplicated union of works, not the column sum: 748 raw records and 738 refined works carry more than one provenance flag, which puts the source rows 773 and 763 memberships above their totals (25 and 25 of them carry three). *%non-EN*: share of non-English works. *%DOI*, *%Abstract*, *%Refs*: metadata completeness among refined records. {#tbl-quality}
