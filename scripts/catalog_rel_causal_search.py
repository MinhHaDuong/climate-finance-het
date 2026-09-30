"""REL causal-map lane over OpenAlex, with its EconLit adaptation (ticket 1652).

Groups the 126 arcs of Annex A of ``conception/carte-causale-icf-co2.md`` into
the mechanism families of ``config/rel_causal_families.yaml``, expands the query
matrix of ``config/rel_causal_search.yaml`` (family or theme x formulation x
language, plus citation searches from the tuning sentinels of
``config/rel_causal_sentinels.csv``) and writes for every OpenAlex row its
EconLit (EBSCOhost) twin.

The run meters its own spend from the ``x-ratelimit-*`` headers: it stops
cleanly when the lane has spent its cap or the day's remaining budget falls
below the floor, and marks the stopped and unrun queries incomplete. A query
stopped by the record cap is incomplete too. An output directory that already
holds a registry is refused. Harvest only: nothing here decides ICF inclusion.

Usage:
    python scripts/catalog_rel_causal_search.py --plan-out matrix.csv
    python scripts/catalog_rel_causal_search.py --output-dir RUN_DIR \
        [--corpus data/catalogs/refined_works.csv] [--dry-run]
"""

import argparse
import csv
import gzip
import json
import os
import re
import sys
from datetime import datetime, timezone

import yaml
from catalog_rel_sud_search import OA_API, OA_SELECT, build_filter, load_corpus_keys, slim
from pipeline_keystore import read_credential
from utils import MAILTO, get_logger, polite_get

log = get_logger("rel_causal_search")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP_PATH = os.path.join(ROOT, "conception", "carte-causale-icf-co2.md")
FORMULATIONS = ("IM", "IO", "SY", "CS", "SI", "TH")
ECONLIT_NOT_RUN = "not run: not licensed via bibCNRS (2026-09-30)"
REGISTRY_FIELDS = [
    "search_id", "question", "question_type", "group", "formulation", "language",
    "platform", "query_string", "filter", "run_at", "n_expected", "n_received",
    "pages", "cost_usd", "completed", "stop_reason",
]
MATRIX_FIELDS = [
    "search_id", "question", "question_type", "group", "a_priori", "formulation",
    "language", "platform", "query_string", "openalex_filter", "econlit_string",
    "sentinels_tuning", "sentinels_holdout",
]


# --- Annex A and the family partition -------------------------------------

_ARC = re.compile(r"^\s*(\w+)\s*->\s*(\w+)\s*$")


def parse_annex_arcs(path=MAP_PATH):
    """Arcs ``(tail, head)`` of the dagitty block of Annex A, in file order."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    annex = text[text.index("## Annexe A"):]
    block = annex[annex.index("```"):]
    block = block[3:block.index("```", 3)]
    return [(m.group(1), m.group(2)) for line in block.splitlines()
            if (m := _ARC.match(line))]


def arc_key(arc):
    tail, head = arc if isinstance(arc, tuple) else _ARC.match(arc).groups()
    return f"{tail} -> {head}"


def partition_problems(families, annex_arcs):
    """Unassigned, duplicated and unknown arcs of a family partition."""
    annex = [arc_key(a) for a in annex_arcs]
    seen = {}
    problems = []
    for fam, spec in families.items():
        for arc in spec.get("arcs", []):
            if not _ARC.match(arc):
                problems.append(f"malformed arc in {fam}: {arc!r}")
                continue
            key = arc_key(arc)
            if key in seen:
                problems.append(f"duplicated arc {key}: {seen[key]} and {fam}")
            seen.setdefault(key, fam)
            if key not in annex:
                problems.append(f"unknown arc {key} in {fam}")
    problems += [f"unassigned arc {k}" for k in annex if k not in seen]
    return problems


# --- query matrix ------------------------------------------------------------

_BLOCK = re.compile(r"\{([A-Z_]+)\}")


def expand_blocks(template, blocks):
    def sub(m):
        if m.group(1) not in blocks:
            raise KeyError(f"unknown block {{{m.group(1)}}}")
        return blocks[m.group(1)]
    return _BLOCK.sub(sub, template)


def load_sentinels(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _sentinel_ids(sentinels, question, which):
    return [s["openalex_id"] for s in sentinels
            if s["family"] == question and s["set"] == which and s["openalex_id"]]


def _order(spec):
    """Priority families in English first, then citation searches, themes,
    French and Spanish strings, then the other families: a budget stop cuts
    from the end."""
    g, lang, f = spec["group"], spec["language"], spec["formulation"]
    if f == "SI":
        return (1, 0)
    if spec["question_type"] == "theme":
        return (2, 0)
    if g and lang == "en":
        return (0, g)
    if g:
        return (3, g)
    return (4, 0)


def plan_queries(search_cfg, families_cfg, sentinels):
    y0, y1 = search_cfg["year_min"], search_cfg["year_max"]
    fams, themes = families_cfg["families"], families_cfg["themes"]
    specs = []
    for qtype, source in (("family", search_cfg["queries"]), ("theme", search_cfg["themes"])):
        for question, by_lang in source.items():
            meta = fams.get(question) or themes[question]
            for lang, forms in by_lang.items():
                for form, template in forms.items():
                    query = expand_blocks(template, search_cfg["blocks"][lang])
                    specs.append({
                        "search_id": f"RC-{question}-{form}-{lang}",
                        "question": question, "question_type": qtype,
                        "group": meta.get("group", 0), "a_priori": meta.get("a_priori", "empirical"),
                        "formulation": form, "language": lang, "query_string": query,
                        "filter": build_filter(query, y0, y1,
                                               language=None if lang == "en" else f"{lang}|null")})
    for question in list(fams) + list(themes):
        ids = _sentinel_ids(sentinels, question, "tuning")
        if not ids:
            continue
        meta = fams.get(question) or themes[question]
        specs.append({
            "search_id": f"RC-{question}-SI-any", "question": question,
            "question_type": "family" if question in fams else "theme",
            "group": meta.get("group", 0), "a_priori": meta.get("a_priori", "empirical"),
            "formulation": "SI", "language": "any",
            "query_string": "cites:" + "|".join(ids),
            "filter": f"cites:{'|'.join(ids)},publication_year:{y0}-{y1}"})
    specs.sort(key=_order)  # stable: config order within each rank
    return specs


# --- EconLit (EBSCOhost) adaptation ---------------------------------------

def split_and_groups(query):
    """Top-level AND groups of a query, outer parentheses removed."""
    groups, depth, quoted, start, i = [], 0, False, 0, 0
    while i < len(query):
        c = query[i]
        if c == '"':
            quoted = not quoted
        elif not quoted and c == "(":
            depth += 1
        elif not quoted and c == ")":
            depth -= 1
        elif not quoted and depth == 0 and query.startswith(" AND ", i):
            groups.append(query[start:i])
            start = i + 5
            i += 5
            continue
        i += 1
    groups.append(query[start:])
    out = []
    for g in groups:
        g = g.strip()
        if g.startswith("(") and g.endswith(")"):
            g = g[1:-1].strip()
        out.append(g)
    return out


def _in_fields(group, fields):
    return "(" + " OR ".join(f"{f} ({group})" for f in fields) + ")"


def _clean_title(title):
    # EBSCOhost reads ? * # as wildcards; quotes would end the phrase early.
    return re.sub(r"\s+", " ", re.sub(r'[?*#"“”]', " ", title)).strip()


def econlit_twin(spec, econ_cfg, sentinels=()):
    """The EconLit string that replays one OpenAlex row."""
    if spec["formulation"] == "SI":
        titles = [_clean_title(s["title"]) for s in sentinels
                  if s["family"] == spec["question"] and s["set"] == "tuning"]
        body = "TI (" + " OR ".join(f'"{t}"' for t in titles) + ")"
    else:
        body = " AND ".join(_in_fields(g, econ_cfg["text_fields"])
                            for g in split_and_groups(spec["query_string"]))
    return f"{body} AND {econ_cfg['date']}"


def econlit_only_rows(specs, search_cfg, families_cfg):
    """Per family: a JEL row (JEL codes AND the mediator group) and, for the
    priority families, a working-paper row (the IO twin, working papers only)."""
    econ = search_cfg["econlit"]
    by_id = {s["search_id"]: s for s in specs}
    rows = []
    for fam, meta in families_cfg["families"].items():
        base = by_id.get(f"RC-{fam}-IM-en") or by_id[f"RC-{fam}-IO-en"]
        mediator = split_and_groups(base["query_string"])[-1]
        jel = " OR ".join(econ["jel"][fam])
        common = {"question": fam, "question_type": "family", "group": meta.get("group", 0),
                  "a_priori": meta.get("a_priori", "empirical"), "language": "en",
                  "query_string": "", "filter": ""}
        rows.append({**common, "search_id": f"RE-{fam}-JEL-en", "formulation": "JEL",
                     "econlit": f"({jel}) AND {_in_fields(mediator, econ['text_fields'])} AND {econ['date']}"})
        if meta.get("group"):
            io = by_id[f"RC-{fam}-IO-en"]
            rows.append({**common, "search_id": f"RE-{fam}-WP-en", "formulation": "WP",
                         "econlit": f"{econlit_twin(io, econ)} AND {econ['working_paper']}"})
    return rows


_FIELD = re.compile(r"(?<![\w\"])([A-Z]{2})(?= [(\"A-Z0-9])")


def econlit_problems(s, allowed):
    """Syntax problems of an EBSCOhost string: unbalanced parentheses, an odd
    number of quotes, a field code outside ``allowed``, an empty group."""
    problems = []
    if s.count('"') % 2:
        problems.append("odd number of quotes")
    depth = 0
    unquoted = re.sub(r'"[^"]*"', '""', s)
    for c in unquoted:
        depth += (c == "(") - (c == ")")
        if depth < 0:
            break
    if depth:
        problems.append("unbalanced parentheses")
    if "()" in unquoted.replace(" ", ""):
        problems.append("empty group")
    for code in _FIELD.findall(unquoted):
        if code not in allowed and code not in {"OR", "AND", "NOT"}:
            problems.append(f"field code {code} not allowed")
    return problems


def build_matrix(search_cfg, families_cfg, sentinels):
    specs = plan_queries(search_cfg, families_cfg, sentinels)
    econ = search_cfg["econlit"]
    rows = []
    for s in specs:
        rows.append({**s, "platform": "openalex", "openalex_filter": s["filter"],
                     "econlit_string": econlit_twin(s, econ, sentinels)})
    for r in econlit_only_rows(specs, search_cfg, families_cfg):
        rows.append({**r, "platform": "econlit", "openalex_filter": "",
                     "econlit_string": r["econlit"]})
    for r in rows:
        r["sentinels_tuning"] = "|".join(s["sentinel"] for s in sentinels
                                         if s["family"] == r["question"] and s["set"] == "tuning")
        r["sentinels_holdout"] = "|".join(s["sentinel"] for s in sentinels
                                          if s["family"] == r["question"] and s["set"] == "holdout")
    return specs, rows


def write_matrix(rows, path):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, MATRIX_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# --- metered OpenAlex run ---------------------------------------------------

class Meter:
    """Lane spend summed from ``x-ratelimit-cost-usd``; the day's remaining
    budget from ``x-ratelimit-remaining-usd``."""

    def __init__(self, lane_cap, daily_floor):
        self.lane_cap, self.daily_floor = lane_cap, daily_floor
        self.spent, self.remaining, self.prepaid, self.requests = 0.0, None, None, 0

    def observe(self, headers):
        h = {k.lower(): v for k, v in (headers or {}).items()}
        self.requests += 1
        try:
            self.spent += float(h.get("x-ratelimit-cost-usd") or 0)
        except ValueError:
            pass
        for attr, key in (("remaining", "x-ratelimit-remaining-usd"),
                          ("prepaid", "x-ratelimit-prepaid-remaining-usd")):
            try:
                setattr(self, attr, float(h[key]))
            except (KeyError, ValueError):
                pass

    def stop_reason(self):
        if self.spent >= self.lane_cap:
            return f"budget: lane cap {self.lane_cap} USD reached"
        if self.remaining is not None and self.remaining < self.daily_floor:
            return f"budget: daily remaining below {self.daily_floor} USD"
        return ""


def fetch_metered(spec, api_key, cap, delay, meter):
    """Yield ('meta', count), ('work', dict), ('page', cost); last ('end', reason)."""
    cursor, received = "*", 0
    while cursor:
        if reason := meter.stop_reason():
            yield ("end", reason)
            return
        params = {"filter": spec["filter"], "select": OA_SELECT, "per_page": 200,
                  "cursor": cursor, "mailto": MAILTO}
        if api_key:
            params["api_key"] = api_key
        before = meter.spent
        try:
            resp = polite_get(OA_API, params=params, delay=delay)
        except Exception as exc:  # network failure after retries
            yield ("end", f"error: {type(exc).__name__}")
            return
        meter.observe(resp.headers)
        yield ("page", meter.spent - before)
        if resp.status_code == 429:
            yield ("end", "rate limited or budget exhausted")
            return
        if resp.status_code != 200:
            yield ("end", f"http {resp.status_code}")
            return
        try:
            body = resp.json()
            count, results = body["meta"]["count"], body["results"]
            next_cursor = body["meta"].get("next_cursor")
        except (ValueError, KeyError, TypeError):
            yield ("end", "error: bad body")
            return
        if cursor == "*":
            yield ("meta", count)
        for i, w in enumerate(results):
            yield ("work", w)
            received += 1
            if cap and received >= cap and not (i == len(results) - 1 and not next_cursor):
                yield ("end", "record cap")
                return
        cursor = next_cursor
    yield ("end", "")


def run(search_cfg, families_cfg, sentinels, args, api_key, fetch=fetch_metered):
    specs, matrix = build_matrix(search_cfg, families_cfg, sentinels)
    if args.dry_run:
        for s in specs:
            log.info("%s %s", s["search_id"], s["filter"][:160])
        log.info("%d OpenAlex queries, %d EconLit strings", len(specs), len(matrix))
        return 0
    os.makedirs(args.output_dir, exist_ok=True)
    reg_path = os.path.join(args.output_dir, "registry.csv")
    if os.path.exists(reg_path):
        log.error("%s already holds a registry; use a new --output-dir", args.output_dir)
        return 2
    write_matrix(matrix, os.path.join(args.output_dir, "matrix.csv"))
    corpus_dois, corpus_ids = load_corpus_keys(args.corpus)
    budget = search_cfg["budget"]
    meter = Meter(budget["lane_cap_usd"], budget["daily_floor_usd"])
    cap = search_cfg["cap"] if args.cap is None else args.cap
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(reg_path, "w", encoding="utf-8", newline="") as reg_fh, \
            gzip.open(os.path.join(args.output_dir, "results.jsonl.gz"), "wt",
                      encoding="utf-8") as res_fh:
        reg = csv.DictWriter(reg_fh, REGISTRY_FIELDS, extrasaction="ignore")
        reg.writeheader()
        stop_all = ""
        for spec in specs:
            row = {**spec, "platform": "openalex", "query_string": spec["query_string"],
                   "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "n_expected": "", "n_received": 0, "pages": 0, "cost_usd": 0.0,
                   "completed": False, "stop_reason": f"not run ({stop_all})" if stop_all else ""}
            if not stop_all:
                n, reason = 0, "no response"
                for kind, val in fetch(spec, api_key, cap, args.delay, meter):
                    if kind == "meta":
                        row["n_expected"] = val
                    elif kind == "page":
                        row["pages"] += 1
                        row["cost_usd"] += val
                    elif kind == "work":
                        rec = slim(val)
                        rec.update(search_id=spec["search_id"],
                                   in_corpus=bool(rec["openalex_id"] in corpus_ids
                                                  or (rec["doi"] and rec["doi"] in corpus_dois)))
                        res_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        n += 1
                    else:
                        reason = val
                row.update(n_received=n, completed=reason == "", stop_reason=reason)
                if reason.startswith(("budget", "rate limited")):
                    stop_all = reason
            row["cost_usd"] = round(row["cost_usd"], 6)
            reg.writerow(row)
            reg_fh.flush()
            log.info("%s expected=%s received=%s cost=%.4f %s", spec["search_id"],
                     row["n_expected"], row["n_received"], row["cost_usd"],
                     row["stop_reason"] or "complete")
        for r in matrix:  # every EconLit string, kept in the registry as not run
            reg.writerow({**r, "platform": "econlit", "query_string": r["econlit_string"],
                          "filter": "", "run_at": "", "n_expected": "", "n_received": "",
                          "pages": 0, "cost_usd": 0, "completed": False,
                          "stop_reason": ECONLIT_NOT_RUN,
                          "search_id": r["search_id"].replace("RC-", "EL-", 1)})
    with open(os.path.join(args.output_dir, "spend.json"), "w", encoding="utf-8") as fh:
        json.dump({"started": started,
                   "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "lane_spent_usd": round(meter.spent, 6), "requests": meter.requests,
                   "daily_remaining_usd_at_end": meter.remaining,
                   "prepaid_remaining_usd_at_end": meter.prepaid,
                   "lane_cap_usd": meter.lane_cap, "daily_floor_usd": meter.daily_floor,
                   "stopped": stop_all}, fh, indent=1)
    log.info("lane spent %.4f USD in %d requests; daily remaining %s",
             meter.spent, meter.requests, meter.remaining)
    return 0


def load_configs(search_path, families_path, sentinels_path):
    with open(search_path, encoding="utf-8") as fh:
        search_cfg = yaml.safe_load(fh)
    with open(families_path, encoding="utf-8") as fh:
        families_cfg = yaml.safe_load(fh)
    return search_cfg, families_cfg, load_sentinels(sentinels_path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default="config/rel_causal_search.yaml")
    ap.add_argument("--families", default="config/rel_causal_families.yaml")
    ap.add_argument("--sentinels", default="config/rel_causal_sentinels.csv")
    # Multi-output script (registry, results, matrix, spend): --output-dir.
    ap.add_argument("--output-dir")
    ap.add_argument("--plan-out", help="write the query matrix CSV and exit (no network)")
    ap.add_argument("--corpus", default=None,
                    help="refined_works.csv, to flag works already in the corpus")
    ap.add_argument("--cap", type=int, default=None, help="override the config record cap")
    ap.add_argument("--delay", type=float, default=0.2)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    search_cfg, families_cfg, sentinels = load_configs(args.config, args.families, args.sentinels)
    if args.plan_out:
        _, rows = build_matrix(search_cfg, families_cfg, sentinels)
        write_matrix(rows, args.plan_out)
        log.info("%d matrix rows written to %s", len(rows), args.plan_out)
        return 0
    if not args.output_dir and not args.dry_run:
        ap.error("--output-dir is required for a run")
    api_key = None if args.dry_run else read_credential("openalex", "OPENALEX_API_KEY")
    return run(search_cfg, families_cfg, sentinels, args, api_key)


if __name__ == "__main__":
    sys.exit(main())
