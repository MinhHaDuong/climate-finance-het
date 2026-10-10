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
import math
import os
import re
import socket
import sqlite3
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import qa_rel_intake as contract
import requests
from openalex_corpus.text import reconstruct_abstract
from pipeline_keystore import read_credential
from utils import MAILTO, get_logger, normalize_doi, normalize_title

log = get_logger("rel_citation_chaining")
OA = "https://api.openalex.org/works"


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


def reference_ids(work):
    """Distinguish native empty-list evidence from absent/malformed references."""
    if "referenced_works" not in work:
        return None, "absent"
    values = work["referenced_works"]
    if not isinstance(values, list):
        return None, "not_list"
    if any(not isinstance(value, str) or not re.fullmatch(r"(?:https?://openalex\.org/)?W\d+", value)
           for value in values):
        return None, "invalid_member"
    return [oid(value) for value in values], ""


def reference_diagnostic(work, query):
    refs, reason = reference_ids(work)
    if refs is not None:
        return None
    digest = hashlib.sha256(json.dumps(work, ensure_ascii=False, sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest()
    key = query + ":" + oid(work["id"]) + ":references:" + digest
    note = {"query_id": query, "work_id": oid(work["id"]), "native_work_sha256": digest,
            "reason": reason, "evidence": "native reference field absent or malformed; query coverage is independent"}
    return {"k": key, "kind": "reference_evidence", "note": json.dumps(note, sort_keys=True)}


def record_reference_evidence(store, work, query):
    diagnostic = reference_diagnostic(work, query)
    if diagnostic:
        store.db.execute("INSERT OR IGNORE INTO unresolved VALUES(?,?,?)",
                         (diagnostic["k"], diagnostic["kind"], diagnostic["note"]))
    return reference_ids(work)[0]


def forward_edges(work, seeds, query, aliases=None):
    refs = set(reference_ids(work)[0] or [])
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
            CREATE TABLE IF NOT EXISTS direction_reuse(seed TEXT,direction TEXT,evidence TEXT,
              PRIMARY KEY(seed,direction));
        """)

    def budget_exposure(self):
        values = []
        for row in self.db.execute("SELECT reserve,cost FROM budget.calls"):
            reserve, cost = row
            if reserve is None or not math.isfinite(reserve) or reserve <= 0 or (cost is not None and
                    (not math.isfinite(cost) or cost < 0)):
                self.db.rollback()
                raise ChainError("positive finite reserve and nonnegative finite cost required")
            values.append(reserve if cost is None else cost)
        try:
            total = math.fsum(values)
        except OverflowError as error:
            self.db.rollback()
            raise ChainError("finite budget exposure required") from error
        if not math.isfinite(total):
            self.db.rollback()
            raise ChainError("finite budget exposure required")
        return total

    def authorize_budget(self, cap, authorization):
        """Record an explicit steering change in the shared ledger atomically."""
        if not math.isfinite(cap) or cap <= 0 or not authorization.strip():
            raise ChainError("positive cap and explicit authorization evidence required")
        self.db.execute("CREATE TABLE IF NOT EXISTS budget.policy(k TEXT PRIMARY KEY,v TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS budget.policy_history(at TEXT,old_cap REAL,new_cap REAL,authorization TEXT)")
        self.db.execute("BEGIN IMMEDIATE")
        old = self.db.execute("SELECT v FROM budget.policy WHERE k='cap_usd'").fetchone()
        previous = float(old[0]) if old else self.config("budget_usd")
        spent = self.budget_exposure()
        if spent > cap:
            self.db.rollback()
            raise ChainError("authorized cap below existing liabilities")
        self.db.execute("INSERT OR REPLACE INTO budget.policy VALUES('cap_usd',?)", (str(cap),))
        self.db.execute("INSERT INTO budget.policy_history VALUES(?,?,?,?)", (now(), previous, cap, authorization))
        self.db.commit()

    def bind(self, name, value):
        if name == "budget_usd" and (not math.isfinite(value) or value <= 0):
            raise ChainError("positive finite budget cap required")
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

    def reserve(self, provider, bound, details, *, admission_ceiling=None):
        if not math.isfinite(bound) or bound <= 0:
            raise ChainError("positive request liability required")
        if admission_ceiling is not None and (not math.isfinite(admission_ceiling) or admission_ceiling <= 0):
            raise ChainError("positive finite admission ceiling required")
        self.db.execute("BEGIN IMMEDIATE")
        spent = self.budget_exposure()
        policy_exists = self.db.execute("SELECT 1 FROM budget.sqlite_master WHERE type='table' AND name='policy'").fetchone()
        policy = self.db.execute("SELECT v FROM budget.policy WHERE k='cap_usd'").fetchone() if policy_exists else None
        cap = float(policy[0]) if policy else self.config("budget_usd")
        if not math.isfinite(cap) or cap <= 0 or not math.isfinite(spent) or spent < 0:
            self.db.rollback()
            raise ChainError("positive finite cap and nonnegative finite budget exposure required")
        if admission_ceiling is not None:
            cap = min(cap, admission_ceiling)
        if spent + bound > cap:
            self.db.rollback()
            raise ChainError(f"cumulative budget: {spent:.5f}+{bound:.5f} exceeds cap")
        call = self.db.execute("INSERT INTO budget.calls(round,provider,reserve,status,details,date) VALUES(?,?,?,?,?,?)",
                               (str(self.root), provider, bound, "reserved", json.dumps(details), now())).lastrowid
        self.db.commit()
        return call

    def settle(self, call, cost, details):
        if not math.isfinite(cost) or cost < 0:
            raise ChainError("nonnegative finite actual cost required")
        reserve = self.db.execute("SELECT reserve FROM budget.calls WHERE k=?", (call,)).fetchone()[0]
        self.db.execute("UPDATE budget.calls SET cost=?,status='settled',details=? WHERE k=?",
                        (cost, json.dumps(details), call))
        self.db.commit()
        if cost > reserve + 1e-8:
            raise ChainError("actual charge exceeded reserved bound; pause and reconcile")


def init_seeds(store, pool, view, sentinel_paths, budget, *, frontier_path=None):
    desired = {r["work_key"]: "baseline:" + r["status"] for r in rows(view)
               if r["status"] in {"icf", "unsure_unresolved"}}
    frontier_basis = None
    if frontier_path is not None:
        frontier = json.loads(Path(frontier_path).read_text())
        if frontier.get("version") != "1654-final-frontier-v1":
            raise ChainError("unsupported frontier version")
        closure_path = Path(frontier["closure_artifact"])
        if sha(closure_path) != frontier["closure_sha256"]:
            raise ChainError("frontier closure artifact changed")
        closure = json.loads(closure_path.read_text())
        if not all(closure.get(name) is True for name in
                   ("round_dispositions_reconciled", "venue_dimensions_reconciled", "yield_reconciled")):
            raise ChainError("frontier closure is not fully reconciled")
        if frontier["pool_sha256"] != sha(pool) or frontier["view_sha256"] != sha(view):
            raise ChainError("frontier final pool/view basis changed")
        if any(closure.get(name) != frontier[name] for name in ("pool_sha256", "view_sha256")):
            raise ChainError("frontier closure pool/view basis mismatch")
        if frontier.get("previous_round") and closure.get("previous_round") != frontier["previous_round"]:
            raise ChainError("frontier closure final source-proof binding mismatch")
        selected = {}
        for record in frontier["records"]:
            key = record["work_key"]
            if key in selected or key not in desired or not record["selection_reason"] or not record["stratum"]:
                raise ChainError("invalid or unretained frontier identity")
            selected[key] = "frontier:" + record["stratum"] + ":" + record["selection_reason"]
        desired = selected
        frontier_basis = {"frontier_sha256": sha(frontier_path), "closure_sha256": frontier["closure_sha256"]}
    store.bind("basis", {"pool": sha(pool), "view": sha(view),
                         "sentinels": {str(p): sha(p) for p in sentinel_paths},
                         **({"frontier": frontier_basis} if frontier_basis else {})})
    store.bind("budget_usd", budget)
    seeds = {r["work_key"]: (r, desired[r["work_key"]]) for r in rows(pool) if r["work_key"] in desired}
    if frontier_path is not None and set(seeds) != set(desired):
        raise ChainError("frontier/view identity absent from exact pool")
    for path in sentinel_paths:
        for r in rows(path):
            key = "sentinel:" + Path(path).stem + ":" + r["sentinel"]
            seeds[key] = (r, "sentinel:" + r.get("set", "") + ":" + r["sentinel"])
    for key, (record, reason) in sorted(seeds.items()):
        oa = oid(record.get("openalex_id"))
        store.db.execute("INSERT OR IGNORE INTO seeds VALUES(?,?,?,?,?)",
                         (key, oa, json.dumps(record), reason, "identified" if oa else "pending"))
    store.db.commit()
    if frontier_path is not None and frontier.get("previous_round"):
        previous = frontier["previous_round"]
        # Call-time import: _rel_chaining_reuse imports this module at load time.
        from _rel_chaining_reuse import reuse_completed_directions
        reuse_completed_directions(store, previous["snapshot"], previous["native_root"], previous["snapshot_sha256"],
                                  native_index_path=previous["native_index"],
                                  native_index_sha256=previous["native_index_sha256"])
    csv_write(store.root / "seeds.csv", ["work_key", "openalex_id", "doi", "title", "year", "reason"],
              ({**json.loads(r["body"]), "work_key": r["k"], "reason": r["reason"]}
               for r in store.db.execute("SELECT * FROM seeds ORDER BY k")))
    log.info("seed roster: %d rows", len(seeds))


def oa_request(store, params, get=requests.get, *, admission_ceiling=None):
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
    call = store.reserve("openalex", bound, public, admission_ceiling=admission_ceiling)
    entity = params.get("entity")
    params = {k: v for k, v in params.items() if k != "entity"}
    params = {**params, "api_key": read_credential("openalex", "OPENALEX_API_KEY"), "mailto": MAILTO}
    try:
        response = get(OA + ("/" + entity if entity else ""), params=params, timeout=90)
    except requests.RequestException as exc:
        raise ChainError(f"OpenAlex transport failed; reservation retained (call {call})") from exc
    headers = {k: v for k, v in response.headers.items()
               if k.lower().startswith("x-ratelimit") or k.lower() == "retry-after"}
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
                             [(old, ref, "backward", qid) for ref in record_reference_evidence(store, work, qid) or []])
        store.db.execute("UPDATE queries SET completed=1,received=1,expected=1,run_at=? WHERE k=?", (now(), qid))
    store.db.commit()
    store.db.close()


def resolve_seed_aliases(store, get=requests.get, workers=8):
    missing = [r[0] for r in store.db.execute("SELECT DISTINCT oa FROM seeds WHERE oa<>'' AND oa NOT IN (SELECT k FROM works) AND oa NOT IN (SELECT old FROM seed_aliases) AND oa NOT IN (SELECT seed FROM direction_reuse WHERE direction='backward') ORDER BY oa")]
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
                                         [(key, ref, "backward", qid) for ref in record_reference_evidence(store, work, qid) or []])
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
            refs = record_reference_evidence(store, work, query["k"])
            edges = [(source, ref, "backward", query["k"]) for ref in refs or []]
        elif query["kind"] == "forward":
            record_reference_evidence(store, work, query["k"])
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


def plan_citation_queries(store):
    """Plan missing directions independently; interrupted queries retain their cursor."""
    identities = [r[0] for r in store.db.execute("SELECT DISTINCT oa FROM seeds WHERE oa<>'' ORDER BY oa")]
    for direction, field in (("backward", "openalex_id"), ("forward", "cites")):
        planned = list(store.db.execute("SELECT seeds FROM queries WHERE kind=? ORDER BY k", (direction,)))
        planned_ids = {seed for r in planned for seed in json.loads(r[0])}
        planned_ids.update(r[0] for r in store.db.execute("SELECT seed FROM direction_reuse WHERE direction=?", (direction,)))
        missing = [identity for identity in identities if identity not in planned_ids]
        for i, batch in batches(missing):
            suffix = hashlib.sha256("|".join(batch).encode()).hexdigest()[:20] if planned else f"{i:05d}"
            store.add_query(direction + ":" + suffix, direction, field + ":" + "|".join(batch), batch)


def harvest(store):
    index_raw_pages(store)
    resolve_seeds(store)
    plan_citation_queries(store)
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
