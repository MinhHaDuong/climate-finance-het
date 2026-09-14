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
let overview, countries, comparison, editions, projects;
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
  main.innerHTML = `<div class="page-head"><div class="breadcrumb"><a href="#countries">Countries</a> / ${esc(c.name)}</div><p class="eyebrow">${c.code} · Partnership announced ${date(c.signed_on)}</p><h1>${esc(c.name)}</h1><p class="lede">${esc(c.headline_detail)}</p>${countryTabs(code)}</div><div class="callout"><h3>${esc(c.headline)}</h3><p>${esc(c.stage_label)} · ${date(c.headline_date)} · ${sourceLink(c.headline_source_record, "Read the source")}</p></div><div class="metrics"><div class="metric"><strong>${c.named}</strong><span>Named portfolio records</span></div><div class="metric"><strong>${c.undisclosed}</strong><span>Unpublished identities</span></div><div class="metric"><strong>${refs}</strong><span>Linked sources</span></div><div class="metric"><strong>${esc(c.pledge_label)}</strong><span>Original political pledge</span></div></div><div class="split"><div><h2>Reading this portfolio</h2><div class="markdown">${markdown(d.editorial)}</div><div class="actions"><a class="button" href="#projects?country=${code}">Explore ${c.named} records ↗</a><a class="text-link" href="#comparison?country=${code}">Historical reference →</a></div></div><div class="panel"><h3>Financing evidence</h3>${stageChart([c])}<p class="note" style="margin-top:20px">Counts show the most advanced coded evidence for a record, not the stage of every financing tranche. Programme overlaps prevent summing record-level amounts.</p><h3 style="margin-top:25px">Portfolio composition</h3>${technologyChart(d.projects)}</div></div><section class="section" style="margin-top:35px"><div class="section-head"><h2>Inside the portfolio</h2><a class="text-link" href="#projects?country=${code}">View all →</a></div>${projectTable(d.projects.slice(0, 8))}<div class="downloads"><a class="button light" href="data/${code}.json" download>Download ${c.name} data ↓</a></div></section>`;
}
function projectTable(rows) {
  if (!rows.length)
    return '<div class="empty">No records match these filters.</div>';
  return `<div class="table-wrap"><table><thead><tr><th>Project / programme</th><th>Country</th><th>Theme / technology</th><th>Financing evidence</th><th>Sources</th></tr></thead><tbody>${rows.map((p) => `<tr><td><a href="#project/${encodeURIComponent(p.id)}">${esc(p.name)}</a><small>${esc(p.location)}</small></td><td>${esc(country(p.country).short)}</td><td>${esc(p.technology)}</td><td>${pill(p.finance_stage === "Not documented" ? "Not coded in ledger" : p.finance_stage)}</td><td>${p.sources.length}</td></tr>`).join("")}</tbody></table></div>`;
}
function options(values, selected) {
  return values
    .map(
      (v) =>
        `<option value="${esc(v)}" ${v === selected ? "selected" : ""}>${esc(v)}</option>`,
    )
    .join("");
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
function projectPage(id) {
  const p = projects.find((p) => p.id === id);
  if (!p) return notFound();
  const c = country(p.country),
    sources = countries[p.country].sources;
  main.innerHTML = `<div class="page-head"><div class="breadcrumb"><a href="#projects">Projects</a> / <a href="#country/${c.code}">${esc(c.name)}</a></div><p class="eyebrow">${esc(p.technology)} · ${c.code}</p><h1>${esc(p.name)}</h1><p class="lede">${esc(p.location)}</p>${pill(p.finance_stage === "Not documented" ? "Financial events not yet coded" : p.finance_stage)}</div><div class="project-layout"><div><h2>Essential features</h2><dl class="facts"><dt>Operator</dt><dd>${esc(p.operator)}</dd><dt>Funders</dt><dd>${esc(p.funders.join("; ") || "See individual sources; no reconciled funder entry")}</dd><dt>Project ID</dt><dd>${esc(p.id)}</dd><dt>Source follow-up</dt><dd>${esc(p.coverage.replaceAll("_", " "))}</dd></dl><p class="note">${esc(p.notes)}</p><section class="section"><h2>Documented timeline</h2><p class="note">Events and dated status reports are distinguished. A financing amount at approval and again at signature is not two separate amounts to add.</p>${p.events.length ? `<ol class="timeline">${p.events.map((e) => eventView(e, sources)).join("")}</ol>` : '<div class="callout">No financial or implementation events have yet been reconciled into this record. The linked sources may establish more; absence from this timeline is not zero progress.</div>'}</section>${p.claims.length ? `<section class="section"><h2>Further source observations</h2>${p.claims.map((r) => `<article style="margin:20px 0"><p>${esc(r.claim_summary)}</p><p class="note">Match verdict: ${esc(r.match_status.replaceAll("_", " "))} · ${esc(r.notes)}</p>${sourceLink(sources[r.source_id], "Source")} <span class="date-tag">${esc(r.section)}</span></article>`).join("")}</section>` : ""}</div><aside><div class="panel"><h3>Evidence & references</h3><p class="note">${esc(p.coverage_note)}</p><ul class="sources">${p.sources
    .map((id) => {
      const s = sources[id];
      return s
        ? `<li>${sourceLink(s)}<small>${esc(s.publisher)} · ${esc(s.collection.replaceAll("_", " "))}</small>${s.retrieved ? `<small>Retrieved ${esc(s.retrieved.slice(0, 10))}</small>` : ""}${sourceAdjudication(p, id)}</li>`
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
function editionHistoryPage() {
  const rows = editions.editions;
  main.innerHTML = header("Monthly editions", "What changed, and what did not.", "Each edition is frozen after review. A failed refresh remains a recorded gap and never removes evidence from an earlier download.") +
    `<div class="table-wrap"><table><thead><tr><th>Edition</th><th>Evidence cutoff</th><th>Prepared</th><th>State</th><th>Published</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${esc(row.edition)}</td><td>${date(row.observation_cutoff)}</td><td>${date(row.release_prepared_date)}</td><td>${esc(row.release_state)}</td><td>${row.publication_date ? date(row.publication_date) : "Not published"}</td></tr>`).join("")}</tbody></table></div><p class="note">A correction uses a new <code>YYYY-MM-rN</code> edition and preserves the prior archive. Later reports are labelled by their original event date; they are not treated as new events.</p><div class="downloads"><a class="button light" href="data/editions.json" download>Download release history ↓</a></div>`;
}
function methodsPage() {
  main.innerHTML =
    header(
      "Methods & downloads",
      "Evidence you can follow.",
      "A transparent view of four partnerships, with source-specific dates, explicit gaps and downloadable observations.",
    ) +
    `<div class="method-list"><h2>What this first edition contains</h2><p>${projects.length} named portfolio records, ${undisclosedCount()} unpublished identity slots, ${overview.source_count} curated sources and ${comparison.projects.length} historical closed operations. The named records include programmes and components; they are not ${projects.length} distinct physical assets. Evidence cutoff: ${date(overview.provenance.cutoff)}. National snapshots retain their own dates.</p><h2>Three different kinds of progress</h2><p>Financial observations distinguish needs, announcements, memoranda, approvals, signatures and disbursements. Implementation observations are a separate layer. Documentary coverage describes what we could locate, not what a project achieved. Register-derived dates are not presented as verified signature dates.</p><h2>How the aggregate views work</h2><p>Headline financing amounts reproduce attributed national reports; they are not computed by adding project events. The stages differ across countries, so headline amounts must not be pooled. Portfolio bars count each named registry identity once and assign its most advanced coded financing evidence; multiple tranches may be at different stages. “Not coded in ledger” does not mean “no finance”. No project-level disbursement total is available in this release.</p><h2>Historical comparison: useful context, not an effect estimate</h2><p>${esc(comparison.method)} ${esc(comparison.date_note)} The API may contain older status snapshots; retrieval date is not the date of its latest substantive update. Energy-related includes mixed-sector operations, and additional-financing records may refer to the same underlying investment. Comparisons of preparation speed require a credible causal design from the separate lifecycle research programme.</p><h2>Dates, conflicts and missing observations</h2><p>Event dates, date intervals, dated status reports and collection dates remain distinct. Timing is explicitly adjudicated independently of source authority; unreviewed timing is labelled and cannot supply an event date. Source cards retain provisional, contextual and confirmed link decisions. Historical downloads preserve each acquisition date and query-page hash; the substantive update date is unknown unless separately documented. Conflicting source values are preserved in notes; we do not average them. Unpublished identities appear in country disclosure counts rather than fabricated project pages. Original-currency amounts remain canonical. Missing payment data is not a zero payment.</p><h2>Download this snapshot</h2><div class="downloads">${overview.countries.map((c) => `<a class="button light" href="data/${c.code}.json" download>${esc(c.name)} ↓</a>`).join("")}<a class="button light" href="data/comparison.json" download>Historical cohort ↓</a><a class="button light" href="data/overview.json" download>Overview & input hashes ↓</a><a class="button light" href="data/provenance.json" download>Claim provenance & glossary ↓</a></div><p>JSON downloads include project records, source URLs and locators. Input SHA-256 hashes identify the files used to build this preview. This is a local preview, not yet a formally deposited monthly release. Original source documents retain their publishers' rights; their bulk redistribution is not implied.</p><h2>Reproducible, without a live database</h2><p>Markdown provides editorial context; CSV registries provide structured evidence. The static website reads generated JSON. DVC preserves the research source archive, independently of the website. No visitor needs access to the archive or a database service.</p><p class="note">Input Git revision: <code>${esc(overview.provenance.input_git_sha || "Uncommitted preview inputs; use the file hashes")}</code><br>Edition: ${esc(overview.provenance.edition)}</p></div>`;
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
    const active = a.hash === "#" + (page === "country" ? "countries" : page === "project" ? "projects" : page);
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
  else if (page === "editions") editionHistoryPage();
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
            : page.charAt(0).toUpperCase() + page.slice(1)) +
    " · JETP Observatory";
  window.scrollTo(0, 0);
}
async function start() {
  try {
    const load = async (file) => {
      const response = await fetch("data/" + file + ".json");
      if (!response.ok) throw Error(`${file}: ${response.status}`);
      return response.json();
    };
    [overview, comparison, editions] = await Promise.all([
      load("overview"),
      load("comparison"),
      load("editions").catch(() => ({ editions: [] })),
    ]);
    countries = Object.fromEntries(
      await Promise.all(
        overview.countries.map(async (c) => [c.code, await load(c.code)]),
      ),
    );
    projects = Object.values(countries).flatMap((c) => c.projects);
    window.addEventListener("hashchange", render);
    render();
  } catch (error) {
    main.innerHTML = `<div class="error"><h1>The snapshot could not load.</h1><p>Serve this directory with a local HTTP server, then reload.</p><p>${esc(error.message)}</p></div>`;
    console.error(error);
  }
}
start();
