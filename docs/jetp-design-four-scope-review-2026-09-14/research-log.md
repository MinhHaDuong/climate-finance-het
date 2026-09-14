# Research and verification log

## Scope and baseline

Research assessed on 14 September 2026 in the existing
`explore-jetp-backend-design` worktree. Baseline:
`68fd404cb55242ab38430e6bcbcd31b470285259`, backend design revision 2.

The four scopes are open standards/ontologies, integration of the present research
programme, comparable research methods/tools, and future expansion beyond JETPs.
The agreed comparison balances methods and reusable tooling. Whole-transition
observation and a PyPSA electricity modelling arm are future directions only.
The deliverable is a review and proposed revision package; no design rewrite,
schema migration, estimator selection or model implementation is included.

Local inputs included the backend design, its Astra/Fable review-response record,
the observatory-and-papers programme, and historical-population/research briefs.
The original design is checked byte-for-byte against the baseline commit.

## Evidence collection

The source inventory contains 39 primary publications, project pages,
methodologies, specifications and repositories. The matrix covers 18 comparator
families. Sources were followed from project pages to methods, repository
documentation and replication metadata where these clarified a material claim.
Earlier exploration and the final verification pass form one research exercise.

Searches focused on documentary finance, physical assets, emissions and electricity
series, policy monitoring, publication pipelines and energy-system modelling.
The stopping condition was support for each material comparison, explicit bounds
on conflicting definitions and unresolved access, and no remaining gap likely to
change the architectural recommendation. This is a purposive comparison, not a
systematic-review claim of exhaustive coverage.

Specific edition checks included TUFF 4.0 rather than 3.0, the 2025 Oxford Monitor's
August 2025 information cutoff, CAPMF's examined 1990–2023 coverage, Climate Funds
Update's stated February 2026 coverage for most funds, and Ember's retrieved v1.5
methodology. PyPSA-Earth's current repository describes sector coupling; an older
electricity-only description would understate the current documented workflow.

## Access and interpretation limits

- Some Open Energy Platform overview content appeared in indexed primary-page
  text while direct rendering returned navigation only. Platform documentation
  corroborated the distinction between model factsheets and scenario bundles.
- Climate Policy Explorer's dashboard route was unavailable through the examined
  route. The associated publication and replication metadata remain usable
  evidence of the research approach; the live application was not verified.
- Zenodo replication file metadata were visible in indexed results; the package
  was not downloaded or executed. No replication-success claim is made.
- Carbon Monitor's rendered last-data-update value was unavailable. Website news
  dates were not substituted for a data cutoff.
- Climate TRACE's 2025 changelog was examined as a revision example. It was not
  presented as the latest 2026 release. A failed downloads-page route was not
  interpreted as absence of downloadable data.
- Software licence statements are limited to the inspected repositories.
  Data and source-document licences are separate. GEM maps licensing and several
  complete upstream-data reuse conditions remain unverified.
- No authenticated API, external dataset join, classifier benchmark, replication
  run, application installation or PyPSA model run was performed.
- No institutional messages were sent and no new external model-review payload
  was transmitted. Earlier permission for the Astra/Fable design review was not
  treated as blanket authorisation for a new external-service payload.

The research artifacts preserve citations, editions/access notes and analytical
findings. They do not claim to be an immutable byte archive of all cited web pages
or PDFs. Creating such a corpus remains distinct from this design review.

## Artifact checks

The Markdown assessment and report are the maintained source documents. Numbered
footnotes resolve to the source inventory, and each report includes a full Sources
section. The CSV matrix carries source IDs and direct URLs so it remains usable
outside the report. Tables were checked for consistent column counts and source
references.

Standalone HTML reading copies were rendered with Pandoc and embedded monochrome
CSS. Each has a single report title, a contents list and linked footnotes, with no
external script or stylesheet requirement. HTML copies are covered by the
repository's existing generated-file ignore rules. Their content, internal anchors
and local links were checked mechanically; visual browser inspection was not
performed.

The original design, backend data and production code remain unchanged. Validation
is document consistency, citation/link resolution, CSV structure, HTML generation
and baseline equality. No pipeline test result is claimed for this document-only
research task.
