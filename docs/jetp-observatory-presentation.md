# JETP observatory: presentation

What readers of the observatory see and how the site is organised. Decided by
the author on 2026-09-23. Tickets [0881](../tickets/0881-le-mvp-distingue-o-d-e-et-m-et-pr-sente.erg)
(organisation and page vocabulary) and
[0882](../tickets/0882-page-ontologie-du-mvp-d-finitions-des-ob.erg) (Glossary)
implement it. What the ledger's terms mean is [`jetp-ontology.md`](jetp-ontology.md);
how the builders speak about the ledger is [`jetp-language.md`](jetp-language.md).

## Organisation and vocabulary

The four ODEM objects of [`jetp-language.md`](jetp-language.md) are the observatory's organising
principle: they decide what is grouped with what, in which order, and what
may link to what. They are not its vocabulary. The pages assume a reader who
knows how empirical work proceeds, that a figure rests on documents and that
words need definitions, and they never put the framework's names in front of
that reader. "Ontology", "Evidence", "Model", the letters O, D, E, M and the
step codes D1 to D4 appear in code, data attributes and these documents, not
in page copy.

The page vocabulary is a newsroom's, decided by the author on 2026-09-23:
data desks organise document-based work the same way, and their words are
plain. It keeps to the neutral side of that vocabulary, attribution rather
than suspicion, because the readers are researchers as well as journalists.

| ODEM object | What the reader sees | Label on the page |
|---|---|---|
| O | What each word, status, measure and relation means, where the definition comes from, and when it changed | **Glossary** |
| D | The documented route from a figure back to the page that supports it, walked in both directions | **The paper trail**: **Documents** → **Entries** → **On the record** → **Projects**, **Funding**, **Who's who** |
| E | Counts and totals computed by the ledger, each with its unit, its perimeter and a link to what it was computed from | **By the numbers** |
| M | Nothing | none |
| (methods) | What was done, what was not, and which tables are not served | **How we did this** |

**Navigation order.** The paper trail (Documents, Entries, On the record,
Projects, Funding, Who's who) · By the numbers · Glossary · How we did this.
The Glossary sits last, beside How we did this: a reader consults it, and
does not start from it (author's cold read of ticket 0881, 2026-09-23).

**Addresses match labels.** Each page's address is its label's slug:
`#documents`, `#entries`, `#on-the-record`, `#projects`, `#funding`,
`#whos-who`, `#by-the-numbers`, `#glossary`, `#how-we-did-this`, and
`#historical-comparison`, `#release-history` for the two pages reached from
By the numbers and How we did this. A country's page nests under its step
(`#funding/<CODE>`, `#entries/<CODE>`, `#on-the-record/<CODE>`); a project is
`#project/<project_id>`. The addresses of earlier previews (`#countries`,
`#country/<CODE>`, `#evidence`, `#numbers`, `#comparison`, `#methods`,
`#editions`, `#inventory/<CODE>` with its `?row=` and `?tab=record`) forward
in place to the new ones; the pages emit only the new names (same decision).
The full table is in the observatory's
[README](../deliverables/jetp-observatory/README.md).

- **Glossary.** Grouped by theme, alphabetical within each group: what the
  ledger tracks (projects, assets, agreements, parties, perimeters), how
  documents are read (documents, entries, locators, publishers), statuses,
  measures, relations. These themes are the lists of the ontology tables, so
  the hand-written first list and the generated one group alike. The terms in force, grouped by list: each class, relation
  and value with its definition, its external source and its revision
  history. A relation shows what it connects. Every term used elsewhere on
  the site links to its glossary entry. Generated from the ontology tables, `data/jetp/ontology/` ([`jetp-ontology.md`](jetp-ontology.md) section 5).
- **The paper trail.** Documents is D1 (publishers, documents, retrievals,
  snapshots). Entries is D2: a row of a register, a line of a plan annex, a
  submission in a list. On the record is D3: each item reads "according to"
  its publisher, with the date. Projects, Funding and Who's who are D4:
  projects and assets, agreements, and parties. Each page shows where it
  sits on the trail and lets the reader step one stage up or down, from a
  project to what is on the record about it, to the entries, to the page of
  the document, and back.
- **By the numbers.** A number the ledger computes is visibly set apart from
  a number a publisher printed: it states its unit and perimeter and opens
  the items on the record it was computed from. Accounts, when they exist,
  appear only here.
- **No models.** The observatory tests no causal explanation, and its
  navigation has no place for one. How we did this says in plain words what
  the observatory does not do.

Words avoided on the pages: *claims* (it implies doubt about a publisher's
statement), *deals* and *players* (loaded), *sources* (a source is also a
person, and the ledger retired the word), *entities* and *records* (opaque to
a general reader).

The serving contract, every table served or named as not served, is
[`jetp-ledger-storage.md`](jetp-ledger-storage.md) section 2.

