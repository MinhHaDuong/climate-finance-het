"""Resumable REL citation rounds: full metadata, every edge, no year filter.

Multiple outputs live below required --output-dir. SQLite is the checkpoint;
raw API pages are durable before cursor advancement. Deliveries are exported
only on request, and remain incomplete when any route cannot be traversed.
"""

import csv
import gzip
import hashlib
import html
import json
import os
import re
import socket
import sqlite3
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import _icf_screen as screens
import qa_rel_intake as contract
import requests
from openalex_corpus.text import reconstruct_abstract
from pipeline_keystore import read_credential
from utils import MAILTO, get_logger, normalize_doi, normalize_title

log = get_logger("rel_citation_chaining")
OA = "https://api.openalex.org/works"


def parse_stage1_batch_results(native_results, mapping, input_price=.05 / 1e6, output_price=.25 / 1e6):
    """Associate unordered native Batch results exactly; quarantine ambiguity.

    Returns valid labels, per-request cost/disposition evidence and faults.
    Whole-request coverage is required before callers release the reservation.
    No labels are invented for failed, partial or duplicated answers.
    """
    expected = dict(mapping)
    work_keys = [key for keys in expected.values() for key in keys]
    if len(work_keys) != len(set(work_keys)):
        raise ChainError("duplicate work keys in Batch mapping")
    seen, labels, receipts, faults = set(), [], [], []
    for native in native_results:
        ident = native.get("custom_id")
        if ident not in expected or ident in seen:
            raise ChainError("unknown or duplicate native Batch custom_id")
        seen.add(ident)
        result = native.get("result") or {}
        kind = result.get("type")
        if kind in {"errored", "canceled", "expired"}:
            receipts.append({"custom_id": ident, "type": kind, "derived_cost": 0,
                             "charge_basis": "documented terminal Batch result: no message created/billed"})
            faults.append({"custom_id": ident, "fault": kind, "pending_keys": expected[ident]})
            continue
        if kind != "succeeded":
            raise ChainError("unknown native Batch result type; liability retained")
        message = result.get("message") or {}
        if message.get("model") != "claude-haiku-5-5":
            raise ChainError("unexpected Batch served model")
        usage = message.get("usage") or {}
        valid_usage = all(type(usage.get(k)) is int and usage[k] >= 0 for k in ["input_tokens", "output_tokens"])
        cache = usage.get("cache_creation_input_tokens", 0) or usage.get("cache_read_input_tokens", 0)
        cost = usage["input_tokens"] * input_price + usage["output_tokens"] * output_price if valid_usage and not cache else None
        receipts.append({"custom_id": ident, "type": kind, "usage": usage, "derived_cost": cost,
                         "model": message["model"], "stop_reason": message.get("stop_reason")})
        if message.get("stop_reason") != "end_turn":
            faults.append({"custom_id": ident, "fault": "truncated reply", "pending_keys": expected[ident]})
            continue
        text = "\n".join(c.get("text", "") for c in message.get("content", []) if c.get("type") == "text")
        try:
            lo, hi = text.index("["), text.rindex("]")
            answers = json.loads(text[lo:hi + 1])
            if not isinstance(answers, list):
                raise ValueError("not a list")
        except (ValueError, TypeError):
            faults.append({"custom_id": ident, "fault": "invalid JSON answer list", "pending_keys": expected[ident]})
            continue
        numbers = Counter(a.get("n") for a in answers if isinstance(a, dict) and type(a.get("n")) is int)
        valid = set()
        for answer in answers:
            if not isinstance(answer, dict):
                continue
            n = answer.get("n")
            if type(n) is not int or not 1 <= n <= len(expected[ident]) or numbers[n] != 1:
                continue
            label, doc = answer.get("label"), answer.get("doc")
            if not isinstance(label, str) or not isinstance(doc, str):
                continue
            if label not in {"icf", "aux", "out", "unsure"} or doc not in {"research", "institutional", "other"}:
                continue
            key = expected[ident][n - 1]
            labels.append({"work_key": key, "label": label, "doc": doc,
                           "why": str(answer.get("why", ""))[:160], "model": message["model"], "custom_id": ident})
            valid.add(key)
        pending = [key for key in expected[ident] if key not in valid]
        if pending:
            faults.append({"custom_id": ident, "fault": "missing/invalid/duplicate record answers", "pending_keys": pending})
    missing = set(expected) - seen
    if missing:
        raise ChainError(f"incomplete native Batch result coverage: {len(missing)} requests missing")
    return labels, receipts, faults


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def oid(value):
    return str(value or "").rsplit("/", 1)[-1]


def sha(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def dump(path, obj):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def rows(path):
    with open(path, encoding="utf-8", newline="") as stream:
        yield from csv.DictReader(stream)


def csv_write(path, fields, records):
    with open(path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def forward_edges(work, seeds, query, aliases=None):
    refs = {oid(v) for v in work.get("referenced_works") or []}
    aliases = aliases or {}
    return [(seed, oid(work["id"]), "forward", query) for seed in seeds if aliases.get(seed, seed) in refs]


def intake_record(work, query, date):
    authors = work.get("authorships") or []
    names = [a.get("author", {}).get("display_name", "") for a in authors]
    source = (work.get("primary_location") or {}).get("source") or {}
    loc = work.get("primary_location") or {}
    key = oid(work.get("id"))
    return {
        "record_id": key, "query_id": query, "platform": "openalex", "retrieved_at": date,
        "title": work.get("display_name") or work.get("title") or "",
        "platform_record_id": key, "doi": normalize_doi(work.get("doi")) or "",
        "openalex_id": key, "first_author": names[0] if names else "",
        "all_authors": "; ".join(names), "year": work.get("publication_year") or "",
        "publication_date": work.get("publication_date") or "", "journal": source.get("display_name") or "",
        "issn": "; ".join(source.get("issn") or []), "doc_type": work.get("type") or "",
        "language": work.get("language") or "",
        "abstract": reconstruct_abstract(work.get("abstract_inverted_index")) or "",
        "url": loc.get("landing_page_url") or work.get("doi") or work.get("id") or "",
        "affiliation_countries": "; ".join(sorted({c for a in authors for c in a.get("countries") or []})),
        "cited_by_count": work.get("cited_by_count") or 0,
    }


class ChainError(Exception):
    """A route cannot safely advance."""


def bounded_screen_post(root, ledger, pricing, key, post=requests.post):
    """Injected DesignB transport: reserve every HTTP attempt, including retries.

    Pricing is an archived current endpoint snapshot. Text bytes conservatively
    bound tokens; native request/reply evidence belongs to the immutable run.
    Unknown responses retain the liability and abort rather than retry blindly.
    """
    def send(url, body, timeout):
        store = Store(root, ledger)
        store.bind("budget_usd", 20)
        store.db.execute("CREATE TABLE IF NOT EXISTS screen_http(call INTEGER PRIMARY KEY,request BLOB,reply BLOB)")
        store.db.commit()
        model = body["model"]
        price = pricing[model]
        payload = json.loads(json.dumps(body))
        payload["provider"] = {"max_price": {"prompt": str(price["prompt"] * 1e6),
                                            "completion": str(price["completion"] * 1e6),
                                            "request": str(price.get("request", 0))}}
        if "max_tokens" in body:
            payload["provider"]["require_parameters"] = True
        bound = (len(json.dumps(payload, ensure_ascii=False).encode()) + 2048) * price["prompt"]
        bound += body.get("max_tokens", price.get("max_completion_tokens", 0)) * price["completion"]
        bound += price.get("request", 0)
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        call = store.reserve("openrouter-designb", max(bound, 1e-9), {"model": model, "request_sha256": digest})
        request = {"url": url, "body": payload, "call": call,
                   "pricing": price, "reserved_usd": bound, "at": now()}
        store.db.execute("INSERT INTO screen_http(call,request) VALUES(?,?)",
                         (call, gzip.compress(json.dumps(request, ensure_ascii=False).encode(), mtime=0)))
        store.db.commit()
        try:
            response = post(url, headers={"Authorization": "Bearer " + key}, json=payload, timeout=timeout)
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            store.db.close()
            raise ChainError("ambiguous stage1 request; liability retained; no automatic retry") from exc
        reply = {"status": response.status_code, "body": data, "at": now()}
        store.db.execute("UPDATE screen_http SET reply=? WHERE call=?",
                         (gzip.compress(json.dumps(reply, ensure_ascii=False).encode(), mtime=0), call))
        store.db.commit()
        cost = (data.get("usage") or {}).get("cost")
        if cost is None:
            if response.status_code == 529 and data.get("error") and not data.get("answers") and not data.get("choices"):
                store.db.execute("UPDATE budget.calls SET details=? WHERE k=?", (json.dumps({
                    "model": model, "request_sha256": digest, "http": 529,
                    "disposition": "terminal overload, no valid decision; replacement allowed within established retry limit",
                    "maximum_liability_retained": True}), call))
                store.db.commit()
                store.db.close()
                return 529, data, "terminal overload; full unknown liability retained"
            if response.status_code == 429:
                cost = 0
            else:
                store.db.close()
                raise ChainError("stage1 charge unknown; liability retained; reconcile native reply")
        store.settle(call, float(cost), {"model": model, "http": response.status_code,
                                      "usage": data.get("usage"), "reply": f"{store.root}/checkpoint.sqlite#screen_http:{call}"})
        store.db.close()
        return response.status_code, data, None if response.status_code == 200 else f"http {response.status_code}"
    return send


class Store:
    def __init__(self, root, budget_ledger=None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "raw").mkdir(exist_ok=True)
        self.db = sqlite3.connect(self.root / "checkpoint.sqlite", timeout=120)
        self.db.row_factory = sqlite3.Row
        self.budget_path = Path(budget_ledger) if budget_ledger else self.root.parent / "budget.sqlite"
        self.db.execute("ATTACH DATABASE ? AS budget", (str(self.budget_path),))
        self.db.execute("CREATE TABLE IF NOT EXISTS budget.calls(k INTEGER PRIMARY KEY,round TEXT,provider TEXT,reserve REAL,cost REAL,status TEXT,details TEXT,date TEXT)")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS config(k TEXT PRIMARY KEY,v TEXT);
            CREATE TABLE IF NOT EXISTS seeds(k TEXT PRIMARY KEY,oa TEXT,body TEXT,reason TEXT,resolution TEXT);
            CREATE TABLE IF NOT EXISTS queries(k TEXT PRIMARY KEY,kind TEXT,filter TEXT,seeds TEXT,
              cursor TEXT DEFAULT '*',received INTEGER DEFAULT 0,expected INTEGER,pages INTEGER DEFAULT 0,
              completed INTEGER DEFAULT 0,stop TEXT DEFAULT '',run_at TEXT DEFAULT '');
            CREATE TABLE IF NOT EXISTS works(k TEXT PRIMARY KEY,body TEXT,query TEXT,date TEXT);
            CREATE TABLE IF NOT EXISTS discoveries(q TEXT,w TEXT,PRIMARY KEY(q,w));
            CREATE TABLE IF NOT EXISTS edges(seed TEXT,candidate TEXT,direction TEXT,q TEXT,
              PRIMARY KEY(seed,candidate,direction,q));
            CREATE TABLE IF NOT EXISTS unresolved(k TEXT PRIMARY KEY,kind TEXT,note TEXT);
            CREATE TABLE IF NOT EXISTS api_pages(k TEXT PRIMARY KEY,path TEXT,call INTEGER);
            CREATE TABLE IF NOT EXISTS seed_aliases(old TEXT PRIMARY KEY,new TEXT,status TEXT);
        """)

    def bind(self, name, value):
        value = json.dumps(value, sort_keys=True)
        old = self.db.execute("SELECT v FROM config WHERE k=?", (name,)).fetchone()
        if old and old[0] != value:
            raise ChainError(f"resume basis changed: {name}")
        self.db.execute("INSERT OR IGNORE INTO config VALUES(?,?)", (name, value))
        self.db.commit()

    def config(self, key):
        return json.loads(self.db.execute("SELECT v FROM config WHERE k=?", (key,)).fetchone()[0])

    def put_work(self, work, query, date):
        key = oid(work.get("id"))
        if not key:
            raise ChainError("work without OpenAlex ID")
        self.db.execute("INSERT OR IGNORE INTO works VALUES(?,?,?,?)", (key, json.dumps(work), query, date))
        self.db.execute("INSERT OR IGNORE INTO discoveries VALUES(?,?)", (query, key))

    def add_query(self, key, kind, filt, seeds=()):
        old = self.db.execute("SELECT filter FROM queries WHERE k=?", (key,)).fetchone()
        if old and old[0] != filt:
            raise ChainError(f"changed query {key}")
        self.db.execute("INSERT OR IGNORE INTO queries(k,kind,filter,seeds) VALUES(?,?,?,?)",
                        (key, kind, filt, json.dumps(list(seeds))))
        self.db.commit()

    def reserve(self, provider, bound, details):
        if bound <= 0:
            raise ChainError("positive request liability required")
        self.db.execute("BEGIN IMMEDIATE")
        spent = self.db.execute("SELECT COALESCE(SUM(COALESCE(cost,reserve)),0) FROM budget.calls").fetchone()[0]
        if spent + bound > self.config("budget_usd"):
            self.db.rollback()
            raise ChainError(f"cumulative budget: {spent:.5f}+{bound:.5f} exceeds cap")
        call = self.db.execute("INSERT INTO budget.calls(round,provider,reserve,status,details,date) VALUES(?,?,?,?,?,?)",
                               (str(self.root), provider, bound, "reserved", json.dumps(details), now())).lastrowid
        self.db.commit()
        return call

    def settle(self, call, cost, details):
        reserve = self.db.execute("SELECT reserve FROM budget.calls WHERE k=?", (call,)).fetchone()[0]
        self.db.execute("UPDATE budget.calls SET cost=?,status='settled',details=? WHERE k=?",
                        (cost, json.dumps(details), call))
        self.db.commit()
        if cost > reserve + 1e-8:
            raise ChainError("actual charge exceeded reserved bound; pause and reconcile")


def init_seeds(store, pool, view, sentinel_paths, budget):
    store.bind("basis", {"pool": sha(pool), "view": sha(view),
                         "sentinels": {str(p): sha(p) for p in sentinel_paths}})
    store.bind("budget_usd", budget)
    desired = {r["work_key"]: "baseline:" + r["status"] for r in rows(view)
               if r["status"] in {"icf", "unsure_unresolved"}}
    seeds = {r["work_key"]: (r, desired[r["work_key"]]) for r in rows(pool) if r["work_key"] in desired}
    for path in sentinel_paths:
        for r in rows(path):
            key = "sentinel:" + Path(path).stem + ":" + r["sentinel"]
            seeds[key] = (r, "sentinel:" + r.get("set", "") + ":" + r["sentinel"])
    for key, (record, reason) in sorted(seeds.items()):
        oa = oid(record.get("openalex_id"))
        store.db.execute("INSERT OR IGNORE INTO seeds VALUES(?,?,?,?,?)",
                         (key, oa, json.dumps(record), reason, "identified" if oa else "pending"))
    store.db.commit()
    csv_write(store.root / "seeds.csv", ["work_key", "openalex_id", "doi", "title", "year", "reason"],
              ({**json.loads(r["body"]), "work_key": r["k"], "reason": r["reason"]}
               for r in store.db.execute("SELECT * FROM seeds ORDER BY k")))
    log.info("seed roster: %d rows", len(seeds))


def oa_request(store, params, get=requests.get):
    public = dict(params)
    # Field-specific title filters are charged as search, too. Reserve the
    # search ceiling for every request; settle list calls at their lower cost.
    bound = .001
    request_key = hashlib.sha256(json.dumps(public, sort_keys=True).encode()).hexdigest()
    cached = store.db.execute("SELECT path,call FROM api_pages WHERE k=?", (request_key,)).fetchone()
    if cached:
        with gzip.open(store.root / cached["path"], "rt", encoding="utf-8") as stream:
            archived = json.load(stream)
        prior = store.db.execute("SELECT status FROM budget.calls WHERE k=?", (cached["call"],)).fetchone()
        if prior and prior[0] == "reserved":
            charge = reported_oa_cost(archived["headers"], archived["body"], bound)
            store.settle(cached["call"], charge, {"recovered_from": cached["path"], "query": public})
        return entity_result(archived["body"], public)
    call = store.reserve("openalex", bound, public)
    entity = params.get("entity")
    params = {k: v for k, v in params.items() if k != "entity"}
    params = {**params, "api_key": read_credential("openalex", "OPENALEX_API_KEY"), "mailto": MAILTO}
    try:
        response = get(OA + ("/" + entity if entity else ""), params=params, timeout=90)
    except requests.RequestException as exc:
        raise ChainError(f"OpenAlex transport failed; reservation retained (call {call})") from exc
    headers = {k: v for k, v in response.headers.items() if k.lower().startswith("x-ratelimit")}
    try:
        body = response.json()
    except ValueError:
        body = {"error": "non-JSON response", "status": response.status_code}
    raw = store.root / "raw" / f"call{call:07d}.json.gz"
    with gzip.open(raw, "wt", encoding="utf-8") as stream:
        json.dump({"query": public, "retrieved_at": now(), "status": response.status_code,
                   "headers": headers, "body": body}, stream, ensure_ascii=False)
    if response.status_code == 200:
        store.db.execute("INSERT OR IGNORE INTO api_pages VALUES(?,?,?)",
                         (request_key, str(raw.relative_to(store.root)), call))
        store.db.commit()
    credit_cost = (body.get("meta") or {}).get("cost")
    cost = reported_oa_cost(headers, body, bound)
    store.settle(call, cost, {"query": public, "status": response.status_code, "headers": headers,
                             "credits": credit_cost, "cost_basis": "reported" if credit_cost is not None else "bound"})
    if response.status_code != 200:
        raise ChainError(f"OpenAlex HTTP {response.status_code}; raw call {call} archived")
    result = entity_result(body, public)
    if "results" not in result:
        raise ChainError(f"OpenAlex response lacks results (call {call})")
    return result


def entity_result(body, params):
    if params.get("entity") and body.get("id"):
        return {"meta": {"count": 1}, "results": [body]}
    return body


def reported_oa_cost(headers, body, bound):
    lower = {k.lower(): v for k, v in headers.items()}
    meta = body.get("meta") or {}
    if lower.get("x-ratelimit-cost-usd") is not None:
        return float(lower["x-ratelimit-cost-usd"])
    if meta.get("cost_usd") is not None:
        return float(meta["cost_usd"])
    credit = meta.get("cost")
    return float(credit) * .0001 if isinstance(credit, (int, float)) else bound


def index_raw_pages(store):
    indexed = {r[0] for r in store.db.execute("SELECT path FROM api_pages")}
    for path in sorted((store.root / "raw").glob("*.json.gz")):
        relative = str(path.relative_to(store.root))
        if relative in indexed:
            continue
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            archived = json.load(stream)
        if archived["status"] == 200 and "results" in entity_result(archived["body"], archived["query"]):
            key = hashlib.sha256(json.dumps(archived["query"], sort_keys=True).encode()).hexdigest()
            call = int(path.name.split(".")[0][4:])
            store.db.execute("INSERT OR IGNORE INTO api_pages VALUES(?,?,?)", (key, relative, call))
    store.db.commit()


def same_title_identity(seed, work):
    if normalize_title(seed.get("title", "")) != normalize_title(work.get("display_name", "")):
        return False
    if str(seed.get("year", "")) != str(work.get("publication_year", "")):
        return False
    author = normalize_title(seed.get("first_author") or "")
    names = {normalize_title(a.get("author", {}).get("display_name") or "")
             for a in work.get("authorships") or []}
    return bool(author and author in names)


def archive_identity_results(store, params, body, date):
    text = json.dumps(params, sort_keys=True)
    qid = "resolve:" + hashlib.sha256(text.encode()).hexdigest()[:20]
    store.add_query(qid, "resolution", text)
    results = body.get("results") or []
    expected = (body.get("meta") or {}).get("count", len(results))
    complete = expected == len(results)
    for work in results:
        store.put_work(work, qid, date)
    store.db.execute("UPDATE queries SET completed=?,received=?,expected=?,run_at=?,stop=?,pages=1 WHERE k=?",
                     (int(complete), len(results), expected, date, "" if complete else "identity lookup record cap", qid))
    store.db.commit()
    return complete


def resolve_one_seed(root, ledger, seed, archived, get):
    store = Store(root, ledger)
    rec = json.loads(seed["body"])
    doi = normalize_doi(rec.get("doi"))
    title_query = re.sub(r"[^\w\s]", " ", html.unescape(rec.get("title") or ""))
    title_query = " ".join(title_query.split())
    params = {"filter": "doi:" + doi, "per_page": 100} if doi else {
        "filter": 'title.search:"' + title_query + '"', "per_page": 100}
    if not doi and not title_query:
        matches = []
    else:
        body = archived.get(json.dumps(params, sort_keys=True))
        if body is None:
            body = oa_request(store, params, get)
        complete = archive_identity_results(store, params, body, now())
        results = body["results"]
        matches = [w for w in results if normalize_doi(w.get("doi")) == doi] if doi else [
            w for w in results if same_title_identity(rec, w)]
        if not complete:
            matches = []
    if len(matches) == 1:
        oa = oid(matches[0]["id"])
        store.db.execute("UPDATE seeds SET oa=?,resolution=? WHERE k=?",
                         (oa, "doi_exact" if doi else "title_year_author_exact", seed["k"]))
        store.db.execute("DELETE FROM unresolved WHERE k=? AND kind='seed'", (seed["k"],))
    else:
        reason = "ambiguous identity" if matches else "no exact identity match"
        store.db.execute("UPDATE seeds SET resolution=? WHERE k=?", (reason, seed["k"]))
        store.db.execute("INSERT OR REPLACE INTO unresolved VALUES(?,?,?)", (seed["k"], "seed", reason))
    store.db.commit()
    store.db.close()


def retry_title_identities(store):
    pending = [r["k"] for r in store.db.execute("SELECT * FROM seeds WHERE oa='' AND resolution<>'pending'")
               if not normalize_doi(json.loads(r["body"]).get("doi"))]
    with (store.root / "identity_retries.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"at": now(), "reason": "field-specific title lookup after broad fulltext diagnostic",
                                 "seed_keys": pending}) + "\n")
    store.db.executemany("UPDATE seeds SET resolution='pending' WHERE k=?", [(key,) for key in pending])
    store.db.commit()
    resolve_seeds(store)


def resolve_seeds(store, get=requests.get, workers=8):
    pending = list(store.db.execute("SELECT * FROM seeds WHERE oa='' AND resolution='pending' ORDER BY k"))
    if not pending:
        return
    # oa_request replays the exact indexed page; unrelated citation pages do
    # not need to be decompressed when resuming identity lookup.
    archived = {}
    # Bound task submission as well as calls in flight: errors stop the next wave.
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for start in range(0, len(pending), workers):
            tasks = [executor.submit(resolve_one_seed, store.root, store.budget_path, seed, archived, get)
                     for seed in pending[start:start + workers]]
            for task in tasks:
                task.result()
            if start % 80 == 0:
                log.info("identity resolution %d/%d", min(start + workers, len(pending)), len(pending))


def resolve_seed_alias(root, ledger, old, get):
    store = Store(root, ledger)
    qid = "seed-singleton:" + old
    params = {"entity": old}
    store.add_query(qid, "singleton", OA + "/" + old)
    try:
        body = oa_request(store, params, get)
    except ChainError as exc:
        if "HTTP 404" not in str(exc):
            store.db.close()
            raise
        store.db.execute("INSERT OR REPLACE INTO seed_aliases VALUES(?,?,?)", (old, "", "not_found"))
        store.db.execute("INSERT OR REPLACE INTO unresolved VALUES(?,?,?)", (old, "seed_metadata", "OpenAlex singleton returns404"))
        store.db.execute("UPDATE queries SET completed=1,received=0,expected=0,run_at=? WHERE k=?", (now(), qid))
    else:
        work = body["results"][0]
        new = oid(work["id"])
        store.put_work(work, qid, now())
        store.db.execute("INSERT OR REPLACE INTO seed_aliases VALUES(?,?,?)", (old, new, "redirect" if old != new else "found"))
        store.db.executemany("INSERT OR IGNORE INTO edges VALUES(?,?,?,?)",
                             [(old, oid(ref), "backward", qid) for ref in work.get("referenced_works") or []])
        store.db.execute("UPDATE queries SET completed=1,received=1,expected=1,run_at=? WHERE k=?", (now(), qid))
    store.db.commit()
    store.db.close()


def resolve_seed_aliases(store, get=requests.get, workers=8):
    missing = [r[0] for r in store.db.execute("SELECT DISTINCT oa FROM seeds WHERE oa<>'' AND oa NOT IN (SELECT k FROM works) AND oa NOT IN (SELECT old FROM seed_aliases) ORDER BY oa")]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for start in range(0, len(missing), workers):
            tasks = [executor.submit(resolve_seed_alias, store.root, store.budget_path, old, get)
                     for old in missing[start:start + workers]]
            for task in tasks:
                task.result()
    log.info("missing seed singleton lookups: %d", len(missing))


def restore_cached_metadata(store, cache_dir):
    target_file = store.root / "cache_targets.txt"
    if target_file.exists():
        wanted = set(target_file.read_text().splitlines())
    else:
        wanted = {r[0] for r in store.db.execute("SELECT DISTINCT candidate FROM edges WHERE candidate NOT IN (SELECT k FROM works)")}
        wanted.update(r[0] for r in store.db.execute("SELECT DISTINCT oa FROM seeds WHERE oa<>'' AND oa NOT IN (SELECT k FROM works)"))
        target_file.write_text("\n".join(sorted(wanted)) + "\n")
    store.bind("cache_targets_sha256", sha(target_file))
    seed_ids = {r[0] for r in store.db.execute("SELECT DISTINCT oa FROM seeds WHERE oa<>''")}
    total = 0
    for path in sorted(Path(cache_dir).glob("*.jsonl.gz")):
        digest = sha(path)
        qid = "archive:" + path.name
        query = f"DVC OpenAlex archive {path.name} sha256={digest}; exact IDs in cache_targets.txt sha256={sha(target_file)}"
        store.add_query(qid, "archive", query)
        n = 0
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line in stream:
                work = json.loads(line)
                key = oid(work.get("id"))
                if key not in wanted:
                    continue
                n += 1
                store.put_work(work, qid, now())
                if key in seed_ids:
                    store.db.executemany("INSERT OR IGNORE INTO edges VALUES(?,?,?,?)",
                                         [(key, oid(ref), "backward", qid) for ref in work.get("referenced_works") or []])
                store.db.execute("DELETE FROM unresolved WHERE k=? AND kind IN ('reference','seed_metadata')", (key,))
        store.db.execute("UPDATE queries SET completed=1,received=?,expected=?,run_at=? WHERE k=?", (n, n, now(), qid))
        store.db.commit()
        total += n
    log.info("historical metadata recovered: %d retrievals", total)


def query_page(store, query, get=requests.get):
    params = {"filter": query["filter"], "per_page": 100, "cursor": query["cursor"]}
    body = oa_request(store, params, get)
    works, meta, date = body["results"], body.get("meta") or {}, now()
    seeds = json.loads(query["seeds"])
    for work in works:
        store.put_work(work, query["k"], date)
        if query["kind"] == "backward":
            source = oid(work["id"])
            edges = [(source, oid(ref), "backward", query["k"]) for ref in work.get("referenced_works") or []]
        elif query["kind"] == "forward":
            aliases = {r["old"]: r["new"] for r in store.db.execute("SELECT * FROM seed_aliases WHERE new<>''")}
            edges = forward_edges(work, seeds, query["k"], aliases)
            if not edges:
                store.db.execute("INSERT OR REPLACE INTO unresolved VALUES(?,?,?)",
                                 (query["k"] + ":" + oid(work["id"]), "edge", "forward result has no returned seed reference"))
        else:
            edges = []
        store.db.executemany("INSERT OR IGNORE INTO edges VALUES(?,?,?,?)", edges)
    received = query["received"] + len(works)
    cursor = meta.get("next_cursor")
    expected = meta.get("count", query["expected"])
    stop = ""
    completed = not cursor
    if cursor and (cursor == query["cursor"] or not works):
        stop = "repeated cursor or empty page with next cursor"
        completed = False
    if completed and expected is not None and received != expected:
        stop, completed = f"short cursor: {received} of {expected}", False
    store.db.execute("UPDATE queries SET cursor=?,received=?,expected=?,pages=pages+1,completed=?,stop=?,run_at=? WHERE k=?",
                     (cursor or "", received, expected, int(completed), stop, date, query["k"]))
    store.db.commit()
    if stop:
        raise ChainError(f"{query['k']}: {stop}")


def traverse_one(root, ledger, key, get):
    store = Store(root, ledger)
    try:
        while True:
            q = store.db.execute("SELECT * FROM queries WHERE k=?", (key,)).fetchone()
            if q["completed"]:
                break
            if not q["cursor"] or q["stop"].startswith(("short cursor", "repeated")):
                raise ChainError(f"query requires explicit restart: {q['k']} {q['stop']}")
            query_page(store, q, get)
        log.info("%s: %d received", q["k"], q["received"])
    finally:
        store.db.close()


def traverse(store, kinds, get=requests.get, workers=8):
    for kind in kinds:
        todo = [r[0] for r in store.db.execute("SELECT k FROM queries WHERE kind=? AND completed=0 ORDER BY k", (kind,))]
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for start in range(0, len(todo), workers):
                tasks = [executor.submit(traverse_one, store.root, store.budget_path, key, get)
                         for key in todo[start:start + workers]]
                for task in tasks:
                    task.result()


def batches(values, size=100):
    for start in range(0, len(values), size):
        yield start // size, values[start:start + size]


def harvest(store):
    index_raw_pages(store)
    resolve_seeds(store)
    planned = list(store.db.execute("SELECT seeds FROM queries WHERE kind='backward' ORDER BY k"))
    planned_ids = {seed for r in planned for seed in json.loads(r[0])}
    seeds = [r[0] for r in store.db.execute("SELECT DISTINCT oa FROM seeds WHERE oa<>'' ORDER BY oa") if r[0] not in planned_ids]
    for i, batch in batches(seeds):
        suffix = hashlib.sha256("|".join(batch).encode()).hexdigest()[:20] if planned else f"{i:05d}"
        store.add_query("backward:" + suffix, "backward", "openalex_id:" + "|".join(batch), batch)
        store.add_query("forward:" + suffix, "forward", "cites:" + "|".join(batch), batch)
    traverse(store, ["backward"])
    resolve_seed_aliases(store)
    refs = [r[0] for r in store.db.execute("SELECT DISTINCT candidate FROM edges WHERE direction='backward' ORDER BY candidate")]
    existing = list(store.db.execute("SELECT filter FROM queries WHERE kind='references'"))
    planned_refs = {key for r in existing for key in r[0].split(":", 1)[1].split("|")}
    extra = sorted(set(refs) - planned_refs)
    for i, batch in batches(extra):
        suffix = hashlib.sha256("|".join(batch).encode()).hexdigest()[:20] if existing else f"{i:05d}"
        store.add_query("references:" + suffix, "references", "openalex_id:" + "|".join(batch))
    traverse(store, ["references", "forward"])
    for r in store.db.execute("SELECT DISTINCT candidate FROM edges WHERE candidate NOT IN (SELECT k FROM works)"):
        store.db.execute("INSERT OR IGNORE INTO unresolved VALUES(?,?,?)", (r[0], "reference", "referenced ID absent from metadata response"))
    store.db.commit()


def export_delivery(store, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "manifest.json").exists():
        raise ChainError("delivery already exported; choose a new immutable directory")
    # Identity searches are diagnostic routes, not citation discoveries. Their
    # complete native payloads remain in the checkpoint and raw archive.
    citation_queries = {r["k"] for r in store.db.execute("SELECT k FROM queries WHERE kind<>'resolution'")}
    provenance = {}
    for row in store.db.execute("SELECT q,w FROM discoveries ORDER BY q,w"):
        if row["q"] in citation_queries:
            provenance.setdefault(row["w"], row["q"])
    excluded = []
    def records():
        for row in store.db.execute("SELECT * FROM works ORDER BY k"):
            if row["k"] not in provenance:
                continue
            source_query = provenance[row["k"]]
            record = intake_record(json.loads(row["body"]), source_query, row["date"])
            if record["title"].strip():
                yield record
            else:
                excluded.append({"record_id": row["k"], "query_id": source_query, "reason": "not_retrievable",
                                 "title": "", "note": "OpenAlex returned no title"})
    csv_write(output / "records.csv", contract.RECORD_COLUMNS + ["cited_by_count"], records())
    for row in store.db.execute("SELECT q,w FROM discoveries ORDER BY q,w"):
        if row["q"] not in citation_queries or row["q"] == provenance.get(row["w"]):
            continue
        excluded.append({"record_id": row["w"], "query_id": row["q"], "reason": "duplicate_in_lane",
                         "title": "", "note": "same OpenAlex ID; all routes preserved in edges.csv"})
    csv_write(output / "excluded.csv", contract.EXCLUDED_COLUMNS, excluded)
    incomplete = [{"unit": r["k"], "reason": r["stop"] or "query not completed"}
                  for r in store.db.execute("SELECT * FROM queries WHERE completed=0 AND kind<>'resolution'")]
    incomplete += [{"unit": r["k"], "reason": r["note"]} for r in store.db.execute("SELECT * FROM unresolved")]
    registry = [{"query_id": r["k"], "platform": "openalex", "query": r["filter"],
                 "run_at": r["run_at"] or now(), "n_received": r["received"], "n_expected": r["expected"],
                 "completed": "true" if r["completed"] else "false", "stop_reason": r["stop"] or ("not run" if not r["completed"] else ""),
                 "pages": r["pages"], "direction": r["kind"]} for r in store.db.execute("SELECT * FROM queries WHERE kind<>'resolution' ORDER BY k")]
    csv_write(output / "registry.csv", contract.REGISTRY_REQUIRED + ["n_expected", "stop_reason", "pages", "direction"], registry)
    csv_write(output / "edges.csv", ["seed", "candidate", "direction", "query_id"],
              ({"seed": r["seed"], "candidate": r["candidate"], "direction": r["direction"], "query_id": r["q"]}
               for r in store.db.execute("SELECT * FROM edges ORDER BY direction,seed,candidate,q")))
    n = sum(1 for _ in rows(output / "records.csv"))
    commit = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    dump(output / "manifest.json", {"lane": output.parent.name, "ticket": "1654", "delivery": output.name,
          "delivered_at": now(), "producer": {"script": "scripts/catalog_rel_citation_chaining.py", "commit": commit, "machine": socket.gethostname()},
          "counts": {"records": n, "excluded": dict(Counter(r["reason"] for r in excluded))},
          "coverage": "incomplete" if incomplete else "complete", "incomplete": incomplete,
          "needs_human": [], "supersedes": None, "notes": "Every retrieved full payload is archived in the round checkpoint; all citation routes are in edges.csv."})
    faults = contract.check_delivery(str(output))
    if faults:
        raise ChainError(str(faults))
    log.info("exported %d records; %d incomplete units", n, len(incomplete))


def identity_indexes(new_rows):
    by_identity = {}
    by_member = {}
    for row in new_rows:
        for field in ("all_dois", "all_openalex_ids"):
            for value in (row.get(field) or "").split(";"):
                if value:
                    by_identity.setdefault((field, value), set()).add(row["work_key"])
        for member in (row.get("member_record_ids") or "").split(";"):
            if member:
                by_member.setdefault(member, set()).add(row["work_key"])
    return by_identity, by_member


def exact_rekey_map(old_rows, new_rows):
    by_identity, by_member = identity_indexes(new_rows)
    new_keys = {r["work_key"] for r in new_rows}
    result, unresolved = {}, []
    old_member_counts = Counter(m for r in old_rows for m in (r.get("member_record_ids") or "").split(";") if m)
    for old in old_rows:
        key = old["work_key"]
        if key in new_keys:
            continue
        candidates = set()
        for field in ("all_dois", "all_openalex_ids"):
            for value in (old.get(field) or "").split(";"):
                if value:
                    candidates.update(by_identity.get((field, value), ()))
        members = [m for m in (old.get("member_record_ids") or "").split(";") if m]
        if not candidates and members and all(old_member_counts[m] == 1 for m in members):
            member_sets = [by_member.get(m, set()) for m in members]
            candidates = set.intersection(*member_sets)
            # These are unchanged source-record identities, not title guesses.
            # A newly preferred title/year must not erase the exact membership.
        if len(candidates) == 1:
            result[key] = candidates.pop()
        else:
            unresolved.append({"old_key": key, "candidates": sorted(candidates), "reason": "absent or ambiguous exact identity"})
    multi = Counter(result.values())
    for old, new in list(result.items()):
        if multi[new] > 1:
            unresolved.append({"old_key": old, "candidates": [new], "reason": "many-to-one historical identity"})
            del result[old]
    return result, unresolved


def migrate_labels(store, old_pool, new_pool, table, dims_table):
    mapping, unresolved = exact_rekey_map(list(rows(old_pool)), list(rows(new_pool)))
    report = {"old_pool_sha256": sha(old_pool), "new_pool_sha256": sha(new_pool),
              "mapping": mapping, "unresolved": unresolved, "tables": {}}
    for path, schema in ((table, screens.ICF), (dims_table, screens.DIMENSIONS)):
        entries = screens.read_table(path, schema)
        additions = [{**row, "work_key": mapping[row["work_key"]]} for row in entries if row["work_key"] in mapping]
        added, skipped = screens.append_new(path, additions, "t1654 exact identity migration", schema=schema)
        report["tables"][str(path)] = {"appended": added, "skipped": skipped}
    path = store.root / "key_migrations.jsonl"
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"at": now(), **report}, ensure_ascii=False) + "\n")
    if unresolved:
        raise ChainError(f"{len(unresolved)} rekey identities remain unresolved; no labels transferred for them")
