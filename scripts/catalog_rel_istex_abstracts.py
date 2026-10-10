"""Recover missing abstracts from the ISTEX archive by DOI (ticket 2046, stage A).

ISTEX (``api.istex.fr/document/``) answers metadata queries without credentials.
This script looks up, in batches of 20, every pool work that has a DOI and no
abstract, archives the raw responses, then judges each hit against the pool.

Two subcommands share one archive directory (``--output-dir``, a multi-output
script, hence no ``--output``; see ``.claude/rules/script-io.md``):

``fetch``    copies the pool table into the archive (sha256 recorded), runs the
             positive and negative controls, then queries the batches. Resumable:
             a batch whose raw file exists is skipped, never rewritten. Stops at
             the first HTTP error, timeout, unparsable or truncated answer: no
             retry loop. Writes ``MANIFEST.sha256``.
``analyze``  refuses to write counts unless the last control record passed and
             every batch is archived; then writes, under ``analysis/`` (never
             overwritten): the decisions per DOI, the accepted abstracts, the
             counts by lane, period and language, and the residue.

Archive layout::

    pool_input.csv  pool_input.sha256  run_meta.json  controls.jsonl
    requests.jsonl  run.log  raw/b000001.json ...  analysis/  MANIFEST.sha256

Match safety. A DOI hit is accepted only if all hold, tested in this order, the
first failure being its rejection cause:

1. the record carries an abstract (``record_without_abstract``);
2. publication years differ by at most ``--year-tolerance`` (default 1: online
   first against issue year) when both are known (``year_mismatch``);
3. normalised titles (casefold, accents and punctuation dropped) have a
   difflib similarity of at least ``--title-threshold`` (default 0.80) when both
   are known (``title_mismatch``);
4. the abstract is not boilerplate (``openalex_corpus.embedding.
   is_boilerplate_abstract``, with the pool title) (``boilerplate``);
5. the abstract has at least ``--min-chars`` characters (default 100; the pilot
   showed none shorter) (``stub_too_short``).

A leading ``Abstract:`` style label is stripped from the ISTEX text (Elsevier and
Springer records carry it); the raw archive keeps it. A pool abstract is never
replaced: only abstract-less rows are queried and each is re-checked as blank
at decision time.

Usage (padme)::

    PYTHONPATH=libs/openalex-corpus/src python3 scripts/catalog_rel_istex_abstracts.py \\
        fetch --pool POOL.csv --output-dir ~/data/projets/climate-finance-het/rel_istex_abstracts/<date>
    ... analyze --output-dir <same>
"""

import argparse
import csv
import difflib
import hashlib
import json
import logging
import os
import re
import shutil
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone

import pandas as pd

BASE_URL = "https://api.istex.fr/document/"
BATCH_SIZE = 20
SIZE_PARAM = 100  # hits per page; a batch with more records than this stops the run
OUTPUT_FIELDS = "doi,abstract,language,title,publicationDate,corpusName,arkIstex"
POS_CONTROL_DOI = "10.1016/j.enpol.2010.01.001"  # Energy Policy 2010, ISTEX record with an abstract
NEG_CONTROL_DOI = "10.9999/istex-absent-control-0000"  # no such DOI in any archive
USER_AGENT = "climate-finance-het-istex-abstracts/1.0 (research; ticket 2046)"
PERIODS = ("1990-2006", "2007-2014", "2015-2025", "2026+")
CAUSES = ("record_without_abstract", "year_mismatch", "title_mismatch", "boilerplate", "stub_too_short")
# Pilot of 2026-10-09 (ticket 2046 context): 341 of 600 random abstract-less DOIs.
PILOT = {"overall": (341, 600), "1990-2006": (97, 148), "2007-2014": (105, 144),
         "2015-2025": (139, 273), "2026+": (0, 34)}
LABEL_RE = re.compile(r"^\s*(abstract|summary|résumé|resumen|zusammenfassung)\s*[:.—–-]\s*", re.I)

log = logging.getLogger("istex_abstracts")


class StopRun(Exception):
    """A condition on which the run stops without retrying."""


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def norm_doi(s):
    return str(s).strip().lower()


def batches_of(dois, n=BATCH_SIZE):
    return [dois[i:i + n] for i in range(0, len(dois), n)]


def build_url(batch, base_url=BASE_URL):
    q = "doi:(" + " OR ".join('"%s"' % d.replace("\\", "\\\\").replace('"', '\\"') for d in batch) + ")"
    return base_url + "?" + urllib.parse.urlencode(
        {"q": q, "size": SIZE_PARAM, "output": OUTPUT_FIELDS})


def period_of(year):
    try:
        y = int(str(year)[:4])
    except ValueError:
        return "unknown"
    if y < 1990:
        return "pre-1990"
    if y <= 2006:
        return "1990-2006"
    if y <= 2014:
        return "2007-2014"
    if y <= 2025:
        return "2015-2025"
    return "2026+"


def lang_of(s):
    s = str(s).strip().lower()
    if s in ("", "nan"):
        return "unknown"
    return "en" if s == "eng" else s


def year_of(s):
    m = re.match(r"\s*(\d{4})", str(s))
    return int(m.group(1)) if m else None


def _title_key(s):
    s = unicodedata.normalize("NFKD", str(s).casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^0-9a-z]+", " ", s).strip()


def title_ratio(a, b):
    ka, kb = _title_key(a), _title_key(b)
    if not ka or not kb:
        return None
    return round(difflib.SequenceMatcher(None, ka, kb, autojunk=False).ratio(), 4)


def clean_abstract(raw):
    """Return (text, label_stripped)."""
    text = re.sub(r"\s+", " ", str(raw or "")).strip()
    new = LABEL_RE.sub("", text, count=1)
    return new, new != text


def judge(pool_row, records, requested_doi, cfg, is_boilerplate):
    """Decide one DOI. ``records`` are the ISTEX hits carrying the DOI.

    Returns a dict: status ('accepted' | 'not_found' | 'rejected:<cause>'), plus
    the fields of the retained record. Never accepts for a pool row that already
    has an abstract.
    """
    if str(pool_row["abstract"]).strip():
        raise ValueError("pool row already has an abstract: %s" % requested_doi)
    if not records:
        return {"status": "not_found", "n_records": 0}
    first_cause, best = None, None
    for rec in records:
        text, stripped = clean_abstract(rec.get("abstract"))
        ratio = title_ratio(pool_row["title"], rec.get("title"))
        iy, py = year_of(rec.get("publicationDate")), year_of(pool_row["year"])
        info = {"istex_ark": rec.get("arkIstex", ""), "corpus": rec.get("corpusName", ""),
                "istex_language": ";".join(rec.get("language") or []),
                "istex_year": iy, "title_ratio": ratio, "abstract_chars": len(text),
                "label_stripped": stripped, "abstract": text, "n_records": len(records)}
        if not text:
            cause = "record_without_abstract"
        elif iy is not None and py is not None and abs(iy - py) > cfg["year_tolerance"]:
            cause = "year_mismatch"
        elif ratio is not None and ratio < cfg["title_threshold"]:
            cause = "title_mismatch"
        elif is_boilerplate(text, title=pool_row["title"]):
            cause = "boilerplate"
        elif len(text) < cfg["min_chars"]:
            cause = "stub_too_short"
        else:
            cause = None
        if cause is None:
            if best is None or len(text) > best["abstract_chars"]:
                best = dict(info, status="accepted")
        elif first_cause is None:
            first_cause = dict(info, status="rejected:" + cause)
    return best or first_cause


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(out_dir):
    """(Re)write MANIFEST.sha256 (sha256sum format) over every file but itself.

    Raw batches and the pool copy are immutable: a hash that differs from the
    previous manifest stops the run instead of being re-recorded.
    """
    mpath = os.path.join(out_dir, "MANIFEST.sha256")
    old = {}
    if os.path.exists(mpath):
        for line in open(mpath, encoding="utf-8"):
            h, _, p = line.rstrip("\n").partition("  ")
            old[p] = h
    new = {}
    for root, _, files in os.walk(out_dir):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, out_dir)
            if rel != "MANIFEST.sha256":
                new[rel] = sha256_file(full)
    for rel, h in old.items():
        if (rel.startswith("raw/") or rel == "pool_input.csv") and new.get(rel) != h:
            raise StopRun("immutable archive file changed or vanished: %s" % rel)
    tmp = mpath + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for rel in sorted(new):
            f.write("%s  %s\n" % (new[rel], rel))
    os.replace(tmp, mpath)
    return len(new)


def http_get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def is_truncated(data):
    return data["total"] > len(data["hits"])


def _query(get, url, allow_truncated=False):
    """One GET. A truncated page is returned only when the caller handles it (a
    malformed pool DOI such as ``10.1007/978-3-030-`` matches thousands of records)."""
    try:
        status, body = get(url)
    except (OSError, urllib.error.URLError) as e:  # timeouts, DNS, resets
        raise StopRun("transport error: %r" % (e,))
    if status != 200:
        raise StopRun("HTTP %s (stopping, no retry)" % status)
    try:
        data = json.loads(body)
    except ValueError:
        raise StopRun("answer is not JSON")
    if not isinstance(data.get("hits"), list) or "total" not in data:
        raise StopRun("answer lacks hits/total")
    if is_truncated(data) and not allow_truncated:
        raise StopRun("truncated answer: total %s > hits %s" % (data["total"], len(data["hits"])))
    return body, data


def hit_dois(hit):
    d = hit.get("doi") or []
    return [norm_doi(x) for x in (d if isinstance(d, list) else [d])]


def run_controls(get, base_url=BASE_URL):
    """Positive: a known DOI returns an abstract. Negative: an absent DOI returns nothing."""
    _, pos = _query(get, build_url([POS_CONTROL_DOI], base_url))
    pos_ok = any(POS_CONTROL_DOI in hit_dois(h) and len(str(h.get("abstract") or "")) >= 100
                 for h in pos["hits"])
    _, neg = _query(get, build_url([NEG_CONTROL_DOI], base_url))
    neg_ok = neg["total"] == 0 and not neg["hits"]
    return {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "positive_doi": POS_CONTROL_DOI, "positive_ok": bool(pos_ok),
            "negative_doi": NEG_CONTROL_DOI, "negative_ok": bool(neg_ok)}


# ---------------------------------------------------------------------------
# Pool
# ---------------------------------------------------------------------------

POOL_COLS = ["work_key", "doi", "title", "year", "abstract", "language", "sources"]


def load_pool(path):
    d = pd.read_csv(path, usecols=POOL_COLS, dtype=str, keep_default_na=False)
    d["doi_n"] = d["doi"].map(norm_doi)
    d["blank"] = d["abstract"].str.strip() == ""
    return d


def todo_dois(pool):
    q = pool[pool["blank"] & (pool["doi_n"] != "")]
    if q["doi_n"].duplicated().any():
        raise StopRun("several abstract-less pool rows share a DOI")
    return sorted(q["doi_n"])


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------

def _append(path, obj):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def cmd_fetch(args, get=http_get):
    out = args.output_dir
    os.makedirs(os.path.join(out, "raw"), exist_ok=True)
    fh = logging.FileHandler(os.path.join(out, "run.log"))
    fh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    log.addHandler(fh)
    try:
        return _fetch(args, get)
    except StopRun as e:
        log.error("STOP: %s", e)
        write_manifest(out)
        return 2
    finally:
        log.removeHandler(fh)
        fh.close()


def _ensure_pool_copy(args):
    out = args.output_dir
    pool_copy = os.path.join(out, "pool_input.csv")
    sha_path = os.path.join(out, "pool_input.sha256")
    if os.path.exists(pool_copy):
        if sha256_file(pool_copy) != open(sha_path).read().split()[0]:
            raise StopRun("archived pool copy does not match its recorded sha256")
        if args.pool and sha256_file(args.pool) != open(sha_path).read().split()[0]:
            raise StopRun("--pool differs from the archived copy; use a new --output-dir")
    else:
        if not args.pool:
            raise StopRun("--pool is required on the first run")
        with open(args.pool, "rb") as src, open(pool_copy, "xb") as dst:
            shutil.copyfileobj(src, dst)
        with open(sha_path, "x") as f:
            f.write("%s  pool_input.csv\n" % sha256_file(pool_copy))
    return pool_copy


class _Pacer:
    def __init__(self, delay):
        self.delay, self.n = delay, 0

    def wait(self):
        if self.n:
            time.sleep(self.delay)
        self.n += 1


def _archive_new(out, name, body):
    with open(os.path.join(out, "raw", name), "xb") as f:  # exclusive: never overwrites
        f.write(body)


def _fetch_batch(out, i, batch, base_url, get, pacer):
    """Archive batch ``i``. A truncated answer (an over-matching malformed DOI)
    is followed by one query per DOI of the batch, archived as ``b<i>.s<k>.json``;
    that split is bounded (len(batch) requests) and is not a retry of an error."""
    path = os.path.join(out, "raw", "b%06d.json" % i)
    if os.path.exists(path):
        data = json.loads(open(path, "rb").read())  # a corrupt archive file stops here
    else:
        pacer.wait()
        body, data = _query(get, build_url(batch, base_url), allow_truncated=True)
        _archive_new(out, "b%06d.json" % i, body)
        _append(os.path.join(out, "requests.jsonl"),
                {"batch": i, "n_dois": len(batch), "total": data["total"], "truncated": is_truncated(data),
                 "sha256": hashlib.sha256(body).hexdigest(), "dois": batch})
    if is_truncated(data) and len(batch) > 1:
        for k, d in enumerate(batch, 1):
            name = "b%06d.s%02d.json" % (i, k)
            if not os.path.exists(os.path.join(out, "raw", name)):
                pacer.wait()
                body, _ = _query(get, build_url([d], base_url), allow_truncated=True)
                _archive_new(out, name, body)


def _fetch(args, get):
    out = args.output_dir
    pool_copy = _ensure_pool_copy(args)
    pool = load_pool(pool_copy)
    dois = todo_dois(pool)
    batches = batches_of(dois)
    todo_sha = hashlib.sha256("\n".join(dois).encode()).hexdigest()
    meta_path = os.path.join(out, "run_meta.json")
    meta = {"todo_sha256": todo_sha, "n_dois": len(dois), "n_batches": len(batches),
            "batch_size": BATCH_SIZE, "base_url": args.base_url, "fields": OUTPUT_FIELDS}
    if os.path.exists(meta_path):
        if json.load(open(meta_path))["todo_sha256"] != todo_sha:
            raise StopRun("DOI list differs from the one of the first run")
    else:
        with open(meta_path, "x") as f:
            json.dump(meta, f, indent=1)
    log.info("%d DOIs in %d batches", len(dois), len(batches))

    ctl = run_controls(get, args.base_url)
    ctl["phase"] = "pre"
    _append(os.path.join(out, "controls.jsonl"), ctl)
    log.info("controls pre: %s", ctl)
    if not (ctl["positive_ok"] and ctl["negative_ok"]):
        raise StopRun("controls failed before any batch")

    pacer = _Pacer(args.delay)
    done = 0
    sent = 0
    for i, batch in enumerate(batches, 1):
        if not os.path.exists(os.path.join(out, "raw", "b%06d.json" % i)):
            if args.max_batches is not None and sent >= args.max_batches:
                break
            sent += 1
        _fetch_batch(out, i, batch, args.base_url, get, pacer)
        done += 1
        if i % 200 == 0:
            log.info("batch %d/%d", i, len(batches))
    log.info("batches archived: %d of %d (%d new)", done, len(batches), sent)
    if done == len(batches):
        ctl = run_controls(get, args.base_url)
        ctl["phase"] = "post"
        _append(os.path.join(out, "controls.jsonl"), ctl)
        log.info("controls post: %s", ctl)
        if not (ctl["positive_ok"] and ctl["negative_ok"]):
            raise StopRun("controls failed after the last batch")
    n = write_manifest(out)
    log.info("MANIFEST.sha256: %d files", n)
    return 0


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------

def _check_controls(out):
    path = os.path.join(out, "controls.jsonl")
    if not os.path.exists(path):
        raise StopRun("no controls recorded; counts refused")
    recs = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
    last = recs[-1]
    if not (last["positive_ok"] and last["negative_ok"]):
        raise StopRun("last control record failed; counts refused")
    return recs


def _load_hits(out, dois):
    """Map requested DOI -> ISTEX records; also diagnostics and the DOIs left unresolved
    (their single-DOI query was still truncated)."""
    by_doi, diag, unresolved = {}, Counter(), set()

    def take(data, req):
        for h in data["hits"]:
            m = [d for d in hit_dois(h) if d in req]
            if not m:
                diag["hit_not_requested"] += 1
            for d in m:
                by_doi.setdefault(d, []).append(h)

    def load(name):
        return json.loads(open(os.path.join(out, "raw", name), "rb").read())

    for i, batch in enumerate(batches_of(dois), 1):
        data = load("b%06d.json" % i)
        if not is_truncated(data):
            take(data, set(batch))
            continue
        diag["truncated_batches"] += 1
        singles = enumerate(batch, 1) if len(batch) > 1 else [(0, batch[0])]
        for k, d in singles:
            one = load("b%06d.s%02d.json" % (i, k)) if k else data
            if is_truncated(one):
                unresolved.add(d)
            else:
                take(one, {d})
    return by_doi, diag, unresolved


def _write_new(path, rows, fields):
    with open(path, "x", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def cmd_analyze(args):
    try:
        return _analyze(args)
    except StopRun as e:
        log.error("STOP: %s", e)
        return 2


def _flags(g):
    s = g["status"]
    o = {"pool_works": len(g), "with_abstract_before": int((~g["blank"]).sum()),
         "abstractless": int(g["blank"].sum()),
         "abstractless_no_doi": int((g["blank"] & (g["doi_n"] == "")).sum()),
         "queried": int((s != "").sum()), "accepted": int((s == "accepted").sum()),
         "not_found": int((s == "not_found").sum()),
         "unresolved_truncated": int((s == "unresolved:truncated").sum())}
    for c in CAUSES:
        o["rejected_" + c] = int((s == "rejected:" + c).sum())
    o["istex_record"] = o["queried"] - o["not_found"] - o["unresolved_truncated"]
    o["istex_abstract"] = o["istex_record"] - o["rejected_record_without_abstract"]
    o["with_abstract_after"] = o["with_abstract_before"] + o["accepted"]
    o["residue"] = o["abstractless"] - o["accepted"]
    return o


def count_tables(pool, status):
    """Long-format counts by overall, period, language and lane (a work in two lanes counts in both)."""
    p = pool.copy()
    p["status"] = p["doi_n"].map(lambda d: status.get(d, "")).where(p["blank"], "")
    p["period"] = p["year"].map(period_of)
    p["lang"] = p["language"].map(lang_of)
    p["lane"] = p["sources"].map(lambda s: [x for x in s.split(";") if x] or ["(none)"])
    counts = []
    groups = [("overall", [("all", p)]), ("period", p.groupby("period")), ("language", p.groupby("lang")),
              ("lane", p.explode("lane").groupby("lane"))]
    for dim, gs in groups:
        for val, g in gs:
            counts += [{"dimension": dim, "value": val, "metric": k, "n": v} for k, v in _flags(g).items()]
    return counts


def _analyze(args):
    from openalex_corpus.embedding import is_boilerplate_abstract

    out = args.output_dir
    recs = _check_controls(out)
    pool = load_pool(os.path.join(out, "pool_input.csv"))
    dois = todo_dois(pool)
    nb = len(batches_of(dois))
    have = len([f for f in os.listdir(os.path.join(out, "raw")) if re.fullmatch(r"b\d{6}\.json", f)])
    if have != nb and not args.allow_partial:
        raise StopRun("%d of %d batches archived; counts refused" % (have, nb))
    ana = os.path.join(out, args.analysis_dir)
    os.makedirs(ana)  # FileExistsError if the analysis exists: never overwritten
    cfg = {"year_tolerance": args.year_tolerance, "title_threshold": args.title_threshold,
           "min_chars": args.min_chars}
    by_doi, diag, unresolved = _load_hits(out, dois[:have * BATCH_SIZE])
    rows = {r.doi_n: r for r in pool[pool["blank"] & (pool["doi_n"] != "")].itertuples()}
    dec, accepted = [], []
    for d in dois[:have * BATCH_SIZE]:
        r = rows[d]
        pr = {"title": r.title, "year": r.year, "abstract": r.abstract}
        j = judge(pr, by_doi.get(d, []), d, cfg, is_boilerplate_abstract)
        if d in unresolved:
            j = {"status": "unresolved:truncated", "n_records": 0}
        dec.append({"doi": d, "work_key": r.work_key, "status": j["status"],
                    "n_records": j.get("n_records", 0), "istex_ark": j.get("istex_ark", ""),
                    "corpus": j.get("corpus", ""), "istex_language": j.get("istex_language", ""),
                    "istex_year": j.get("istex_year", ""), "pool_year": r.year,
                    "title_ratio": j.get("title_ratio", ""), "abstract_chars": j.get("abstract_chars", ""),
                    "label_stripped": j.get("label_stripped", "")})
        if j["status"] == "accepted":
            accepted.append({"doi": d, "work_key": r.work_key, "abstract": j["abstract"],
                             "abstract_source": "istex", "istex_ark": j["istex_ark"],
                             "istex_language": j["istex_language"], "corpus": j["corpus"]})
    _write_new(os.path.join(ana, "istex_decisions.csv"), dec, list(dec[0]))
    _write_new(os.path.join(ana, "istex_abstracts_accepted.csv"), accepted,
               ["doi", "work_key", "abstract", "abstract_source", "istex_ark", "istex_language", "corpus"])

    status = {r["doi"]: r["status"] for r in dec}
    counts = count_tables(pool, status)
    _write_new(os.path.join(ana, "counts.csv"), counts, ["dimension", "value", "metric", "n"])

    ov = {c["metric"]: c["n"] for c in counts if c["dimension"] == "overall"}
    by_period = {}
    for c in counts:
        if c["dimension"] == "period":
            by_period.setdefault(c["value"], {})[c["metric"]] = c["n"]
    dd = pd.DataFrame(dec)
    tr = pd.to_numeric(dd["title_ratio"], errors="coerce")
    ch = pd.to_numeric(dd["abstract_chars"], errors="coerce")
    summary = {
        "thresholds": cfg, "controls_last": recs[-1], "n_control_records": len(recs),
        "batches": have, "expected_batches": nb, "diagnostics": dict(diag),
        "overall": ov, "period": by_period,
        "pilot_rate_overall": PILOT["overall"][0] / PILOT["overall"][1],
        "pilot_by_period": {k: v[0] / v[1] for k, v in PILOT.items() if k != "overall"},
        "found_rate_abstract_in_record": ov["istex_abstract"] / ov["queried"] if ov["queried"] else None,
        "accepted_rate": ov["accepted"] / ov["queried"] if ov["queried"] else None,
        "multi_record_dois": int((dd["n_records"] > 1).sum()),
        "label_stripped": int((dd["label_stripped"] == True).sum()),
        "sensitivity": {
            "title_ratio_0.70_to_threshold": int(((tr >= 0.70) & (tr < cfg["title_threshold"])).sum()),
            "title_ratio_threshold_to_0.90": int(((tr >= cfg["title_threshold"]) & (tr < 0.90)).sum()),
            "accepted_chars_100_to_200": int(((ch >= 100) & (ch < 200) & (dd["status"] == "accepted")).sum()),
        },
        "istex_language_of_accepted": dict(Counter(a["istex_language"] for a in accepted)),
        "corpus_of_accepted": dict(Counter(a["corpus"] for a in accepted).most_common(15)),
    }
    with open(os.path.join(ana, "counts.json"), "x", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, ensure_ascii=False)
    n = write_manifest(out)
    log.info("analysis written to %s (%d files in manifest)", ana, n)
    log.info("%s", json.dumps({k: summary[k] for k in ("overall", "found_rate_abstract_in_record", "accepted_rate",
                                                       "pilot_rate_overall", "sensitivity")}, indent=1))
    return 0


# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="query ISTEX and archive raw responses")
    f.add_argument("--pool", help="pool CSV (copied into the archive on the first run)")
    f.add_argument("--output-dir", required=True, help="archive directory (created if absent)")
    f.add_argument("--delay", type=float, default=0.25, help="seconds between requests")
    f.add_argument("--max-batches", type=int, default=None, help="stop after N new batches (smoke runs)")
    f.add_argument("--base-url", default=BASE_URL)
    a = sub.add_parser("analyze", help="judge hits and write counts")
    a.add_argument("--output-dir", required=True, help="archive directory of a fetch run")
    a.add_argument("--analysis-dir", default="analysis", help="subdirectory to create (must not exist)")
    a.add_argument("--year-tolerance", type=int, default=1)
    a.add_argument("--title-threshold", type=float, default=0.80)
    a.add_argument("--min-chars", type=int, default=100)
    a.add_argument("--allow-partial", action="store_true", help="analyse only the archived batches (smoke)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(message)s")
    return cmd_fetch(args) if args.cmd == "fetch" else cmd_analyze(args)


if __name__ == "__main__":
    sys.exit(main())
