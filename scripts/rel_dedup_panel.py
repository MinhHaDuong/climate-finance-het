"""Precision panel for dedup step 5, working paper and published as one work (ticket 2048).

Three readers from three vendors, blind to each other and to the rule, read
pairs of records that step 5 of dedup version 2 joins by title and window and
say whether they are the same work. The author never checks an item.

Subcommands (all files in ``--dir``, outside the repository):

- ``sample``: rebuild the rows from the pinned catalogue and the archived
  deliveries (``corpus_rel_pool.load_rows``), run version 2 and collect the
  accepted title-and-window pairs of step 5 (``candidates.csv``); draw
  ``--n`` pairs stratified by year gap (-1..+5) and first-author agreement
  (agree, disagree, missing), equal allocation per cell, a short cell taken
  whole and its remainder spread over the others (``sample.jsonl``); add the
  controls (``controls.jsonl``): positive, the Gavard-Schoch pair (lane 1651,
  ZEW 2021 and the 2026 article); negative, two candidate records of
  different titles and fields.
- ``run``: ask each reader each control, then each sampled pair. A positive
  control not read as ``same`` or a negative not read as ``different`` stops
  that reader. Every call is logged with its token usage and its cost at the
  prices of ``PRICES`` (``calls.jsonl``); the run stops before a call that
  could take the total over ``--cap-usd``. A reader stops at its second
  failed call (two key or HTTP failures): the run goes on with the others.
  Resumable: answered items are skipped.
- ``analyze``: majority verdict per pair, precision (share of pairs the
  majority reads ``same``) with Wilson 95 % intervals per gap, per author
  stratum and overall (sample share, and the estimate weighted by the
  population of each cell), agreement between readers (pairwise and Fleiss'
  kappa), and the pairs the majority reads ``different``: the false merges.
  Writes ``summary.json`` and ``summary.md``.

Keys are read from the keystore (``pipeline_keystore``) by the code and never
printed or logged.
"""

import argparse
import csv
import json
import math
import os
import random
import re
import sys
import threading
import time
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAPS = list(range(-1, 6))
AUTHOR_STRATA = ["agree", "disagree", "missing"]
VERDICTS = ("same", "different", "cannot_tell")
ABSTRACT_CHARS = 400
GAVARD_SCHOCH = ("t1651-gavard-schoch", "1651-GS01", "1651-GS02")

# USD per million tokens (input, output), standard tier: the cost logged per
# call. Assumed prices, rounded up (the OpenAI one is a guess on the high side
# for GPT-6.1 Sol, whose flex tier costs half): the logged spend is an upper
# bound, and the cap holds against it.
PRICES = {"anthropic": (3.0, 15.0), "openai": (10.0, 40.0), "mistral": (0.4, 2.0)}
READERS = {
    "anthropic": {"model": "claude-sonnet-5-5", "keyfile": "anthropic", "key": "ANTHROPIC_API_KEY"},
    "openai": {"model": "gpt-6.1-sol", "keyfile": "openai", "key": "OPENAI_API_KEY"},
    "mistral": {"model": "mistral-medium-latest", "keyfile": "mistral", "key": "MISTRAL_API_KEY"},
}
MAX_OUTPUT_TOKENS = 1024


class CapReached(Exception):
    pass


# ── Pairs and sample ──────────────────────────────────────


def _fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).casefold()


def surnames(first_author):
    """Name tokens of a first author, initials dropped (``Gavard, C.`` -> {gavard})."""
    s = _fold(first_author)
    if "," in s:
        s = s.split(",", 1)[0]
    return {t for t in re.findall(r"[^\W\d_]+", s) if len(t) > 2}


def author_stratum(a, b):
    sa, sb = surnames(a), surnames(b)
    if not sa or not sb:
        return "missing"
    return "agree" if sa & sb else "disagree"


def _record(rows, i, by_id):
    """The fields a reader sees for row ``i``, blanks filled from rows of the same DOI or OpenAlex id."""
    r = rows[i]
    same = sorted(set(by_id.get(("doi", r["doi"]), ())) | set(by_id.get(("oa", r["openalex_id"]), ()))) \
        if (r["doi"] or r["openalex_id"]) else []

    def field(name):
        return r.get(name) or next((rows[j].get(name) for j in same if rows[j].get(name)), "")
    return {"record_id": r["record_id"], "title": field("title"), "year": r["year"],
            "first_author": field("first_author"), "journal": field("journal"), "doi": r["doi"],
            "openalex_id": r["openalex_id"], "doc_type": r.get("doc_type", ""),
            "abstract": (field("abstract") or "")[:ABSTRACT_CHARS]}


def candidate_pairs(rows, pairs):
    by_id = defaultdict(list)
    for i, r in enumerate(rows):
        if r["doi"]:
            by_id["doi", r["doi"]].append(i)
        if r["openalex_id"]:
            by_id["oa", r["openalex_id"]].append(i)
    out = []
    for k, p in enumerate(sorted(pairs, key=lambda p: (rows[p["wp_row"]]["record_id"],
                                                       rows[p["pub_row"]]["record_id"]))):
        wp, pub = _record(rows, p["wp_row"], by_id), _record(rows, p["pub_row"], by_id)
        out.append({"pair_id": f"P{k:05d}", "gap": p["gap"],
                    "author": author_stratum(wp["first_author"], pub["first_author"]),
                    "wp": wp, "pub": pub})
    return out


def allocate(sizes, n):
    """Equal allocation over cells; a short cell is taken whole, the rest spread."""
    alloc = {c: 0 for c in sizes}
    left, open_cells = n, [c for c in sizes if sizes[c] > 0]
    while left > 0 and open_cells:
        share = max(left // len(open_cells), 1)
        for c in sorted(open_cells):
            take = min(share, sizes[c] - alloc[c], left)
            alloc[c] += take
            left -= take
        open_cells = [c for c in open_cells if alloc[c] < sizes[c]]
    return alloc


def draw(cands, n, seed=2048):
    cells = defaultdict(list)
    for c in cands:
        cells[c["gap"], c["author"]].append(c)
    alloc = allocate({k: len(v) for k, v in cells.items()}, n)
    rng = random.Random(seed)
    sample = []
    for cell in sorted(cells):
        sample += rng.sample(cells[cell], alloc[cell])
    return sample, {f"{g}|{a}": {"population": len(cells[g, a]), "sampled": alloc[g, a]}
                    for g, a in sorted(cells)}


def controls(rows, cands):
    by_rid = {r["record_id"].split(":", 1)[-1]: i for i, r in enumerate(rows)
              if r["origin"] == GAVARD_SCHOCH[0]}
    by_id = defaultdict(list)
    for i, r in enumerate(rows):
        if r["doi"]:
            by_id["doi", r["doi"]].append(i)
    pos = {"pair_id": "CONTROL+", "expect": "same",
           "wp": _record(rows, by_rid[GAVARD_SCHOCH[1]], by_id),
           "pub": _record(rows, by_rid[GAVARD_SCHOCH[2]], by_id)}
    a = cands[0]
    b = next(c for c in cands if not (set(re.findall(r"\w{5,}", _fold(c["pub"]["title"])))
                                      & set(re.findall(r"\w{5,}", _fold(a["wp"]["title"])))))
    neg = {"pair_id": "CONTROL-", "expect": "different", "wp": a["wp"], "pub": b["pub"]}
    return [pos, neg]


# ── Prompt and readers ────────────────────────────────────

PROMPT = """Two bibliographic records follow. Do they describe the same work, one being a version of the other, or two different works?

Answer with one JSON object on one line and nothing else:
{{"verdict": "same" or "different" or "cannot_tell", "reason": "<one line>"}}

Record A
{a}

Record B
{b}
"""


def _block(rec):
    rec = {**rec, "abstract": (rec.get("abstract") or "")[:ABSTRACT_CHARS]}
    return "\n".join(f"{label}: {rec.get(key) or '(none)'}" for label, key in (
        ("Title", "title"), ("Year", "year"), ("First author", "first_author"),
        ("Journal or series", "journal"), ("DOI", "doi"), ("Abstract (excerpt)", "abstract")))


def prompt(item):
    """The blind prompt: two records, order drawn from the pair id, no rule, no gap."""
    sides = [item["wp"], item["pub"]]
    if random.Random(item["pair_id"]).random() < 0.5:
        sides.reverse()
    return PROMPT.format(a=_block(sides[0]), b=_block(sides[1]))


def parse_verdict(text):
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not m:
        return None, ""
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None, ""
    v = str(obj.get("verdict", "")).strip().lower().replace(" ", "_").replace("'", "")
    return (v if v in VERDICTS else None), str(obj.get("reason", ""))[:300]


def cost(vendor, usage):
    pin, pout = PRICES[vendor]
    return (usage["input_tokens"] * pin + usage["output_tokens"] * pout) / 1e6


def call_bound(vendor, text):
    """Upper bound of one call's cost: four characters a token is generous for input."""
    return cost(vendor, {"input_tokens": len(text) // 2 + 50, "output_tokens": MAX_OUTPUT_TOKENS})


def _post(url, headers, body):
    import requests
    for attempt in range(4):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=300)
        except requests.RequestException as exc:
            err = type(exc).__name__
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code in (429, 500, 502, 503, 529):
            err = f"HTTP {r.status_code}"
            time.sleep(10 * (attempt + 1))
            continue
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text[:200]}"
        return r.json(), ""
    return None, err


def make_reader(vendor):
    from pipeline_keystore import read_credential
    spec = READERS[vendor]
    key = read_credential(spec["keyfile"], spec["key"])
    if not key:
        raise RuntimeError(f"{vendor}: no key {spec['key']} in the keystore")

    def anthropic(text):
        body, err = _post("https://api.anthropic.com/v1/messages",
                          {"x-api-key": key, "anthropic-version": "2023-06-01"},
                          {"model": spec["model"], "max_tokens": MAX_OUTPUT_TOKENS,
                           "messages": [{"role": "user", "content": text}]})
        if body is None:
            return None, None, err
        u = body.get("usage") or {}
        return ("".join(c.get("text", "") for c in body.get("content") or []),
                {"input_tokens": int(u.get("input_tokens") or 0),
                 "output_tokens": int(u.get("output_tokens") or 0), "tier": "standard"}, "")

    def openai(text):
        payload = {"model": spec["model"], "reasoning_effort": "low", "service_tier": "flex",
                   "max_completion_tokens": MAX_OUTPUT_TOKENS,
                   "messages": [{"role": "user", "content": text}]}
        body, err = _post("https://api.openai.com/v1/chat/completions",
                          {"Authorization": f"Bearer {key}"}, payload)
        if body is None:  # flex refused or saturated: the standard tier once
            payload.pop("service_tier")
            body, err = _post("https://api.openai.com/v1/chat/completions",
                              {"Authorization": f"Bearer {key}"}, payload)
        if body is None:
            return None, None, err
        u = body.get("usage") or {}
        return (body["choices"][0]["message"].get("content") or "",
                {"input_tokens": int(u.get("prompt_tokens") or 0),
                 "output_tokens": int(u.get("completion_tokens") or 0),
                 "tier": body.get("service_tier") or payload.get("service_tier", "default")}, "")

    def mistral(text):
        body, err = _post("https://api.mistral.ai/v1/chat/completions",
                          {"Authorization": f"Bearer {key}"},
                          {"model": spec["model"], "max_tokens": MAX_OUTPUT_TOKENS, "temperature": 0,
                           "messages": [{"role": "user", "content": text}]})
        if body is None:
            return None, None, err
        u = body.get("usage") or {}
        return (body["choices"][0]["message"].get("content") or "",
                {"input_tokens": int(u.get("prompt_tokens") or 0),
                 "output_tokens": int(u.get("completion_tokens") or 0), "tier": "standard"}, "")

    return {"anthropic": anthropic, "openai": openai, "mistral": mistral}[vendor]


class Ledger:
    """Spend across readers under one cap; appends every call to ``calls.jsonl``."""

    def __init__(self, path, cap):
        self.path, self.cap, self.lock = path, cap, threading.Lock()
        self.spent = 0.0
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                self.spent = sum(json.loads(line)["usd"] for line in fh if line.strip())

    def reserve(self, bound):
        with self.lock:
            if self.spent + bound > self.cap:
                raise CapReached(f"spent {self.spent:.4f} + next call bound {bound:.4f} > cap {self.cap}")
            self.spent += bound

    def settle(self, bound, entry):
        with self.lock:
            self.spent += entry["usd"] - bound
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")


def _answered(path):
    done = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                a = json.loads(line)
                if a.get("verdict"):
                    done.add((a["reader"], a["pair_id"]))
    return done


def ask(vendor, reader, item, ledger, out_lock, answers_path):
    text = prompt(item)
    bound = call_bound(vendor, text)
    ledger.reserve(bound)
    t0 = time.time()
    reply, usage, err = reader(text)
    usage = usage or {"input_tokens": 0, "output_tokens": 0, "tier": ""}
    usd = cost(vendor, usage)
    ledger.settle(bound, {"reader": vendor, "model": READERS[vendor]["model"], "pair_id": item["pair_id"],
                          **usage, "usd": usd, "seconds": round(time.time() - t0, 2), "error": err})
    verdict, reason = parse_verdict(reply) if reply is not None else (None, "")
    entry = {"reader": vendor, "pair_id": item["pair_id"], "verdict": verdict, "reason": reason,
             "error": err or ("" if verdict else "unparsed reply"), "raw": (reply or "")[:500]}
    with out_lock:
        with open(answers_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def run_panel(d, cap, vendors, workers=4, readers=None):
    """Controls then the sample, per reader; returns per-reader status."""
    items = [json.loads(line) for line in open(os.path.join(d, "sample.jsonl"), encoding="utf-8")]
    ctrl = [json.loads(line) for line in open(os.path.join(d, "controls.jsonl"), encoding="utf-8")]
    ledger = Ledger(os.path.join(d, "calls.jsonl"), cap)
    answers_path = os.path.join(d, "answers.jsonl")
    out_lock = threading.Lock()
    status = {}

    def one_reader(vendor):
        try:
            reader = (readers or {}).get(vendor) or make_reader(vendor)
        except RuntimeError as exc:
            return f"stopped: {exc}"
        failures = 0
        for c in ctrl:
            e = ask(vendor, reader, c, ledger, out_lock, answers_path)
            if e["error"]:
                failures += 1
                e = ask(vendor, reader, c, ledger, out_lock, answers_path)
                if e["error"]:
                    return f"stopped: control {c['pair_id']} failed twice ({e['error'][:120]})"
            if e["verdict"] != c["expect"]:
                return f"stopped: control {c['pair_id']} read {e['verdict']}, expected {c['expect']}"
        done = _answered(answers_path)
        todo = [it for it in items if (vendor, it["pair_id"]) not in done]
        with ThreadPoolExecutor(workers) as pool:
            for e in pool.map(lambda it: ask(vendor, reader, it, ledger, out_lock, answers_path), todo):
                if e["error"]:
                    failures += 1
                    if failures >= 2:
                        pool.shutdown(wait=False, cancel_futures=True)
                        return f"stopped: second failed call ({e['error'][:120]})"
        return "completed"

    with ThreadPoolExecutor(len(vendors)) as pool:
        futures = {v: pool.submit(one_reader, v) for v in vendors}
        for v, f in futures.items():
            try:
                status[v] = f.result()
            except CapReached as exc:
                status[v] = f"stopped at the cap: {exc}"
    status["spent_usd"] = round(ledger.spent, 4)
    return status


# ── Analysis ──────────────────────────────────────────────


def wilson(k, n, z=1.96):
    if n == 0:
        return None, None
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, mid - half), min(1.0, mid + half)


def majority(verdicts):
    c = Counter(v for v in verdicts if v)
    top = [v for v, n in c.items() if n >= 2]
    return top[0] if top else "no_majority"


def fleiss_kappa(table, categories=VERDICTS):
    """``table``: per item, the verdicts of the same number of readers."""
    rows = [Counter(t) for t in table]
    if not rows:
        return None
    n = len(table[0])
    N = len(rows)
    p_j = [sum(r[c] for r in rows) / (N * n) for c in categories]
    P_i = [(sum(r[c] ** 2 for c in categories) - n) / (n * (n - 1)) for r in rows]
    P_bar, P_e = sum(P_i) / N, sum(p * p for p in p_j)
    return None if P_e == 1 else (P_bar - P_e) / (1 - P_e)


def analyze(d):
    items = {json.loads(x)["pair_id"]: json.loads(x)
             for x in open(os.path.join(d, "sample.jsonl"), encoding="utf-8")}
    meta = json.load(open(os.path.join(d, "sample_meta.json"), encoding="utf-8"))
    answers = defaultdict(dict)
    for line in open(os.path.join(d, "answers.jsonl"), encoding="utf-8"):
        a = json.loads(line)
        if a["verdict"]:
            answers[a["pair_id"]][a["reader"]] = a
    readers = sorted({r for v in answers.values() for r in v})
    complete = [p for p in items if all(r in answers.get(p, {}) for r in readers)]

    def verdicts(p):
        return [answers[p][r]["verdict"] for r in readers]

    maj = {p: majority(verdicts(p)) for p in complete}

    def block(ps):
        k, n = sum(maj[p] == "same" for p in ps), len(ps)
        lo, hi = wilson(k, n)
        return {"n": n, "same": k, "different": sum(maj[p] == "different" for p in ps),
                "cannot_tell_or_split": n - k - sum(maj[p] == "different" for p in ps),
                "precision": k / n if n else None, "wilson95": [lo, hi]}

    by_gap = {g: block([p for p in complete if items[p]["gap"] == g]) for g in GAPS}
    by_author = {a: block([p for p in complete if items[p]["author"] == a]) for a in AUTHOR_STRATA}
    # Population-weighted: each cell's precision weighted by its share of all candidate pairs.
    pop = {k: v["population"] for k, v in meta["cells"].items()}
    total = sum(pop.values())
    est, var = 0.0, 0.0
    for cell, npop in pop.items():
        g, a = cell.split("|")
        ps = [p for p in complete if items[p]["gap"] == int(g) and items[p]["author"] == a]
        if not ps:
            continue
        ph = sum(maj[p] == "same" for p in ps) / len(ps)
        w = npop / total
        est += w * ph
        var += w * w * ph * (1 - ph) / len(ps) * (1 - len(ps) / npop if npop > 1 else 0)
    pairwise = {}
    for i, a in enumerate(readers):
        for b in readers[i + 1:]:
            both = [p for p in complete]
            pairwise[f"{a}~{b}"] = sum(answers[p][a]["verdict"] == answers[p][b]["verdict"]
                                       for p in both) / len(both) if both else None
    false_merges = [{"pair_id": p, "gap": items[p]["gap"], "author": items[p]["author"],
                     "wp": {k: items[p]["wp"][k] for k in ("record_id", "title", "year", "first_author",
                                                            "journal", "doi")},
                     "pub": {k: items[p]["pub"][k] for k in ("record_id", "title", "year",
                                                              "first_author", "journal", "doi")},
                     "verdicts": {r: answers[p][r]["verdict"] for r in readers},
                     "reasons": {r: answers[p][r]["reason"] for r in readers}}
                    for p in complete if maj[p] == "different"]
    summary = {
        "readers": readers, "pairs_sampled": len(items), "pairs_read_by_all": len(complete),
        "overall_sample_share": block(complete),
        "overall_population_weighted": {"precision": est, "normal95": [est - 1.96 * math.sqrt(var),
                                                                       est + 1.96 * math.sqrt(var)]},
        "by_gap": by_gap, "by_author": by_author,
        "agreement": {"pairwise": pairwise,
                      "fleiss_kappa": fleiss_kappa([verdicts(p) for p in complete]),
                      "unanimous": sum(len(set(verdicts(p))) == 1 for p in complete)},
        "verdicts_by_reader": {r: dict(Counter(answers[p][r]["verdict"] for p in complete))
                               for r in readers},
        "false_merges": false_merges,
    }
    with open(os.path.join(d, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(os.path.join(d, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write(summary_markdown(summary))
    return summary


def _pct(b):
    lo, hi = b["wilson95"]
    return "n/a" if b["n"] == 0 else f"{b['precision']:.3f} [{lo:.3f}, {hi:.3f}] (n {b['n']})"


def summary_markdown(s):
    lines = ["# Dedup step 5 precision panel (ticket 2048)", "",
             f"Readers: {', '.join(s['readers'])}. Pairs read by all: {s['pairs_read_by_all']} "
             f"of {s['pairs_sampled']}. Precision = share the majority reads same, Wilson 95 %.", "",
             f"- overall, sample share: {_pct(s['overall_sample_share'])}",
             "- overall, weighted by cell population: {:.3f} [{:.3f}, {:.3f}]".format(
                 s["overall_population_weighted"]["precision"],
                 *s["overall_population_weighted"]["normal95"]), "", "## By year gap", ""]
    lines += [f"- {g:+d}: {_pct(b)}" for g, b in s["by_gap"].items()]
    lines += ["", "## By first-author agreement", ""]
    lines += [f"- {a}: {_pct(b)}" for a, b in s["by_author"].items()]
    ag = s["agreement"]
    lines += ["", "## Agreement", "", f"- Fleiss kappa: {ag['fleiss_kappa']}",
              f"- unanimous: {ag['unanimous']}"] + [f"- {k}: {v:.3f}" for k, v in ag["pairwise"].items()]
    lines += ["", f"## False merges (majority different): {len(s['false_merges'])}", ""]
    for f in s["false_merges"]:
        lines.append(f"- {f['pair_id']} gap {f['gap']:+d}, {f['author']}: \"{f['wp']['title']}\" "
                     f"({f['wp']['year']}, {f['wp']['doi'] or f['wp']['record_id']}) vs "
                     f"\"{f['pub']['title']}\" ({f['pub']['year']}, {f['pub']['doi'] or f['pub']['record_id']})")
    return "\n".join(lines) + "\n"


# ── CLI ──────────────────────────────────────────────────


def cmd_sample(args):
    import yaml
    from _rel_pool_dedup import cluster_with
    from _rel_title_key import title_key
    from corpus_rel_pool import load_rows
    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    rows = load_rows(cfg, args.catalogue or cfg["catalogue"]["path"],
                     args.intake_dir or cfg["intake_dir"])[0]
    pairs = []
    cluster_with(rows, None, title_key, repec=True, guard=True, versions=True, pairs=pairs)
    cands = candidate_pairs(rows, pairs)
    os.makedirs(args.dir, exist_ok=True)
    with open(os.path.join(args.dir, "candidates.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["pair_id", "gap", "author", "wp_record_id", "wp_doi", "wp_year", "wp_title",
                    "pub_record_id", "pub_doi", "pub_year", "pub_title"])
        for c in cands:
            w.writerow([c["pair_id"], c["gap"], c["author"]]
                       + [c[s][k] for s in ("wp", "pub") for k in ("record_id", "doi", "year", "title")])
    sample, cells = draw(cands, args.n)
    for name, objs in (("sample.jsonl", sample), ("controls.jsonl", controls(rows, cands))):
        with open(os.path.join(args.dir, name), "w", encoding="utf-8") as fh:
            for o in objs:
                fh.write(json.dumps(o, ensure_ascii=False) + "\n")
    with open(os.path.join(args.dir, "sample_meta.json"), "w", encoding="utf-8") as fh:
        json.dump({"candidates": len(cands), "sampled": len(sample), "seed": 2048, "cells": cells,
                   "by_gap": dict(sorted(Counter(c["gap"] for c in cands).items())),
                   "by_author": dict(Counter(c["author"] for c in cands))}, fh, indent=2)
    print(json.dumps({"candidates": len(cands), "sampled": len(sample)}))


def main(argv=None):
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample")
    s.add_argument("--dir", required=True)
    s.add_argument("--config", default=os.path.join(ROOT, "config", "rel_pool.yaml"))
    s.add_argument("--catalogue")
    s.add_argument("--intake-dir")
    s.add_argument("--n", type=int, default=400)
    r = sub.add_parser("run")
    r.add_argument("--dir", required=True)
    r.add_argument("--cap-usd", type=float, default=10.0)
    r.add_argument("--readers", default="anthropic,openai,mistral")
    a = sub.add_parser("analyze")
    a.add_argument("--dir", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "sample":
        cmd_sample(args)
    elif args.cmd == "run":
        print(json.dumps(run_panel(args.dir, args.cap_usd, args.readers.split(",")), indent=1))
    else:
        s = analyze(args.dir)
        print(summary_markdown(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
