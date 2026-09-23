/* Render one observatory route with the shipped app.js against the shipped
 * JSON, without a browser, and print what the renderer wrote (ticket 0856).
 *
 *   node tests/_jetp_observatory_render.js <site-dir> <route> [<state-json>] [<expression>]
 *
 * <route> is the hash without "#" ("documents", "project/<id>", ...); the
 * optional state is {"<element id>": "<value>"} — what a reader would have
 * typed into a search field or chosen in a select before the page rendered,
 * keyed as filterTable() reads them (document.getElementById(id).value).
 * The optional expression is evaluated in app.js's own scope once the page
 * has settled, for a rule the shipped data exercises on one side only (the
 * first-page agreement of ticket 0857: no shipped source disagrees).
 *
 * The DOM is a stub, not a parser: app.js writes HTML strings into
 * `.innerHTML` and reads back only element values, an aria attribute of the
 * markup it just wrote, and a few no-op listeners. Everything it writes is
 * captured verbatim, so a test asserts on the HTML the browser would receive,
 * and tests/browser/jetp_observatory.py stays the check that the browser
 * then does the right thing with it. Fetches read files under <site-dir>.
 *
 * Output: one JSON object, {"main": <#main innerHTML>, "elements": {id:
 * {"innerHTML", "textContent"}}} for every element the renderer touched —
 * a fold-out filled after a fetch lands in the element the renderer
 * addressed by id, not inside the results block that holds its placeholder —
 * plus "eval", the expression's value, when one was given.
 */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const [site, route, stateJson, expression] = process.argv.slice(2);
if (!site || !route) {
  console.error("usage: node _jetp_observatory_render.js <site-dir> <route> [<state-json>]");
  process.exit(2);
}
const state = stateJson ? JSON.parse(stateJson) : {};

const elements = {};
const element = (id) =>
  elements[id] ||
  (elements[id] = {
    id,
    value: state[id] ?? "",
    innerHTML: "",
    textContent: "",
    tagName: id.endsWith("-search") || id === "search" ? "INPUT" : "SELECT",
    addEventListener() {},
    // The renderer reads back an attribute of markup it wrote itself (the
    // selected tab), so the attribute is read from that markup.
    getAttribute(name) {
      const pattern = new RegExp(`id="${id}"[^>]*\\s${name}="([^"]*)"`);
      const match = pattern.exec(main.innerHTML);
      return match ? match[1] : null;
    },
    setAttribute() {},
    toggleAttribute() {},
    classList: { toggle() {} },
  });
const main = element("main");
const document = {
  getElementById: element,
  querySelectorAll: () => [],
  title: "",
};
const location = { hash: "#" + route };
// replaceState moves the address as a browser would, so an old route that
// forwards to its new name (ticket 0881) is read back under the new one.
const window = {
  addEventListener() {},
  scrollTo() {},
  history: { replaceState(state, title, url) { location.hash = url; } },
};
const fetch = async (file) => {
  const target = path.join(site, file);
  if (!fs.existsSync(target)) return { ok: false, status: 404 };
  return { ok: true, json: async () => JSON.parse(fs.readFileSync(target, "utf8")) };
};
const context = vm.createContext({
  document, location, window, fetch, console, setTimeout, URLSearchParams,
});
vm.runInContext(fs.readFileSync(path.join(site, "app.js"), "utf8"), context, {
  filename: "app.js",
});

// start() resolves its loads in microtasks; an async page (inventory, project
// evidence) then fills in after further ones. Wait until nothing changes.
const settle = async () => {
  let previous = null;
  let stable = 0;
  for (let i = 0; i < 500 && stable < 5; i++) {
    await new Promise((resolve) => setTimeout(resolve, 5));
    const snapshot = JSON.stringify(elements);
    stable = snapshot === previous ? stable + 1 : 0;
    previous = snapshot;
  }
};
settle().then(() => {
  const out = {};
  for (const [id, el] of Object.entries(elements)) {
    out[id] = { innerHTML: el.innerHTML, textContent: el.textContent };
  }
  const result = { main: main.innerHTML, elements: out };
  if (expression) result.eval = vm.runInContext(expression, context);
  process.stdout.write(JSON.stringify(result));
});
