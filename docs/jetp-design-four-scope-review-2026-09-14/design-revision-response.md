# Backend design revision 3: response to the four-scope review

Revision 3 incorporates the agreed findings into the
[backend design note](../jetp-backend-design.md). The assessment and comparison
report remain the historical review of revision 2 at
`68fd404cb55242ab38430e6bcbcd31b470285259`; their findings are not a fresh independent
review of revision 3.

| Scope | Change in the revised design |
|---|---|
| Open standards and ontologies | Section 2 defines a small application profile, mapping direction/strength, external versions and shared glossary definitions. It identifies IATI, PROV-O, SKOS and OWL-Time, with selective FIBO/OEO consultation. Sections 4, 6 and 7 connect mappings to typed validation, revision history and releases. |
| Integration of present research | Section 1 names the present scientific products. Sections 2–4 own protocols, frames, coverage, coding, analytical runs and artifacts. Sections 6–8 define their changes, releases and full source-to-paper lineage. Section 9 preserves research-critical history during ingestion; section 10 states research acceptance cases. Section 11 now contains scientific decision gates rather than detached schema extensions. |
| Comparable methods and tools | Section 2 records the selected methodological and engineering precedents and links the detailed comparison. The contracts preserve original source values, documentary disagreement, external dataset versions and adapter metadata. No full external platform is adopted. |
| Future whole-transition and PyPSA direction | Section 3 marks the country-keyed partnership lookup as a compatibility convention. Section 12 documents future initiative/jurisdiction/asset separation, external data and storage migration, and a possible model/scenario boundary. It explicitly creates no current MVP requirement, empty registry, model installation or acceptance gate. |

Research integration includes qualitative case selection, codebooks, independent
excerpt annotations, contrary evidence and reviewed interpretation. Quantitative
exports retain protocol revisions, frozen frames, typed unit keys, censoring and
input dependencies. Failed runs cannot supply published results. A source
correction identifies affected website claims and manuscript exhibits while older
released packages remain reproducible.

The earlier accounting decisions remain: assertions and reported positions feed
derived accounts; occurrence decisions prevent duplicate payments; financial
perimeters and date precision govern aggregation; and country-card text draws on
the total evidence while its principal source link retains its distinct role.
Section 5's reconciliation/first-metric contract is unchanged from revision 2.

Validation covers Markdown structure and links, the JSON provenance example,
the expanded provenance diagram's identifiers, internal contract consistency and
preservation of the earlier accounting section. No production code, canonical
data, pipeline tests or migrations are included. The design specifies work; it
does not claim that the proposed schemas or scientific analyses are implemented.
