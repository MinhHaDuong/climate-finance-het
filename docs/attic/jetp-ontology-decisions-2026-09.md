Retired 2026-09-30 from `docs/jetp-ontology.md` (ticket 1701); their effect is written into the ontology, the storage contract and the fusion rules.

# JETP ontology v2: design decisions and the case against the old schema

The author's decisions of 2026-09-22 and 2026-09-23 shape it:

1. Split the identity registry now rather than tag it. The current
   `projects.csv` mixes four kinds of row; a column would only name the mix.
2. The published line is the first-class unit, and its storages are unified.
3. Statuses follow each publisher's practice. The publisher's word is stored
   verbatim and crosswalked; it is never overwritten or inferred.
4. Design the target, then migrate. No incremental patching of the current
   tables.
5. Line identifiers are minted, not keyed on fingerprint and locator
   ([storage contract](../jetp-ledger-storage.md) section 1).
6. The party table is built in the identity split, minimal, with funder and
   channel roles populated first ([migration](jetp-ledger-migration.md), step 4).
7. Matching is a tiered, defeasible, traceable process ([storage contract](../jetp-ledger-storage.md) section 4).
   The record format is designed now; the matcher starts at its simplest tier.
8. Translations are managed as document relations and derived text
   ([storage contract](../jetp-ledger-storage.md) section 5). Automatic summaries and translations are derived aids, never
   justification, and are nice-to-have.
9. After the fit-for-purpose review (review 5): amount semantics are closed
   vocabularies (measure, basis, flow type, modality, period roles); every
   record row carries `recorded_at`; external identifiers and the comparator
   pools (World Bank, CRS, IATI) enter as lines of API snapshots; the
   adjudications and accounts of the backend design keep their tables;
   rates and deflators are sourced records. The storage contract's section 3 volume projection is
   corrected.
10. After the proofing review (review 6, 36 random pages of 12 documents):
    sector is a shared axis coded with the OECD DAC purpose list and reached
    by crosswalk from each publisher's own scheme; Rio and policy markers
    are a measure with a sourced coefficient table; targets and counts in
    publisher units are measures; roles exist on any subject; lines relate
    to lines; locator syntax is defined per format; a delivery axis for
    agreements is aligned to the IATI activity status list; ranges have
    bounds; a publisher's own modality scheme stays a verbatim field. What
    stays out of scope is named in section 6. The delivery axis and the
    section 6 list were proposed as defaults and approved by the author on
    2026-09-22.
11. On 2026-09-23, after the ODEM acceptance review
    ([`jetp-odem-acceptance-review-2026-09-23.md`](jetp-odem-acceptance-review-2026-09-23.md)):
    the ledger is Data guided by Ontology, Evidence comes on top, and there
    is no Model (section 0). The ontology is a set of tables with
    definitions, external mappings and revisions (section 5). The builders'
    language, including five retired terms, is
    [`jetp-language.md`](../jetp-language.md); the observatory's organisation
    and page vocabulary are
    [`jetp-observatory-presentation.md`](../jetp-observatory-presentation.md).
12. On 2026-09-23, organisations are under authority control, as in a
    library's name authority file or the ROR and GLEIF registries. The ledger
    keeps one organisation table: a publisher is a party in a publishing
    role, and the publishers table folds into `parties`. Every form of an
    organisation's name is a row of `party-names` with its form type, its
    language and the document or line it was read from, and one form is
    preferred. Senelec and SENELEC, EVN, Vietnam Electricity and Tập đoàn
    Điện lực Việt Nam, PLN and Perusahaan Listrik Negara, AFD and Agence
    française de développement each resolve to one organisation. An
    external identifier (IATI organisation identifier, ROR, LEI, Wikidata)
    is tier 1 of matching for organisations; case, diacritic and spacing
    variants are merged when the party is minted; acronyms, translations
    and former names are tier-2 candidates, reviewed
    ([storage contract](../jetp-ledger-storage.md) section 4).

## Why the old schema failed

The four reviews make the case; the short form is this. The four
partnerships never publish a project registry. They publish lists: a grants
register keyed by funder and sequence (South Africa, 257 rows), plan appendices
of capacity lines by system (Indonesia, 1 579 rows over two editions), plan
annexes of positions and task groups (Viet Nam, 279 rows), promoter submissions
and quick wins (Senegal, 49 rows). The ledger read all of these as projects.
The result is one foreign key, `events.project_id`, that resolves to a funder
tranche in 257 cases, a donor facility or programme in about 40, and a physical
undertaking in about 60, so that no count and no sum in the ledger states its
unit. The register's own status letters were dropped into a notes string. The
21 Viet Nam count slots, a cardinality assertion, sit in the registry as rows.
The partnership pledges, which are the headline of every country page, have no
table and live in configuration. Asset attributes exist in three tables but
no asset does. The same kind of thing, a published line, lives in four
storages with three schemas.
