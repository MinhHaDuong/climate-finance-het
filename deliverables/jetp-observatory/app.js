/* Static, release-bound exploration. All text from data is escaped before rendering. */
"use strict";
const main = document.getElementById("main");
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const cleanURL = (value) =>
  /^https?:\/\//i.test(value || "") ? value : "#methods";
const fmt = (n) => new Intl.NumberFormat("en").format(n);
const money = (n, c) =>
  n == null ? "Amount not published" : `${c || ""} ${fmt(Number(n))}`;
const date = (d) =>
  d
    ? new Date(d + (d.length === 10 ? "T12:00:00Z" : "")).toLocaleDateString(
        "en-GB",
        { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" },
      )
    : "Date not established";
const STAGE_COLOURS = {
  Disbursed: "#174936",
  Signed: "#24634f",
  Approved: "#589480",
  "Registered financing": "#99b299",
  Mou: "#d7b46d",
  Announced: "#e2c896",
  Need: "#bc9c7d",
  "Not documented": "#dce0d5",
};
let overview, countries, comparison, editions, evidence, m1a, projects, documentsData, documentIndex, documentsBySha, ontology, partyNames;
const country = (code) => overview.countries.find((c) => c.code === code);
const undisclosedCount = () =>
  overview.countries.reduce((total, c) => total + c.undisclosed, 0);
const sourceLink = (s, label) =>
  s
    ? `<a href="${esc(cleanURL(s.url))}" target="_blank" rel="noopener">${esc(label || s.title)} ↗</a>`
    : "";
const pill = (text) => `<span class="pill">${esc(text)}</span>`;
/* Ticket 0881 (docs/jetp-observatory-presentation.md): the pages are organised
 * by the four objects of docs/jetp-language.md and never name them. The page
 * top is two bars (author, 2026-09-23). The header holds three sections as
 * tabs, each with a dropdown of its pages. Under it, on every page of a
 * section, the section's sub-bar: one component for all three, plain sibling
 * tabs with the current page selected — no separators, no grouping. The
 * paper trail's tabs keep their step codes in data attributes; their order
 * is the trail's, carried by position and explained on #the-paper-trail. A
 * trail page scoped to a country shows it at the bar's right as a removable
 * chip, and every trail tab keeps the country. */
const SECTIONS = {
  "the-paper-trail": ["the-paper-trail", "documents", "entries", "on-the-record", "projects",
    "project", "funding", "whos-who"],
  "the-tallies": ["counts", "comparisons"],
  about: ["about", "glossary", "methods", "who-we-are", "release-history"],
};
/* Where each header tab lands: a section's landing page, or its first page
 * where a landing page would be empty ceremony (The tallies has two). */
const LANDING = { "the-paper-trail": "the-paper-trail", "the-tallies": "counts", about: "about" };
const sectionOf = (page) =>
  Object.keys(SECTIONS).find((section) => SECTIONS[section].includes(page)) || "";
const STEPS = [
  { step: "D1", page: "documents", label: "Documents",
    href: (code) => (code ? `#documents?country=${code}` : "#documents") },
  { step: "D2", page: "entries", label: "Document rows",
    href: (code) => (code ? `#document-rows/${code}` : "#document-rows") },
  { step: "D3", page: "on-the-record", label: "Statements",
    href: (code) => (code ? `#statements/${code}` : "#statements") },
  { step: "D4", page: "projects", label: "Projects",
    href: (code) => (code ? `#projects?country=${code}` : "#projects") },
  { step: "D4", page: "funding", label: "Funding",
    href: (code) => (code ? `#funding/${code}` : "#funding") },
  { step: "D4", page: "whos-who", label: "Organisations",
    href: (code) => (code ? `#organisations?country=${code}` : "#organisations") },
];
const plain = (page, label, extra = {}) => ({ page, label, href: () => "#" + page, ...extra });
/* The pages of each section, in the order its sub-bar and its dropdown list
 * them. The tallies lists only pages with content today; the accounts page of
 * ticket 0877 joins it as "Money". */
const SUB_PAGES = {
  "the-paper-trail": STEPS,
  "the-tallies": [plain("counts", "Counts", { object: "E" }),
    plain("comparisons", "Non-JETP energy operations", { href: () => "#non-jetp-energy-operations" })],
  about: [
    plain("glossary", "Glossary", { object: "O" }),
    plain("methods", "Methods", { object: "methods" }),
    plain("who-we-are", "Who we are"),
  ],
};
/* The page a sub-bar marks as current: a project under Projects, the release
 * history under Methods, which links to it. */
const CURRENT = { project: "projects", "release-history": "methods" };
// Internal page keys stay stable while public addresses follow their labels.
// An internal key is not itself an address, and no earlier address is kept:
// the site was never published (author, 2026-09-24).
const CANONICAL = {
  entries: "document-rows", "on-the-record": "statements",
  "whos-who": "organisations", comparisons: "non-jetp-energy-operations",
};
const INTERNAL = Object.fromEntries(Object.entries(CANONICAL).map(([key, value]) => [value, key]));
// A code the site does not know is no code: the bar falls back to the whole
// site rather than carry an address fragment into an href.
const knownCountry = (code) => (code && overview.countries.some((c) => c.code === code) ? code : "");
function subBar(section, page, rawCode) {
  const current = CURRENT[page] || page;
  const code = section === "the-paper-trail" ? knownCountry(rawCode) : "";
  const tabs = SUB_PAGES[section]
    .map(
      (s) =>
        `<li><a href="${esc(s.href(code))}" data-sub="${s.page}"${s.step ? ` data-step="${s.step}"` : ""}${s.object ? ` data-object="${s.object}"` : ""}${s.page === current ? ' aria-current="page"' : ""}>${esc(s.label)}</a></li>`,
    )
    .join("");
  const chip = code
    ? `<span class="scope-chip">${esc(country(code).name)} <a href="#${esc(CANONICAL[current] || current)}" aria-label="Remove the ${esc(country(code).name)} filter" data-scope-remove="${esc(code)}">×</a></span>`
    : "";
  return `<ul class="sub-tabs" data-sub-bar="${section}">${tabs}</ul>${chip}`;
}
/* One sentence under the title; the rest of the page's explanation, word for
 * word, folded under "About this page". */
function titleBlock(description) {
  const [, lede, rest] = /^(.+?[.!?])\s+(.+)$/s.exec(description) || [null, description, ""];
  return `<p class="lede">${lede}</p>${rest ? `<details class="about"><summary>About this page</summary><p>${rest}</p></details>` : ""}`;
}
/* A number a publisher printed reads "according to" that publisher, with the
 * date the country view carries for the document. */
function according(doc) {
  if (!doc) return "According to a publisher not named in this release";
  return `According to ${esc(doc.publisher || "a publisher not named in this release")}, ${
    doc.date ? date(doc.date) : "undated"
  }`;
}
const documentOf = (code, id) => countries[code]?.sources?.[id];
/* A number the ledger computes is set apart from a number a publisher printed
 * (ticket 0881): it carries its unit and its perimeter, and it links to what
 * it was counted from where the site holds that list. */
function computedMetric(n, unit, perimeter, href, tag = "metric") {
  return `<div class="${tag} computed" data-unit="${esc(unit)}"><strong>${typeof n === "number" ? fmt(n) : esc(n)}</strong><span>${esc(unit)}</span><small><span class="computed-tag">Our calculation</span> · ${esc(perimeter)}${
    href ? ` · <a href="${esc(href)}">See what was counted →</a>` : ""
  }</small></div>`;
}
const countryTabs = (selected) =>
  `<div class="country-tabs">${overview.countries.map((c) => `<a class="${selected === c.code ? "selected" : ""}" href="#funding/${c.code}">${esc(c.name)}</a>`).join("")}</div>`;
const countStages = (rows) =>
  rows.reduce(
    (a, p) => ((a[p.finance_stage] = (a[p.finance_stage] || 0) + 1), a),
    {},
  );
const header = (title, description) =>
  `<div class="page-head"><h1>${title}</h1>${titleBlock(description)}</div>`;
function card(c) {
  return `<article class="country-card" style="--accent:${c.colour}"><span class="country-code">${c.code} · SINCE ${c.signed_on.slice(0, 4)}</span><h3><a href="#funding/${c.code}" style="text-decoration:none">${esc(c.name)}</a></h3><div class="headline published">${esc(c.headline)}</div><p class="detail">${esc(c.headline_detail)}</p><div class="asof"><span class="published-tag">As published</span> ${esc(c.stage_label)} at ${date(c.headline_date)} · ${according(c.headline_source_record)} · ${sourceLink(c.headline_source_record, "Read the document")}</div><div class="card-bottom"><span class="computed" data-unit="named projects"><span class="computed-tag">Our calculation</span> ${c.named} named projects${c.undisclosed ? " + " + c.undisclosed + " unnamed" : ""}</span><a href="#funding/${c.code}" aria-label="Explore ${esc(c.name)}">Explore ↗</a></div></article>`;
}
function stageChart(cs) {
  return `<div role="img" aria-label="Furthest financing milestone on the record, by country. Counts of named projects, not assets or amounts.">${cs
    .map(
      (c) =>
        `<div class="chart-row"><a href="#funding/${c.code}">${esc(c.short)}</a><div class="bar-track">${Object.entries(
          STAGE_COLOURS,
        )
          .map(([s, col]) =>
            c.stages[s]
              ? `<div class="bar-fill" style="width:${(100 * c.stages[s]) / c.named}%;background:${col}" title="${esc(s)}: ${c.stages[s]}"><span class="visually-hidden">${esc(s)}: ${c.stages[s]}</span></div>`
              : "",
          )
          .join("")}</div><span>${c.named}</span></div>`,
    )
    .join("")}</div><div class="legend">${Object.entries(STAGE_COLOURS)
    .filter(([s]) => cs.some((c) => c.stages[s]))
    .map(
      ([s, c]) =>
        `<span><i style="background:${c}"></i>${esc(s === "Not documented" ? "Not coded in ledger" : s)}</span>`,
    )
    .join("")}</div>`;
}
function technologyChart(rows) {
  const counts = {};
  rows.forEach((p) => (counts[p.technology] = (counts[p.technology] || 0) + 1));
  const top = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 7);
  const max = top[0]?.[1] || 1;
  return top
    .map(
      ([n, k]) =>
        `<div class="chart-row"><span title="${esc(n)}">${esc(n.length > 22 ? n.slice(0, 20) + "…" : n)}</span><div class="bar-track"><div class="bar-fill" style="width:${(100 * k) / max}%"></div></div><span>${k}</span></div>`,
    )
    .join("");
}
/* The four counts of the landing page's aside, each counted by
 * us and linked to what it counts. */
function headlineCounts(tag) {
  return [
    computedMetric(projects.length, "named projects", "projects, programmes and components of the four portfolios", "#projects", tag),
    computedMetric(overview.historical_count, "closed World Bank operations", "same four countries, before each partnership", "#non-jetp-energy-operations", tag),
    computedMetric(overview.source_count, "documents cited", "the curated collection the country pages cite", "#documents", tag),
    computedMetric(undisclosedCount(), "unpublished project identities", "counted in the countries' own disclosures", "#funding", tag),
  ].join("");
}
function overviewPage() {
  main.innerHTML = `<section class="hero"><div><p class="eyebrow">From promise to progress</p><h1>Where do the<br><em>JETPs stand?</em></h1><p class="lede">Four partnerships to support a just energy transition. Explore what has been planned, financed and documented — and what remains to be seen.</p><div class="actions"><a class="button" href="#funding">Explore the four partnerships ↗</a><a class="text-link" href="#documents">Follow the paper trail →</a></div></div><aside class="evidence-box"><p class="eyebrow">The tallies</p><div class="stat-grid">${headlineCounts("stat")}</div><div class="box-foot">Documents collected through ${date(overview.provenance.cutoff)}.<br>Each publisher's report keeps its own date. <a href="#counts">The tallies</a> · <a href="#methods">Methods</a></div></aside></section>
<section class="section"><div class="section-head"><div><p class="eyebrow">Country snapshot</p><h2>A shared ambition.<br>Four different trajectories.</h2></div><p>Each national figure is shown as its publisher reported it, with its own date and definition.<br>Allocation, approval and payment are different milestones.</p></div><div class="country-grid">${overview.countries.map(card).join("")}</div></section>
<section class="section"><div class="section-head"><div><p class="eyebrow">Reading across the documents</p><h2>What the documents tell us</h2></div></div><div class="insight-grid"><article class="insight"><span class="number">01</span><h3>Financing moves through different channels</h3><p>South Africa reports substantial allocations; Indonesia identifies approved programmes, investments and grants. Their headline figures measure different milestones, so there is no single comparable “delivery rate”.</p><a class="text-link" href="#funding">Read the four partnerships →</a></article><article class="insight"><span class="number">02</span><h3>A plan is not yet a transaction</h3><p>Senegal's portfolio mixes investment needs, programmes and components. Viet Nam's 2025 portfolio leaves most project identities unnamed. These gaps matter when interpreting totals.</p><a class="text-link" href="#funding/SEN">Explore the Senegal portfolio →</a></article><article class="insight"><span class="number">03</span><h3>Speed needs a historical reference</h3><p>${overview.historical_count} closed energy-related World Bank operations provide context from the same countries. Compare instruments and vintages before interpreting their financing windows as a benchmark.</p><a class="text-link" href="#non-jetp-energy-operations">Browse earlier energy operations →</a></article></div></section>
<section class="section"><div class="section-head"><div><p class="eyebrow">The paper trail</p><h2>Follow a number back to its document</h2></div><p>Start with a project, amount or count and follow its links to the documents behind it.</p></div><ol class="trail-intro">${STEPS.map((step) => `<li><a href="${step.href("")}"><strong>${esc(step.label)}</strong></a> ${esc(STEP_NOTES[step.page])}</li>`).join("")}</ol><p class="note">These pages show different views of the same material; their row counts should not be added together. <a href="#the-paper-trail">See an example →</a></p></section>
<div class="comparison-banner"><div><p class="eyebrow">A longer view</p><h2>Earlier energy<br>operations</h2><p>Browse the historical pool by country, instrument and approval year. See the distribution behind a typical financing window, not just an average.</p></div><div><p class="note">Administrative closure is not a measure of physical completion. This historical pool is descriptive; it does not show what the partnerships caused.</p><a class="button" href="#non-jetp-energy-operations">Explore ${overview.historical_count} closed operations ↗</a></div></div>`;
}
function countriesPage() {
  main.innerHTML =
    header(
      "Financing reported for each partnership",
      "Read each partnership’s published headline alongside the financing statements recorded for its projects and programmes. Financing needs describe money required; pledges, approvals, signatures and payments describe different commitments or events, and their amounts are not added here.",
    ) +
    `<div class="country-grid">${overview.countries.map(card).join("")}</div><section class="section" style="margin-top:35px"><h2>Side by side</h2><div class="table-wrap"><table><thead><tr><th>Country</th><th>Named projects <small class="computed-tag">Our calculation</small></th><th>Unpublished identities <small class="computed-tag">Our calculation</small></th><th>Original pledge</th><th>Announcement</th></tr></thead><tbody>${overview.countries.map((c) => `<tr><td><a href="#funding/${c.code}">${esc(c.name)}</a></td><td><a href="#projects?country=${c.code}">${c.named}</a></td><td>${c.undisclosed}</td><td>${esc(c.pledge_label)}</td><td>${date(c.signed_on)}</td></tr>`).join("")}</tbody></table></div><p class="note" style="margin-top:15px">Original political pledges are context, not committed transactions. Counts include programmes and components; they are not additive counts of power plants.</p></section>`;
}
function markdown(text) {
  return text
    .split(/\n\n+/)
    .map((p) =>
      p.startsWith("## ")
        ? `<h2>${esc(p.slice(3))}</h2>`
        : p.startsWith("# ")
          ? ""
          : `<p>${esc(p.replace(/\n/g, " "))}</p>`,
    )
    .join("");
}
function fundingDate(event) {
  const label = event.date
    ? `Event ${date(event.date)}`
    : event.event_start && event.event_end
      ? `Event between ${date(event.event_start)} and ${date(event.event_end)}`
      : event.observed_date
        ? `Observed as of ${date(event.observed_date)}`
        : event.reported_on
          ? `Document published ${date(event.reported_on)}`
          : "Event date not established";
  return `${esc(label)}<small>${esc(event.date_basis || "Date role not reviewed")}</small>`;
}
function fundingDocument(event, code) {
  const entry = documentIndex[event.source_id];
  const page = pdfPageOf(event.locator);
  const archived = entry && documentHref(entry, page);
  const link = archived
    ? `<a href="${esc(archived)}" target="_blank" rel="noopener">Archived document ↗</a>`
    : sourceLink(documentOf(code, event.source_id), "Publisher's document");
  return `${link || esc(event.source_id)}<small>${esc(event.locator || "No locator recorded")}</small>`;
}
function fundingStatements(data, code) {
  const rows = data.projects.flatMap((project) =>
    project.events.map((event) => ({ ...event, project })),
  );
  const needs = rows.filter((row) => row.status === "Need");
  const financing = rows.filter((row) => row.status !== "Need");
  const table = filterTable("funding-statements", financing, {
    facets: [
      { key: "status", label: "Milestone", all: "All milestones",
        options: [...new Set(financing.map((row) => row.status))].sort() },
      { key: "funder", label: "Funder", all: "All funders",
        options: [...new Set(financing.map((row) => row.funder).filter(Boolean))].sort() },
    ],
    columns: [
      { label: "Project or programme", cell: (row) =>
        `<a href="#project/${encodeURIComponent(row.project.id)}">${esc(row.project.name)}</a>` },
      { label: "Reported milestone", cell: (row) => pill(row.status) },
      { label: "Original amount", cell: (row) => esc(money(row.amount, row.currency)) },
      { label: "Funder · instrument", cell: (row) =>
        esc([row.funder, row.instrument].filter(Boolean).join(" · ") || "Not stated") },
      { label: "Date and its role", cell: fundingDate },
      { label: "Document and location", cell: (row) => fundingDocument(row, code) },
    ],
    empty: "No financing statements match these filters.",
    resultNoun: "financing statements",
    pageSize: 25,
  });
  const needsList = needs.length
    ? `<section class="section"><h2>Financing needs stated in the documents</h2><p>These amounts describe money required, not financing supplied. They are not added to the statements above.</p><ul class="citing">${needs.map((row) =>
      `<li><a href="#project/${encodeURIComponent(row.project.id)}">${esc(row.project.name)}</a> · ${esc(money(row.amount, row.currency))} · ${fundingDate(row)} · ${fundingDocument(row, code)}</li>`
    ).join("")}</ul></section>`
    : "";
  return {
    head: `<section class="section" id="funding-statements"><div class="section-head"><h2>Financing statements in the documents</h2><a class="text-link" href="#projects?country=${code}">Browse all named projects →</a></div><p>Each row reports one milestone for one project or programme. These rows should not be added together: the same amount may appear at several milestones. Amounts stay in the publisher's currency.</p>${table.head}${needsList}</section>`,
    mount: table.mount,
  };
}
function countryPage(code) {
  const d = countries[code],
    c = country(code);
  if (!d) return notFound();
  const refs = Object.keys(d.sources).length;
  const funding = fundingStatements(d, code);
  main.innerHTML = `<div class="page-head"><div class="breadcrumb"><a href="#funding">Funding</a> › ${esc(c.name)}</div><h1>${esc(c.name)}: funding</h1>${titleBlock("Read this partnership's published headline alongside the financing statements recorded for its projects and programmes. Financing needs are listed separately because they describe money required, not money provided.")}${countryTabs(code)}</div><div class="callout published"><h3>${esc(c.headline)}</h3><p><span class="published-tag">As published</span> ${esc(c.stage_label)} at ${date(c.headline_date)} · ${according(c.headline_source_record)} · ${sourceLink(c.headline_source_record, "Read the document")}</p></div><div class="metrics">${computedMetric(c.named, "named projects", "this partnership's portfolio", `#projects?country=${code}`)}${computedMetric(c.undisclosed, "unpublished identities", "counted in the country's own disclosure, which lists none of them by name")}${computedMetric(refs, "documents cited", "by this country's projects and headline", "#documents")}<div class="metric published"><strong>${esc(c.pledge_label)}</strong><span>Original political pledge</span><small><span class="published-tag">As published</span> · announced ${date(c.signed_on)}</small></div></div><div class="split"><div><h2>Reading this partnership</h2><div class="markdown">${markdown(d.editorial)}</div><div class="actions"><a class="button" href="#projects?country=${code}">Browse named projects ↗</a><a class="text-link" href="#non-jetp-energy-operations?country=${code}">Earlier energy operations →</a></div></div><div class="panel"><h3>Furthest financing milestone reported</h3>${stageChart([c])}<p class="note" style="margin-top:20px"><span class="computed-tag">Our calculation</span> Each named project appears once at its furthest recorded milestone. A later milestone does not make an earlier amount a second tranche.</p><h3 style="margin-top:25px">Portfolio composition</h3>${technologyChart(d.projects)}<p class="note" style="margin-top:10px">Named projects by the theme or technology their documents give.</p></div></div>${code === "VNM" ? vietnamSideBySide(d) : ""}${funding.head}`;
  funding.mount();
}
/* Rendering only: both figures already exist — the RMP row count in the M1a
 * manifest and the portfolio record count in the country view — and no field
 * joins them. The two columns are two objects of two dates, shown side by side
 * because that is the recipe of ticket 0834; matching a 2023 position to a 2025
 * record is the matching work of ticket 0833, not this page's. */
function vietnamSideBySide(d) {
  const rmp = m1a.countries.VNM;
  const source = rmp.sublayers[0]?.source_id || "vnm-rmp-2023";
  return `<section class="section" id="vnm-side-by-side" style="margin-top:35px"><div class="section-head"><h2>Two lists, kept apart</h2></div><div class="split"><div class="panel" data-side="rmp-2023"><h3>RMP 2023 initial table</h3><p><strong>${fmt(rmp.row_count)}</strong> positions listed in the annexes of the Resource Mobilisation Plan, document <code>${esc(source)}</code>. <span class="computed-tag">Our calculation</span></p><a class="text-link" href="#document-rows/VNM">Browse the ${fmt(rmp.row_count)} positions →</a></div><div class="panel" data-side="portfolio-2025"><h3>2025 portfolio</h3><p><strong>${fmt(d.record_count)}</strong> projects: ${fmt(d.projects.length)} named and ${fmt(d.undisclosed)} unpublished identities. <span class="computed-tag">Our calculation</span></p><a class="text-link" href="#projects?country=VNM">Browse the named projects →</a></div></div><p class="note" style="margin-top:15px">No link between the 2023 table and the 2025 portfolio is established here: a position in the plan and a project in the portfolio are neither matched nor counted together. Matching them is the work of ticket 0833.</p></section>`;
}
function projectTable(rows) {
  if (!rows.length)
    return '<div class="empty">No projects match these filters.</div>';
  return `<div class="table-wrap"><table><thead><tr><th>Project / programme</th><th>Country</th><th>Theme / technology</th><th>Furthest financing milestone</th><th>Documents</th></tr></thead><tbody>${rows.map((p) => `<tr><td><a href="#project/${encodeURIComponent(p.id)}">${esc(p.name)}</a><small>${esc(p.location)}</small></td><td>${esc(country(p.country).short)}</td><td>${esc(p.technology)}</td><td>${pill(p.finance_stage === "Not documented" ? "Not coded in ledger" : p.finance_stage)}</td><td>${p.sources.length}</td></tr>`).join("")}</tbody></table></div>`;
}
/* A value is a string, or { value, label } where the two differ (a country
 * code and its name, ticket 0853). */
function options(values, selected) {
  return values
    .map((v) => {
      const { value, label } = typeof v === "object" ? v : { value: v, label: v };
      return `<option value="${esc(value)}" ${value === selected ? "selected" : ""}>${esc(label)}</option>`;
    })
    .join("");
}
/* filterTable(id, rows, opts) -> { head, mount }
 *   id            unique DOM id prefix, e.g. "documents"
 *   rows          full unfiltered row array (the caller already scoped the data)
 *   opts.facets   [{ key, label, options, all }] one <select> per facet; a row
 *                 matches when row[facet.key] === the selected value. `options`
 *                 is the caller's already-deduped, sorted value list — strings,
 *                 or { value, label } pairs where the two differ (see
 *                 options()); `all` is the optional label of the unfiltered
 *                 choice. `selected`, optional, is the value chosen when the
 *                 page opens (a country the address names).
 *   opts.search   { placeholder, text(row), label } where text(row) returns the
 *                 lower-cased haystack for the free-text field.
 *   opts.columns  [{ label, cell(row), width }] one <th>/<td> pair each; `cell`
 *                 returns an already-esc()-escaped HTML string. `width`,
 *                 optional, is "short" (a label that must not wrap) or
 *                 "wide" (a column that takes the room the others leave).
 *   opts.empty    message for the `.empty` fallback when no row matches.
 *   opts.resultNoun  plural noun for the count line, e.g. "sources".
 *   opts.pageSize    rows per page; 0 or absent renders every matching row.
 * head: HTML string (filters block + `#<id>-count` aria-live paragraph +
 *   `#<id>-results` div) to splice into main.innerHTML.
 * mount(): call once head is in the DOM. It wires the listeners, resets to
 *   page 1 on every filter change, and renders the first pass.
 *
 * cataloguePage and comparisonPage keep their hand-written filters, and that
 * is settled (ticket 0852, measured once 0836, 0838 and 0839 had made three
 * callers of this API). Of the traits those two pages need, only facet
 * preselection from the URL is shared, and only by the two of them; the
 * others — array membership, a numeric threshold, a negated facet, a summary
 * redrawn on every filter, and above all their own element ids, which the
 * browser recipe asserts — each serve one page. The retrofit that keeps their
 * HTML byte-identical costs this API seven options, most for a single caller,
 * and leaves the two pages longer than they are. Two readable pages beat a
 * component with seven options.
 */
function filterTable(id, rows, opts) {
  const facets = opts.facets || [];
  const pageSize = opts.pageSize || 0;
  let page = 1;
  const searchField = opts.search
    ? `<label class="search">${esc(opts.search.label || opts.search.placeholder)}<input id="${id}-search" type="search" placeholder="${esc(opts.search.placeholder)}"></label>`
    : "";
  const head =
    `<div class="filters" id="${id}-filters">${searchField}${facets
      .map(
        (f) =>
          `<label>${esc(f.label)}<select id="${id}-filter-${f.key}"><option value="">${esc(f.all || "All " + f.label.toLowerCase())}</option>${options(f.options, f.selected)}</select></label>`,
      )
      .join(
        "",
      )}</div><p id="${id}-count" class="result-count" aria-live="polite"></p><div id="${id}-results"></div>`;
  const table = (visible) =>
    `<div class="table-wrap"><table><thead><tr>${opts.columns
      .map((c) => `<th${c.width ? ` class="col-${c.width}"` : ""}>${esc(c.label)}</th>`)
      .join("")}</tr></thead><tbody>${visible
      .map(
        (row) =>
          `<tr>${opts.columns.map((c) => `<td${c.width ? ` class="col-${c.width}"` : ""}>${c.cell(row)}</td>`).join("")}</tr>`,
      )
      .join("")}</tbody></table></div>`;
  const pager = (pages) =>
    pages < 2
      ? ""
      : `<div class="downloads"><button type="button" class="button light" id="${id}-prev"${page === 1 ? " disabled" : ""}>← Previous</button><span>Page ${page} of ${pages}</span><button type="button" class="button light" id="${id}-next"${page === pages ? " disabled" : ""}>Next →</button></div>`;
  const matching = () => {
    const q = opts.search
      ? document.getElementById(id + "-search").value.toLowerCase()
      : "";
    const chosen = facets.map((f) => [
      f,
      document.getElementById(`${id}-filter-${f.key}`).value,
    ]);
    return rows.filter(
      (row) =>
        (!q || opts.search.text(row).includes(q)) &&
        chosen.every(([facet, value]) =>
          !value || (facet.matches ? facet.matches(row, value) : row[facet.key] === value)),
    );
  };
  const draw = () => {
    const filtered = matching();
    const pages = pageSize
      ? Math.max(1, Math.ceil(filtered.length / pageSize))
      : 1;
    if (page > pages) page = pages;
    const visible = pageSize
      ? filtered.slice((page - 1) * pageSize, page * pageSize)
      : filtered;
    document.getElementById(id + "-count").textContent =
      `${filtered.length} of ${rows.length} ${opts.resultNoun}` +
      (pages > 1 ? ` · page ${page} of ${pages}` : "");
    document.getElementById(id + "-results").innerHTML = filtered.length
      ? table(visible) + pager(pages)
      : `<div class="empty">${esc(opts.empty)}</div>`;
    const step = (delta) => () => {
      page += delta;
      draw();
    };
    const prev = document.getElementById(id + "-prev");
    const next = document.getElementById(id + "-next");
    if (prev) prev.addEventListener("click", step(-1));
    if (next) next.addEventListener("click", step(1));
  };
  const mount = () => {
    document
      .querySelectorAll(`#${id}-filters input,#${id}-filters select`)
      .forEach((el) =>
        el.addEventListener(el.tagName === "INPUT" ? "input" : "change", () => {
          page = 1;
          draw();
        }),
      );
    draw();
  };
  return { head, mount };
}
/* Ticket 0915: one site for the local preview and the public one. Every
 * document reference links to the page it was collected from — the address
 * the registry records — with the collection date and the SHA-256 of the
 * bytes read. The archived copy is an extra link, drawn only where this
 * server holds it: which copies it holds is read once, at load, from
 * documents/index.json, which `make jetp-observatory-documents` writes beside
 * the staged copies. documents/ is untracked, so the public bundle (the
 * tracked tree) cannot carry the index, and its pages cannot draw a link to
 * a copy they do not serve. No flag, no second build: the data decides. */
let stagedCopies = new Set();
const archiveServed = (entry) => Boolean(entry?.local_path && stagedCopies.has(entry.local_path));
const documentHref = (entry, page) =>
  archiveServed(entry) ? entry.local_path + (page ? "#page=" + page : "") : null;
const ORIGIN = /^https?:\/\/([^/?#]+)/i;
const hostOf = (url) => (ORIGIN.exec(url || "") || [])[1] || "";
/* A PDF page travels to the origin only when the origin served a PDF — the
 * content type the collector recorded, or a .pdf path where it recorded none
 * — since a fragment on an HTML page names nothing. */
const originIsPdf = (entry) =>
  /pdf/i.test(entry.content_type || "") || /\.pdf$/i.test((entry.url || "").split(/[?#]/)[0]);
function publisherHref(entry, page) {
  if (!ORIGIN.test(entry?.url || "")) return null;
  const base = entry.url.split("#")[0];
  return page && originIsPdf(entry) ? base + "#page=" + page : base;
}
function publisherLink(entry, page, attrs = "", label) {
  const href = publisherHref(entry, page);
  return href
    ? `<a href="${esc(href)}"${attrs} data-link="publisher" target="_blank" rel="noopener">${label || "Publisher's page — " + esc(hostOf(entry.url))} ↗</a>`
    : `<span class="note"${attrs} data-link="publisher">No publisher address recorded</span>`;
}
function archivedLink(entry, page, attrs = "", label = "Open archived copy") {
  const href = documentHref(entry, page);
  return href
    ? `<a href="${esc(href)}"${attrs} data-link="archived" target="_blank" rel="noopener">${esc(label)} ↗</a>`
    : "";
}
/* Ticket 0925: publisher pages rot. Two tables of their own, served beside
 * the registry and joined to it here on the address the registry records
 * (the entry's `url`): the Web Archive copy of that address
 * (data/web-archive.json, from data/jetp/web-archive-captures.csv) and the
 * last check of it (data/publisher-links.json, from
 * data/jetp/publisher-link-checks.csv). Either may be missing or empty; a
 * page then shows no copy and no dead link. The origin address is never
 * rewritten: a dead publisher link stays the link we collected from, placed
 * after the copy and marked with the date it was first found dead. */
let webArchive = {};
let linkChecks = {};
const indexBy = (rows, key) => Object.fromEntries((rows || []).map((row) => [row[key], row]));
const webArchiveOf = (entry) => {
  const capture = webArchive[entry?.url];
  return capture?.capture_url && ["captured", "reused"].includes(capture.outcome) ? capture : null;
};
const deadSince = (entry) => {
  const check = linkChecks[entry?.url];
  return check?.outcome === "dead" ? check.dead_since || (check.checked_at || "").slice(0, 10) : null;
};
/* A PDF opens as the archived bytes themselves (Wayback's id_ form), at the
 * page, so its SHA-256 can be compared with ours; a web page opens in the
 * Wayback replay, which rewrites it and so is never byte-identical. */
const WAYBACK_STAMP = /\/web\/([0-9]{14})\//;
function webArchiveHref(entry, page) {
  const capture = webArchiveOf(entry);
  if (!capture) return null;
  if (!originIsPdf(entry)) return capture.capture_url;
  return capture.capture_url.replace(WAYBACK_STAMP, "/web/$1id_/") + (page ? "#page=" + page : "");
}
/* A reference that pins no fingerprint (a ledger row with none, resolved by
 * source id for the publisher's link only) has no SHA-256 to compare with,
 * and must not claim one. */
const identityKind = (entry) =>
  !originIsPdf(entry) ? "html" : entry.sha256 ? "pdf" : "pdf-unpinned";
const IDENTITY_NOTES = {
  pdf: "Our SHA-256 lets you check that the Web Archive copy is the same file we read.",
  "pdf-unpinned": "No fingerprint is recorded here to check the Web Archive copy against.",
  html: "A Web Archive capture of a web page is not byte-identical to what we read.",
};
const identityNote = (entry) => IDENTITY_NOTES[identityKind(entry)];
/* The same, short enough to sit on the link's line: a Documents row has a
 * fixed height budget (PR #1459), which a sentence per row broke. */
const IDENTITY_SHORT = {
  pdf: "same file? compare the SHA-256",
  "pdf-unpinned": "no fingerprint to compare",
  html: "not byte-identical",
};
function webArchiveLink(entry, page, attrs = "", label) {
  const href = webArchiveHref(entry, page);
  if (!href) return "";
  const when = (webArchiveOf(entry).captured_at || "").slice(0, 10);
  return `<a href="${esc(href)}"${attrs} data-link="web-archive" title="${esc(identityNote(entry))}" target="_blank" rel="noopener">${esc(label || "Web Archive copy — " + date(when))} ↗</a>`;
}
function deadNote(entry) {
  const since = deadSince(entry);
  return since
    ? ` <span class="note dead-link" data-dead-since="${esc(since)}">publisher link dead since ${esc(date(since))}</span>`
    : "";
}
/* The publisher's page and its Web Archive copy side by side, the copy first
 * once the publisher's link is dead. */
function sourceLinks(entry, page, attrs = "", publisherLabel, archiveLabel) {
  const publisher = publisherLink(entry, page, attrs, publisherLabel) + deadNote(entry);
  const link = webArchiveLink(entry, page, attrs, archiveLabel);
  if (!link) return publisher;
  const copy = `${link} ${identityMark(entry)}`;
  return deadSince(entry) ? `${copy} · ${publisher}` : `${publisher} · ${copy}`;
}
/* Said beside every Web Archive copy: what it can prove, by type. */
const identityMark = (entry) =>
  `<span class="note" data-identity="${identityKind(entry)}" title="${esc(identityNote(entry))}">(${esc(IDENTITY_SHORT[identityKind(entry)])})</span>`;
/* Ticket 1210 (author's decision, 2026-09-25): documents.json keeps one row
 * per retrieval attempt, and the Documents page one row per document — its
 * best attempt: the latest collected one if any, otherwise the latest — with
 * every attempt listed under a fold. Grouped here, at read time: the served
 * table stays the retrievals as recorded. Time order is the retrieval time,
 * then the attempt number (row keys are not always in time order). */
const attemptNumber = (entry) => Number(entry.row_key.slice(entry.row_key.lastIndexOf(":") + 1));
const attemptOrder = (a, b) =>
  (a.collected_on || "").localeCompare(b.collected_on || "") || attemptNumber(a) - attemptNumber(b);
function documentRows(entries) {
  const byId = new Map();
  entries.forEach((entry) => {
    if (!byId.has(entry.id)) byId.set(entry.id, []);
    byId.get(entry.id).push(entry);
  });
  return [...byId.values()].map((attempts) => {
    attempts.sort(attemptOrder);
    const collected = attempts.filter((a) => a.status === "collected");
    return { ...(collected.length ? collected : attempts).at(-1), attempts };
  });
}
/* One attempt in a word or a status code, and its time to the minute (UTC). */
const HTTP_CODE = /^HTTP ([0-9]{3})\b/;
function attemptOutcome(entry) {
  if (entry.status === "collected") return "collected";
  const code = HTTP_CODE.exec(entry.error || "");
  if (code) return code[1];
  if (entry.error) return entry.error.split(":")[0].trim().slice(0, 24);
  return (entry.status || "outcome not recorded").replaceAll("_", " ");
}
const attemptTime = (entry, year) =>
  entry.collected_on
    ? new Date(entry.collected_on).toLocaleDateString("en-GB", {
        day: "numeric", month: "short", timeZone: "UTC", ...(year ? { year: "numeric" } : {}),
      }) + " " + entry.collected_on.slice(11, 16)
    : "date not recorded";
function attemptsFold(doc) {
  if (doc.attempts.length < 2) return "";
  const summary = `${doc.attempts.length} attempts: ` +
    doc.attempts.map((a) => `${attemptOutcome(a)} on ${attemptTime(a)}`).join(", ");
  const item = (a) => {
    const method = collectionMethod(a);
    const read = a.sha256
      ? `SHA-256 <code title="${esc(a.sha256)}">${esc(a.sha256.slice(0, 12))}…</code>`
      : collectionFailure(a.error);
    return `<li data-attempt="${esc(a.row_key)}">${esc(attemptTime(a, true))} UTC · ${esc((a.status || "").replaceAll("_", " "))} · ${read}${method ? " · " + esc(method) : ""}</li>`;
  };
  return `<details class="attempts" data-attempts="${doc.attempts.length}"><summary>${esc(summary)}</summary><ul class="citing">${doc.attempts.map(item).join("")}</ul></details>`;
}
/* What was read, and when: the collection date and the fingerprint of the
 * bytes, or the failure the collector recorded where no bytes were kept. */
/* How the bytes were sought (ticket 0926): the registry's collection_method,
 * in words. */
const COLLECTION_METHODS = {
  script: "by the collector",
  "browser-session": "through the author's browser session",
  "browser-manual": "saved by hand in a browser",
  "local-record": "research record written here",
};
const collectionMethod = (entry) =>
  COLLECTION_METHODS[entry.collection_method] || entry.collection_method || "";
function collectedFacts(entry, separator = " · ") {
  const method = collectionMethod(entry);
  const when = (entry.collected_on ? "Collected " + date(entry.collected_on.slice(0, 10)) : "Collection date not recorded") +
    (method ? ` <span data-collection-method="${esc(entry.collection_method)}">${esc(method)}</span>` : "");
  return entry.sha256
    ? `${when}${separator}SHA-256 <code data-sha256="${esc(entry.sha256)}" title="${esc(entry.sha256)}">${esc(entry.sha256.slice(0, 12))}…</code>`
    : `${when}${separator}${collectionFailure(entry.error)}`;
}
/* Hand-written port of scripts/jetp/_m1a_document_links.py. The two are kept in
 * step by tests/test_jetp_observatory_inventories.py, never generated from one
 * another. The Viet Nam and Senegal locators publish a PDF page (Senegal's
 * since ticket 0861), and Viet Nam's publish three numbers — PDF page, printed
 * page, ordinal — so the pattern is anchored
 * on its own label rather than on "the first number in the string". [0-9]
 * rather than \d, which is ASCII-only here and every Unicode decimal in
 * Python: the two would read an OCR'd fullwidth digit differently. */
const PDF_PAGE = /PDF pages? ([0-9]+)/;
/* Ticket 0853: one source id can carry several collection attempts. A row link
 * has to open one file, so the archived, collected attempt wins; where nothing
 * was archived, the first attempt is kept so the id still resolves and the page
 * can show what the collection recorded instead. */
const collectionRank = (entry) =>
  entry.local_path ? (entry.status === "collected" ? 2 : 1) : 0;
/* One tie-break, keyed either way: an inventory row addresses a document by
 * source id, a ledger observation by the fingerprint build_observations.py
 * already resolved. A falsy key is skipped rather than indexed, so a document
 * with no sha256 recorded cannot collide under a shared "" key. */
function indexDocumentsBy(entries, keyOf) {
  const index = {};
  entries.forEach((entry) => {
    const key = keyOf(entry);
    if (!key) return;
    const kept = index[key];
    if (!kept || collectionRank(entry) > collectionRank(kept)) index[key] = entry;
  });
  return index;
}
function indexDocuments(entries) {
  return indexDocumentsBy(entries, (entry) => entry.id);
}
/* The ledger observations arrive with the fingerprint already resolved by
 * scripts/jetp/build_observations.py, so they address a document by sha256
 * where an inventory row addresses it by source id. One pass at load time
 * rather than a scan of the registry per rendered row. */
function indexDocumentsBySha256(entries) {
  return indexDocumentsBy(entries, (entry) => entry.sha256);
}
/* Returns null where the Python raises: a renderer cannot abort a page over one
 * row, so an unresolved id degrades to its locator text. */
const pdfPageOf = (locator) => {
  const match = PDF_PAGE.exec(locator || "");
  return match ? Number(match[1]) : null;
};
function resolveDocumentLink(sourceId, locator, registry) {
  const entry = registry[sourceId];
  if (!entry) return null;
  return {
    sha256: entry.sha256,
    pdf_page: pdfPageOf(locator),
    local_path: entry.local_path,
  };
}
const byteSize = (n) =>
  n == null
    ? "Not recorded"
    : n >= 1e6
      ? (n / 1e6).toFixed(1) + " MB"
      : Math.max(1, Math.round(n / 1000)) + " kB";
/* The climb, document → what cites it, is a join made here at read time
 * (ticket 0858; author's decision of 2026-09-22: one served file is one
 * table). documents.json names nothing a source yielded. The rows live in the
 * views that serve them — m1a/<CODE>.json and observations/<CODE>.json,
 * loaded once per country and filtered on source_id — and the facts in the
 * country views and reviewed-evidence.json, in memory since start(), filtered
 * on their sources and their proofs. Two stage-two products and two kinds of
 * fact, four filters, never a total across any of them; a source nothing
 * cites is rendered as that statement, never as an empty list dressed as one.
 * Until 0858 the generator wrote this join into documents.json as
 * `by_source_id`, 874 kB that grew with every collection and that every
 * route loaded; the pre-commit's file ceiling refused it. */
/* Ticket 0857: an M1a position links to its own inventory row — ?row=N is the
 * row's rank in the export the inventory page loads, the rank the join gives
 * it — and, where its locator names a PDF page, to that page of the archived
 * copy, read by the same port the inventory page reads the same rows with. A
 * ledger row gets the same page link when it carries one. No page named, no
 * link: an absent page is not page 1. */
function extractedPageLink(row, entry, key) {
  if (!row.pdf_page) return "";
  const attrs = ` data-extracted-page="${esc(key)}"`;
  const archived = archivedLink(entry, row.pdf_page, attrs, "archived copy");
  return ` · PDF page ${Number(row.pdf_page)}: ${sourceLinks(entry, row.pdf_page, attrs, "publisher's page", "Web Archive copy")}${archived ? " · " + archived : ""}`;
}
function extractedItem(row, entry) {
  if (row.product === "m1a")
    return `<li><a href="#document-rows/${esc(row.country)}?row=${Number(row.row)}"><code>${esc(row.source_row_id)}</code></a> ${esc(row.label || "Identity not published")}${extractedPageLink(row, entry, row.source_row_id)}<small>${esc(row.source_layer)} · ${esc(row.evidence_locator || "No locator recorded")}</small></li>`;
  return `<li><a href="#document-rows/${esc(row.country)}">${esc(OBSERVATION_KINDS[row.kind] || row.kind)} <code>${esc(row.id)}</code></a> · ${pill(row.verification)}${extractedPageLink(row, entry, row.id)}<small>${esc(row.table)} · <a href="#project/${encodeURIComponent(row.project_id)}">${esc(row.project_id)}</a> · ${esc(row.locator || "No locator recorded")}</small></li>`;
}
function factItem(fact) {
  return fact.record_id
    ? `<li><a href="#statements">${esc(fact.label)}</a><small>Reviewed item on the record · ${esc(fact.status.replaceAll("_", " "))} · ${esc(country(fact.country)?.short || fact.country)}</small></li>`
    : `<li><a href="#project/${encodeURIComponent(fact.project_id)}">${esc(fact.name)}</a><small>Named project · ${esc(country(fact.country)?.short || fact.country)}</small></li>`;
}
function foldout(label, items, item, key, none, attrs = "") {
  return `<details class="foldout"${attrs} data-${key}-count="${items.length}"><summary>${esc(label)} · ${fmt(items.length)}</summary>${items.length ? `<ul class="citing">${items.map(item).join("")}</ul>` : `<p class="note">${esc(none)}</p>`}</details>`;
}
/* One sentence where a list has nothing to show, in place of the list: the
 * same shape wherever a fold-out's source is empty, carrying the data
 * attribute a test or the browser recipe reads. The body is HTML the caller
 * has already escaped, since some notes carry a link. */
function emptyNote(key, value, html) {
  return `<p class="note" data-${key}="${esc(value)}">${html}</p>`;
}
/* Ticket 0856: one fold-out per stage-two product, each with its own count in
 * its own summary. A ledger row and an M1a row can describe the same paragraph
 * of the same file, so "Extracted here · 514" for the ZAF register — 257 of
 * each — was the sum this site forbids everywhere else. A product the document
 * has no row of gets no fold-out, not an empty one; a product this table does
 * not name is still listed, under its own name, rather than dropped. A source
 * nothing was extracted from (55 in this edition, cited by facts only) gets
 * one sentence and no fold-out at all — an empty list is still a list, and
 * this site never fabricates one (author's decision, 2026-09-22, PR #1439). */
const PRODUCT_LABELS = { ledger: "Statements", m1a: "Document rows" };
function extractedFoldouts(extracted, entry) {
  const products = [...new Set(extracted.map((row) => row.product))];
  if (!products.length)
    return emptyNote("extracted-count", 0, "Nothing was extracted from this document in this release.");
  return products
    .map((product) =>
      foldout(PRODUCT_LABELS[product] || product,
        extracted.filter((row) => row.product === product),
        (row) => extractedItem(row, entry), "extracted", "",
        ` data-extracted-product="${esc(product)}"`))
    .join("");
}
/* Port of the rule ticket 0857 wrote in the generator: each product's first
 * page is the lowest its rows name, and the file gets one only when every
 * product that names a page starts at the same one. A ledger reading that
 * starts at page 12 beside an M1a reading that starts at page 30 names no
 * first page. Rows naming no page are silent, not zero: no page comes from
 * nowhere. */
function firstPdfPage(extracted) {
  const starts = {};
  extracted.forEach((row) => {
    if (row.pdf_page)
      starts[row.product] = Math.min(starts[row.product] ?? row.pdf_page, row.pdf_page);
  });
  const firsts = new Set(Object.values(starts));
  return firsts.size === 1 ? [...firsts][0] : null;
}
/* The rows one source yielded, ledger first, each in its own view's shape
 * plus what the fold-out addresses it by: `product`; for an M1a row its rank
 * in the export and the page its locator names, null when it names none; for
 * a ledger row the key its table gave it (its page it already carries). No
 * value is recoded, no row is copied that the filter did not select. */
function extractedRows(sourceId, { rows, observations }) {
  const ledger = observations
    .filter((row) => row.source_id === sourceId)
    .map((row) => ({ ...row, product: "ledger", id: observationId(row) }));
  const positions = rows.flatMap((row, i) =>
    row.source_id === sourceId
      ? [{ ...row, product: "m1a", row: i + 1, pdf_page: pdfPageOf(row.evidence_locator) }]
      : []);
  return [...ledger, ...positions];
}
/* The facts relying on one source: every named record whose sources name it,
 * then every reviewed record one of whose proofs names it. A record is one
 * fact however many of its proofs cite the same file. */
function factsRelyingOn(sourceId) {
  const named = projects
    .filter((p) => p.sources.includes(sourceId))
    .map((p) => ({ project_id: p.id, name: p.name, country: p.country }));
  const reviewed = (evidence.records || [])
    .filter((record) => record.evidence.some((proof) => proof.source_id === sourceId))
    .map((record) => ({ record_id: record.id, label: record.label,
      country: record.country, status: record.status }));
  return [...named, ...reviewed];
}
const documentAttrs = (entry) => ` data-document-id="${esc(entry.row_key)}"`;
/* Drawn with the page as a placeholder, filled once the attempt's country has
 * its two stage-two views — one load per country per session, shared with
 * the inventory page — so a reader filtering one country loads that
 * country's rows and no other's. Filled by id: when the reader has moved on,
 * the placeholder is gone and nothing is written. The archived copy's link is
 * refilled with the first page the rows agree on, where the snapshot holds a
 * copy and the rows name one (ticket 0857): the fold-outs land after it, so
 * a reader who sees them sees the page too. */
function extractionCell(entry) {
  const key = "extraction-" + entry.row_key;
  stageTwo(entry.country)
    .then((views) => {
      const cell = document.getElementById(key);
      if (!cell) return;
      const extracted = extractedRows(entry.id, views);
      const relying = factsRelyingOn(entry.id);
      const page = firstPdfPage(extracted);
      const publisher = document.getElementById("publisher-" + entry.row_key);
      const archived = document.getElementById("archived-" + entry.row_key);
      if (page && publisher) publisher.innerHTML = sourceLinks(entry, page, documentAttrs(entry));
      if (page && archived) archived.innerHTML = archivedLink(entry, page, documentAttrs(entry));
      cell.innerHTML =
        !extracted.length && !relying.length
          ? `<span class="note" data-uncited="${esc(entry.id)}">Nothing was extracted from this document, and nothing on these pages relies on it, in this release.</span>`
          : extractedFoldouts(extracted, entry) +
            foldout("Projects and items relying on it", relying, factItem, "facts",
              "Nothing relies on this document in this release.");
    })
    .catch((error) => {
      const cell = document.getElementById(key);
      if (cell)
        cell.innerHTML = emptyNote("extracted-count", "unavailable", `The ${esc(entry.country)} entries and items on the record could not load (${esc(error.message)}). What this document yielded is in the <a href="#document-rows/${esc(entry.country)}">${esc(entry.country)} entries</a>, under <code>${esc(entry.id)}</code>.`);
    });
  return `<span id="${esc(key)}" class="note">Loading what this document yielded…</span>`;
}
/* A failed collection attempt as a short label — "HTTP 403", "SSLError" —
 * with the whole message the collector recorded in its title. The messages
 * run to 300 characters of host names and URLs, which broke mid-token and
 * set the Documents rows' height (PR #1459, author's cold read). */
function collectionFailure(error) {
  if (!error) return '<span class="note">No copy collected</span>';
  const short = error.split(":")[0].trim().slice(0, 24);
  return `<span class="note" data-collection-error title="${esc(error)}">${esc(short)}</span>`;
}
function documentsPage(params) {
  // One row per document, on its best attempt (ticket 1210): the facets, the
  // search and the count all read that attempt, so they count documents.
  const rows = documentRows(documentsData.documents);
  const values = (key) =>
    [...new Set(rows.map((r) => r[key]).filter(Boolean))].sort();
  // Both links open at the file's own first page until the join says
  // otherwise: each sits in a placeholder extractionCell() refills with the
  // first page the extracted rows agree on (ticket 0857), never with a page
  // of its own. The publisher's page is always there; the archived copy only
  // where this server holds it (ticket 0915).
  const links = (r) =>
    `<span id="publisher-${esc(r.row_key)}">${sourceLinks(r, null, documentAttrs(r))}</span><small>${collectedFacts(r, "<br>")}</small><span id="archived-${esc(r.row_key)}">${archivedLink(r, null, documentAttrs(r))}</span>${attemptsFold(r)}`;
  const table = filterTable("documents", rows, {
    facets: [
      {
        key: "country",
        label: "Country",
        all: "All four countries",
        // Names, as cataloguePage shows them; the value stays the code the
        // row carries (ticket 0853).
        options: overview.countries
          .filter((c) => rows.some((r) => r.country === c.code))
          .map((c) => ({ value: c.code, label: c.name })),
        selected: knownCountry(params.get("country")),
      },
      {
        key: "status",
        label: "Collection status",
        all: "All collection outcomes",
        options: values("status"),
      },
      {
        key: "collection_method",
        label: "Collection method",
        all: "All collection methods",
        options: values("collection_method").map((value) => ({
          value, label: COLLECTION_METHODS[value] || value })),
      },
      {
        key: "content_type",
        label: "Content type",
        all: "All content types",
        options: values("content_type"),
      },
    ],
    search: {
      label: "Search document identifiers and addresses",
      placeholder: "Try jet-investment-register, .pdf…",
      text: (r) => (r.id + " " + (r.url || "")).toLowerCase(),
    },
    columns: [
      { label: "Document", cell: (r) => `<code>${esc(r.id)}</code>` },
      {
        label: "Country",
        cell: (r) => esc(country(r.country)?.short || r.country),
      },
      { label: "Collection", cell: (r) => pill(r.status) },
      { label: "Content type", cell: (r) => esc(r.content_type || "Not recorded") },
      { label: "Size", cell: (r) => esc(byteSize(r.size_bytes)), width: "short" },
      { label: "Publisher's page · what we read", cell: links },
      { label: "Document rows and statements · relied on by", cell: extractionCell, width: "wide" },
    ],
    empty: "No documents match these filters.",
    resultNoun: "documents",
    pageSize: 50,
  });
  main.innerHTML =
    header(
      "Reports, plans and registers",
      "See which publications we sought, who issued them, when we tried to retrieve them, and whether an archived copy is available. Inclusion here does not endorse everything a publication says; failed attempts remain visible.",
    ) +
    copiesCallout() +
    table.head +
    `<div class="downloads"><a class="button light" href="data/documents.json" download>Download the collection registry ↓</a></div>`;
  table.mount();
}
/* The five facets wired here are the ones every country's inventory carries.
 * Everything else a row holds — the ZAF register's pass-through raw_ columns
 * included — is shown in the row detail, in the order the generator wrote it,
 * so a widened export needs no change here. */
const INVENTORY_FACETS = [
  ["source_layer", "Document extract", "All extracts"],
  ["record_type", "Entry type", "All entry types"],
  ["reported_status", "Reported status", "All reported statuses"],
  ["identity_status", "Identity", "All identity outcomes"],
];
/* One load per key per session. A rejected load is dropped from the cache so a
 * transient failure is retried on the next visit, not replayed for the rest
 * of the session. */
function cached(cache, key, make) {
  if (!cache[key])
    cache[key] = make().catch((error) => {
      delete cache[key];
      throw error;
    });
  return cache[key];
}
/* One load per country per session, shared by the Observations tab and every
 * project page of that country (ticket 0855): the ledger rows are served once,
 * in observations/<CODE>.json, and a fact's fold-out is a filter on them. */
const observationsCache = {};
const observationsView = (code) =>
  cached(observationsCache, code, () => load("observations/" + code));
/* The companion file carries the column names once and then one array of
 * values per row, so the row objects are rebuilt here in the generator's own
 * column order — pass-through columns included. */
const inventoryRows = (payload) =>
  payload.rows.map((values) =>
    Object.fromEntries(payload.fields.map((field, i) => [field, values[i]])),
  );
/* Both stage-two views of one country, loaded once per session and shared by
 * the inventory page and the Documents page's fold-outs (ticket 0858): the
 * M1a export rebuilt into row objects once, in export order, beside the
 * ledger observations. */
const stageTwoCache = {};
const stageTwo = (code) =>
  cached(stageTwoCache, code, () =>
    Promise.all([load("m1a/" + code), observationsView(code)]).then(
      ([payload, observations]) => ({ rows: inventoryRows(payload), observations }),
    ),
  );
function inventoryUnknowns(details) {
  return (
    `<div class="metrics">${details.sublayers
      .map(
        (layer) =>
          `<div class="metric computed" data-unit="entries"><strong>${fmt(layer.row_count)}</strong><span>${esc(layer.sublayer_id)}</span><small><span class="computed-tag">Our calculation</span> · entries of this extract<br>${esc(layer.edition)} · cutoff ${esc(layer.cutoff)}<br>${fmt(layer.unknowns.field_values)} unknown field values · ${fmt(layer.unknowns.identity_rows)} unknown identities · ${fmt(layer.unknowns.unavailable_source_rows)} rows unavailable at the publisher</small></div>`,
      )
      .join("")}</div>` +
    `<p class="note">Each figure counts one extract of this country's documents. The count line under the filters is the size of this export, the extracts laid end to end: it says how many rows the file holds, not how many projects the country has, because the extracts overlap and count different things, and a country is not the unit any of them measures.</p>`
  );
}
/* Link only HTTP(S) URLs inside a document's description. Every other byte is
 * escaped as text; a malformed URL remains text rather than becoming markup. */
function linkedDescription(value) {
  const source = String(value);
  const pattern = /\bhttps?:\/\/[^\s<>"']+/gi;
  let result = "", last = 0;
  for (const match of source.matchAll(pattern)) {
    result += esc(source.slice(last, match.index));
    const raw = match[0];
    const urlText = raw.replace(/[.,;:!?)}\]]+$/, "");
    const trailing = raw.slice(urlText.length);
    let href = null;
    try {
      const parsed = new URL(urlText);
      if (["http:", "https:"].includes(parsed.protocol) && parsed.hostname) href = parsed.href;
    } catch { /* Keep the printed text when the URL is malformed. */ }
    result += href
      ? `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(urlText)}</a>${esc(trailing)}`
      : esc(raw);
    last = match.index + raw.length;
  }
  return result + esc(source.slice(last));
}
/* A row's own fields, listed under whichever summary its caller names — an
 * inventory row and a ledger observation share every column but the label. */
function rowDetail(row, summary, open) {
  return `<details${open ? " open" : ""}><summary>${summary}</summary><dl class="facts">${Object.entries(
    row,
  )
    .map(
      ([key, value]) =>
        `<dt>${esc(key)}</dt><dd>${
          value === "" || value == null ? "Not published" : key === "raw_project_description"
            ? linkedDescription(value) : FIELD_TERMS[key] ? FIELD_TERMS[key](value) : esc(value)
        }</dd>`,
    )
    .join("")}</dl></details>`;
}
function inventoryRowDetail(row, open) {
  return rowDetail(row, esc(row.label || "Identity not published"), open);
}
/* One evidence cell for every stage-two table: the locator as text, then the
 * document's page on the publisher's site — at the PDF page, where the
 * locator names one and the origin is a PDF — with what was collected, and
 * the archived copy where this server holds it (ticket 0915). The callers
 * differ only in how they find the document entry and what they say when
 * there is none. */
function evidenceLink(locator, entry, pdfPage, dataAttr, dataValue, noEntry) {
  const text = esc(locator || "No locator recorded") + (pdfPage ? " · PDF page " + Number(pdfPage) : "");
  if (!entry)
    return `<span class="note">${text}${noEntry ? "<br>" + noEntry : ""}</span>`;
  const attrs = ` ${dataAttr}="${esc(dataValue)}"`;
  const archived = archivedLink(entry, pdfPage, attrs, "archived copy");
  return `<span class="document-ref">${text}<br>${sourceLinks(entry, pdfPage, attrs)}${archived ? " · " + archived : ""}<small>${collectedFacts(entry)}</small></span>`;
}
function inventoryEvidence(row) {
  const entry = documentIndex[row.source_id];
  const pdfPage = entry
    ? resolveDocumentLink(row.source_id, row.evidence_locator, documentIndex).pdf_page
    : null;
  return evidenceLink(
    row.evidence_locator,
    entry,
    pdfPage,
    "data-inventory-row",
    row.source_row_id,
    "",
  );
}
/* The second stage-two product: the ledger rows analysts wrote from the same
 * documents, under a different schema. The three tables keep their own names,
 * the ones data/jetp uses, rather than a display vocabulary invented here. */
const OBSERVATION_TABLES = [
  "events",
  "implementation-events",
  "project-source-links",
];
const OBSERVATION_KINDS = {
  financial_event: "Financial event",
  implementation_event: "Implementation event",
  project_source_link: "Project–document link",
};
/* Each table names its rows with its own key. */
const observationId = (row) =>
  row.event_id || row.implementation_event_id || row.link_id || "";
/* Counted from the rows this tab serves, never from a stored total: a head
 * count that can drift from the table below it is a claim, not a summary. */
const observationCounts = (rows) =>
  OBSERVATION_TABLES.map((table) => ({
    table,
    count: rows.filter((row) => row.table === table).length,
  }));
function observationTotals(rows, code) {
  const c = country(code);
  return (
    `<div class="metrics">${observationCounts(rows)
      .map(
        ({ table, count }) =>
          `<div class="metric computed" data-unit="items on the record" data-observation-table="${esc(table)}"><strong>${fmt(count)}</strong><span>${esc(table)}</span><small><span class="computed-tag">Our calculation</span> · items recorded for ${esc(c?.short || code)}</small></div>`,
      )
      .join("")}</div>` +
    `<p class="note">Document rows and statements are two readings of some of the same publications. A row may support several statements, and statements may come from prose; their counts are never added together. Legacy event rows without a precise cited line are held for review and do not appear as observations here.</p>`
  );
}
function observationDetail(row) {
  return rowDetail(
    row,
    `${esc(OBSERVATION_KINDS[row.kind] || row.kind)} · ${esc(observationId(row))}`,
  );
}
/* The fingerprint is resolved once, in the generator, so the row addresses its
 * document directly. A document the collection never archived keeps its locator
 * as text, exactly as an unresolved inventory row does. */
/* A row whose document was never collected has no fingerprint; it still
 * reaches the publisher's page through its source identifier, but pins no
 * bytes, so it shows no other attempt's fingerprint or archived copy. */
const unpinned = (entry) => entry && { ...entry, sha256: null, local_path: null };
function observationEvidence(row) {
  return evidenceLink(
    row.locator,
    row.sha256 ? documentsBySha[row.sha256] : unpinned(documentIndex[row.source_id]),
    row.pdf_page,
    "data-observation-id",
    observationId(row),
    "This document is not in the collection registry",
  );
}
/* A facet's option list is the values a column actually carries, sorted and
 * deduplicated: shared by every table's facet setup rather than closed over
 * each one's own `rows` afresh. */
const distinctValues = (rows, key) =>
  [...new Set(rows.map((row) => row[key]).filter(Boolean))].sort();
function observationsTable(rows) {
  const values = (key) => distinctValues(rows, key);
  return filterTable("observations", rows, {
    facets: [
      {
        key: "table",
        label: "Ledger table",
        all: "All three tables",
        options: values("table"),
      },
      {
        key: "kind",
        label: "Kind",
        all: "All kinds",
        options: values("kind"),
      },
      // Only the financial events publish a funder. The other two tables have
      // no such column, so their rows carry no such key and can never match a
      // chosen funder — which is the honest answer: the ledger does not record
      // one for them, and inventing a blank would make the absence look like a
      // value.
      {
        key: "funder",
        label: "Funder",
        all: "All funders",
        options: values("funder"),
      },
      {
        key: "verification",
        label: "Verification state",
        all: "All verification states",
        options: values("verification"),
      },
    ],
    search: {
      // The notes, the locator and the source identifier, because that is
      // where a row names things no column holds: the Viet Nam link rows name
      // their funder only inside the source identifier.
      label: "Search notes, locators and document identifiers",
      placeholder: "Try eib, Annex, Bac Ai…",
      text: (row) =>
        (
          (row.notes || "") +
          " " +
          (row.locator || "") +
          " " +
          (row.source_id || "")
        ).toLowerCase(),
    },
    columns: [
      { label: "Table", cell: (row) => esc(row.table) },
      { label: "Row", cell: observationDetail },
      {
        label: "Kind",
        cell: (row) => esc(OBSERVATION_KINDS[row.kind] || row.kind),
      },
      { label: "Project", cell: (row) => `<code>${esc(row.project_id)}</code>` },
      { label: "Funder", cell: (row) => esc(row.funder || "Not recorded here") },
      // Verbatim, as the ledger wrote it: this is the word a reader has to be
      // able to check against the source, not a grade assigned here.
      { label: "Verification", cell: (row) => pill(row.verification) },
      { label: "According to", cell: (row) => according(documentOf(row.country, row.source_id)) },
      { label: "Document page", cell: observationEvidence },
    ],
    empty: "No statements or project–document links match these filters.",
    resultNoun: "items on the record",
    pageSize: 50,
  });
}

/* Ticket 0857: the Documents page cites a row by its rank in this export, and
 * #document-rows/<CODE>?row=N opens the page on that one row, unfolded, with the
 * whole export one link away. A rank the export has no row for shows the whole
 * export and says so, rather than an empty table dressed as a result. */
function inventoryFocus(code, rows, focus) {
  if (!focus) return { shown: rows, note: "" };
  const row = rows[focus - 1];
  if (!row)
    return {
      shown: rows,
      note: emptyNote("inventory-focus", "none", `This export has no row ${fmt(focus)}; showing all ${fmt(rows.length)} rows.`),
    };
  return {
    shown: [row],
    note: emptyNote("inventory-focus", focus, `Row ${fmt(focus)} of the ${fmt(rows.length)} rows in this export, as the Documents page cites it. <a href="#document-rows/${code}">Show all ${fmt(rows.length)} rows →</a>`),
  };
}
/* A country's entries (D2) or what is on the record for it (D3): both read
 * the same two views, loaded once per country, and show one of them. */
function renderInventory(code, rows, observations, focus, tab) {
  const details = m1a.countries[code];
  const c = country(code);
  const { shown, note } = inventoryFocus(code, rows, focus);
  const values = (key) => distinctValues(shown, key);
  const table = filterTable("inventory", shown, {
    facets: INVENTORY_FACETS.map(([key, label, all]) => ({
      key,
      label,
      all,
      options: values(key),
    })),
    search: {
      // The label and the evidence locator, because the locator is how a
      // source addresses its own rows: "Annex I.1" selects the 37 Viet Nam
      // rows of that annex, which no facet can express — the annex is not a
      // sub-layer, and hard-wiring a fifth select for it would bind this page
      // to one country's locator vocabulary.
      label: "Search the label or locator",
      placeholder: "Try Tri An, Annex I.1, transmission…",
      text: (row) =>
        ((row.label || "") + " " + (row.evidence_locator || "")).toLowerCase(),
    },
    columns: [
      { label: "Document row", cell: (row) => `<code>${esc(row.source_row_id)}</code>` },
      {
        label: "Label and document columns",
        cell: (row) => inventoryRowDetail(row, shown !== rows),
      },
      { label: "Extract", cell: (row) => esc(row.source_layer) },
      { label: "Entry type", cell: (row) => esc(row.record_type) },
      { label: "Reported status", cell: (row) => statusPill(row.reported_status) },
      { label: "Identity", cell: (row) => pill(row.identity_status) },
      { label: "Document page", cell: inventoryEvidence },
    ],
    empty: "No entries match these filters.",
    resultNoun: "rows in this export",
    pageSize: 50,
  });
  // One step per address (author's cold read, 2026-09-23): the step bar is
  // how a reader moves between a country's entries and what is on the
  // record, so the page shows one of the two, never both behind tabs.
  const name = esc(c?.name || code);
  if (tab === "record") {
    const observationsPanel = observationsTable(observations);
    main.innerHTML =
      `<div class="page-head"><h1>${name}: statements</h1>${titleBlock("Browse reported amounts, dates and statuses with their publisher and document location. Project–document links are also listed here; a document row can support several statements, and some statements come from prose.")}</div>` +
      `<section id="panel-observations">` +
      observationTotals(observations, code) +
      observationsPanel.head +
      `<div class="downloads"><a class="button light" href="data/observations/${code}.json" download>Download the ${code} statements (JSON) ↓</a></div></section>`;
    observationsPanel.mount();
    return;
  }
  main.innerHTML =
    `<div class="page-head"><h1>${name}: document rows</h1>${titleBlock("Browse selected rows with the wording and values recorded from their document columns. A row is not necessarily a unique project, and it may support more than one statement.")}</div>` +
    `<section id="panel-inventory">` +
    inventoryUnknowns(details) +
    copiesCallout("Each entry links to its document on the publisher's site, at its PDF page where the document gives one and the publisher serves a PDF.") +
    note +
    table.head +
    `<div class="downloads"><a class="button light" href="data/m1a/${code}.csv" download>Download the ${code} document rows (CSV) ↓</a></div></section>`;
  table.mount();
}
/* #document-rows/<CODE> and #statements/<CODE>: two steps over the same loaded
 * views; `tab` is "record" for the second. Rendered only if the reader is
 * still on one of this country's two pages when the views arrive. */
function inventoryPage(code, params, tab) {
  if (!m1a.countries[code]) return notFound();
  main.innerHTML = `<p class="note">Loading the ${esc(code)} entries…</p>`;
  const focus = Math.trunc(Number(params.get("row"))) || 0;
  stageTwo(code)
    .then(({ rows, observations }) => {
      const here = location.hash.slice(1).split("?")[0];
      if (here === "document-rows/" + code || here === "statements/" + code)
        renderInventory(code, rows, observations, focus > 0 ? focus : 0, tab);
    })
    .catch((error) => {
      main.innerHTML = `<div class="error"><h1>The ${esc(code)} entries could not load.</h1><p>${esc(error.message)}</p></div>`;
    });
}
function cataloguePage(params) {
  main.innerHTML =
    header(
      "Named projects, programmes and components",
      "Search the undertakings named in the documents and follow their links to recorded statements and publications. Programmes and components can overlap, so their number is not a count of distinct physical assets.",
    ) +
    `<div class="note"><span class="computed-tag">Our calculation</span> ${projects.length} named projects · ${undisclosedCount()} unpublished identities remain in the countries' own disclosures. Programmes and components may overlap.</div><div class="filters"><label class="search">Search projects, operators or locations<input id="search" type="search" placeholder="Try transmission, geothermal, Bac Ai…"></label><label>Country<select id="country-filter"><option value="">All countries</option>${overview.countries.map((c) => `<option value="${c.code}" ${params.get("country") === c.code ? "selected" : ""}>${esc(c.name)}</option>`).join("")}</select></label><label>Theme / technology<select id="technology-filter"><option value="">All themes / technologies</option>${options([...new Set(projects.map((p) => p.technology))].sort())}</select></label><label>Funder<select id="funder-filter"><option value="">All funders</option>${options([...new Set(projects.flatMap((p) => p.funders))].sort())}</select></label><label>Financing milestone<select id="stage-filter"><option value="">All milestones</option>${options(Object.keys(STAGE_COLOURS))}</select></label></div><p id="result-count" class="result-count" aria-live="polite"></p><div id="results"></div>`;
  const update = () => {
    const q = document.getElementById("search").value.toLowerCase();
    const code = document.getElementById("country-filter").value,
      tech = document.getElementById("technology-filter").value,
      stage = document.getElementById("stage-filter").value,
      funder = document.getElementById("funder-filter").value;
    const filtered = projects.filter(
      (p) =>
        (!q ||
          [p.name, p.operator, p.location, p.id]
            .join(" ")
            .toLowerCase()
            .includes(q)) &&
        (!code || p.country === code) &&
        (!tech || p.technology === tech) &&
        (!stage || p.finance_stage === stage) &&
        (!funder || p.funders.includes(funder)),
    );
    document.getElementById("result-count").textContent =
      `${filtered.length} of ${projects.length} named projects`;
    document.getElementById("results").innerHTML = projectTable(filtered);
  };
  document
    .querySelectorAll(".filters input,.filters select")
    .forEach((el) =>
      el.addEventListener(el.tagName === "INPUT" ? "input" : "change", update),
    );
  update();
}
function eventView(e, sources) {
  const timing = e.date
    ? `Event ${date(e.date)}`
    : e.event_start && e.event_end
      ? `Event between ${date(e.event_start)} and ${date(e.event_end)} (${e.event_precision} precision)`
      : "Event date not established";
  const context = [
    e.observed_date ? `Observed as of ${date(e.observed_date)}` : "",
    e.reported_on ? `Document published ${date(e.reported_on)}` : "",
    e.collected_on ? `Collected ${date(e.collected_on.slice(0, 10))}` : "",
    e.recorded_date && !e.date && !e.observed_date && !e.reported_on
      ? `Legacy date ${date(e.recorded_date)} (${e.date_role}; not event timing)`
      : "",
  ]
    .filter(Boolean)
    .join(" · ");
  return `<li data-event-id="${esc(e.id)}"><div class="date">${esc(timing)}</div><p class="note">${esc(context)} · ${esc(e.date_basis)}</p><h3>${esc(e.status)}${e.amount != null ? " · " + esc(money(e.amount, e.currency)) + ' <span class="published-tag">As published</span>' : ""}</h3>${e.funder ? `<p>${esc(e.funder)} · ${esc(e.instrument)}</p>` : ""}<p>${esc(e.notes)}</p>${sourceLink(sources[e.source_id], "Read the document")} <span class="date-tag">${esc(e.locator)}</span></li>`;
}
function sourceAdjudication(p, id) {
  return (p.source_links || [])
    .filter((link) => link.source_id === id)
    .map(
      (link) =>
        `<div class="source-adjudication" data-link-id="${esc(link.link_id)}"><small><strong>${esc(link.relationship.replaceAll("_", " "))}</strong> · ${esc(link.review_status.replaceAll("_", " "))}</small><small>${esc(link.locator)}</small><p class="note">${esc(link.notes)}</p></div>`,
    )
    .join("");
}
/* The descent, fact → its stage-two rows: the country's ledger observations
 * addressed to this record, read from observations/<CODE>.json — the view the
 * Observations tab loads — and filtered on project_id here, never copied into
 * the country view (ticket 0855). Same detail, same evidence cell, same
 * fingerprint resolution, so the two pages are one reading. */
function projectEvidenceRow(row) {
  return `<tr data-evidence-row="${esc(observationId(row))}"><td>${esc(row.table)}</td><td>${observationDetail(row)}</td><td>${pill(row.verification)}</td><td>${according(documentOf(row.country, row.source_id))}</td><td>${observationEvidence(row)}</td></tr>`;
}
function projectEvidence(rows) {
  return rows.length
    ? `<details class="foldout" data-evidence-count="${rows.length}"><summary>${fmt(rows.length)} ${rows.length === 1 ? "item" : "items"} on the record</summary><div class="table-wrap"><table><thead><tr><th>Table</th><th>Row</th><th>Verification</th><th>According to</th><th>Document page</th></tr></thead><tbody>${rows.map(projectEvidenceRow).join("")}</tbody></table></div></details>`
    : emptyNote("evidence-count", 0, "Nothing on the record is addressed to this project in this release.");
}
/* Fills the section once the view arrives, if the reader is still on this
 * page. The view absent, the section says so and points at the tab that
 * would have shown the same rows, rather than showing an empty list. */
function fillProjectEvidence(p) {
  const still = () =>
    location.hash.slice(1).split("?")[0] === "project/" + encodeURIComponent(p.id);
  const section = () => document.getElementById("project-evidence-rows");
  observationsView(p.country)
    .then((rows) => {
      if (!still() || !section()) return;
      section().innerHTML = projectEvidence(rows.filter((row) => row.project_id === p.id));
    })
    .catch((error) => {
      if (!still() || !section()) return;
      section().innerHTML = emptyNote("evidence-count", "unavailable", `The ${esc(p.country)} items on the record could not load (${esc(error.message)}). They are the items <a href="#statements/${esc(p.country)}">recorded for this country</a> addressed to <code>${esc(p.id)}</code>.`);
    });
}
/* A source card's title already links to the publisher's page; under it, the
 * host of that very link (the country view's address, which can differ from
 * the registry's, e.g. a byte range on a Common Crawl record), what was
 * collected and, where this server holds it, the archived copy. Resolved by
 * source identifier through the same ranked index as an inventory row: the
 * card names a source, not a fingerprint. */
function archivedCopy(id, source) {
  const entry = documentIndex[id];
  if (!entry) return "";
  const archived = archivedLink(entry, null, ` data-archived-source="${esc(id)}"`);
  const copy = webArchiveLink(entry, null, ` data-web-archive-source="${esc(id)}"`);
  return `<small data-document-facts="${esc(id)}">Publisher's page: ${esc(hostOf(source.url) || "no address recorded")}${deadNote(entry)} · ${collectedFacts(entry)}</small>${copy ? `<small>${copy} ${identityMark(entry)}</small>` : ""}${archived ? `<small>${archived}</small>` : ""}`;
}
function projectPage(id) {
  const p = projects.find((p) => p.id === id);
  if (!p) return notFound();
  const c = country(p.country),
    sources = countries[p.country].sources;
  main.innerHTML = `<div class="page-head"><div class="breadcrumb"><a href="#projects">Projects</a> › ${esc(p.name)}</div><h1>${esc(p.name)} <span class="badge" data-review-state="${esc(p.coverage)}">Review state · ${esc(p.coverage.replaceAll("_", " "))}</span></h1><p class="lede">${esc(p.location)}</p>${pill(p.finance_stage === "Not documented" ? "Financial events not yet coded" : p.finance_stage)}</div><div class="project-layout"><div><h2>Essential features</h2><dl class="facts"><dt>Country</dt><dd><a href="#funding/${c.code}">${esc(c.name)}</a></dd><dt>Theme / technology</dt><dd>${esc(p.technology)}</dd><dt>Operator</dt><dd>${esc(p.operator)}</dd><dt>Funders</dt><dd>${esc(p.funders.join("; ") || "See the individual documents; no funder entry yet")}</dd><dt>Project ID</dt><dd>${esc(p.id)}</dd><dt>Document follow-up</dt><dd>${esc(p.coverage.replaceAll("_", " "))}</dd></dl><p class="note">${esc(p.notes)}</p><section class="section"><h2>Documented timeline</h2><p class="note">Events and dated status reports are distinguished. A financing amount at approval and again at signature is not two separate amounts to add.</p>${p.events.length ? `<ol class="timeline">${p.events.map((e) => eventView(e, sources)).join("")}</ol>` : '<div class="callout">No financial or implementation event has yet been added to this project\'s timeline. Its documents may establish more; absence from this timeline is not zero progress.</div>'}</section><section class="section" id="project-evidence"><h2>Statements about this project</h2><p class="note">Reported amounts, dates and statuses about this project, plus project–document links, each with a publisher and document location. These items are not amounts to add together.</p><div id="project-evidence-rows"><p class="note">Loading statements for ${esc(c.short)}…</p></div></section>${p.claims.length ? `<section class="section"><h2>What other documents say</h2>${p.claims.map((r) => `<article style="margin:20px 0"><p>${esc(r.claim_summary)}</p><p class="note">${according(sources[r.source_id])} · Match verdict: ${esc(r.match_status.replaceAll("_", " "))} · ${esc(r.notes)}</p>${sourceLink(sources[r.source_id], "Read the document")} <span class="date-tag">${esc(r.section)}</span></article>`).join("")}</section>` : ""}</div><aside><div class="panel"><h3>Documents</h3><p class="note">${esc(p.coverage_note)}</p><ul class="sources">${p.sources
    .map((id) => {
      const s = sources[id];
      return s
        ? `<li>${sourceLink(s)}<small>${esc(s.publisher)} · ${esc(s.collection.replaceAll("_", " "))}</small>${s.retrieved ? `<small>Retrieved ${esc(s.retrieved.slice(0, 10))}</small>` : ""}${archivedCopy(id, s)}${sourceAdjudication(p, id)}</li>`
        : "";
    })
    .join(
      "",
    )}</ul></div><p class="note" style="margin-top:20px">Each item keeps its document's scope. An agreement, approval or register entry does not establish a payment or physical delivery.</p><a class="button light" href="data/${c.code}.json" download>Download the country's data ↓</a></aside></div>`;
  fillProjectEvidence(p);
}
function median(values) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b),
    n = sorted.length;
  return n % 2 ? sorted[(n - 1) / 2] : (sorted[n / 2 - 1] + sorted[n / 2]) / 2;
}
function histogram(rows) {
  const bins = Array(9).fill(0);
  rows
    .filter((p) => p.years != null)
    .forEach((p) => bins[Math.min(8, Math.floor(p.years / 2))]++);
  const max = Math.max(1, ...bins);
  return `<div class="histogram" role="img" aria-label="Distribution of reported approval-to-closing windows">${bins.map((n, i) => `<div class="hist-bin" style="height:${(n / max) * 130}px" title="${i === 8 ? "16+" : i * 2 + "–" + (i + 1) * 2} years: ${n} operations"><b>${n}</b><span>${i === 8 ? "16+" : i * 2 + "–" + (i + 1) * 2}</span></div>`).join("")}</div>`;
}
function comparisonPage(params) {
  main.innerHTML =
    header(
      "Earlier energy operations outside the JETPs",
      "Browse closed World Bank energy-related operations approved before each country’s JETP. They provide historical context; they do not establish whether the JETPs changed financing timelines.",
    ) +
    `<div class="callout"><strong>What “closed” means here.</strong> These are completed administrative financing operations, not verified completed power plants. Approval-to-closing windows describe lending history; they do not yet establish whether JETPs accelerated preparation or financing.</div><div class="filters"><label class="search">Search historical operations<input id="history-search" type="search" placeholder="Search by name or World Bank project ID"></label><label>Country<select id="history-country"><option value="">All four countries</option>${overview.countries.map((c) => `<option value="${c.code}" ${params.get("country") === c.code ? "selected" : ""}>${esc(c.name)}</option>`).join("")}</select></label><label>Instrument<select id="history-instrument"><option value="">All instruments</option>${options([...new Set(comparison.projects.map((p) => p.instrument))].sort())}</select></label><label>Approval vintage<select id="history-vintage"><option value="0">All pre-JETP years</option><option value="2000">2000 onwards</option><option value="2010">2010 onwards</option></select></label><label>Additional financing<select id="history-additional"><option value="">Include, labelled</option><option value="exclude">Exclude additional financing</option></select></label></div><div id="history-summary" aria-live="polite"></div><div id="history-table"></div><div class="downloads"><a class="button light" href="data/comparison.json" download>Download historical cohort ↓</a></div><p class="note">${esc(comparison.method)}</p><p class="note">${esc(comparison.date_note)} Publisher: World Bank Projects & Operations. Frozen snapshots retrieved: ${Object.entries(
      comparison.snapshots,
    )
      .map(
        ([code, snapshot]) =>
          `${esc(country(code).short)} ${date(snapshot.retrieved_on)}`,
      )
      .join(
        "; ",
      )}. Each operation links to its official World Bank page.</p>`;
  const update = () => {
    const q = document.getElementById("history-search").value.toLowerCase(),
      code = document.getElementById("history-country").value,
      inst = document.getElementById("history-instrument").value,
      vintage = Number(document.getElementById("history-vintage").value),
      extra = document.getElementById("history-additional").value;
    const rows = comparison.projects.filter(
      (p) =>
        (!q || (p.name + " " + p.id).toLowerCase().includes(q)) &&
        (!code || p.country === code) &&
        (!inst || p.instrument === inst) &&
        Number(p.approval.slice(0, 4)) >= vintage &&
        (!extra || !p.additional_financing),
    );
    const durations = rows.filter((p) => p.years != null),
      med = median(durations.map((p) => p.years));
    document.getElementById("history-summary").innerHTML =
      `<div class="split" style="margin-bottom:25px"><div><div class="metrics" style="grid-template-columns:1fr 1fr">${computedMetric(rows.length, "closed operations", "this selection")}${computedMetric(med == null ? "—" : med.toFixed(1) + "y", "median reported financing window", "operations with both dates, this selection")}${computedMetric(durations.length, "usable approval / closing pairs", "this selection")}${computedMetric(rows.filter((p) => p.additional_financing).length, "additional-financing operations", "this selection")}</div><p class="note">Closed-only selection favours operations that have finished. Mixed-sector and older projects may differ substantially from today's JETP investments. No pooled causal effect is estimated.</p></div><div class="panel"><h3>Reported financing windows</h3><p class="note"><span class="computed-tag">Our calculation</span> Years from approval to the closing date the World Bank reports · n = ${durations.length}</p>${histogram(rows)}</div></div>`;
    document.getElementById("history-table").innerHTML = rows.length
      ? `<div class="table-wrap"><table><thead><tr><th>Historical operation</th><th>Country</th><th>Instrument</th><th>Approval</th><th>Reported closing</th><th>Window</th></tr></thead><tbody>${rows.map((p) => `<tr><td><a href="${esc(cleanURL(p.source_url))}" target="_blank" rel="noopener">${esc(p.name)} ↗</a><small>${esc(p.id)} · ${esc(p.sectors.join("; "))}</small>${p.additional_financing ? '<span class="badge">Additional financing</span>' : ""}</td><td>${esc(country(p.country).short)}</td><td>${esc(p.instrument)}</td><td>${esc(p.approval)}</td><td>${esc(p.closing || "Not recorded")}</td><td>${p.years == null ? "—" : p.years.toFixed(1) + "y"}</td></tr>`).join("")}</tbody></table></div>`
      : '<div class="empty">No historical operations match these filters.</div>';
  };
  document
    .querySelectorAll(".filters input,.filters select")
    .forEach((el) =>
      el.addEventListener(el.tagName === "INPUT" ? "input" : "change", update),
    );
  update();
}
/* The tallies (author's cold read, 2026-09-23, third batch): one table,
 * a row per figure we computed, grouped by country and never summed across
 * countries. Each row says what the figure is, its value and unit, what it
 * covers, the date it holds as of, and links to what was counted where the
 * site lists it. The two charts follow as numbered figures. */
function countRows(c) {
  const code = c.code;
  const cutoff = date(overview.provenance.cutoff);
  const inventory = m1a.countries[code];
  const pool = comparison.projects.filter((p) => p.country === code);
  const snapshot = comparison.snapshots?.[code];
  const readings = evidence.evidence_depth?.structured_atomic_observations?.by_country?.[code];
  const reviewed = (evidence.records || []).filter((r) => r.country === code);
  const rows = [
    ["Named projects", c.named, "projects", "the partnership's portfolio; programmes and components may overlap", cutoff, `#projects?country=${code}`],
    ["Unpublished identities", c.undisclosed, "identities", "counted in the country's own disclosure, which names none of them", cutoff, null],
    ["Documents cited", Object.keys(countries[code].sources).length, "documents", "by this country's projects and headline", cutoff, `#documents?country=${code}`],
    ["Document rows in the export", inventory?.row_count, "rows", "the frozen export, its extracts laid end to end; a file size, not a project count", inventory?.sublayers.map((s) => (/^\d{4}-\d{2}-\d{2}$/.test(s.cutoff) ? date(s.cutoff) : s.cutoff)).join(", "), `#document-rows/${code}`],
    ["Reviewed items on the record", reviewed.length, "items", "national headlines reviewed one by one, never added", cutoff, "#statements"],
    ["Closed World Bank operations", pool.length, "operations", "energy-related operations approved before the partnership, the historical pool", snapshot ? date(snapshot.retrieved_on) : "Not dated in this release", `#non-jetp-energy-operations?country=${code}`],
    ["Structured readings", readings, "readings", "an analysis snapshot of the same documents, not published on these pages", "Not dated in this release", null],
  ];
  return rows
    .filter(([, value]) => value != null)
    .map(
      ([what, value, unit, covers, asOf, href]) =>
        `<tr data-computed-figure="${esc(what)}" data-country="${code}"><td>${esc(what)}</td><td class="num">${fmt(value)}</td><td>${esc(unit)}</td><td>${esc(covers)}</td><td>${esc(asOf || "Not dated in this release")}</td><td>${href ? `<a href="${esc(href)}">Computed from →</a>` : '<span class="note">Not listed on these pages</span>'}</td></tr>`,
    )
    .join("");
}
function numbersPage() {
  main.innerHTML =
    header(
      "The tallies: what we counted, and from what",
      "Every figure on this page is our calculation from the paper trail, one row per figure and one group per country. Each row states its unit, what it covers and the date it holds as of, and links to what was counted where these pages list it. Publishers' own figures stay on their pages, marked as published, with their publisher and date.",
    ) +
    `<div class="table-wrap"><table class="counts"><caption><span class="computed-tag">Our calculation</span> One row per figure, grouped by country. They are not a common total. No row is summed across countries.</caption><thead><tr><th scope="col">What it is</th><th scope="col">Value</th><th scope="col">Unit</th><th scope="col">What it covers</th><th scope="col">As of</th><th scope="col">Computed from</th></tr></thead>${overview.countries
      .map(
        (c) =>
          `<tbody data-country="${c.code}"><tr class="group"><th scope="colgroup" colspan="6"><a href="#funding/${c.code}">${esc(c.name)}</a></th></tr>${countRows(c)}</tbody>`,
      )
      .join("")}</table></div>` +
    `<figure class="counts-figure" data-figure="1"><figcaption><strong>Figure 1.</strong> Furthest financing milestone on the record, named projects by country. <span class="computed-tag">Our calculation</span> Each named project once, at the most advanced milestone on the record for it. Registered financing is not an independently verified signature or payment, and “Not coded in ledger” can coexist with financing described in a document.</figcaption>${stageChart(overview.countries)}</figure>` +
    `<figure class="counts-figure" data-figure="2"><figcaption><strong>Figure 2.</strong> Named projects by theme or technology, the seven most frequent. <span class="computed-tag">Our calculation</span> Categories keep each document's own wording.</figcaption>${technologyChart(projects)}</figure>` +
    `<section class="section"><h2>Accounts</h2><p>No account of pledges, allocations and payments is computed in this release: nothing on these pages adds amounts across documents, or a project's amounts to a partnership's headline.</p><p><a class="text-link" href="#release-history">Release history →</a></p></section>`;
}
function editionHistoryPage() {
  const rows = editions.editions;
  main.innerHTML = header(
      "What changed, and what did not.", "Each release is frozen after review. A failed refresh remains a recorded gap and never removes a document from an earlier download.") +
    `<div class="table-wrap"><table><thead><tr><th>Release</th><th>Knowledge cutoff</th><th>Prepared</th><th>State</th><th>Published</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${esc(row.edition)}</td><td>${date(row.observation_cutoff)}</td><td>${date(row.release_prepared_date)}</td><td>${esc(row.release_state)}</td><td>${row.publication_date ? date(row.publication_date) : "Not published"}</td></tr>`).join("")}</tbody></table></div><p class="note">A correction uses a new <code>YYYY-MM-rN</code> release and preserves the prior archive. Later reports are labelled by their original event date; they are not treated as new events.</p><div class="downloads"><a class="button light" href="data/editions.json" download>Download release history ↓</a></div><p><a class="text-link" href="#counts">What the data work added: the tallies →</a></p>`;
}
/* A reviewed record pins a fingerprint, so its pedigree opens the archived copy
 * of those bytes and no other attempt of the same source identifier: resolved
 * by sha256, as a ledger observation is, through the same evidence cell. Text
 * where the snapshot holds no such copy. The record itself gains no field. */
function reviewedProof(proof, code) {
  const entry = documentsBySha[proof.sha256] || null;
  return `${according(documentOf(code, proof.source_id))} · <code>${esc(proof.source_id)}</code> · ${evidenceLink(
    proof.locator,
    entry,
    null,
    "data-reviewed-source",
    proof.source_id,
    "No collected document carries this fingerprint",
  )}${entry ? "" : ` · <code>${esc(proof.sha256.slice(0, 12))}…</code>`}`;
}
function evidencePage() {
  const records = evidence.records || [];
  main.innerHTML =
    header(
      "What the documents say",
      "Browse reported amounts, dates, financing and implementation statuses, with the publisher and document location for each item. This page also lists links between projects and documents; a reported approval is not a payment.",
    ) +
    `<section class="section"><div class="section-head"><div><p class="eyebrow">Country by country</p><h2>Statements by country</h2></div><p>Open each country's statements and links between projects and documents. Document rows and statements may describe the same material; their counts should not be added together.</p></div><ul class="country-links">${overview.countries.map((c) => `<li><a href="#statements/${c.code}">${esc(c.name)}: statements →</a></li>`).join("")}</ul></section>` +
    `<section class="section"><div class="section-head"><div><p class="eyebrow">Reviewed one by one</p><h2>The national headlines</h2></div></div><div class="callout"><h3>Analytical snapshot: ${esc(evidence.analytical_snapshot?.status || "not available")}</h3><p>The comparative staging snapshot is derived research material and is not published in this preview.</p></div><div class="table-wrap"><table><thead><tr><th>Item</th><th>Country</th><th>Review state</th><th>According to · document</th><th>Reading note</th></tr></thead><tbody>${records.map((record) => `<tr data-reviewed-evidence-id="${esc(record.id)}"><td>${esc(record.label)}</td><td>${esc(country(record.country)?.name || record.country)}</td><td>${esc(record.status.replaceAll("_", " "))}</td><td>${record.evidence.map((proof) => reviewedProof(proof, record.country)).join("<br>")}</td><td>${esc(record.notes)}<br><small>Non-aggregate record.</small></td></tr>`).join("")}</tbody></table></div>${records.length ? "" : '<p class="note">No separately releasable reviewed item is available in this release. That is a coverage statement, not a sign of no activity.</p>'}<div class="downloads"><a class="button light" href="data/reviewed-evidence.json" download>Download the reviewed items ↓</a></div></section>`;
}
function entriesPage() {
  const rows = ["ZAF", "IDN", "VNM", "SEN"]
    .map((code) => {
      const item = m1a.countries[code];
      const sublayers = item.sublayers
        .map((layer) => `${esc(layer.edition)} · cutoff ${esc(layer.cutoff)}`)
        .join("<br>");
      return `<tr><td><a href="#document-rows/${code}">${esc(country(code)?.name || code)}</a></td><td>${fmt(item.row_count)}</td><td>${sublayers}</td><td>${fmt(item.unknowns.field_values)}</td><td>${fmt(item.unknowns.identity_rows)}</td><td>${fmt(item.unknowns.unavailable_source_rows)}</td></tr>`;
    })
    .join("");
  main.innerHTML =
    header(
      "Rows selected from the documents",
      "Browse selected rows from registers, annexes and lists, with wording and values recorded from their document columns. A row may describe a programme, project or component; it does not necessarily identify a unique project.",
    ) +
    `<p>These four tables keep every row of six selected document extracts. They are frozen, not a live status service, and their row counts are not comparable project totals.</p><div class="table-wrap"><table><thead><tr><th>Country</th><th>Rows in this export <small class="computed-tag">Our calculation</small></th><th>Publisher's issue · cutoff</th><th>Unknown field values</th><th>Unknown identities</th><th>Rows unavailable at the publisher</th></tr></thead><tbody>${rows}</tbody></table></div><p class="note">The per-country figures are the extract figures of one export laid end to end — the size of a file, not a count of projects: the extracts overlap and count different things. Each extract's own figures are on the country's document rows page.</p><div class="downloads"><a class="button light" href="data/m1a/ZAF.csv" download>South Africa document rows ↓</a><a class="button light" href="data/m1a/IDN.csv" download>Indonesia document rows ↓</a><a class="button light" href="data/m1a/VNM.csv" download>Viet Nam document rows ↓</a><a class="button light" href="data/m1a/SEN.csv" download>Senegal document rows ↓</a><a class="button light" href="data/m1a/manifest.json" download>Document rows manifest ↓</a></div><p>The manifest pins input and document hashes and reports <code>field_values</code>, <code>identity_rows</code> and <code>unavailable_source_rows</code> separately for every extract. Country names above open the row-by-row entries.</p>`;
}
/* Group exact printed names within a country. A reviewed party-name mapping
 * can additionally join name forms under one party ID; ambiguous names never
 * receive an inferred identity. Roles and linked projects remain distinct. */
let whosWhoRows;
function organisationIndex() {
  const formsByParty = new Map();
  const formsByName = new Map();
  for (const form of partyNames.names) {
    if (!formsByParty.has(form.party_id)) formsByParty.set(form.party_id, []);
    formsByParty.get(form.party_id).push(form);
    if (!formsByName.has(form.name)) formsByName.set(form.name, []);
    formsByName.get(form.name).push(form);
  }
  const byKey = new Map();
  for (const project of projects) {
    const named = [...project.funders.map((name) => [name, "Funder"]),
      [project.operator, "Operator"]];
    for (const [name, role] of named) {
      if (!name || name === "Not specified") continue;
      const ids = new Set((formsByName.get(name) || [])
        .filter((form) => !form.country || form.country === project.country)
        .map((form) => form.party_id));
      const partyId = ids.size === 1 ? [...ids][0] : null;
      const forms = partyId ? formsByParty.get(partyId) : [];
      const preferred = forms.find((form) => form.form_type === "preferred");
      const key = [partyId || name, project.country].join("\u0000");
      if (!byKey.has(key)) byKey.set(key, {
        name: preferred?.name || name, country: project.country,
        roles: new Set(), projects: new Map(), aliases: forms.filter((form) => form.name !== preferred?.name),
      });
      const row = byKey.get(key);
      row.roles.add(role);
      row.projects.set(project.id, project);
    }
  }
  return [...byKey.values()].map((row) => ({
    ...row, roles: [...row.roles].sort(), projects: [...row.projects.values()],
  })).sort((a, b) => a.name.localeCompare(b.name));
}
function organisationProjects(row) {
  const link = (project) =>
    `<a href="#project/${encodeURIComponent(project.id)}">${esc(project.name)}</a>`;
  const first = row.projects.slice(0, 3).map(link).join(", ");
  const rest = row.projects.slice(3);
  return `<div class="organisation-projects" data-party-projects-count="${row.projects.length}">${first}${rest.length
    ? `<details><summary>and ${rest.length} more</summary><ul class="citing">${rest.map((project) => `<li>${link(project)}</li>`).join("")}</ul></details>`
    : ""}</div>`;
}
function organisationName(row) {
  const aliases = row.aliases.filter((form) => form.name !== row.name);
  const title = aliases.length ? ` title="${esc(`Also recorded as: ${aliases.map((form) => form.name).join(", ")}`)}"` : "";
  return `<span${title}>${esc(row.name)}</span>${aliases.length
    ? `<details class="organisation-aliases"><summary>Other recorded names · ${aliases.length}</summary><ul class="citing">${aliases.map((form) =>
      `<li>${esc(form.name)} <small>${esc(form.form_type.replaceAll("_", " "))} · ${esc(form.document_id || form.line_id || "Source not recorded")}</small></li>`
    ).join("")}</ul></details>`
    : ""}`;
}
function whosWhoPage(params) {
  whosWhoRows ||= organisationIndex();
  const rows = whosWhoRows;
  const table = filterTable("parties", rows, {
    facets: [
      { key: "roles", label: "Named as", all: "Funders and operators",
        options: ["Funder", "Operator"], matches: (row, value) => row.roles.includes(value) },
      { key: "country", label: "Country", all: "All four countries",
        options: overview.countries.map((c) => ({ value: c.code, label: c.name })),
        selected: knownCountry(params.get("country")) },
    ],
    search: { label: "Search names", placeholder: "Try KfW, EVN, Eskom…",
      text: (row) => [row.name, ...row.aliases.map((form) => form.name)].join(" ").toLowerCase() },
    columns: [
      { label: "Name in the documents", cell: organisationName },
      { label: "Named as", cell: (row) => row.roles.map(pill).join(" ") },
      { label: "Country", cell: (row) => esc(country(row.country)?.short || row.country) },
      { label: "Projects naming it", cell: organisationProjects, width: "wide" },
    ],
    empty: "No names match these filters.", resultNoun: "names", pageSize: 50,
  });
  main.innerHTML = header(
    "Organisations named in the documents",
    "See which organisations are named as funders or operators and which projects name them. Rows with the same name and country are grouped; only reviewed name forms are shown as aliases, and a shared spelling alone does not establish a shared identity.",
  ) + table.head;
  table.mount();
}
/* The Glossary (ticket 0882), generated from the ontology tables served one
 * file per table under data/ontology/: each term in force with its
 * definition, its external mapping and its revision history. No definition
 * is written here. The page's one choice is the theme each list sits under:
 * grouped by theme, A–Z inside each group (author's cold read, 2026-09-23).
 * Classes are split between the first two themes by name, as the author's
 * grouping does; a list or class no theme names lands in "Other lists", so a
 * new list can never drop its terms from the page. */
const GLOSSARY_THEMES = [
  ["What we track", {
    classes: ["agreement", "asset", "country", "party", "party_name", "perimeter", "project"],
    lists: ["authority_category", "country", "form_type", "project_classification", "role"],
  }],
  ["How documents are read", {
    classes: ["comparator_record", "crosswalk", "document", "external_identifier", "line",
      "observation", "publisher", "retrieval", "snapshot", "timing"],
    lists: ["date_precision", "date_role", "decision_status", "decision_type", "document_type",
      "line_classification", "mapping_relation", "retrieval_status", "term_kind"],
  }],
  ["Statuses", { lists: ["asset_state", "axis", "delivery", "money", "project_stage"] }],
  ["Measures", { lists: ["basis", "flow_type", "marker", "marker_score", "measure", "modality"] }],
  ["Relations", { lists: ["relation"] }],
];
const themeOf = (t) =>
  GLOSSARY_THEMES.find(([, sel]) =>
    t.kind === "class" ? (sel.classes || []).includes(t.term_id) : (sel.lists || []).includes(t.list),
  )?.[0] || "Other lists";
/* A term is addressed by its list and its identifier, which is unique within
 * the list only; the classes without a list go under their kind. */
const termKey = (t) => `${t.list || t.kind}/${t.term_id}`;
const termHref = (key) => "#glossary?term=" + encodeURIComponent(key);
/* The served view as row objects, with the rows in force as the builder
 * decided them: the page never re-derives the revision rule. */
function ontologyTable(view) {
  const rows = view.rows.map((values) => Object.fromEntries(view.fields.map((f, i) => [f, values[i]])));
  const live = new Set(view.in_force);
  return { rows, inForce: rows.filter((row) => live.has(row[view.key])), key: view.key };
}
function readOntology(termsView, statusView) {
  const terms = ontologyTable(termsView);
  return {
    terms: new Map(terms.inForce.map((t) => [termKey(t), t])),
    termRows: new Map(terms.rows.map((row) => [row.term_row_id, row])),
    statusCrosswalk: ontologyTable(statusView).inForce,
  };
}
/* Every term shown elsewhere links to its entry; a word that is not a term
 * in force stays plain text. */
function termLink(list, id, text) {
  const key = `${list}/${id}`;
  const shown = esc(text ?? id);
  return ontology.terms.has(key)
    ? `<a href="${esc(termHref(key))}" data-term-link="${esc(key)}">${shown}</a>`
    : shown;
}
/* A publisher's own status word reaches its shared status through the status
 * crosswalk. The served rows do not yet name the publisher of an entry (the
 * publishers table arrives with the ledger migration), so the lookup is on
 * the word alone, and a word two publishers map differently stays unlinked
 * rather than linked to one of them. */
function statusKey(word) {
  const targets = new Set(
    ontology.statusCrosswalk
      .filter((row) => row.own_status === word)
      .map((row) => `${row.axis}/${row.shared_status}`),
  );
  const [key] = targets;
  return targets.size === 1 && ontology.terms.has(key) ? key : null;
}
function statusPill(word) {
  const key = word ? statusKey(word) : null;
  return key ? `<a href="${esc(termHref(key))}" data-term-link="${esc(key)}">${pill(word)}</a>` : pill(word);
}
/* Ledger columns whose value is a term: the financial events' status words
 * are the money axis's states (docs/jetp-ontology.md section 4), so each
 * links to the term of the same identifier when one is in force. */
const FIELD_TERMS = {
  financial_status: (value) => termLink("money", value),
  reported_status: (value) => (statusKey(value) ? statusPill(value) : esc(value)),
};
/* A relation's domain and range name classes, which are terms too. */
const classNames = (value) =>
  String(value || "")
    .split(/,\s*/)
    .filter(Boolean)
    .map((name) => termLink("class", name.replace(/ /g, "_"), name))
    .join(", ");
function termMapping(t) {
  if (!t.external_scheme) return `Defined for this ledger · ${termLink("mapping_relation", t.mapping_relation)}`;
  const scheme = t.external_uri
    ? `<a href="${esc(cleanURL(t.external_uri))}" target="_blank" rel="noopener">${esc(t.external_scheme)} ↗</a>`
    : esc(t.external_scheme);
  return `External reference: ${scheme} · ${termLink("mapping_relation", t.mapping_relation)}`;
}
/* The rows a term's in-force row superseded, newest first. */
function termHistory(t) {
  const history = [];
  const seen = new Set([t.term_row_id]);
  let row = ontology.termRows.get(t.supersedes);
  while (row && !seen.has(row.term_row_id)) {
    history.push(row);
    seen.add(row.term_row_id);
    row = ontology.termRows.get(row.supersedes);
  }
  return history;
}
function glossaryEntry(t, target) {
  const key = termKey(t);
  const words = ontology.statusCrosswalk.filter((row) => row.axis === t.list && row.shared_status === t.term_id);
  const history = termHistory(t);
  return (
    `<dt id="term-${esc(key)}" data-term="${esc(key)}"${key === target ? ' data-targeted aria-current="true"' : ""}><span class="term-label">${esc(t.label)}</span> <span class="term-list">${esc((t.list || t.kind).replace(/_/g, " "))}</span></dt>` +
    `<dd><p class="term-definition">${esc(t.definition)}</p>` +
    (t.scope_note ? `<p class="note">${esc(t.scope_note)}</p>` : "") +
    (t.kind === "relation"
      ? `<p class="term-connects">Connects <span data-domain>${classNames(t.domain)}</span> to <span data-range>${classNames(t.range)}</span></p>`
      : "") +
    `<p class="term-mapping">${termMapping(t)}</p>` +
    (words.length
      ? `<p data-crosswalk>Publishers' own words mapped here: ${words.map((row) => `${pill(row.own_status)} <small>${esc(row.publisher_id)}</small>`).join(", ")}</p>`
      : "") +
    `<p class="note">Recorded ${date(t.recorded_at)}, decided by ${esc(t.decided_by)}</p>` +
    (history.length
      ? `<details class="term-history"><summary>Revision history</summary><ol>${history
          .map((row) => `<li>${date(row.recorded_at)}, decided by ${esc(row.decided_by)}: ${esc(row.definition)}</li>`)
          .join("")}</ol></details>`
      : "") +
    `</dd>`
  );
}
const byLabel = (a, b) => {
  const [x, y] = [a.label.toLowerCase(), b.label.toLowerCase()];
  return x < y ? -1 : x > y ? 1 : termKey(a) < termKey(b) ? -1 : 1;
};
function glossaryPage(target) {
  const themes = [...GLOSSARY_THEMES.map(([name]) => name), "Other lists"];
  const terms = [...ontology.terms.values()];
  main.innerHTML =
    header(
      "The words these pages use",
      "What each word on these pages means, grouped by theme and alphabetical within each group. Every entry is generated from the ledger's own term tables: its definition, the external reference it maps to, and its revision history. A status also lists the publishers' own words that map to it.",
    ) +
    themes
      .map((name) => [name, terms.filter((t) => themeOf(t) === name).sort(byLabel)])
      .filter(([, members]) => members.length)
      .map(
        ([name, members]) =>
          `<section class="section" data-glossary-group="${esc(name)}"><h2>${esc(name)}</h2><dl class="facts glossary">${members
            .map((t) => glossaryEntry(t, target))
            .join("")}</dl></section>`,
      )
      .join("");
}
/* About's landing page: one line per page under it, as #the-paper-trail. */
const ABOUT_NOTES = {
  glossary: "The words these pages use, grouped by theme.",
  methods: "What we collected, how we read it, what we counted, and what this observatory does not do; the release history is linked from there.",
  "who-we-are": "Who makes this observatory.",
};
function aboutPage() {
  main.innerHTML =
    header("About", "What stands behind these pages: their words, their methods and their authors.") +
    `<ol class="trail-intro">${SUB_PAGES.about.map((s) => `<li><a href="#${s.page}"><strong>${esc(s.label)}</strong></a> ${esc(ABOUT_NOTES[s.page])}</li>`).join("")}</ol>`;
}
/* Who we are: the author's own text, from his published homepage bio
 * (supplied 2026-09-23 for PR #1459), kept as written, with the links he
 * gave. No phone or postal address. */
function whoWeArePage() {
  main.innerHTML =
    header(
      "Who we are",
      "The JETP Observatory is a research project of Minh Ha-Duong, Directeur de Recherche at CNRS, working at CIRED (Centre international de recherche sur l'environnement et le développement) near Paris.",
    ) +
    `<div class="who-we-are" data-who-we-are><p>He works on energy, climate change, society, economics and uncertainty. He was a lead author of the IPCC's Fourth and Fifth Assessment Reports, founded the Vietnam Initiative for the Energy Transition (VIET) in 2018, and set up the Clean Energy and Sustainable Development lab at the University of Science and Technology of Hanoi in 2014.</p>` +
    `<p>The observatory reads what the four partnerships and their funders publish, archives every document it relies on, and shows how each figure was reached. Its data and code are open.</p>` +
    `<p>Homepage: <a href="https://minh.haduong.com" target="_blank" rel="noopener">https://minh.haduong.com</a> · ORCID: <a href="https://orcid.org/0000-0001-9988-2100" target="_blank" rel="noopener">https://orcid.org/0000-0001-9988-2100</a></p></div>`;
}
function methodsPage() {
  main.innerHTML =
    header(
      "Methods",
      "What we collected, how we read it, what we counted, and what this observatory does not do. Every figure can be followed back to its page.",
    ) +
    `<div class="method-list"><h2>What this release contains</h2><p>${projects.length} named projects, ${undisclosedCount()} unpublished identities, ${overview.source_count} curated documents and ${comparison.projects.length} closed historical operations. The named projects include programmes and components; they are not ${projects.length} distinct physical assets. Knowledge cutoff: ${date(overview.provenance.cutoff)}. Each country's reports keep their own dates.</p><h2>The paper trail, step by step</h2><p>The <a href="#documents">Documents</a> page lists the publications sought and the outcome of each retrieval. The <a href="#document-rows">Document rows</a> page preserves selected rows and their document wording. The <a href="#statements">Statements</a> page shows reported amounts, dates and statuses with publisher and document location, and also lists project–document links. A row may support several statements, while statements may come from prose. <a href="#projects">Projects</a>, <a href="#funding">Funding</a> and <a href="#organisations">Organisations</a> show the undertakings, financing and named organisations those documents discuss.</p><h2>Words and numbers</h2><p>The <a href="#glossary">Glossary</a> defines the words these pages use. A number a publisher printed is marked “As published” and shown with its publisher and date. A number we counted is marked “Our calculation”, with its unit and what it covers, and links to what was counted; <a href="#counts">The tallies</a> gathers them.</p><h2>What this observatory does not do</h2><p>It does not explain. It tests no causal explanation of why a partnership moves fast or slow, and estimates no effect of the partnerships. It does not add amounts across documents, nor a project's amounts to a partnership's headline. It does not convert or deflate amounts. It does not treat a plan, an approval or a register line as a payment. It does not match a 2023 plan position to a 2025 portfolio project. Missing payment data is not a zero payment.</p><h2>Three different kinds of progress</h2><p>Financial items distinguish needs, announcements, memoranda, approvals, signatures and disbursements. Implementation items are a separate table. Documentary coverage describes what we could locate, not what a project achieved. Register-derived dates are not presented as verified signature dates.</p><h2>How the national figures work</h2><p>Headline financing amounts reproduce attributed national reports; they are not computed by adding project events. The milestones differ across countries, so headline amounts must not be pooled. Portfolio bars count each named project once, at the most advanced financing milestone on the record for it; tranches may be at different milestones. “Not coded in ledger” does not mean “no finance”. No project-level disbursement total is available in this release.</p><h2>Earlier energy operations: context, not an effect estimate</h2><p>${esc(comparison.method)} ${esc(comparison.date_note)} The API may contain older status snapshots; retrieval date is not the date of its latest substantive update. Energy-related includes mixed-sector operations, and additional-financing operations may refer to the same underlying investment. Comparisons of preparation speed require a credible causal design from the separate lifecycle research programme.</p><h2>Dates, conflicts and missing items</h2><p>Event dates, date intervals, dated status reports and collection dates remain distinct. Timing is adjudicated independently of the publisher's authority; unreviewed timing is labelled and cannot supply an event date. Document cards keep provisional, contextual and confirmed link decisions. Historical downloads preserve each acquisition date and query-page hash; the substantive update date is unknown unless separately documented. Conflicting values are preserved in notes; we do not average them. Unpublished identities appear in country disclosure counts rather than invented project pages. Original-currency amounts remain the reference. An extract's unknown field values count the cells its document prints but leaves blank or unreadable, not the empty columns of our own extraction.</p><h2>Download this snapshot</h2><div class="downloads">${overview.countries.map((c) => `<a class="button light" href="data/${c.code}.json" download>${esc(c.name)} ↓</a>`).join("")}<a class="button light" href="data/comparison.json" download>Historical cohort ↓</a><a class="button light" href="data/documents.json" download>Collection registry ↓</a><a class="button light" href="data/overview.json" download>Overview & input hashes ↓</a><a class="button light" href="data/provenance.json" download>Where each headline comes from ↓</a></div><div class="downloads"><a class="button light" href="data/m1a/ZAF.csv" download>South Africa document rows ↓</a><a class="button light" href="data/m1a/IDN.csv" download>Indonesia document rows ↓</a><a class="button light" href="data/m1a/VNM.csv" download>Viet Nam document rows ↓</a><a class="button light" href="data/m1a/SEN.csv" download>Senegal document rows ↓</a><a class="button light" href="data/m1a/manifest.json" download>Document rows manifest ↓</a></div><p>JSON downloads include project data, document addresses and locators. Input SHA-256 hashes identify the files used to build this preview. This is a local preview, not yet a formally deposited monthly release; the <a href="#release-history">release history</a> lists what was prepared. Original documents retain their publishers' rights; their bulk redistribution is not implied.</p><h2>Reproducible, without a live database</h2><p>Markdown provides editorial context; CSV registries provide the structured data. The static website reads generated JSON. DVC preserves the research document archive, independently of the website. No visitor needs access to the archive or a database service.</p><p class="note">Input Git revision: <code>${esc(overview.provenance.input_git_sha || "Uncommitted preview inputs; use the file hashes")}</code><br>Release: ${esc(overview.provenance.edition)}</p></div>`;
}
function notFound() {
  main.innerHTML =
    header(
      "This page is not in the snapshot.",
      "Return to the projects to explore what is available.",
    ) + '<a class="button" href="#projects">Open the projects</a>';
}
const TITLES = {
  overview: "From promise to progress",
  "the-paper-trail": "The paper trail",
  funding: "Funding",
  projects: "Projects",
  project: "Project",
  "comparisons": "Non-JETP energy operations",
  "on-the-record": "Statements",
  "release-history": "Release history",
  documents: "Documents",
  entries: "Document rows",
  "whos-who": "Organisations",
  counts: "Counts",
  glossary: "Glossary",
  about: "About",
  methods: "Methods",
  "who-we-are": "Who we are",
};
/* The header's three section tabs: the current section is selected, and
 * aria-current says "page" when the tab's landing page is the page itself,
 * "true" when the page sits inside that section. */
function markNav(page) {
  const section = sectionOf(page);
  document.querySelectorAll("header nav a[data-section]").forEach((a) => {
    const active = a.dataset.section === section;
    a.classList.toggle("active", active);
    a.toggleAttribute("aria-current", active);
    if (active) a.setAttribute("aria-current", LANDING[section] === page ? "page" : "true");
  });
}
const SECTION_LABELS = { "the-paper-trail": "The paper trail", "the-tallies": "The tallies", about: "About" };
/* Header dropdowns (author, fifth batch, 2026-09-23): a disclosure per
 * section — a button with aria-expanded controlling a list of links, not
 * role=menu — so every page is two clicks from anywhere. The tab's label
 * stays a link to its landing page. Click, tap, Enter and Space toggle
 * (native button behaviour), ArrowDown opens and moves to the first link,
 * Escape closes and returns focus to the button, and a click outside the
 * header closes every menu. Hover opens one in CSS only, as an enhancement.
 * At phone width the three stack inside one collapsible nav. */
const menuButton = (section) => document.getElementById("toggle-" + section);
const menuList = (section) => document.getElementById("menu-" + section);
function setMenu(section, open) {
  const button = menuButton(section);
  const list = menuList(section);
  if (!button || !list) return;
  button.setAttribute("aria-expanded", String(open));
  list.toggleAttribute("hidden", !open);
}
function closeMenus(except) {
  Object.keys(SECTIONS).forEach((section) => section !== except && setMenu(section, false));
}
function openMenu(section) {
  closeMenus(section);
  setMenu(section, true);
}
function fillMenus() {
  Object.keys(SECTIONS).forEach((section) => {
    const list = menuList(section);
    if (list)
      list.innerHTML = SUB_PAGES[section]
        .map((s) => `<li><a href="${esc(s.href(""))}" data-sub="${s.page}">${esc(s.label)}</a></li>`)
        .join("");
  });
}
function wireMenus() {
  Object.keys(SECTIONS).forEach((section) => {
    const button = menuButton(section);
    const list = menuList(section);
    if (!button || !list) return;
    button.addEventListener("click", () =>
      button.getAttribute("aria-expanded") === "true" ? setMenu(section, false) : openMenu(section),
    );
    button.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        openMenu(section);
        list.querySelector("a")?.focus();
      }
    });
    list.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        setMenu(section, false);
        button.focus();
      }
    });
  });
  const toggle = document.getElementById("nav-toggle");
  toggle?.addEventListener("click", () => {
    const open = toggle.getAttribute("aria-expanded") !== "true";
    toggle.setAttribute("aria-expanded", String(open));
    document.getElementById("site-nav")?.toggleAttribute("data-open", open);
  });
  document.addEventListener?.("keydown", (event) => {
    if (event.key === "Escape") closeMenus();
  });
  document.addEventListener?.("click", (event) => {
    if (!event.target.closest?.("header")) closeMenus();
  });
}
/* The second bar belongs to a section, on every page of it, its landing page
 * included; the landing page and the overview aside, not the bar, say what
 * the order means. */
function drawStepBar(page, id, params) {
  const bar = document.getElementById("step-bar");
  if (!bar) return;
  const section = sectionOf(page);
  const code =
    page === "project"
      ? projects.find((p) => p.id === decodeURIComponent(id || ""))?.country
      : ["entries", "on-the-record", "funding"].includes(page)
        ? id
        : params.get("country");
  const html = section ? subBar(section, page, code) : "";
  bar.innerHTML = html;
  bar.setAttribute("aria-label", SECTION_LABELS[section] || "Pages");
  bar.toggleAttribute("hidden", !html);
}
function pageTitle(page, id) {
  const name = country(id)?.name;
  return (
    (page === "funding" && id
      ? name || "Country"
      : (page === "entries" || page === "on-the-record") && id
        ? `${name || "Country"}: ${page === "on-the-record" ? "statements" : "document rows"}`
        : TITLES[page] || "Page not found") + " · JETP Observatory"
  );
}
/* The section's own page: what each step holds, one line each. */
function paperTrailPage() {
  main.innerHTML =
    header(
      "Follow a number back to its document",
      "Start with a project, amount or count and follow its links to the documents behind it. You can also start with a document and see what we recorded from it; these pages show different views of the same material, so their row counts should not be added together.",
    ) +
    `<ol class="trail-intro">${STEPS.map((s) => `<li><a href="${s.href("")}"><strong>${esc(s.label)}</strong></a> ${esc(STEP_NOTES[s.page])}</li>`).join("")}</ol>` +
    `<p>For example, South Africa's <a href="#document-rows/ZAF?row=1">ACTIP001 register row</a> names the Skills Research Programme and prints USD 2.28 million. A <a href="#statements/ZAF">separate statement</a> shows that amount at the signed milestone, citing the same register row (ACTIP001). One document row need not yield exactly one statement.</p><p class="note">The words are defined in the <a href="#glossary">Glossary</a>.</p>`;
}
const STEP_NOTES = {
  documents: "Each report, register and plan we tried to retrieve, linked to its publisher and to the copy we read when available.",
  entries: "Selected rows from registers, annexes and lists, preserving document wording.",
  "on-the-record": "Reported amounts, dates and statuses, plus links between projects and documents.",
  projects: "Named projects, programmes and components, which can overlap.",
  funding: "Published headlines and separate financing statements for each partnership.",
  "whos-who": "Funders and operators named by project documents, with reviewed alternative names.",
};
function render() {
  const raw = location.hash.slice(1) || "overview";
  const [path, query] = raw.split("?"),
    params = new URLSearchParams(query || "");
  const [publicPage, id] = path.split("/");
  const page = INTERNAL[publicPage] || (Object.hasOwn(CANONICAL, publicPage) ? "" : publicPage);
  markNav(page);
  closeMenus();
  drawStepBar(page, id, params);
  if (page === "overview") overviewPage();
  else if (page === "the-paper-trail") paperTrailPage();
  else if (page === "funding") id ? countryPage(id) : countriesPage();
  else if (page === "projects") cataloguePage(params);
  else if (page === "project") projectPage(decodeURIComponent(id || ""));
  else if (page === "comparisons") comparisonPage(params);
  else if (page === "on-the-record") id ? inventoryPage(id, params, "record") : evidencePage();
  else if (page === "release-history") editionHistoryPage();
  else if (page === "documents") documentsPage(params);
  else if (page === "entries") id ? inventoryPage(id, params, "") : entriesPage();
  else if (page === "whos-who") whosWhoPage(params);
  else if (page === "counts") numbersPage();
  else if (page === "glossary") glossaryPage(params.get("term"));
  else if (page === "about") aboutPage();
  else if (page === "who-we-are") whoWeArePage();
  else if (page === "methods") methodsPage();
  else notFound();
  document.title = pageTitle(page, id);
  window.scrollTo(0, 0);
  // A link to one term opens the Glossary at its entry.
  if (page === "glossary" && params.get("term"))
    document.getElementById("term-" + params.get("term"))?.scrollIntoView?.();
}
/* The staged copies' index, where this server has one (see archiveServed).
 * Its absence is the public site's normal state, not an error. */
const stagedIndex = () =>
  fetch("documents/index.json")
    .then((response) => (response.ok ? response.json() : null))
    .catch(() => null);
/* Said once per page that lists documents: what the links are, and whether
 * this server also holds copies. */
function copiesCallout(lead) {
  const held = stagedCopies.size
    ? " This local preview also opens the archived copies staged in <code>documents/</code> by <code>make jetp-observatory-documents</code>; the public site serves none."
    : " This site serves no copy of the documents.";
  return `<div class="callout" data-staged-copies="${stagedCopies.size}">${lead ? esc(lead) + " " : ""}Each document links to the page we collected it from, with the collection date and the SHA-256 fingerprint of the bytes we read. Page numbers refer to those bytes; the publisher's current file may differ.${held} Where the Internet Archive holds a copy of that page, a dated “Web Archive copy” link sits beside it; once a periodic check finds the publisher's link dead, the copy comes first. Documents retain their publishers' rights.</div>`;
}
const load = async (file) => {
  const response = await fetch("data/" + file + ".json");
  if (!response.ok) throw Error(`${file}: ${response.status}`);
  return response.json();
};
async function start() {
  try {
    let termsView, statusCrosswalkView, staged, captures, checks;
    [overview, comparison, documentsData, editions, evidence, m1a, termsView, statusCrosswalkView, partyNames, staged, captures, checks] = await Promise.all([
      load("overview"),
      load("comparison"),
      load("documents"),
      load("editions").catch(() => ({ editions: [] })),
      load("reviewed-evidence").catch(() => ({ records: [], analytical_snapshot: { status: "not available" } })),
      load("m1a/manifest"),
      load("ontology/terms"),
      load("ontology/status-crosswalk"),
      load("party-names"),
      stagedIndex(),
      load("web-archive").catch(() => ({ captures: [] })),
      load("publisher-links").catch(() => ({ checks: [] })),
    ]);
    stagedCopies = new Set(staged?.objects || []);
    webArchive = indexBy(captures.captures, "url");
    linkChecks = indexBy(checks.checks, "url");
    ontology = readOntology(termsView, statusCrosswalkView);
    countries = Object.fromEntries(
      await Promise.all(
        overview.countries.map(async (c) => [c.code, await load(c.code)]),
      ),
    );
    projects = Object.values(countries).flatMap((c) => c.projects);
    documentIndex = indexDocuments(documentsData.documents);
    documentsBySha = indexDocumentsBySha256(documentsData.documents);
    fillMenus();
    wireMenus();
    // "Skip to content" moves focus to the page, not the address: #main is
    // not a route, and following it re-rendered the fallback page instead.
    document.querySelector?.(".skip")?.addEventListener("click", (event) => {
      event.preventDefault();
      main.focus();
    });
    window.addEventListener("hashchange", render);
    render();
  } catch (error) {
    main.innerHTML = `<div class="error"><h1>The snapshot could not load.</h1><p>Serve this directory with a local HTTP server, then reload.</p><p>${esc(error.message)}</p></div>`;
    console.error(error);
  }
}
start();
