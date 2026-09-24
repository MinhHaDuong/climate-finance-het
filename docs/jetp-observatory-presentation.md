# JETP observatory: presentation

What readers of the observatory see and how the site is organised. Decided by
the author on 2026-09-23 and revised after the 2026-09-24 cold read (ticket 0902). Tickets [0881](../tickets/0881-le-mvp-distingue-o-d-e-et-m-et-pr-sente.erg)
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
| D | The documented route from a figure back to the page that supports it, walked in both directions | **The paper trail**: **Documents** → **Document rows** → **Statements** → **Projects**, **Funding**, **Organisations** |
| E | Counts and totals computed by the ledger, each with its unit, its perimeter and a link to what it was computed from | **The tallies** |
| M | Nothing | none |
| (methods) | What was done, what was not, and which tables are not served | **Methods** |

**Navigation.** Decided by the author on 2026-09-23, over the cold read of
ticket 0881 and the batches that followed it. The header holds three
sections: **The paper trail** · **The tallies** · **About**.

| Section | Its pages, in sub-bar order | Tab lands on |
|---|---|---|
| The paper trail | Documents · Document rows · Statements · Projects · Funding · Organisations | `#the-paper-trail`, a short page on what each step holds and why they run in that order |
| The tallies | Counts · Non-JETP energy operations (the accounts page of ticket 0877 joins as Money) | `#counts`: two pages need no landing page |
| About | Glossary · Methods · Who we are | `#about`, one line per page |

The Glossary sits under About: a reader consults it, and does not start
from it. The release history is in no bar; Methods links to it and is
marked current when it is open.

**Page top: two bars.**

- **Header tabs with dropdowns.** Each tab's label is a link to its
  landing page. Beside it, a disclosure button (`aria-expanded`, controlling
  a list of links; not `role=menu`) opens the section's pages, so every page
  is two clicks from anywhere. Click, tap, Enter and Space toggle it;
  ArrowDown opens it on its first link; Escape and a click outside close it.
  Hover opens one as an enhancement only. At phone width the three sections
  stack inside one collapsible nav behind a Menu button. The paper trail's
  dropdown lists the six steps in trail order.
- **The sub-bar.** On every page of a section, its landing page included, a
  second bar holds the section's pages as plain sibling tabs, the current one
  selected (`aria-current="page"`). It is one component for all three
  sections: no separators, no grouping. On the paper trail the order of the
  six tabs is the trail's, carried by position left to right and explained
  on `#the-paper-trail`, not by arrows or numerals. The selected tab is the
  page's position indicator, and the tabs beside it are the neighbouring
  steps. No page repeats it with an eyebrow, a trail block or in-page tabs,
  so a country's selected document rows and attributed statements are two steps
  (`#document-rows/<CODE>`, `#statements/<CODE>`).
- **Country chip.** A trail page scoped to a country shows the country at
  the right of the sub-bar as a removable chip ("Viet Nam ×"). Removing it
  opens the same step unscoped, and every trail tab keeps the country.
- **Breadcrumbs** appear on detail pages only (Projects › Bac Ai, Funding ›
  Viet Nam): small muted text with arrows, which never looks like the
  sub-bar's tabs.
- **Title block:** an h1 and a one-sentence lede. The page's longer
  explanation follows, word for word, folded under "About this page".

**Markers.** A number we calculated carries "Our calculation", with its
unit, its perimeter and a link to what was counted. A number a publisher
printed carries "As published", with the publisher and the date. The two
labels are a pair: each kind of number carries its own, and neither kind
goes unmarked.

**Addresses match labels.** Each page's address is its label's slug:
`#documents`, `#document-rows`, `#statements`, `#projects`, `#funding`,
`#organisations`, `#counts`, `#non-jetp-energy-operations`, `#glossary`, `#methods`,
`#who-we-are`, and the landing pages `#the-paper-trail` and `#about`; the
release history is `#release-history`. A country's page nests under its step
(`#funding/<CODE>`, `#document-rows/<CODE>`, `#statements/<CODE>`); a project is
`#project/<project_id>`. The addresses of earlier previews forward in place,
in one hop, to the new ones: `#countries`, `#country/<CODE>`, `#evidence`,
`#entries`, `#on-the-record`, `#whos-who`, `#comparisons` (including their
country filters and deep links),
`#numbers`, `#by-the-numbers`, `#the-tallies`, `#comparison`,
`#historical-comparison`, `#how-we-did-this`, `#editions`, and
`#inventory/<CODE>` with its `?row=` and `?tab=record`. The pages emit only
the new names. The full table is in the observatory's
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
  snapshots). Document rows is D2: selected rows from registers, annexes and
  lists, with the original column wording preserved where available; an
  extracted row is not necessarily a unique project. Statements is D3:
  attributed amounts, dates and statuses, plus project–document links, with
  a document location where recorded. Several statements may come from one
  row, while some come from prose. Projects, Funding and Organisations are D4:
  projects and assets, financing, and parties. Funding's country table lists
  individual financing statements, with needs separately labelled; it does
  not repeat the first eight projects or sum milestones. Organisations groups
  exact names by country and combines funder and operator roles; reviewed
  party-name forms appear as aliases without guessing unreviewed matches.
  The sub-bar shows where each
  page sits on the trail and lets the reader step one level up or down: from
  a project to what is on the record about it, to the entries, to the page
  of the document, and back.
- **The tallies.** A number the ledger computes is visibly set apart from
  a number a publisher printed ("Our calculation" against "As published"):
  it states its unit and perimeter and opens the items on the record it was
  computed from. Accounts, when they exist, appear only here. The page is
  one table, not a second landing page: a row per computed figure — what it
  is, value, unit, what it covers, as of, and a "computed from" link —
  grouped under a subheading per country and never summed across countries.
  The charts follow as numbered, captioned figures ("Figure 1. …"), each
  marked "Our calculation". The landing page keeps its stat grid, under the
  eyebrow "The tallies".
- **No models.** The observatory tests no causal explanation, and its
  navigation has no place for one. Methods says in plain words what
  the observatory does not do.

Words avoided on the pages: *claims* (it implies doubt about a publisher's
statement), *deals* and *players* (loaded), *sources* (a source is also a
person, and the ledger retired the word), *entities* and *records* (opaque to
a general reader).

The serving contract, every table served or named as not served, is
[`jetp-ledger-storage.md`](jetp-ledger-storage.md) section 2.
