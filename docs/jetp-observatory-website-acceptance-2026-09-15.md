# JETP observatory website acceptance — 15 September 2026

This is a local acceptance record for the prepared `2026-09` release. It does
not publish a website or assign a public URL.

## Preview and recovery

The static preview is `deliverables/jetp-observatory/`; it needs only an HTTP
server and its committed JSON handoffs. The prepared archive is
`data/jetp/releases/2026-09/jetp-observatory-2026-09.zip`, with descriptor
`release.json` and SHA-256
`06df22ca8c0050842ef26accabea484df35305fdad9d4c9b33d5186eba341e80`.
`tests/test_jetp_public_release.py` verifies its complete inventory and an
offline restoration, without Git, DVC, network access or source-document
redistribution.

The website keeps stable hash routes for overview, country, project, historical
comparison and methods pages. Country and project evidence comes only from the
frozen JSON handoffs. The September package therefore remains readable if a
later preview changes. The preview now derives disclosure-slot counts from
`overview.json` in every aggregate view, so a later edition cannot leave a
stale hard-coded count behind.

## Local acceptance

The browser exercise in `tests/browser/jetp_observatory.py` covers country to
filtered-project to source navigation, country totals and constituent records,
status-only timeline observations, filters, all six byte-exact downloads,
four-country deep links, mobile overflow, local-only requests and errors. Its
keyboard extension checks the skip link, focus transfer to `main`, keyboard
continuation, and an `aria-current="page"` main-navigation marker on deep
country routes.

The focused renderer regression and the release restoration test pass locally.
This environment has no installed Chromium executable, so the Playwright
exercise is retained as a required author-run preview check and is not reported
as passed here.

## Hosting and URL decision

The proposed production shape is static hosting of the *reviewed release
archive's extracted `site/` directory* on a repository-controlled GitHub Pages
or equivalent static origin. It needs no database, DVC route, build-on-request
or raw-source upload. Before a launch, an author must choose the controlled
hostname, review the exact archive and descriptor, run the browser exercise
against that hosted copy, and record the resulting URL and date in a new release
descriptor. The current decision is **no public URL and no deployment**: the
edition remains `prepared`, not published.
