## Retrieval protocol {.unnumbered}

All API queries are bounded to publication years 1990--2024. Terms, concept groups, and the title blacklist are in `config/openalex_queries.yaml` and `config/corpus_filter.yaml`; the curated seed lists are in `config/grey_sources.yaml`, `config/unfccc_sources.yaml`, and `config/oecd_dac_sources.yaml`. Tier 3 and Tier 4 terms are retained only when the abstract mentions at least 2 and 3 respectively of the 4 concept groups (climate, development, environment, finance).

| Source | Retrieval | Query fields | Query terms | Languages |
|:---|:---|:---|:---|:---|
| OpenAlex | Four-tier keyword search (co-occurrence filter, T3 2 / T4 3 of 4 concept groups) | default.search (title, abstract, indexed fulltext) | 52 (T1 15, T2 25, T3 10, T4 2) | 8: Arabic, Chinese, English, French, German, Japanese, Portuguese, Spanish |
| ISTEX | Boolean phrase search | ISTEX default index | "climate finance" OR "finance climat" OR "finance climatique" | English, French |
| Institutional reports | Curated seed list plus World Bank repository API | seed identifiers; repository full-text search | 17 curated reports, 3 API queries | English |
| UNFCCC key documents | Curated seed list (config/unfccc_sources.yaml) | document symbol | 232 seed documents | English |
| OECD DAC key documents | Curated seed list (config/oecd_dac_sources.yaml) | document symbol | 35 seed documents | English |
| bibCNRS | Hand-harvested export (CNRS credentials) | aggregator native search (Gale, Wanfang, NewsBank) | not machine-readable | French, Chinese, Japanese, German |
| SciSpace | AI-assisted systematic review, hand-exported | vendor native search | not machine-readable | English |
| Teaching canon | Syllabus scraping plus LLM reference extraction | syllabus full text | not machine-readable | English |

: Retrieval protocol per source. *Retrieval*: how records enter the corpus. *Query fields*: the index fields the query matched. *Query terms*: search terms, or curated seed documents where the source is a hand-assembled list. *Languages*: the languages the query terms or seed documents are written in. Query-term counts are rendered from the deposited configuration for the five configured sources (OpenAlex, ISTEX, the institutional-reports seed list, and the two key-document layers). Language coverage is config-derived only for OpenAlex, whose terms carry language tags, and for the two key-document layers, whose seed entries carry a language field. The ISTEX and institutional-reports languages are asserted by the harvest scripts, because neither source declares a language a script could read. The three restricted sources have no machine-readable query — their rows describe the harvest as it was performed and are marked accordingly. Records returned and retained per source are in the corpus composition table; per-run harvest counts are not reported here because no machine-readable record of them exists.


### Curated institutional-reports seed list {.unnumbered}

| Title | Author | Year | Organisation |
|:---|:---|:---|:---|
| Climate Finance in 2013-14 and the USD 100 Billion Goal | OECD | 2015 | OECD |
| Mobilising Bond Markets for a Low-Carbon Transition | OECD | 2017 | OECD |
| Climate Finance Provided and Mobilised by Developed Countries in 2013-18 | OECD | 2020 | OECD |
| Aggregate Trends of Climate Finance Provided and Mobilised by Developed Countries in 2013-2022 | OECD | 2024 | OECD |
| Better Aid: 2008 Survey on Monitoring the Paris Declaration | OECD | 2008 | OECD DAC |
| Summary and recommendations by the Standing Committee on Finance on the 2014 Biennial Assessment and Overview of Climate Finance Flows | UNFCCC Standing Committee on Finance | 2014 | UNFCCC |
| Summary and recommendations by the Standing Committee on Finance on the 2016 Biennial Assessment and Overview of Climate Finance Flows | UNFCCC Standing Committee on Finance | 2016 | UNFCCC |
| Summary and recommendations by the Standing Committee on Finance on the 2018 Biennial Assessment and Overview of Climate Finance Flows | UNFCCC Standing Committee on Finance | 2018 | UNFCCC |
| Fourth Biennial Assessment and Overview of Climate Finance Flows | UNFCCC Standing Committee on Finance | 2020 | UNFCCC |
| Fifth Biennial Assessment and Overview of Climate Finance Flows | UNFCCC Standing Committee on Finance | 2022 | UNFCCC |
| Report of the Secretary-General's High-Level Advisory Group on Climate Change Financing | United Nations | 2010 | UN HLAGCC |
| The Landscape of Climate Finance | Climate Policy Initiative | 2012 | CPI |
| Global Landscape of Climate Finance 2023 | Climate Policy Initiative | 2023 | CPI |
| Stern Review: The Economics of Climate Change | Stern, Nicholas | 2006 | HM Treasury |
| World Development Report 2010: Development and Climate Change | World Bank | 2009 | World Bank |
| Providing Global Public Goods: Managing Globalization | Kaul, Inge; Conceição, Pedro; Le Goulven, Katell; Mendoza, Ronald U. | 2003 | UNDP/Oxford University Press |
| Reporting on Development: ODA and Financing for Development | Vanheukelom, Jan and Migliorisi, Stefano and Herrero Cangas, Alisa and Keijzer, Niels and Spierings, Eunike | 2012 | ECDPM |

: The curated institutional-reports seed list, in full (`config/grey_sources.yaml`). The World Bank Open Knowledge Repository contributes further records by API query and is not enumerated.

