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
  /^https?:\/\//i.test(value || "") ? value : "#how-we-did-this";
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
  Signed: "#24634f",
  Approved: "#589480",
  "Registered financing": "#99b299",
  Mou: "#d7b46d",
  Announced: "#e2c896",
  Need: "#bc9c7d",
  "Not documented": "#dce0d5",
};
let overview, countries, comparison, editions, evidence, m1a, projects, documentsData, documentIndex, documentsBySha;
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
 * top is two bars (author's cold read, 2026-09-23). The header holds the four
 * sections as tabs. On a paper-trail page a second bar, the step bar, holds
 * the steps of D — their codes stay in data attributes — with the current one
 * marked: it is the page's position indicator, and its neighbours are the
 * links one step either way. The last three steps are parallel siblings. A
 * page scoped to a country shows it at the bar's right as a removable chip,
 * and every step link keeps the country. */
const SECTIONS = {
  "the-paper-trail": ["the-paper-trail", "documents", "entries", "on-the-record", "projects",
    "project", "funding", "whos-who"],
  "by-the-numbers": ["by-the-numbers", "historical-comparison"],
  glossary: ["glossary"],
  "how-we-did-this": ["how-we-did-this", "release-history"],
};
const sectionOf = (page) =>
  Object.keys(SECTIONS).find((section) => SECTIONS[section].includes(page)) || "";
const STEPS = [
  { step: "D1", page: "documents", label: "Documents",
    href: (code) => (code ? `#documents?country=${code}` : "#documents") },
  { step: "D2", page: "entries", label: "Entries",
    href: (code) => (code ? `#entries/${code}` : "#entries") },
  { step: "D3", page: "on-the-record", label: "On the record",
    href: (code) => (code ? `#on-the-record/${code}` : "#on-the-record") },
  { step: "D4", page: "projects", label: "Projects",
    href: (code) => (code ? `#projects?country=${code}` : "#projects") },
  { step: "D4", page: "funding", label: "Funding",
    href: (code) => (code ? `#funding/${code}` : "#funding") },
  { step: "D4", page: "whos-who", label: "Who's who",
    href: (code) => (code ? `#whos-who?country=${code}` : "#whos-who") },
];
// A code the site does not know is no code: the bar falls back to the whole
// site rather than carry an address fragment into an href.
const knownCountry = (code) => (code && overview.countries.some((c) => c.code === code) ? code : "");
function stepBar(page, rawCode) {
  const current = page === "project" ? "projects" : page;
  const code = knownCountry(rawCode);
  const link = (s) =>
    `<a href="${esc(s.href(code))}" data-step="${s.step}"${s.page === current ? ' aria-current="page"' : ""}>${esc(s.label)}</a>`;
  const chip = code
    ? `<span class="scope-chip">${esc(country(code).name)} <a href="#${esc(current)}" aria-label="Remove the ${esc(country(code).name)} filter" data-scope-remove="${esc(code)}">×</a></span>`
    : "";
  return `<ol data-trail-step="${STEPS.find((s) => s.page === current)?.step || ""}">${STEPS.slice(0, 3)
    .map((s) => `<li>${link(s)}</li>`)
    .join("")}<li class="siblings">${STEPS.slice(3).map(link).join("")}</li></ol>${chip}`;
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
/* The four counts the landing page and By the numbers share, each counted by
 * us and linked to what it counts. */
function headlineCounts(tag) {
  return [
    computedMetric(projects.length, "named projects", "projects, programmes and components of the four portfolios", "#projects", tag),
    computedMetric(overview.historical_count, "closed World Bank operations", "same four countries, before each partnership", "#historical-comparison", tag),
    computedMetric(overview.source_count, "documents cited", "the curated collection the country pages cite", "#documents", tag),
    computedMetric(undisclosedCount(), "unpublished project identities", "counted in the countries' own disclosures", "#funding", tag),
  ].join("");
}
function overviewPage() {
  main.innerHTML = `<section class="hero"><div><p class="eyebrow">From promise to progress</p><h1>Where do the<br><em>JETPs stand?</em></h1><p class="lede">Four partnerships to support a just energy transition. Explore what has been planned, financed and documented — and what remains to be seen.</p><div class="actions"><a class="button" href="#funding">Explore the four partnerships ↗</a><a class="text-link" href="#documents">Follow the paper trail →</a></div></div><aside class="evidence-box"><p class="eyebrow">By the numbers</p><div class="stat-grid">${headlineCounts("stat")}</div><div class="box-foot">Documents collected through ${date(overview.provenance.cutoff)}.<br>Each publisher's report keeps its own date. <a href="#by-the-numbers">All the numbers</a> · <a href="#how-we-did-this">How we did this</a></div></aside></section>
<section class="section"><div class="section-head"><div><p class="eyebrow">Country snapshot</p><h2>A shared ambition.<br>Four different trajectories.</h2></div><p>Each national figure is shown as its publisher reported it, with its own date and definition.<br>Allocation, approval and payment are different milestones.</p></div><div class="country-grid">${overview.countries.map(card).join("")}</div></section>
<section class="section"><div class="section-head"><div><p class="eyebrow">Reading across the documents</p><h2>What the documents tell us</h2></div></div><div class="insight-grid"><article class="insight"><span class="number">01</span><h3>Financing moves through different channels</h3><p>South Africa reports substantial allocations; Indonesia identifies approved programmes, investments and grants. Their headline figures measure different milestones, so there is no single comparable “delivery rate”.</p><a class="text-link" href="#funding">Read the four partnerships →</a></article><article class="insight"><span class="number">02</span><h3>A plan is not yet a transaction</h3><p>Senegal's portfolio mixes investment needs, programmes and components. Viet Nam's 2025 portfolio leaves most project identities unnamed. These gaps matter when interpreting totals.</p><a class="text-link" href="#funding/SEN">Explore the Senegal portfolio →</a></article><article class="insight"><span class="number">03</span><h3>Speed needs a historical reference</h3><p>${overview.historical_count} closed energy-related World Bank operations provide context from the same countries. Compare instruments and vintages before interpreting their financing windows as a benchmark.</p><a class="text-link" href="#historical-comparison">Explore the comparison pool →</a></article></div></section>
<section class="section"><div class="section-head"><div><p class="eyebrow">The paper trail</p><h2>From a figure back to its page</h2></div><p>Every project on these pages can be followed to the document it comes from, and every document to what relies on it.</p></div><ol class="trail-intro"><li><a href="#documents"><strong>Documents</strong></a> Each report, register and plan we tried to retrieve, with an archived copy where we have one.</li><li><a href="#entries"><strong>Entries</strong></a> Rows of a register, lines of a plan annex, as the document prints them.</li><li><a href="#on-the-record"><strong>On the record</strong></a> What a publisher said in one document, read as a date, a status or an amount, according to that publisher.</li><li><a href="#projects"><strong>Projects</strong></a>, <a href="#funding"><strong>Funding</strong></a> and <a href="#whos-who"><strong>Who's who</strong></a> The projects, the partnerships and the organisations those statements are about.</li></ol><p class="note">The words are defined in the <a href="#glossary">Glossary</a>. Numbers we counted, rather than read in a document, are gathered <a href="#by-the-numbers">by the numbers</a>.</p></section>
<div class="comparison-banner"><div><p class="eyebrow">A longer view</p><h2>What did ordinary energy<br>projects look like?</h2><p>Browse the historical pool by country, instrument and approval year. See the distribution behind a typical financing window, not just an average.</p></div><div><p class="note">Administrative closure is not a measure of physical completion. This first pool is descriptive; the separate lifecycle research programme is a separate research task.</p><a class="button" href="#historical-comparison">Explore ${overview.historical_count} closed operations ↗</a></div></div>`;
}
function countriesPage() {
  main.innerHTML =
    header(
      "The four partnerships",
      "Each partnership is an agreement between a country and its funders. Read each on its own terms: what was pledged, what its publishers report, and how complete the public paper trail is.",
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
function countryPage(code) {
  const d = countries[code],
    c = country(code);
  if (!d) return notFound();
  const refs = Object.keys(d.sources).length;
  main.innerHTML = `<div class="page-head"><div class="breadcrumb"><a href="#funding">Funding</a> › ${esc(c.name)}</div><h1>${esc(c.name)}</h1>${titleBlock(esc(c.headline_detail))}${countryTabs(code)}</div><div class="callout published"><h3>${esc(c.headline)}</h3><p><span class="published-tag">As published</span> ${esc(c.stage_label)} at ${date(c.headline_date)} · ${according(c.headline_source_record)} · ${sourceLink(c.headline_source_record, "Read the document")}</p></div><div class="metrics">${computedMetric(c.named, "named projects", "this partnership's portfolio", `#projects?country=${code}`)}${computedMetric(c.undisclosed, "unpublished identities", "counted in the country's own disclosure, which lists none of them by name")}${computedMetric(refs, "documents cited", "by this country's projects and headline", "#documents")}<div class="metric published"><strong>${esc(c.pledge_label)}</strong><span>Original political pledge</span><small><span class="published-tag">As published</span> · announced ${date(c.signed_on)}</small></div></div><div class="split"><div><h2>Reading this portfolio</h2><div class="markdown">${markdown(d.editorial)}</div><div class="actions"><a class="button" href="#projects?country=${code}">Explore ${c.named} projects ↗</a><a class="text-link" href="#historical-comparison?country=${code}">Historical reference →</a></div></div><div class="panel"><h3>Furthest financing milestone on the record</h3>${stageChart([c])}<p class="note" style="margin-top:20px"><span class="computed-tag">Our calculation</span> Each named project once, at the most advanced financing milestone on the record for it — not the milestone of every tranche. Programmes overlap, so project amounts are never added.</p><h3 style="margin-top:25px">Portfolio composition</h3>${technologyChart(d.projects)}<p class="note"><span class="computed-tag">Our calculation</span> Named projects by the theme or technology their documents give.</p></div></div>${code === "VNM" ? vietnamSideBySide(d) : ""}<section class="section" style="margin-top:35px"><div class="section-head"><h2>Inside the portfolio</h2><a class="text-link" href="#projects?country=${code}">View all →</a></div>${projectTable(d.projects.slice(0, 8))}<div class="downloads"><a class="button light" href="#entries/${code}">Read the entries, row by row ↗</a><a class="button light" href="data/${code}.json" download>Download ${c.name} data ↓</a></div></section>`;
}
/* Rendering only: both figures already exist — the RMP row count in the M1a
 * manifest and the portfolio record count in the country view — and no field
 * joins them. The two columns are two objects of two dates, shown side by side
 * because that is the recipe of ticket 0834; matching a 2023 position to a 2025
 * record is the matching work of ticket 0833, not this page's. */
function vietnamSideBySide(d) {
  const rmp = m1a.countries.VNM;
  const source = rmp.sublayers[0]?.source_id || "vnm-rmp-2023";
  return `<section class="section" id="vnm-side-by-side" style="margin-top:35px"><div class="section-head"><h2>Two lists, kept apart</h2></div><div class="split"><div class="panel" data-side="rmp-2023"><h3>RMP 2023 initial table</h3><p><strong>${fmt(rmp.row_count)}</strong> positions listed in the annexes of the Resource Mobilisation Plan, document <code>${esc(source)}</code>. <span class="computed-tag">Our calculation</span></p><a class="text-link" href="#entries/VNM">Browse the ${fmt(rmp.row_count)} positions →</a></div><div class="panel" data-side="portfolio-2025"><h3>2025 portfolio</h3><p><strong>${fmt(d.record_count)}</strong> projects: ${fmt(d.projects.length)} named and ${fmt(d.undisclosed)} unpublished identities. <span class="computed-tag">Our calculation</span></p><a class="text-link" href="#projects?country=VNM">Browse the named projects →</a></div></div><p class="note" style="margin-top:15px">No link between the 2023 table and the 2025 portfolio is established here: a position in the plan and a project in the portfolio are neither matched nor counted together. Matching them is the work of ticket 0833.</p></section>`;
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
 *   opts.columns  [{ label, cell(row) }] one <th>/<td> pair each; `cell`
 *                 returns an already-esc()-escaped HTML string.
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
      .map((c) => `<th>${esc(c.label)}</th>`)
      .join("")}</tr></thead><tbody>${visible
      .map(
        (row) =>
          `<tr>${opts.columns.map((c) => `<td>${c.cell(row)}</td>`).join("")}</tr>`,
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
      f.key,
      document.getElementById(`${id}-filter-${f.key}`).value,
    ]);
    return rows.filter(
      (row) =>
        (!q || opts.search.text(row).includes(q)) &&
        chosen.every(([key, value]) => !value || row[key] === value),
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
const documentHref = (entry, page) =>
  entry.local_path ? entry.local_path + (page ? "#page=" + page : "") : null;
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
  const href = row.pdf_page ? documentHref(entry, row.pdf_page) : null;
  return href
    ? ` · <a href="${esc(href)}" data-extracted-page="${esc(key)}" target="_blank" rel="noopener">PDF page ${row.pdf_page} ↗</a>`
    : "";
}
function extractedItem(row, entry) {
  if (row.product === "m1a")
    return `<li><a href="#entries/${esc(row.country)}?row=${Number(row.row)}"><code>${esc(row.source_row_id)}</code></a> ${esc(row.label || "Identity not published")}${extractedPageLink(row, entry, row.source_row_id)}<small>${esc(row.source_layer)} · ${esc(row.evidence_locator || "No locator recorded")}</small></li>`;
  return `<li><a href="#entries/${esc(row.country)}">${esc(OBSERVATION_KINDS[row.kind] || row.kind)} <code>${esc(row.id)}</code></a> · ${pill(row.verification)}${extractedPageLink(row, entry, row.id)}<small>${esc(row.table)} · <a href="#project/${encodeURIComponent(row.project_id)}">${esc(row.project_id)}</a> · ${esc(row.locator || "No locator recorded")}</small></li>`;
}
function factItem(fact) {
  return fact.record_id
    ? `<li><a href="#on-the-record">${esc(fact.label)}</a><small>Reviewed item on the record · ${esc(fact.status.replaceAll("_", " "))} · ${esc(country(fact.country)?.short || fact.country)}</small></li>`
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
const PRODUCT_LABELS = { ledger: "On the record", m1a: "Entries" };
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
const archivedCopyLink = (entry, page) =>
  `<a href="${esc(documentHref(entry, page))}" data-document-id="${esc(entry.row_key)}" target="_blank" rel="noopener">Open archived copy ↗</a>`;
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
      const archived = document.getElementById("archived-" + entry.row_key);
      if (archived && entry.local_path && page)
        archived.innerHTML = archivedCopyLink(entry, page);
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
        cell.innerHTML = emptyNote("extracted-count", "unavailable", `The ${esc(entry.country)} entries and items on the record could not load (${esc(error.message)}). What this document yielded is in the <a href="#entries/${esc(entry.country)}">${esc(entry.country)} entries</a>, under <code>${esc(entry.id)}</code>.`);
    });
  return `<span id="${esc(key)}" class="note">Loading what this document yielded…</span>`;
}
function documentsPage(params) {
  const rows = documentsData.documents;
  const values = (key) =>
    [...new Set(rows.map((r) => r[key]).filter(Boolean))].sort();
  // Opens at the file's own first page until the join says otherwise: the
  // link sits in a placeholder extractionCell() refills with the first page
  // the extracted rows agree on (ticket 0857), never with a page of its own.
  const archived = (r) =>
    r.local_path
      ? `<span id="archived-${esc(r.row_key)}">${archivedCopyLink(r)}</span>`
      : `<span class="note">${esc(r.error || "Not in the local snapshot")}</span>`;
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
      { label: "Size", cell: (r) => esc(byteSize(r.size_bytes)) },
      { label: "Archived copy", cell: archived },
      { label: "Entries and items on the record · relied on by", cell: extractionCell },
      {
        label: "Origin",
        cell: (r) =>
          r.url
            ? `<a href="${esc(cleanURL(r.url))}" target="_blank" rel="noopener">Publisher ↗</a>`
            : '<span class="note">No address recorded</span>',
      },
    ],
    empty: "No documents match these filters.",
    resultNoun: "documents",
    pageSize: 50,
  });
  main.innerHTML =
    header(
      "Every collection attempt, kept on file",
      "The collection registry lists each document we tried to retrieve, with the outcome recorded at the time. A blocked or failed attempt stays listed; it does not show that the document does not exist.",
    ) +
    `<div class="callout"><strong>Archived copies open locally only.</strong> The preview serves them from <code>documents/</code> after <code>make jetp-observatory-documents</code>. A published release carries this registry and the publisher's address, never the archived bytes; documents retain their publishers' rights.</div>` +
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
/* A row's own fields, listed under whichever summary its caller names — an
 * inventory row and a ledger observation share every column but the label. */
function rowDetail(row, summary, open) {
  return `<details${open ? " open" : ""}><summary>${summary}</summary><dl class="facts">${Object.entries(
    row,
  )
    .map(
      ([key, value]) =>
        `<dt>${esc(key)}</dt><dd>${esc(value === "" || value == null ? "Not published" : value)}</dd>`,
    )
    .join("")}</dl></details>`;
}
function inventoryRowDetail(row, open) {
  return rowDetail(row, esc(row.label || "Identity not published"), open);
}
/* One evidence cell for both stage-two tables: the locator as a link into the
 * archived copy when the snapshot holds one, as text otherwise. The callers
 * differ only in how they find the document entry and what they say when
 * there is none. */
function evidenceLink(locator, entry, pdfPage, dataAttr, dataValue, noEntry) {
  const text = esc(locator || "No locator recorded");
  if (!entry)
    return `<span class="note">${text}${noEntry ? "<br>" + noEntry : ""}</span>`;
  const href = documentHref(entry, pdfPage);
  return href
    ? `<a href="${esc(href)}" ${dataAttr}="${esc(dataValue)}" target="_blank" rel="noopener">${text}${pdfPage ? " · PDF page " + pdfPage : ""} ↗</a>`
    : `<span class="note">${text}<br>${esc(entry.error || "Not in the local snapshot")}</span>`;
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
          `<div class="metric computed" data-unit="items on the record" data-observation-table="${esc(table)}"><strong>${fmt(count)}</strong><span>${esc(table)}</span><small><span class="computed-tag">Our calculation</span> · items on the record for ${esc(c?.short || code)}</small></div>`,
      )
      .join("")}</div>` +
    `<p class="note">These items and the country's entries, one step back on the trail, are two extractions of the same documents under two schemas. They are read separately and never added together: one item on the record and one entry can describe the same paragraph of the same file. Each figure counts one table, for this country alone.</p>`
  );
}
function observationDetail(row) {
  return rowDetail(
    row,
    `${esc(OBSERVATION_KINDS[row.kind] || row.kind)} · ${esc(observationId(row))}`,
  );
}
/* The fingerprint is resolved once, in the generator, so the row addresses its
 * document directly. A source the collection never archived keeps its locator
 * as text, exactly as an unresolved inventory row does. */
function observationEvidence(row) {
  return evidenceLink(
    row.locator,
    row.sha256 ? documentsBySha[row.sha256] : null,
    row.pdf_page,
    "data-observation-id",
    observationId(row),
    "No archived copy of this source",
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
    empty: "No items on the record match these filters.",
    resultNoun: "items on the record",
    pageSize: 50,
  });
}

/* Ticket 0857: the Documents page cites a row by its rank in this export, and
 * #entries/<CODE>?row=N opens the page on that one row, unfolded, with the
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
    note: emptyNote("inventory-focus", focus, `Row ${fmt(focus)} of the ${fmt(rows.length)} rows in this export, as the Documents page cites it. <a href="#entries/${code}">Show all ${fmt(rows.length)} rows →</a>`),
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
      { label: "Reported status", cell: (row) => pill(row.reported_status) },
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
      `<div class="page-head"><h1>${name}: on the record</h1>${titleBlock("Each item is one statement a publisher made in one of this country's documents, read under the ledger's schema. These items and the entries of the same documents are two separate readings: they are not comparable, and never added together.")}</div>` +
      `<section id="panel-observations">` +
      observationTotals(observations, code) +
      observationsPanel.head +
      `<div class="downloads"><a class="button light" href="data/observations/${code}.json" download>Download the ${code} items on the record (JSON) ↓</a></div></section>`;
    observationsPanel.mount();
    return;
  }
  main.innerHTML =
    `<div class="page-head"><h1>${name}: entries</h1>${titleBlock("Each entry is one row of this country's documents, as the document prints it. The entries and the items on the record of the same documents are two separate readings: they are not comparable, and never added together.")}</div>` +
    `<section id="panel-inventory">` +
    inventoryUnknowns(details) +
    `<div class="callout">Each entry opens its archived document, at its PDF page where the document gives one. Archived copies open locally only; a published release carries the registry and the publisher's address.</div>` +
    note +
    table.head +
    `<div class="downloads"><a class="button light" href="data/m1a/${code}.csv" download>Download the ${code} entries (CSV) ↓</a></div></section>`;
  table.mount();
}
/* #entries/<CODE> and #on-the-record/<CODE>: two steps over the same loaded
 * views; `tab` is "record" for the second. Rendered only if the reader is
 * still on one of this country's two pages when the views arrive. */
function inventoryPage(code, params, tab) {
  if (!m1a.countries[code]) return notFound();
  main.innerHTML = `<p class="note">Loading the ${esc(code)} entries…</p>`;
  const focus = Math.trunc(Number(params.get("row"))) || 0;
  stageTwo(code)
    .then(({ rows, observations }) => {
      const here = location.hash.slice(1).split("?")[0];
      if (here === "entries/" + code || here === "on-the-record/" + code)
        renderInventory(code, rows, observations, focus > 0 ? focus : 0, tab);
    })
    .catch((error) => {
      main.innerHTML = `<div class="error"><h1>The ${esc(code)} entries could not load.</h1><p>${esc(error.message)}</p></div>`;
    });
}
function cataloguePage(params) {
  main.innerHTML =
    header(
      "Follow a project to its documents",
      "Search the named portfolio. Each project links to what is on the record about it, to its timeline and to the documents behind them.",
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
      section().innerHTML = emptyNote("evidence-count", "unavailable", `The ${esc(p.country)} items on the record could not load (${esc(error.message)}). They are the items <a href="#on-the-record/${esc(p.country)}">on the record for this country</a> addressed to <code>${esc(p.id)}</code>.`);
    });
}
/* A source card opens the archived copy where the registry holds one. Resolved
 * by source identifier through the same ranked index as an inventory row: the
 * card names a source, not a fingerprint. Text only where nothing is archived,
 * the expected case of the public edition. */
function archivedCopy(id) {
  const href = documentIndex[id] ? documentHref(documentIndex[id]) : null;
  return href
    ? `<small><a href="${esc(href)}" data-archived-source="${esc(id)}" target="_blank" rel="noopener">Open archived copy ↗</a></small>`
    : "";
}
function projectPage(id) {
  const p = projects.find((p) => p.id === id);
  if (!p) return notFound();
  const c = country(p.country),
    sources = countries[p.country].sources;
  main.innerHTML = `<div class="page-head"><div class="breadcrumb"><a href="#projects">Projects</a> › ${esc(p.name)}</div><h1>${esc(p.name)} <span class="badge" data-review-state="${esc(p.coverage)}">Review state · ${esc(p.coverage.replaceAll("_", " "))}</span></h1><p class="lede">${esc(p.location)}</p>${pill(p.finance_stage === "Not documented" ? "Financial events not yet coded" : p.finance_stage)}</div><div class="project-layout"><div><h2>Essential features</h2><dl class="facts"><dt>Country</dt><dd><a href="#funding/${c.code}">${esc(c.name)}</a></dd><dt>Theme / technology</dt><dd>${esc(p.technology)}</dd><dt>Operator</dt><dd>${esc(p.operator)}</dd><dt>Funders</dt><dd>${esc(p.funders.join("; ") || "See the individual documents; no funder entry yet")}</dd><dt>Project ID</dt><dd>${esc(p.id)}</dd><dt>Document follow-up</dt><dd>${esc(p.coverage.replaceAll("_", " "))}</dd></dl><p class="note">${esc(p.notes)}</p><section class="section"><h2>Documented timeline</h2><p class="note">Events and dated status reports are distinguished. A financing amount at approval and again at signature is not two separate amounts to add.</p>${p.events.length ? `<ol class="timeline">${p.events.map((e) => eventView(e, sources)).join("")}</ol>` : '<div class="callout">No financial or implementation event has yet been added to this project\'s timeline. Its documents may establish more; absence from this timeline is not zero progress.</div>'}</section><section class="section" id="project-evidence"><h2>On the record about this project</h2><p class="note">What the ledger read about this project, statement by statement, each according to its publisher and opening its archived document where the collection holds one. These items are never added together.</p><div id="project-evidence-rows"><p class="note">Loading what is on the record for ${esc(c.short)}…</p></div></section>${p.claims.length ? `<section class="section"><h2>What other documents say</h2>${p.claims.map((r) => `<article style="margin:20px 0"><p>${esc(r.claim_summary)}</p><p class="note">${according(sources[r.source_id])} · Match verdict: ${esc(r.match_status.replaceAll("_", " "))} · ${esc(r.notes)}</p>${sourceLink(sources[r.source_id], "Read the document")} <span class="date-tag">${esc(r.section)}</span></article>`).join("")}</section>` : ""}</div><aside><div class="panel"><h3>Documents</h3><p class="note">${esc(p.coverage_note)}</p><ul class="sources">${p.sources
    .map((id) => {
      const s = sources[id];
      return s
        ? `<li>${sourceLink(s)}<small>${esc(s.publisher)} · ${esc(s.collection.replaceAll("_", " "))}</small>${s.retrieved ? `<small>Retrieved ${esc(s.retrieved.slice(0, 10))}</small>` : ""}${archivedCopy(id)}${sourceAdjudication(p, id)}</li>`
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
      "A reference beyond the JETPs.",
      "Explore closed World Bank energy-related operations approved before each country’s partnership. A descriptive reference pool for the next step of the research.",
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
function evidenceDepthSummary() {
  const depth = evidence.evidence_depth;
  if (!depth) return "";
  const staged = depth.structured_atomic_observations || {};
  const countries = staged.by_country || {};
  const countryCounts = ["ZAF", "IDN", "VNM", "SEN"]
    .filter((code) => countries[code] != null)
    .map((code) => `${esc(country(code)?.short || code)} ${fmt(countries[code])}`)
    .join(" · ");
  return `<section class="section" aria-label="What the data work added"><div class="section-head"><div><p class="eyebrow">What the data work added</p><h2>Four tables, four counts.</h2></div><p>These are distinct tables. They are not a common total.</p></div><div class="metrics">${computedMetric(depth.canonical_named_records, "named projects", "the four country portfolios", "#projects")}${computedMetric(depth.frozen_source_documents, "archived documents", "the curated collection", "#documents")}${computedMetric(depth.reviewed_canonical_records, "reviewed items on the record", "published one by one, never added", "#on-the-record")}${computedMetric(staged.total, "structured readings", "an analysis snapshot, not published on these pages")}</div><div class="callout"><h3>A separate reading, kept apart</h3><p>${fmt(staged.total)} structured readings: ${esc(countryCounts)}. This includes ${fmt(staged.vnm_rmp_positions)} Viet Nam RMP positions. They are not matched operations, payments or reviewed items, and this snapshot is not published on these pages.</p><p>This figure is not the count of items on the record for each country. That tab reads the ledger tables (events, implementation events, project–document links) as recorded; this snapshot is a separate reading of the same documents by the analysis pipeline. Two populations, two labels, never added together.</p></div></section>`;
}
function numbersPage() {
  main.innerHTML =
    header(
      "What we counted, and from what",
      "Every number on this page is counted by us from the paper trail, not printed by a publisher. Each states its unit and what it covers, and links to what was counted. Publishers' own figures stay on their pages, with their publisher and date.",
    ) +
    `<div class="metrics">${headlineCounts("metric")}</div>` +
    `<section class="section split"><div class="panel"><h3>How far does the financing go on the record?</h3><p class="note"><span class="computed-tag">Our calculation</span> Each named project once, at the most advanced financing milestone on the record for it.</p>${stageChart(overview.countries)}<p class="note" style="margin-top:20px">Registered financing is not independently verified signature or payment. “Not coded in ledger” can coexist with financing described in a document.</p><a class="text-link" href="#projects">See the projects counted →</a></div><div class="panel"><h3>What is in the portfolio?</h3><p class="note"><span class="computed-tag">Our calculation</span> Named projects by the theme or technology their documents give. Categories keep the documents' differences.</p>${technologyChart(projects)}<a class="text-link" href="#projects">Filter and explore the projects →</a></div></section>` +
    `<section class="section"><div class="section-head"><div><p class="eyebrow">Country by country</p><h2>Each partnership, counted apart</h2></div><p>Counts are not added across countries: the portfolios define a project differently.</p></div><div class="table-wrap"><table><thead><tr><th>Country</th><th>Named projects <small class="computed-tag">Our calculation</small></th><th>Unpublished identities <small class="computed-tag">Our calculation</small></th><th>Entries in the export <small class="computed-tag">Our calculation</small></th></tr></thead><tbody>${overview.countries.map((c) => `<tr><td><a href="#funding/${c.code}">${esc(c.name)}</a></td><td><a href="#projects?country=${c.code}">${fmt(c.named)}</a></td><td>${fmt(c.undisclosed)}</td><td><a href="#entries/${c.code}">${fmt(m1a.countries[c.code]?.row_count ?? 0)}</a></td></tr>`).join("")}</tbody></table></div></section>` +
    evidenceDepthSummary() +
    `<section class="section"><h2>Accounts</h2><p>No account of pledges, allocations and payments is computed in this release: nothing on these pages adds amounts across documents, or a project's amounts to a partnership's headline.</p><h2>A historical reference</h2><p><a class="text-link" href="#historical-comparison">${fmt(overview.historical_count)} closed World Bank operations in the same four countries →</a> Their financing windows are counted, with the median, for the selection you choose.</p></section>`;
}
function editionHistoryPage() {
  const rows = editions.editions;
  main.innerHTML = header(
      "What changed, and what did not.", "Each release is frozen after review. A failed refresh remains a recorded gap and never removes a document from an earlier download.") +
    `<div class="table-wrap"><table><thead><tr><th>Release</th><th>Knowledge cutoff</th><th>Prepared</th><th>State</th><th>Published</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${esc(row.edition)}</td><td>${date(row.observation_cutoff)}</td><td>${date(row.release_prepared_date)}</td><td>${esc(row.release_state)}</td><td>${row.publication_date ? date(row.publication_date) : "Not published"}</td></tr>`).join("")}</tbody></table></div><p class="note">A correction uses a new <code>YYYY-MM-rN</code> release and preserves the prior archive. Later reports are labelled by their original event date; they are not treated as new events.</p><div class="downloads"><a class="button light" href="data/editions.json" download>Download release history ↓</a></div><p><a class="text-link" href="#by-the-numbers">What the data work added, by the numbers →</a></p>`;
}
/* A reviewed record pins a fingerprint, so its pedigree opens the archived copy
 * of those bytes and no other attempt of the same source identifier: resolved
 * by sha256, as a ledger observation is, through the same evidence cell. Text
 * where the snapshot holds no such copy. The record itself gains no field. */
function reviewedProof(proof, code) {
  return `${according(documentOf(code, proof.source_id))} · <code>${esc(proof.source_id)}</code> · ${evidenceLink(
    proof.locator,
    documentsBySha[proof.sha256] || null,
    null,
    "data-reviewed-source",
    proof.source_id,
    "No archived copy of this document",
  )} · <code>${esc(proof.sha256.slice(0, 12))}…</code>`;
}
function evidencePage() {
  const records = evidence.records || [];
  main.innerHTML =
    header(
      "What publishers said, as the ledger read it",
      "An item on the record is one statement, read from one document, and it reads according to its publisher, with the date. It is not an account, a payment total, or an estimate.",
    ) +
    `<section class="section"><div class="section-head"><div><p class="eyebrow">Country by country</p><h2>Every item on the record</h2></div><p>Each country's items are listed statement by statement, beside its entries and never added to them.</p></div><ul class="country-links">${overview.countries.map((c) => `<li><a href="#on-the-record/${c.code}">${esc(c.name)}: what is on the record →</a></li>`).join("")}</ul></section>` +
    `<section class="section"><div class="section-head"><div><p class="eyebrow">Reviewed one by one</p><h2>The national headlines</h2></div></div><div class="callout"><h3>Analytical snapshot: ${esc(evidence.analytical_snapshot?.status || "not available")}</h3><p>The comparative staging snapshot is derived research material and is not published in this preview.</p></div><div class="table-wrap"><table><thead><tr><th>Item</th><th>Country</th><th>Review state</th><th>According to · document</th><th>Reading note</th></tr></thead><tbody>${records.map((record) => `<tr data-reviewed-evidence-id="${esc(record.id)}"><td>${esc(record.label)}</td><td>${esc(country(record.country)?.name || record.country)}</td><td>${esc(record.status.replaceAll("_", " "))}</td><td>${record.evidence.map((proof) => reviewedProof(proof, record.country)).join("<br>")}</td><td>${esc(record.notes)}<br><small>Non-aggregate record.</small></td></tr>`).join("")}</tbody></table></div>${records.length ? "" : '<p class="note">No separately releasable reviewed item is available in this release. That is a coverage statement, not a sign of no activity.</p>'}<div class="downloads"><a class="button light" href="data/reviewed-evidence.json" download>Download the reviewed items ↓</a></div></section>`;
}
function entriesPage() {
  const rows = ["ZAF", "IDN", "VNM", "SEN"]
    .map((code) => {
      const item = m1a.countries[code];
      const sublayers = item.sublayers
        .map((layer) => `${esc(layer.edition)} · cutoff ${esc(layer.cutoff)}`)
        .join("<br>");
      return `<tr><td><a href="#entries/${code}">${esc(country(code)?.name || code)}</a></td><td>${fmt(item.row_count)}</td><td>${sublayers}</td><td>${fmt(item.unknowns.field_values)}</td><td>${fmt(item.unknowns.identity_rows)}</td><td>${fmt(item.unknowns.unavailable_source_rows)}</td></tr>`;
    })
    .join("");
  main.innerHTML =
    header(
      "Row by row, as the documents print them",
      "An entry is one row of a register, one line of a plan annex, one submission in a list, kept as its document prints it and before any matching. Choose a country to read its entries.",
    ) +
    `<p>These four tables keep every row of six selected document extracts. They are frozen, not a live status service, and their row counts are not comparable project totals.</p><div class="table-wrap"><table><thead><tr><th>Country</th><th>Rows in this export <small class="computed-tag">Our calculation</small></th><th>Publisher's issue · cutoff</th><th>Unknown field values</th><th>Unknown identities</th><th>Rows unavailable at the publisher</th></tr></thead><tbody>${rows}</tbody></table></div><p class="note">The per-country figures are the extract figures of one export laid end to end — the size of a file, not a count of projects: the extracts overlap and count different things. Each extract's own figures are on the country's entries page.</p><div class="downloads"><a class="button light" href="data/m1a/ZAF.csv" download>South Africa entries ↓</a><a class="button light" href="data/m1a/IDN.csv" download>Indonesia entries ↓</a><a class="button light" href="data/m1a/VNM.csv" download>Viet Nam entries ↓</a><a class="button light" href="data/m1a/SEN.csv" download>Senegal entries ↓</a><a class="button light" href="data/m1a/manifest.json" download>Entries manifest ↓</a></div><p>The manifest pins input and document hashes and reports <code>field_values</code>, <code>identity_rows</code> and <code>unavailable_source_rows</code> separately for every extract. Country names above open the row-by-row entries.</p>`;
}
/* Who's who: the organisations the project documents name, one row per name,
 * role and country, spelled as the documents spell them. No party is matched
 * to another here; that is the parties table's work (ticket 0875). */
// projects is fixed for the session once load() runs, so the funder/operator
// index built from it needs computing only once per page load, not on every
// visit to #whos-who.
let whosWhoRows;
function whosWhoPage(params) {
  if (!whosWhoRows) {
    const byKey = {};
    projects.forEach((p) => {
      const named = [...p.funders.map((name) => [name, "Funder"]), [p.operator, "Operator"]];
      named.forEach(([name, role]) => {
        if (!name) return;
        const key = [name, role, p.country].join("\u0000");
        (byKey[key] ||= { name, role, country: p.country, projects: [] }).projects.push(p);
      });
    });
    whosWhoRows = Object.values(byKey).sort((a, b) => a.name.localeCompare(b.name));
  }
  const rows = whosWhoRows;
  const table = filterTable("parties", rows, {
    facets: [
      { key: "role", label: "Named as", all: "Funders and operators", options: distinctValues(rows, "role") },
      {
        key: "country",
        label: "Country",
        all: "All four countries",
        options: overview.countries.map((c) => ({ value: c.code, label: c.name })),
        selected: knownCountry(params.get("country")),
      },
    ],
    search: {
      label: "Search names",
      placeholder: "Try KfW, EVN, Eskom…",
      text: (row) => row.name.toLowerCase(),
    },
    columns: [
      { label: "Name, as the documents spell it", cell: (row) => esc(row.name) },
      { label: "Named as", cell: (row) => esc(row.role) },
      { label: "Country", cell: (row) => esc(country(row.country)?.short || row.country) },
      {
        label: "Projects naming it",
        cell: (row) =>
          foldout(`${row.projects.length} ${row.projects.length === 1 ? "project" : "projects"}`, row.projects,
            (p) => `<li><a href="#project/${encodeURIComponent(p.id)}">${esc(p.name)}</a></li>`, "party-projects", ""),
      },
    ],
    empty: "No names match these filters.",
    resultNoun: "names",
    pageSize: 50,
  });
  main.innerHTML =
    header(
      "Who is named, and where",
      "The funders and operators the project documents name, each with the projects that name them. Names are kept as each document spells them: two spellings of one organisation stay two rows until they are matched.",
    ) +
    table.head;
  table.mount();
}
/* A first list of the words the pages use, written by hand. The Glossary
 * generated from the ledger's term tables (ticket 0882) replaces it, with each
 * term's external mapping and revision history; until then this list is
 * marked as the hand-written one. Grouped by theme, A–Z inside each group
 * (author's cold read, 2026-09-23), the way 0882 groups the generated terms
 * by list: the classes the ledger tracks, how documents are read, statuses,
 * measures, relations. The order is computed, so a new term cannot break it. */
const GLOSSARY = [
  ["What we track", [
    ["Agreement", "A financing arrangement — a grant, a loan, a guarantee — between funders and a recipient. A partnership is the umbrella agreement; the financing under it are agreements too."],
    ["Asset", "A physical installation a project concerns: a power plant, a unit within it, a transmission line."],
    ["Party", "An organisation that funds, receives, operates or oversees: a government, a development bank, a utility. Who's who lists them as the documents spell them."],
    ["Perimeter", "A defined population that counts are made against: a country's portfolio at a date, a plan's list at a cutoff, a set of unnamed slots."],
    ["Project", "A project, programme or component that the documents name. Programmes and components may overlap, so projects are not physical assets and are not added up."],
    ["Unpublished identity", "A project a country counts in its portfolio without publishing its name."],
  ]],
  ["How documents are read", [
    ["Archived copy", "The bytes a retrieval returned, kept as fetched, with their fingerprint. They open locally in this preview only."],
    ["Document", "A file a publisher released — a report, a register, a plan, a web page — and our record of each attempt to retrieve it."],
    ["Entry", "One row of a register, one line of a plan annex or one submission in a list, kept as its document prints it, before any matching."],
    ["Locator", "Where in a document an entry or an item sits: a table row, an annex, a PDF page."],
    ["On the record", "One statement a publisher made in one document, read by the ledger as a date, a status or an amount. It reads “according to” its publisher, with the date."],
    ["Publisher", "The organisation a document comes from, named on every item read from it."],
    ["Knowledge cutoff", "The last date on which a document entered the ledger for a release."],
    ["Release", "A frozen package of the ledger and these pages, prepared up to a knowledge cutoff."],
  ]],
  ["Statuses", [
    ["Financing milestone", "Need, announcement, memorandum, approval, signature, disbursement: the steps a financing goes through, each on the record only when a document says so."],
    ["Not coded in ledger", "No financing milestone has yet been read from the project's documents. It does not mean there is no finance."],
    ["Registered financing", "A financing line in an official register. It is not an independently verified signature or payment."],
    ["Review state", "How far a project's documents have been followed up, as the ledger recorded it."],
    ["Verification state", "The word the ledger recorded for how an item was checked, shown exactly as written."],
  ]],
  ["Measures", [
    ["Amount", "A sum as its document prints it, in its original currency. Amounts are never converted, and never added across documents."],
    ["As published", "A number printed by a publisher, shown as printed, with its publisher and date."],
    ["Our calculation", "A number computed from the paper trail, as opposed to a number a publisher printed. It states its unit and what it covers, and links to what was counted."],
    ["Financing window", "For a closed historical operation, the years from approval to the closing date the World Bank reports. It is not a construction time."],
  ]],
  ["Relations", [
    ["Component of", "A project within a programme. A component and its programme are never counted twice as one."],
    ["Finances", "An agreement finances a project; one agreement may finance several projects, and one project draw on several agreements."],
    ["Party to", "An organisation's role in an agreement: funder, recipient, channel. One organisation may hold different roles in different agreements."],
    ["Published by", "A document and the organisation that released it; some documents have several."],
    ["Refers to", "An entry or an item and the project, agreement or organisation it names, once a reviewed match has attached it."],
  ]],
];
const byTerm = ([a], [b]) => a.localeCompare(b, "en");
function glossaryPage() {
  main.innerHTML =
    header(
      "The words these pages use",
      "What each word on these pages means, grouped by theme and alphabetical within each group. This first list is written by hand; definitions generated from the ledger's own term tables, with their external references and revision history, will replace it.",
    ) +
    GLOSSARY.map(
      ([group, terms]) =>
        `<section class="section" data-glossary-group="${esc(group)}"><h2>${esc(group)}</h2><dl class="facts glossary" data-glossary="handwritten">${[...terms]
          .sort(byTerm)
          .map(([term, definition]) => `<dt>${esc(term)}</dt><dd>${esc(definition)}</dd>`)
          .join("")}</dl></section>`,
    ).join("");
}
function methodsPage() {
  main.innerHTML =
    header(
      "Follow any figure back to its page.",
      "What we collected, how we read it, what we counted, and what this observatory does not do.",
    ) +
    `<div class="method-list"><h2>What this release contains</h2><p>${projects.length} named projects, ${undisclosedCount()} unpublished identities, ${overview.source_count} curated documents and ${comparison.projects.length} closed historical operations. The named projects include programmes and components; they are not ${projects.length} distinct physical assets. Knowledge cutoff: ${date(overview.provenance.cutoff)}. Each country's reports keep their own dates.</p><h2>The paper trail, step by step</h2><p><a href="#documents">Documents</a>: we try to retrieve each report, register and plan, keep an archived copy where we can, and record every attempt, failed ones included. <a href="#entries">Entries</a>: from a few of those documents we copy the rows of a register or the lines of a plan annex, as printed. <a href="#on-the-record">On the record</a>: we read what a publisher said about a project — a date, a status, an amount — into one item, which keeps its publisher, its date and the page it came from. <a href="#projects">Projects</a>, <a href="#funding">Funding</a> and <a href="#whos-who">Who's who</a>: the projects, partnerships and organisations those items are about. Each page links one step toward the documents and one step toward the projects.</p><h2>Words and numbers</h2><p>The <a href="#glossary">Glossary</a> defines the words these pages use. A number a publisher printed is marked “As published” and shown with its publisher and date. A number we counted is marked “Our calculation”, with its unit and what it covers, and links to what was counted; <a href="#by-the-numbers">By the numbers</a> gathers them.</p><h2>What this observatory does not do</h2><p>It does not explain. It tests no causal explanation of why a partnership moves fast or slow, and estimates no effect of the partnerships. It does not add amounts across documents, nor a project's amounts to a partnership's headline. It does not convert or deflate amounts. It does not treat a plan, an approval or a register line as a payment. It does not match a 2023 plan position to a 2025 portfolio project. Missing payment data is not a zero payment.</p><h2>Three different kinds of progress</h2><p>Financial items distinguish needs, announcements, memoranda, approvals, signatures and disbursements. Implementation items are a separate table. Documentary coverage describes what we could locate, not what a project achieved. Register-derived dates are not presented as verified signature dates.</p><h2>How the national figures work</h2><p>Headline financing amounts reproduce attributed national reports; they are not computed by adding project events. The milestones differ across countries, so headline amounts must not be pooled. Portfolio bars count each named project once, at the most advanced financing milestone on the record for it; tranches may be at different milestones. “Not coded in ledger” does not mean “no finance”. No project-level disbursement total is available in this release.</p><h2>Historical comparison: useful context, not an effect estimate</h2><p>${esc(comparison.method)} ${esc(comparison.date_note)} The API may contain older status snapshots; retrieval date is not the date of its latest substantive update. Energy-related includes mixed-sector operations, and additional-financing operations may refer to the same underlying investment. Comparisons of preparation speed require a credible causal design from the separate lifecycle research programme.</p><h2>Dates, conflicts and missing items</h2><p>Event dates, date intervals, dated status reports and collection dates remain distinct. Timing is adjudicated independently of the publisher's authority; unreviewed timing is labelled and cannot supply an event date. Document cards keep provisional, contextual and confirmed link decisions. Historical downloads preserve each acquisition date and query-page hash; the substantive update date is unknown unless separately documented. Conflicting values are preserved in notes; we do not average them. Unpublished identities appear in country disclosure counts rather than invented project pages. Original-currency amounts remain the reference.</p><h2>Download this snapshot</h2><div class="downloads">${overview.countries.map((c) => `<a class="button light" href="data/${c.code}.json" download>${esc(c.name)} ↓</a>`).join("")}<a class="button light" href="data/comparison.json" download>Historical cohort ↓</a><a class="button light" href="data/documents.json" download>Collection registry ↓</a><a class="button light" href="data/overview.json" download>Overview & input hashes ↓</a><a class="button light" href="data/provenance.json" download>Where each headline comes from ↓</a></div><div class="downloads"><a class="button light" href="data/m1a/ZAF.csv" download>South Africa entries ↓</a><a class="button light" href="data/m1a/IDN.csv" download>Indonesia entries ↓</a><a class="button light" href="data/m1a/VNM.csv" download>Viet Nam entries ↓</a><a class="button light" href="data/m1a/SEN.csv" download>Senegal entries ↓</a><a class="button light" href="data/m1a/manifest.json" download>Entries manifest ↓</a></div><p>JSON downloads include project data, document addresses and locators. Input SHA-256 hashes identify the files used to build this preview. This is a local preview, not yet a formally deposited monthly release; the <a href="#release-history">release history</a> lists what was prepared. Original documents retain their publishers' rights; their bulk redistribution is not implied.</p><h2>Reproducible, without a live database</h2><p>Markdown provides editorial context; CSV registries provide the structured data. The static website reads generated JSON. DVC preserves the research document archive, independently of the website. No visitor needs access to the archive or a database service.</p><p class="note">Input Git revision: <code>${esc(overview.provenance.input_git_sha || "Uncommitted preview inputs; use the file hashes")}</code><br>Release: ${esc(overview.provenance.edition)}</p></div>`;
}
function notFound() {
  main.innerHTML =
    header(
      "This page is not in the snapshot.",
      "Return to the projects to explore what is available.",
    ) + '<a class="button" href="#projects">Open the projects</a>';
}
/* Addresses match labels (author's cold read, 2026-09-23): each page's hash is
 * its label's slug. The addresses of earlier previews — and every deep link
 * under them, query included — forward to the new ones by replaceState, so
 * the site emits only the new names and an old bookmark still opens. An
 * entries page's old ?tab=record becomes its own address, #on-the-record/<CODE>. */
const RENAMED = {
  countries: "funding",
  country: "funding",
  evidence: "on-the-record",
  numbers: "by-the-numbers",
  comparison: "historical-comparison",
  methods: "how-we-did-this",
  editions: "release-history",
};
function forwardOf(raw) {
  const [path, query] = raw.split("?");
  const [page, ...rest] = path.split("/");
  const params = new URLSearchParams(query || "");
  let target;
  if (page === "inventory") {
    target = params.get("tab") === "record" ? "on-the-record" : "entries";
    params.delete("tab");
  } else if (Object.hasOwn(RENAMED, page)) target = RENAMED[page];
  else return null;
  const rest_ = params.toString();
  return [target, ...rest].join("/") + (rest_ ? "?" + rest_ : "");
}
const TITLES = {
  overview: "From promise to progress",
  "the-paper-trail": "The paper trail",
  funding: "Funding",
  projects: "Projects",
  project: "Project",
  "historical-comparison": "Historical comparison",
  "on-the-record": "On the record",
  "release-history": "Release history",
  documents: "Documents",
  entries: "Entries",
  "whos-who": "Who's who",
  "by-the-numbers": "By the numbers",
  glossary: "Glossary",
  "how-we-did-this": "How we did this",
};
/* The header's four section tabs: the current section is selected, and
 * aria-current says "page" when the tab is the page itself, "true" when the
 * page sits inside that section. */
function markNav(page) {
  const section = sectionOf(page);
  document.querySelectorAll("header nav a").forEach((a) => {
    const active = a.hash === "#" + section;
    a.classList.toggle("active", active);
    a.toggleAttribute("aria-current", active);
    if (active) a.setAttribute("aria-current", section === page ? "page" : "true");
  });
}
/* The step bar is drawn for the paper-trail pages only; a page scoped to a
 * country — by its address, or a project by its own country — shows it. */
function drawStepBar(page, id, params) {
  const bar = document.getElementById("step-bar");
  if (!bar) return;
  const onTrail = sectionOf(page) === "the-paper-trail" && page !== "the-paper-trail";
  const code =
    page === "project"
      ? projects.find((p) => p.id === decodeURIComponent(id || ""))?.country
      : ["entries", "on-the-record", "funding"].includes(page)
        ? id
        : params.get("country");
  bar.innerHTML = onTrail ? stepBar(page, code) : "";
  bar.toggleAttribute("hidden", !onTrail);
}
function pageTitle(page, id) {
  const name = country(id)?.name;
  return (
    (page === "funding" && id
      ? name || "Country"
      : (page === "entries" || page === "on-the-record") && id
        ? `${name || "Country"}: ${page === "on-the-record" ? "on the record" : "entries"}`
        : TITLES[page] || TITLES["how-we-did-this"]) + " · JETP Observatory"
  );
}
/* The section's own page: what each step holds, one line each. */
function paperTrailPage() {
  main.innerHTML =
    header(
      "The paper trail",
      "Every project on these pages can be followed to the document it comes from, and every document to what relies on it. Each step below is one level of that route; the bar above moves between them.",
    ) +
    `<ol class="trail-intro">${STEPS.map((s) => `<li><a href="${s.href("")}"><strong>${esc(s.label)}</strong></a> ${esc(STEP_NOTES[s.page])}</li>`).join("")}</ol>` +
    `<p class="note">The words are defined in the <a href="#glossary">Glossary</a>.</p>`;
}
const STEP_NOTES = {
  documents: "Each report, register and plan we tried to retrieve, with an archived copy where we have one.",
  entries: "Rows of a register, lines of a plan annex, as the document prints them.",
  "on-the-record": "What a publisher said in one document, read as a date, a status or an amount, according to that publisher.",
  projects: "The projects, programmes and components the documents name.",
  funding: "The four partnerships and the financing under them.",
  "whos-who": "The funders and operators the documents name.",
};
function render() {
  let raw = location.hash.slice(1) || "overview";
  const forward = forwardOf(raw);
  if (forward !== null) {
    window.history?.replaceState(null, "", "#" + forward);
    raw = forward;
  }
  const [path, query] = raw.split("?"),
    params = new URLSearchParams(query || "");
  const [page, id] = path.split("/");
  markNav(page);
  drawStepBar(page, id, params);
  if (page === "overview") overviewPage();
  else if (page === "the-paper-trail") paperTrailPage();
  else if (page === "funding") id ? countryPage(id) : countriesPage();
  else if (page === "projects") cataloguePage(params);
  else if (page === "project") projectPage(decodeURIComponent(id || ""));
  else if (page === "historical-comparison") comparisonPage(params);
  else if (page === "on-the-record") id ? inventoryPage(id, params, "record") : evidencePage();
  else if (page === "release-history") editionHistoryPage();
  else if (page === "documents") documentsPage(params);
  else if (page === "entries") id ? inventoryPage(id, params, "") : entriesPage();
  else if (page === "whos-who") whosWhoPage(params);
  else if (page === "by-the-numbers") numbersPage();
  else if (page === "glossary") glossaryPage();
  else methodsPage();
  document.title = pageTitle(page, id);
  window.scrollTo(0, 0);
}
const load = async (file) => {
  const response = await fetch("data/" + file + ".json");
  if (!response.ok) throw Error(`${file}: ${response.status}`);
  return response.json();
};
async function start() {
  try {
    [overview, comparison, documentsData, editions, evidence, m1a] = await Promise.all([
      load("overview"),
      load("comparison"),
      load("documents"),
      load("editions").catch(() => ({ editions: [] })),
      load("reviewed-evidence").catch(() => ({ records: [], analytical_snapshot: { status: "not available" } })),
      load("m1a/manifest"),
    ]);
    countries = Object.fromEntries(
      await Promise.all(
        overview.countries.map(async (c) => [c.code, await load(c.code)]),
      ),
    );
    projects = Object.values(countries).flatMap((c) => c.projects);
    documentIndex = indexDocuments(documentsData.documents);
    documentsBySha = indexDocumentsBySha256(documentsData.documents);
    window.addEventListener("hashchange", render);
    render();
  } catch (error) {
    main.innerHTML = `<div class="error"><h1>The snapshot could not load.</h1><p>Serve this directory with a local HTTP server, then reload.</p><p>${esc(error.message)}</p></div>`;
    console.error(error);
  }
}
start();
