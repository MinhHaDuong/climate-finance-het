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
const countryTabs = (selected) =>
  `<div class="country-tabs">${overview.countries.map((c) => `<a class="${selected === c.code ? "selected" : ""}" href="#country/${c.code}">${esc(c.name)}</a>`).join("")}</div>`;
const countStages = (rows) =>
  rows.reduce(
    (a, p) => ((a[p.finance_stage] = (a[p.finance_stage] || 0) + 1), a),
    {},
  );
const header = (eyebrow, title, description) =>
  `<div class="page-head"><p class="eyebrow">${eyebrow}</p><h1>${title}</h1><p class="lede">${description}</p></div>`;
function card(c) {
  return `<article class="country-card" style="--accent:${c.colour}"><span class="country-code">${c.code} · SINCE ${c.signed_on.slice(0, 4)}</span><h3><a href="#country/${c.code}" style="text-decoration:none">${esc(c.name)}</a></h3><div class="headline">${esc(c.headline)}</div><p class="detail">${esc(c.headline_detail)}</p><div class="asof">${esc(c.stage_label)} · ${date(c.headline_date)} ${sourceLink(c.headline_source_record, "Source")}</div><div class="card-bottom"><span>${c.named} named records${c.undisclosed ? " + " + c.undisclosed + " unnamed" : ""}</span><a href="#country/${c.code}" aria-label="Explore ${esc(c.name)}">Explore ↗</a></div></article>`;
}
function stageChart(cs) {
  return `<div role="img" aria-label="Financing evidence by country. Counts of named records, not assets or amounts.">${cs
    .map(
      (c) =>
        `<div class="chart-row"><a href="#country/${c.code}">${esc(c.short)}</a><div class="bar-track">${Object.entries(
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
function overviewPage() {
  main.innerHTML = `<section class="hero"><div><p class="eyebrow">From promise to progress</p><h1>Where do the<br><em>JETPs stand?</em></h1><p class="lede">Four partnerships to support a just energy transition. Explore what has been planned, financed and documented — and what remains to be seen.</p><div class="actions"><a class="button" href="#countries">Explore the four countries ↗</a><a class="text-link" href="#comparison">See the historical context →</a></div></div><aside class="evidence-box"><p class="eyebrow">The evidence at a glance</p><div class="stat-grid"><div class="stat"><strong>${fmt(projects.length)}</strong><span>named portfolio records</span><small>Projects, programmes and components</small></div><div class="stat"><strong>${overview.historical_count}</strong><span>closed historical operations</span><small>World Bank · same four countries</small></div><div class="stat"><strong>${overview.source_count}</strong><span>curated documentary sources</span></div><div class="stat"><strong>${undisclosedCount()}</strong><span>unpublished project identities</span><small>Country disclosure counts</small></div></div><div class="box-foot">Evidence collected through ${date(overview.provenance.cutoff)}.<br>Reporting dates differ by source. <a href="#methods">How to read this observatory</a></div></aside></section>
<section class="section"><div class="section-head"><div><p class="eyebrow">Country snapshot</p><h2>A shared ambition.<br>Four different trajectories.</h2></div><p>Reported national figures retain their own dates and definitions.<br>Allocation, approval and payment are different milestones.</p></div><div class="country-grid">${overview.countries.map(card).join("")}</div></section>
<section class="section"><div class="section-head"><div><p class="eyebrow">Reading across the evidence</p><h2>What the record tells us</h2></div></div><div class="insight-grid"><article class="insight"><span class="number">01</span><h3>Financing moves through different channels</h3><p>South Africa reports substantial allocations; Indonesia identifies approved programmes, investments and grants. Their headline figures measure different stages, so there is no single comparable “delivery rate”.</p><a class="text-link" href="#countries">Read country accounts →</a></article><article class="insight"><span class="number">02</span><h3>A plan is not yet a transaction</h3><p>Senegal's portfolio mixes investment needs, programmes and components. Viet Nam's reconciled portfolio leaves most project identities unnamed. These gaps matter when interpreting totals.</p><a class="text-link" href="#country/SEN">Explore the Senegal portfolio →</a></article><article class="insight"><span class="number">03</span><h3>Speed needs a historical reference</h3><p>${overview.historical_count} closed energy-related World Bank operations provide context from the same countries. Compare instruments and vintages before interpreting their financing windows as a benchmark.</p><a class="text-link" href="#comparison">Explore the comparison pool →</a></article></div></section>
<section class="section split"><div class="panel"><h3>How far does the financing evidence go?</h3><p class="note">Most advanced coded financing evidence for each named record.</p>${stageChart(overview.countries)}<p class="note" style="margin-top:20px">Registered financing is not independently verified signature or payment evidence. “Not coded” can coexist with financing described in source pages.</p><a class="text-link" href="#projects">Inspect the underlying records →</a></div><div class="panel"><h3>What is in the portfolio?</h3><p class="note">Named records by source-coded theme or technology. Categories retain source differences.</p>${technologyChart(projects)}<a class="text-link" href="#projects">Filter and explore the portfolio →</a></div></section>
<div class="comparison-banner"><div><p class="eyebrow">A longer view</p><h2>What did ordinary energy<br>projects look like?</h2><p>Browse the historical pool by country, instrument and approval year. See the distribution behind a typical financing window, not just an average.</p></div><div><p class="note">Administrative closure is not a measure of physical completion. This first pool is descriptive; the separate lifecycle research programme is a separate research task.</p><a class="button" href="#comparison">Explore ${overview.historical_count} closed operations ↗</a></div></div>`;
}
function countriesPage() {
  main.innerHTML =
    header(
      "Four partnerships",
      "The country picture",
      "Read each partnership on its own terms: what is promised, what is documented, and how complete the public record is.",
    ) +
    `<div class="country-grid">${overview.countries.map(card).join("")}</div><section class="section" style="margin-top:35px"><h2>Evidence coverage, side by side</h2><div class="table-wrap"><table><thead><tr><th>Country</th><th>Named records</th><th>Unpublished identities</th><th>Original pledge</th><th>Announcement</th></tr></thead><tbody>${overview.countries.map((c) => `<tr><td><a href="#country/${c.code}">${esc(c.name)}</a></td><td>${c.named}</td><td>${c.undisclosed}</td><td>${esc(c.pledge_label)}</td><td>${date(c.signed_on)}</td></tr>`).join("")}</tbody></table></div><p class="note" style="margin-top:15px">Original political pledges are context, not committed transactions. Counts include programmes and components; they are not additive counts of power plants.</p></section>`;
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
  main.innerHTML = `<div class="page-head"><div class="breadcrumb"><a href="#countries">Countries</a> / ${esc(c.name)}</div><p class="eyebrow">${c.code} · Partnership announced ${date(c.signed_on)}</p><h1>${esc(c.name)}</h1><p class="lede">${esc(c.headline_detail)}</p>${countryTabs(code)}</div><div class="callout"><h3>${esc(c.headline)}</h3><p>${esc(c.stage_label)} · ${date(c.headline_date)} · ${sourceLink(c.headline_source_record, "Read the source")}</p></div><div class="metrics"><div class="metric"><strong>${c.named}</strong><span>Named portfolio records</span></div><div class="metric"><strong>${c.undisclosed}</strong><span>Unpublished identities</span></div><div class="metric"><strong>${refs}</strong><span>Linked sources</span></div><div class="metric"><strong>${esc(c.pledge_label)}</strong><span>Original political pledge</span></div></div><div class="split"><div><h2>Reading this portfolio</h2><div class="markdown">${markdown(d.editorial)}</div><div class="actions"><a class="button" href="#projects?country=${code}">Explore ${c.named} records ↗</a><a class="text-link" href="#comparison?country=${code}">Historical reference →</a></div></div><div class="panel"><h3>Financing evidence</h3>${stageChart([c])}<p class="note" style="margin-top:20px">Counts show the most advanced coded evidence for a record, not the stage of every financing tranche. Programme overlaps prevent summing record-level amounts.</p><h3 style="margin-top:25px">Portfolio composition</h3>${technologyChart(d.projects)}</div></div>${code === "VNM" ? vietnamSideBySide(d) : ""}<section class="section" style="margin-top:35px"><div class="section-head"><h2>Inside the portfolio</h2><a class="text-link" href="#projects?country=${code}">View all →</a></div>${projectTable(d.projects.slice(0, 8))}<div class="downloads"><a class="button light" href="#inventory/${code}">Explore the frozen M1a source rows ↗</a><a class="button light" href="data/${code}.json" download>Download ${c.name} data ↓</a></div></section>`;
}
/* Rendering only: both figures already exist — the RMP row count in the M1a
 * manifest and the portfolio record count in the country view — and no field
 * joins them. The two columns are two objects of two dates, shown side by side
 * because that is the recipe of ticket 0834; matching a 2023 position to a 2025
 * record is the reconciliation work of ticket 0833, not this page's. */
function vietnamSideBySide(d) {
  const rmp = m1a.countries.VNM;
  const source = rmp.sublayers[0]?.source_id || "vnm-rmp-2023";
  return `<section class="section" id="vnm-side-by-side" style="margin-top:35px"><div class="section-head"><h2>Two objects, kept apart</h2></div><div class="split"><div class="panel" data-side="rmp-2023"><h3>RMP 2023 initial table</h3><p><strong>${fmt(rmp.row_count)}</strong> positions listed in the annexes of the Resource Mobilisation Plan, source <code>${esc(source)}</code>.</p><a class="text-link" href="#inventory/VNM">Browse the ${fmt(rmp.row_count)} positions →</a></div><div class="panel" data-side="portfolio-2025"><h3>2025 portfolio</h3><p><strong>${fmt(d.record_count)}</strong> records: ${fmt(d.projects.length)} named and ${fmt(d.undisclosed)} unpublished identities.</p><a class="text-link" href="#projects?country=VNM">Browse the named records →</a></div></div><p class="note" style="margin-top:15px">No link between the 2023 table and the 2025 portfolio is established here: a position in the plan and a record in the portfolio are neither matched, nor counted together, nor reconciled. That reconciliation is the work of ticket 0833.</p></section>`;
}
function projectTable(rows) {
  if (!rows.length)
    return '<div class="empty">No records match these filters.</div>';
  return `<div class="table-wrap"><table><thead><tr><th>Project / programme</th><th>Country</th><th>Theme / technology</th><th>Financing evidence</th><th>Sources</th></tr></thead><tbody>${rows.map((p) => `<tr><td><a href="#project/${encodeURIComponent(p.id)}">${esc(p.name)}</a><small>${esc(p.location)}</small></td><td>${esc(country(p.country).short)}</td><td>${esc(p.technology)}</td><td>${pill(p.finance_stage === "Not documented" ? "Not coded in ledger" : p.finance_stage)}</td><td>${p.sources.length}</td></tr>`).join("")}</tbody></table></div>`;
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
 *                 choice.
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
          `<label>${esc(f.label)}<select id="${id}-filter-${f.key}"><option value="">${esc(f.all || "All " + f.label.toLowerCase())}</option>${options(f.options)}</select></label>`,
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
 * another. Only the Viet Nam locators publish a PDF page, and they publish
 * three numbers — PDF page, printed page, ordinal — so the pattern is anchored
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
function resolveDocumentLink(sourceId, locator, registry) {
  const entry = registry[sourceId];
  if (!entry) return null;
  const match = PDF_PAGE.exec(locator || "");
  return {
    sha256: entry.sha256,
    pdf_page: match ? Number(match[1]) : null,
    local_path: entry.local_path,
  };
}
const byteSize = (n) =>
  n == null
    ? "Not recorded"
    : n >= 1e6
      ? (n / 1e6).toFixed(1) + " MB"
      : Math.max(1, Math.round(n / 1000)) + " kB";
/* The climb, document → what cites it. `by_source_id` is written by
 * extraction_index() in build_observatory.py: per source identifier, the
 * stage-two rows extracted from it (ledger observations and frozen M1a rows,
 * each named by the key its own view gives it) and the stage-three facts that
 * rely on it (named projects, reviewed records). Two lists, never a total;
 * an absent identifier is rendered as the statement that nothing cites the
 * document in this edition, never as an empty list dressed as one. */
function extractedItem(row) {
  if (row.product === "m1a")
    return `<li><a href="#inventory/${esc(row.country)}"><code>${esc(row.source_row_id)}</code></a> ${esc(row.label || "Identity not published")}<small>${esc(row.source_layer)} · ${esc(row.evidence_locator || "No locator recorded")}</small></li>`;
  return `<li><a href="#inventory/${esc(row.country)}">${esc(OBSERVATION_KINDS[row.kind] || row.kind)} <code>${esc(row.id)}</code></a> · ${pill(row.verification)}<small>${esc(row.table)} · <a href="#project/${encodeURIComponent(row.project_id)}">${esc(row.project_id)}</a> · ${esc(row.locator || "No locator recorded")}</small></li>`;
}
function factItem(fact) {
  return fact.record_id
    ? `<li><a href="#evidence">${esc(fact.label)}</a><small>Reviewed record · ${esc(fact.status.replaceAll("_", " "))} · ${esc(country(fact.country)?.short || fact.country)}</small></li>`
    : `<li><a href="#project/${encodeURIComponent(fact.project_id)}">${esc(fact.name)}</a><small>Named record · ${esc(country(fact.country)?.short || fact.country)}</small></li>`;
}
function foldout(label, items, item, key, none) {
  return `<details class="foldout" data-${key}-count="${items.length}"><summary>${esc(label)} · ${fmt(items.length)}</summary>${items.length ? `<ul class="citing">${items.map(item).join("")}</ul>` : `<p class="note">${esc(none)}</p>`}</details>`;
}
function extractionCell(entry) {
  const linked = (documentsData.by_source_id || {})[entry.id];
  if (!linked)
    return `<span class="note" data-uncited="${esc(entry.id)}">No extracted row and no fact cites this source in this edition.</span>`;
  return (
    foldout("Extracted here", linked.extracted, extractedItem, "extracted",
      "Nothing extracted from this source in this edition.") +
    foldout("Facts relying on it", linked.facts, factItem, "facts",
      "No fact relies on this source in this edition.")
  );
}
function documentsPage() {
  const rows = documentsData.documents;
  const values = (key) =>
    [...new Set(rows.map((r) => r[key]).filter(Boolean))].sort();
  const archived = (r) => {
    const href = documentHref(r);
    return href
      ? `<a href="${esc(href)}" data-document-id="${esc(r.row_key)}" target="_blank" rel="noopener">Open archived copy ↗</a>`
      : `<span class="note">${esc(r.error || "Not in the local snapshot")}</span>`;
  };
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
      label: "Search source identifiers and addresses",
      placeholder: "Try jet-investment-register, .pdf…",
      text: (r) => (r.id + " " + (r.url || "")).toLowerCase(),
    },
    columns: [
      { label: "Source", cell: (r) => `<code>${esc(r.id)}</code>` },
      {
        label: "Country",
        cell: (r) => esc(country(r.country)?.short || r.country),
      },
      { label: "Collection", cell: (r) => pill(r.status) },
      { label: "Content type", cell: (r) => esc(r.content_type || "Not recorded") },
      { label: "Size", cell: (r) => esc(byteSize(r.size_bytes)) },
      { label: "Archived copy", cell: archived },
      { label: "Extracted here · relied on by", cell: extractionCell },
      {
        label: "Origin",
        cell: (r) =>
          r.url
            ? `<a href="${esc(cleanURL(r.url))}" target="_blank" rel="noopener">Publisher ↗</a>`
            : '<span class="note">No address recorded</span>',
      },
    ],
    empty: "No sources match these filters.",
    resultNoun: "sources",
    pageSize: 50,
  });
  main.innerHTML =
    header(
      "Source documents",
      "Every collection attempt, kept on the record",
      "The collection registry lists each source we tried to retrieve, with the outcome recorded at the time. A blocked or failed attempt stays listed; it is not evidence that the document does not exist.",
    ) +
    `<div class="callout"><strong>Archived copies open locally only.</strong> The preview serves them from <code>documents/</code> after <code>make jetp-observatory-documents</code>. The published edition carries this registry and the publisher's address, never the archived bytes; source documents retain their publishers' rights.</div>` +
    table.head +
    `<div class="downloads"><a class="button light" href="data/documents.json" download>Download the collection registry ↓</a></div>`;
  table.mount();
}
/* The five facets wired here are the ones every country's inventory carries.
 * Everything else a row holds — the ZAF register's pass-through raw_ columns
 * included — is shown in the row detail, in the order the generator wrote it,
 * so a widened export needs no change here. */
const INVENTORY_FACETS = [
  ["source_layer", "Extraction sub-layer", "All sub-layers"],
  ["record_type", "Record type", "All record types"],
  ["reported_status", "Reported status", "All reported statuses"],
  ["identity_status", "Identity", "All identity outcomes"],
];
const inventoryCache = {};
/* The companion file carries the column names once and then one array of
 * values per row, so the row objects are rebuilt here in the generator's own
 * column order — pass-through columns included. */
const inventoryRows = (payload) =>
  payload.rows.map((values) =>
    Object.fromEntries(payload.fields.map((field, i) => [field, values[i]])),
  );
function inventoryUnknowns(details) {
  return (
    `<div class="metrics">${details.sublayers
      .map(
        (layer) =>
          `<div class="metric"><strong>${fmt(layer.row_count)}</strong><span>${esc(layer.sublayer_id)}</span><small>${esc(layer.edition)} · cutoff ${esc(layer.cutoff)}<br>${fmt(layer.unknowns.field_values)} unknown field values · ${fmt(layer.unknowns.identity_rows)} unknown identities · ${fmt(layer.unknowns.unavailable_source_rows)} unavailable source rows</small></div>`,
      )
      .join("")}</div>` +
    `<p class="note">Each figure counts one extraction sub-layer of this country. This page adds none of them together: the sub-layers overlap, count different things, and a country is not the unit any of them measures.</p>`
  );
}
/* A row's own fields, listed under whichever summary its caller names — an
 * inventory row and a ledger observation share every column but the label. */
function rowDetail(row, summary) {
  return `<details><summary>${summary}</summary><dl class="facts">${Object.entries(
    row,
  )
    .map(
      ([key, value]) =>
        `<dt>${esc(key)}</dt><dd>${esc(value === "" || value == null ? "Not published" : value)}</dd>`,
    )
    .join("")}</dl></details>`;
}
function inventoryRowDetail(row) {
  return rowDetail(row, esc(row.label || "Identity not published"));
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
  project_source_link: "Project–source link",
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
          `<div class="metric" data-observation-table="${esc(table)}"><strong>${fmt(count)}</strong><span>${esc(table)}</span><small>rows recorded for ${esc(c?.short || code)}</small></div>`,
      )
      .join("")}</div>` +
    `<p class="note">These rows and the frozen M1a inventory in the other tab are two extractions of the same documents under two schemas. They are read separately and never added together: one ledger row and one inventory row can describe the same paragraph of the same file. Each figure counts one table, for this country alone.</p>`
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
      label: "Search notes, locators and source identifiers",
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
      { label: "Evidence", cell: observationEvidence },
    ],
    empty: "No ledger rows match these filters.",
    resultNoun: "ledger rows",
    pageSize: 50,
  });
}
/* Mount draws the whole table, so mounting every panel up front pays for the
 * hidden one too on every visit. A panel mounts once, at the point it first
 * becomes visible: the one already marked selected in the static markup, or
 * whichever tab a click reveals — never both, on either path. */
function mountTabs(panels) {
  const mounted = new Set();
  const mountOnce = (panel) => {
    if (panel.mount && !mounted.has(panel.key)) {
      panel.mount();
      mounted.add(panel.key);
    }
  };
  panels.forEach(({ key, mount }) => {
    const tab = document.getElementById("tab-" + key);
    if (tab.getAttribute("aria-selected") === "true") mountOnce({ key, mount });
    tab.addEventListener("click", () => {
      mountOnce({ key, mount });
      panels.forEach((panel) => {
        const selected = panel.key === key;
        document
          .getElementById("tab-" + panel.key)
          .setAttribute("aria-selected", String(selected));
        document
          .getElementById("panel-" + panel.key)
          .toggleAttribute("hidden", !selected);
      });
    });
  });
}
function renderInventory(code, rows, observations) {
  const details = m1a.countries[code];
  const c = country(code);
  const values = (key) => distinctValues(rows, key);
  const table = filterTable("inventory", rows, {
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
      label: "Search the source label or locator",
      placeholder: "Try Tri An, Annex I.1, transmission…",
      text: (row) =>
        ((row.label || "") + " " + (row.evidence_locator || "")).toLowerCase(),
    },
    columns: [
      { label: "Source row", cell: (row) => `<code>${esc(row.source_row_id)}</code>` },
      { label: "Label and source columns", cell: inventoryRowDetail },
      { label: "Sub-layer", cell: (row) => esc(row.source_layer) },
      { label: "Record type", cell: (row) => esc(row.record_type) },
      { label: "Reported status", cell: (row) => pill(row.reported_status) },
      { label: "Identity", cell: (row) => pill(row.identity_status) },
      { label: "Evidence", cell: inventoryEvidence },
    ],
    empty: "No source rows match these filters.",
    resultNoun: "source rows",
    pageSize: 50,
  });
  const observationsView = observationsTable(observations);
  main.innerHTML =
    `<div class="page-head"><div class="breadcrumb"><a href="#countries">Countries</a> / <a href="#country/${code}">${esc(c?.name || code)}</a> / Inventory</div><p class="eyebrow">Source rows · ${code}</p><h1>${esc(c?.name || code)} source rows</h1><p class="lede">Two separate readings of this country's documents: the frozen M1a inventory of what a source published about its own projects, and the ledger rows recorded from those same documents. They are kept in separate tabs because they are not comparable, and never added together.</p></div>` +
    `<div class="view-tabs" role="tablist"><button type="button" role="tab" id="tab-inventory" aria-controls="panel-inventory" aria-selected="true">Frozen M1a inventory</button><button type="button" role="tab" id="tab-observations" aria-controls="panel-observations" aria-selected="false">Ledger observations</button></div>` +
    `<section id="panel-inventory" role="tabpanel" aria-labelledby="tab-inventory">` +
    inventoryUnknowns(details) +
    `<div class="callout">Each row opens the archived source document, at its PDF page where the source publishes one. Archived copies open locally only; the published edition carries the registry and the publisher's address.</div>` +
    table.head +
    `<div class="downloads"><a class="button light" href="data/m1a/${code}.csv" download>Download the ${code} M1a inventory (CSV) ↓</a></div></section>` +
    `<section id="panel-observations" role="tabpanel" aria-labelledby="tab-observations" hidden>` +
    observationTotals(observations, code) +
    observationsView.head +
    `<div class="downloads"><a class="button light" href="data/observations/${code}.json" download>Download the ${code} ledger observations (JSON) ↓</a></div></section>`;
  mountTabs([
    { key: "inventory", mount: table.mount },
    { key: "observations", mount: observationsView.mount },
  ]);
}
function inventoryPage(code) {
  if (!m1a.countries[code]) return notFound();
  main.innerHTML = `<p class="note">Loading the ${esc(code)} source rows…</p>`;
  inventoryCache[code] =
    inventoryCache[code] ||
    Promise.all([load("m1a/" + code), load("observations/" + code)]);
  inventoryCache[code]
    .then(([payload, observations]) => {
      if (location.hash.startsWith("#inventory/" + code))
        renderInventory(code, inventoryRows(payload), observations);
    })
    .catch((error) => {
      // Drop the rejected promise, or one transient failure would be replayed
      // from the cache for the rest of the session without ever retrying.
      delete inventoryCache[code];
      main.innerHTML = `<div class="error"><h1>The ${esc(code)} inventory could not load.</h1><p>${esc(error.message)}</p></div>`;
    });
}
function cataloguePage(params) {
  main.innerHTML =
    header(
      "Project explorer",
      "Follow the project evidence",
      "Search the named portfolio. Each record connects its description, financing observations and timeline to the underlying sources.",
    ) +
    `<div class="note">${projects.length} named records · ${undisclosedCount()} unpublished identity slots remain in country disclosure accounts. Programmes and components may overlap.</div><div class="filters"><label class="search">Search projects, operators or locations<input id="search" type="search" placeholder="Try transmission, geothermal, Bac Ai…"></label><label>Country<select id="country-filter"><option value="">All countries</option>${overview.countries.map((c) => `<option value="${c.code}" ${params.get("country") === c.code ? "selected" : ""}>${esc(c.name)}</option>`).join("")}</select></label><label>Theme / technology<select id="technology-filter"><option value="">All themes / technologies</option>${options([...new Set(projects.map((p) => p.technology))].sort())}</select></label><label>Funder<select id="funder-filter"><option value="">All funders</option>${options([...new Set(projects.flatMap((p) => p.funders))].sort())}</select></label><label>Financing evidence<select id="stage-filter"><option value="">All stages</option>${options(Object.keys(STAGE_COLOURS))}</select></label></div><p id="result-count" class="result-count" aria-live="polite"></p><div id="results"></div>`;
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
      `${filtered.length} of ${projects.length} named records`;
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
    e.reported_on ? `Source published ${date(e.reported_on)}` : "",
    e.collected_on ? `Collected ${date(e.collected_on.slice(0, 10))}` : "",
    e.recorded_date && !e.date && !e.observed_date && !e.reported_on
      ? `Legacy date ${date(e.recorded_date)} (${e.date_role}; not event timing)`
      : "",
  ]
    .filter(Boolean)
    .join(" · ");
  return `<li data-event-id="${esc(e.id)}"><div class="date">${esc(timing)}</div><p class="note">${esc(context)} · ${esc(e.date_basis)}</p><h3>${esc(e.status)}${e.amount != null ? " · " + esc(money(e.amount, e.currency)) : ""}</h3>${e.funder ? `<p>${esc(e.funder)} · ${esc(e.instrument)}</p>` : ""}<p>${esc(e.notes)}</p>${sourceLink(sources[e.source_id], "Source")} <span class="date-tag">${esc(e.locator)}</span></li>`;
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
/* The descent, fact → its stage-two rows. `p.evidence` is the country's ledger
 * observations addressed to this record, filtered in project_data() and served
 * exactly as the Observations tab serves them — same detail, same evidence
 * cell, same fingerprint resolution — so the two pages are one reading. */
function projectEvidenceRow(row) {
  return `<tr data-evidence-row="${esc(observationId(row))}"><td>${esc(row.table)}</td><td>${observationDetail(row)}</td><td>${pill(row.verification)}</td><td>${observationEvidence(row)}</td></tr>`;
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
    sources = countries[p.country].sources,
    evidenceRows = p.evidence || [];
  main.innerHTML = `<div class="page-head"><div class="breadcrumb"><a href="#projects">Projects</a> / <a href="#country/${c.code}">${esc(c.name)}</a></div><p class="eyebrow">${esc(p.technology)} · ${c.code}</p><h1>${esc(p.name)} <span class="badge" data-review-state="${esc(p.coverage)}">Review state · ${esc(p.coverage.replaceAll("_", " "))}</span></h1><p class="lede">${esc(p.location)}</p>${pill(p.finance_stage === "Not documented" ? "Financial events not yet coded" : p.finance_stage)}</div><div class="project-layout"><div><h2>Essential features</h2><dl class="facts"><dt>Operator</dt><dd>${esc(p.operator)}</dd><dt>Funders</dt><dd>${esc(p.funders.join("; ") || "See individual sources; no reconciled funder entry")}</dd><dt>Project ID</dt><dd>${esc(p.id)}</dd><dt>Source follow-up</dt><dd>${esc(p.coverage.replaceAll("_", " "))}</dd></dl><p class="note">${esc(p.notes)}</p><section class="section"><h2>Documented timeline</h2><p class="note">Events and dated status reports are distinguished. A financing amount at approval and again at signature is not two separate amounts to add.</p>${p.events.length ? `<ol class="timeline">${p.events.map((e) => eventView(e, sources)).join("")}</ol>` : '<div class="callout">No financial or implementation events have yet been reconciled into this record. The linked sources may establish more; absence from this timeline is not zero progress.</div>'}</section><section class="section" id="project-evidence"><h2>Ledger evidence</h2><p class="note">The ledger rows recorded for this identity, as the ledger wrote them: each opens its archived document where the collection holds one. They are not added together, and a row here is not a reconciled fact.</p>${evidenceRows.length ? `<details class="foldout" data-evidence-count="${evidenceRows.length}"><summary>${fmt(evidenceRows.length)} ledger ${evidenceRows.length === 1 ? "observation" : "observations"}</summary><div class="table-wrap"><table><thead><tr><th>Table</th><th>Row</th><th>Verification</th><th>Evidence</th></tr></thead><tbody>${evidenceRows.map(projectEvidenceRow).join("")}</tbody></table></div></details>` : '<p class="note" data-evidence-count="0">No ledger observation is addressed to this identity in this edition.</p>'}</section>${p.claims.length ? `<section class="section"><h2>Further source observations</h2>${p.claims.map((r) => `<article style="margin:20px 0"><p>${esc(r.claim_summary)}</p><p class="note">Match verdict: ${esc(r.match_status.replaceAll("_", " "))} · ${esc(r.notes)}</p>${sourceLink(sources[r.source_id], "Source")} <span class="date-tag">${esc(r.section)}</span></article>`).join("")}</section>` : ""}</div><aside><div class="panel"><h3>Evidence & references</h3><p class="note">${esc(p.coverage_note)}</p><ul class="sources">${p.sources
    .map((id) => {
      const s = sources[id];
      return s
        ? `<li>${sourceLink(s)}<small>${esc(s.publisher)} · ${esc(s.collection.replaceAll("_", " "))}</small>${s.retrieved ? `<small>Retrieved ${esc(s.retrieved.slice(0, 10))}</small>` : ""}${archivedCopy(id)}${sourceAdjudication(p, id)}</li>`
        : "";
    })
    .join(
      "",
    )}</ul></div><p class="note" style="margin-top:20px">Observations retain source-specific scopes. An agreement, approval or register entry does not establish a payment or physical delivery.</p><a class="button light" href="data/${c.code}.json" download>Download country evidence ↓</a></aside></div>`;
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
      "Historical comparison",
      "A reference beyond the JETPs.",
      "Explore closed World Bank energy-related operations approved before each country’s partnership. A descriptive reference pool for the next stage of research.",
    ) +
    `<div class="callout"><strong>What “closed” means here.</strong> These are completed administrative financing operations, not verified completed power plants. Approval-to-closing windows describe lending history; they do not yet establish whether JETPs accelerated preparation or financing.</div><div class="filters"><label class="search">Search historical operations<input id="history-search" type="search" placeholder="Search by name or World Bank project ID"></label><label>Country<select id="history-country"><option value="">All four countries</option>${overview.countries.map((c) => `<option value="${c.code}" ${params.get("country") === c.code ? "selected" : ""}>${esc(c.name)}</option>`).join("")}</select></label><label>Instrument<select id="history-instrument"><option value="">All instruments</option>${options([...new Set(comparison.projects.map((p) => p.instrument))].sort())}</select></label><label>Approval vintage<select id="history-vintage"><option value="0">All pre-JETP years</option><option value="2000">2000 onwards</option><option value="2010">2010 onwards</option></select></label><label>Additional financing<select id="history-additional"><option value="">Include, labelled</option><option value="exclude">Exclude additional financing</option></select></label></div><div id="history-summary" aria-live="polite"></div><div id="history-table"></div><div class="downloads"><a class="button light" href="data/comparison.json" download>Download historical cohort ↓</a></div><p class="note">${esc(comparison.method)}</p><p class="note">${esc(comparison.date_note)} Source: World Bank Projects & Operations. Frozen snapshots retrieved: ${Object.entries(
      comparison.snapshots,
    )
      .map(
        ([code, snapshot]) =>
          `${esc(country(code).short)} ${date(snapshot.retrieved_on)}`,
      )
      .join(
        "; ",
      )}. Project links below lead to individual official records.</p>`;
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
      `<div class="split" style="margin-bottom:25px"><div><div class="metrics" style="grid-template-columns:1fr 1fr"><div class="metric"><strong>${rows.length}</strong><span>Closed operations in selection</span></div><div class="metric"><strong>${med == null ? "—" : med.toFixed(1) + "y"}</strong><span>Median reported financing window</span></div><div class="metric"><strong>${durations.length}</strong><span>Usable approval / closing pairs</span></div><div class="metric"><strong>${rows.filter((p) => p.additional_financing).length}</strong><span>Additional-financing operations</span></div></div><p class="note">Closed-only selection favours operations that have finished. Mixed-sector and older projects may differ substantially from today's JETP investments. No pooled causal effect is estimated.</p></div><div class="panel"><h3>Reported financing windows</h3><p class="note">Years from approval to the source's closing date · n = ${durations.length}</p>${histogram(rows)}</div></div>`;
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
  return `<section class="section" aria-label="Evidence depth"><div class="section-head"><div><p class="eyebrow">Evidence depth</p><h2>What the data work added.</h2></div><p>These are distinct layers. They are not a common record total.</p></div><div class="metrics"><div class="metric"><strong>${fmt(depth.canonical_named_records)}</strong><span>named canonical portfolio records</span><small>Existing catalogue identities</small></div><div class="metric"><strong>${fmt(depth.frozen_source_documents)}</strong><span>frozen source documents</span><small>Curated documentary corpus</small></div><div class="metric"><strong>${fmt(depth.reviewed_canonical_records)}</strong><span>reviewed canonical assertions</span><small>Released as non-aggregate facts</small></div><div class="metric"><strong>${fmt(staged.total)}</strong><span>structured analytical observations</span><small>Staged research, not deployed</small></div></div><div class="callout"><h3>Staged extraction, kept separate</h3><p>${fmt(staged.total)} atomic observations: ${esc(countryCounts)}. This includes ${fmt(staged.vnm_rmp_positions)} Viet Nam RMP positions. They are structured observations, not automatically reconciled operations, payments, or canonical facts; the snapshot is not deployed as canonical facts.</p></div></section>`;
}
function editionHistoryPage() {
  const rows = editions.editions;
  main.innerHTML = header("Monthly editions", "What changed, and what did not.", "Each edition is frozen after review. A failed refresh remains a recorded gap and never removes evidence from an earlier download.") +
    `<div class="table-wrap"><table><thead><tr><th>Edition</th><th>Evidence cutoff</th><th>Prepared</th><th>State</th><th>Published</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${esc(row.edition)}</td><td>${date(row.observation_cutoff)}</td><td>${date(row.release_prepared_date)}</td><td>${esc(row.release_state)}</td><td>${row.publication_date ? date(row.publication_date) : "Not published"}</td></tr>`).join("")}</tbody></table></div><p class="note">A correction uses a new <code>YYYY-MM-rN</code> edition and preserves the prior archive. Later reports are labelled by their original event date; they are not treated as new events.</p><div class="downloads"><a class="button light" href="data/editions.json" download>Download release history ↓</a></div>` + evidenceDepthSummary();
}
/* A reviewed record pins a fingerprint, so its pedigree opens the archived copy
 * of those bytes and no other attempt of the same source identifier: resolved
 * by sha256, as a ledger observation is, through the same evidence cell. Text
 * where the snapshot holds no such copy. The record itself gains no field. */
function reviewedProof(proof) {
  return `<code>${esc(proof.source_id)}</code> · ${evidenceLink(
    proof.locator,
    documentsBySha[proof.sha256] || null,
    null,
    "data-reviewed-source",
    proof.source_id,
    "No archived copy of this source",
  )} · <code>${esc(proof.sha256.slice(0, 12))}…</code>`;
}
function evidencePage() {
  const records = evidence.records || [];
  main.innerHTML = header(
    "Reviewed evidence",
    "Source assertions, kept separate",
    "Each row is one reviewed source assertion or pending candidate. It is not an account, a payment total, or an estimate.",
  ) + `<div class="callout"><h3>Analytical snapshot: ${esc(evidence.analytical_snapshot?.status || "not available")}</h3><p>The comparative staging snapshot is derived research material and is not deployed in this MVP edition.</p></div><section class="section"><div class="table-wrap"><table><thead><tr><th>Record</th><th>Country</th><th>Review state</th><th>Pedigree</th><th>Reading note</th></tr></thead><tbody>${records.map((record) => `<tr data-reviewed-evidence-id="${esc(record.id)}"><td>${esc(record.label)}</td><td>${esc(country(record.country)?.name || record.country)}</td><td>${esc(record.status.replaceAll("_", " "))}</td><td>${record.evidence.map(reviewedProof).join("<br>")}</td><td>${esc(record.notes)}<br><small>Non-aggregate record.</small></td></tr>`).join("")}</tbody></table></div>${records.length ? "" : '<p class="note">No separately releasable reviewed evidence rows are available in this edition. That is a coverage statement, not evidence of no activity.</p>'}<div class="downloads"><a class="button light" href="data/reviewed-evidence.json" download>Download reviewed evidence ↓</a></div></section>`;
}
function m1aSection() {
  const rows = ["ZAF", "IDN", "VNM", "SEN"]
    .map((code) => {
      const item = m1a.countries[code];
      const sublayers = item.sublayers
        .map((layer) => `${esc(layer.edition)} · cutoff ${esc(layer.cutoff)}`)
        .join("<br>");
      return `<tr><td><a href="#inventory/${code}">${esc(country(code)?.name || code)}</a></td><td>${fmt(item.row_count)}</td><td>${sublayers}</td><td>${fmt(item.unknowns.field_values)}</td><td>${fmt(item.unknowns.identity_rows)}</td><td>${fmt(item.unknowns.unavailable_source_rows)}</td></tr>`;
    })
    .join("");
  return `<h2>Frozen M1a source inventories</h2><p>These four tables preserve every row of six selected extraction sub-layers before canonical matching. They are frozen inventories, not a live status service, and their row counts are not comparable project totals.</p><div class="table-wrap"><table><thead><tr><th>Country</th><th>Rows</th><th>Source edition · cutoff</th><th>Unknown fields</th><th>Unknown identities</th><th>Unavailable source rows</th></tr></thead><tbody>${rows}</tbody></table></div><div class="downloads"><a class="button light" href="data/m1a/ZAF.csv" download>South Africa M1a ↓</a><a class="button light" href="data/m1a/IDN.csv" download>Indonesia M1a ↓</a><a class="button light" href="data/m1a/VNM.csv" download>Viet Nam M1a ↓</a><a class="button light" href="data/m1a/SEN.csv" download>Senegal M1a ↓</a><a class="button light" href="data/m1a/manifest.json" download>M1a manifest ↓</a></div><p>The manifest pins input and source hashes and reports <code>field_values</code>, <code>identity_rows</code> and <code>unavailable_source_rows</code> separately for every extraction sub-layer. Country names above open the row-by-row inventory.</p>`;
}
function methodsPage() {
  main.innerHTML =
    header(
      "Methods & downloads",
      "Evidence you can follow.",
      "A transparent view of four partnerships, with source-specific dates, explicit gaps and downloadable observations.",
    ) +
    `<div class="method-list"><h2>What this first edition contains</h2><p>${projects.length} named portfolio records, ${undisclosedCount()} unpublished identity slots, ${overview.source_count} curated sources and ${comparison.projects.length} historical closed operations. The named records include programmes and components; they are not ${projects.length} distinct physical assets. Evidence cutoff: ${date(overview.provenance.cutoff)}. National snapshots retain their own dates.</p>${m1aSection()}<h2>Three different kinds of progress</h2><p>Financial observations distinguish needs, announcements, memoranda, approvals, signatures and disbursements. Implementation observations are a separate layer. Documentary coverage describes what we could locate, not what a project achieved. Register-derived dates are not presented as verified signature dates.</p><h2>How the aggregate views work</h2><p>Headline financing amounts reproduce attributed national reports; they are not computed by adding project events. The stages differ across countries, so headline amounts must not be pooled. Portfolio bars count each named registry identity once and assign its most advanced coded financing evidence; multiple tranches may be at different stages. “Not coded in ledger” does not mean “no finance”. No project-level disbursement total is available in this release.</p><h2>Historical comparison: useful context, not an effect estimate</h2><p>${esc(comparison.method)} ${esc(comparison.date_note)} The API may contain older status snapshots; retrieval date is not the date of its latest substantive update. Energy-related includes mixed-sector operations, and additional-financing records may refer to the same underlying investment. Comparisons of preparation speed require a credible causal design from the separate lifecycle research programme.</p><h2>Dates, conflicts and missing observations</h2><p>Event dates, date intervals, dated status reports and collection dates remain distinct. Timing is explicitly adjudicated independently of source authority; unreviewed timing is labelled and cannot supply an event date. Source cards retain provisional, contextual and confirmed link decisions. Historical downloads preserve each acquisition date and query-page hash; the substantive update date is unknown unless separately documented. Conflicting source values are preserved in notes; we do not average them. Unpublished identities appear in country disclosure counts rather than fabricated project pages. Original-currency amounts remain canonical. Missing payment data is not a zero payment.</p><h2>Download this snapshot</h2><div class="downloads">${overview.countries.map((c) => `<a class="button light" href="data/${c.code}.json" download>${esc(c.name)} ↓</a>`).join("")}<a class="button light" href="data/comparison.json" download>Historical cohort ↓</a><a class="button light" href="data/documents.json" download>Collection registry ↓</a><a class="button light" href="data/overview.json" download>Overview & input hashes ↓</a><a class="button light" href="data/provenance.json" download>Claim provenance & glossary ↓</a></div><p>JSON downloads include project records, source URLs and locators. Input SHA-256 hashes identify the files used to build this preview. This is a local preview, not yet a formally deposited monthly release. Original source documents retain their publishers' rights; their bulk redistribution is not implied.</p><h2>Reproducible, without a live database</h2><p>Markdown provides editorial context; CSV registries provide structured evidence. The static website reads generated JSON. DVC preserves the research source archive, independently of the website. No visitor needs access to the archive or a database service.</p><p class="note">Input Git revision: <code>${esc(overview.provenance.input_git_sha || "Uncommitted preview inputs; use the file hashes")}</code><br>Edition: ${esc(overview.provenance.edition)}</p></div>`;
}
function notFound() {
  main.innerHTML =
    header(
      "Record not found",
      "This record is not in the snapshot.",
      "Return to the project catalogue to explore the available evidence.",
    ) + '<a class="button" href="#projects">Open catalogue</a>';
}
function render() {
  const raw = location.hash.slice(1) || "overview";
  const [path, query] = raw.split("?"),
    params = new URLSearchParams(query || "");
  const [page, id] = path.split("/");
  document.querySelectorAll("nav a").forEach((a) => {
    const active = a.hash ===
      "#" +
        (page === "country" || page === "inventory"
          ? "countries"
          : page === "project"
            ? "projects"
            : page);
    a.classList.toggle("active", active);
    a.toggleAttribute("aria-current", active);
    if (active) a.setAttribute("aria-current", "page");
  });
  if (page === "overview") overviewPage();
  else if (page === "countries") countriesPage();
  else if (page === "country") countryPage(id);
  else if (page === "projects") cataloguePage(params);
  else if (page === "project") projectPage(decodeURIComponent(id || ""));
  else if (page === "comparison") comparisonPage(params);
  else if (page === "evidence") evidencePage();
  else if (page === "editions") editionHistoryPage();
  else if (page === "documents") documentsPage();
  else if (page === "inventory") inventoryPage(id);
  else methodsPage();
  document.title =
    (page === "overview"
      ? "From promise to progress"
      : page === "country"
        ? country(id)?.name || "Country"
        : page === "project"
          ? "Project evidence"
          : page === "comparison"
            ? "Historical comparison"
            : page === "inventory"
              ? (country(id)?.name || id) + " M1a inventory"
              : page.charAt(0).toUpperCase() + page.slice(1)) +
    " · JETP Observatory";
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
