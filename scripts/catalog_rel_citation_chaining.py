"""Resumable REL citation rounds: full metadata, every edge, no year filter.

Multiple outputs live below required --output-dir. SQLite is the checkpoint;
raw API pages are durable before cursor advancement. Deliveries are exported
only on request, and remain incomplete when any route cannot be traversed.
"""

import argparse
import csv
import gzip
import hashlib
import json
import os
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


def forward_edges(work, seeds, query):
    refs = {oid(v) for v in work.get("referenced_works") or []}
    return [(seed, oid(work["id"]), "forward", query) for seed in seeds if seed in refs]


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
    call = store.reserve("openalex", bound, public)
    params = {**params, "api_key": read_credential("openalex", "OPENALEX_API_KEY"), "mailto": MAILTO}
    try:
        response = get(OA, params=params, timeout=90)
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
    lower = {k.lower(): v for k, v in headers.items()}
    credit_cost = (body.get("meta") or {}).get("cost")
    cost = float(lower.get("x-ratelimit-cost-usd") or
                 (float(credit_cost) * .0001 if isinstance(credit_cost, (int, float)) else bound))
    store.settle(call, cost, {"query": public, "status": response.status_code, "headers": headers,
                             "credits": credit_cost, "cost_basis": "reported" if credit_cost is not None else "bound"})
    if response.status_code != 200:
        raise ChainError(f"OpenAlex HTTP {response.status_code}; raw call {call} archived")
    if "results" not in body:
        raise ChainError(f"OpenAlex response lacks results (call {call})")
    return body


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
    params = {"filter": "doi:" + doi, "per_page": 100} if doi else {
        "search": normalize_title(rec.get("title") or ""), "per_page": 100}
    if not doi and not params["search"]:
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
    else:
        reason = "ambiguous identity" if matches else "no exact identity match"
        store.db.execute("UPDATE seeds SET resolution=? WHERE k=?", (reason, seed["k"]))
        store.db.execute("INSERT OR REPLACE INTO unresolved VALUES(?,?,?)", (seed["k"], "seed", reason))
    store.db.commit()
    store.db.close()


def resolve_seeds(store, get=requests.get, workers=8):
    # Raw pages also recover an interrupted identity request without recharging.
    archived = {}
    for path in sorted((store.root / "raw").glob("*.json.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            obj = json.load(stream)
        if obj["status"] == 200 and "cursor" not in obj["query"]:
            archive_identity_results(store, obj["query"], obj["body"], obj["retrieved_at"])
            archived[json.dumps(obj["query"], sort_keys=True)] = obj["body"]
    pending = list(store.db.execute("SELECT * FROM seeds WHERE oa='' AND resolution='pending' ORDER BY k"))
    # Bound task submission as well as calls in flight: errors stop the next wave.
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for start in range(0, len(pending), workers):
            tasks = [executor.submit(resolve_one_seed, store.root, store.budget_path, seed, archived, get)
                     for seed in pending[start:start + workers]]
            for task in tasks:
                task.result()
            if start % 80 == 0:
                log.info("identity resolution %d/%d", min(start + workers, len(pending)), len(pending))


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
            edges = forward_edges(work, seeds, query["k"])
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


def traverse(store, kinds, get=requests.get):
    for kind in kinds:
        for row in list(store.db.execute("SELECT k FROM queries WHERE kind=? AND completed=0 ORDER BY k", (kind,))):
            while True:
                q = store.db.execute("SELECT * FROM queries WHERE k=?", (row["k"],)).fetchone()
                if q["completed"]:
                    break
                if not q["cursor"] or q["stop"].startswith(("short cursor", "repeated")):
                    raise ChainError(f"query requires explicit restart: {q['k']} {q['stop']}")
                query_page(store, q, get)
            log.info("%s: %d received", q["k"], q["received"])


def batches(values, size=100):
    for start in range(0, len(values), size):
        yield start // size, values[start:start + size]


def harvest(store):
    resolve_seeds(store)
    seeds = [r[0] for r in store.db.execute("SELECT DISTINCT oa FROM seeds WHERE oa<>'' ORDER BY oa")]
    for i, batch in batches(seeds):
        store.add_query(f"backward:{i:05d}", "backward", "openalex_id:" + "|".join(batch), batch)
        store.add_query(f"forward:{i:05d}", "forward", "cites:" + "|".join(batch), batch)
    traverse(store, ["backward"])
    refs = [r[0] for r in store.db.execute("SELECT DISTINCT candidate FROM edges WHERE direction='backward' ORDER BY candidate")]
    for i, batch in batches(refs):
        store.add_query(f"references:{i:05d}", "references", "openalex_id:" + "|".join(batch))
    traverse(store, ["references", "forward"])
    for r in store.db.execute("SELECT DISTINCT candidate FROM edges WHERE candidate NOT IN (SELECT k FROM works)"):
        store.db.execute("INSERT OR IGNORE INTO unresolved VALUES(?,?,?)", (r[0], "reference", "referenced ID absent from metadata response"))
    store.db.commit()


def export_delivery(store, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "manifest.json").exists():
        raise ChainError("delivery already exported; choose a new immutable directory")
    excluded = []
    def records():
        for row in store.db.execute("SELECT * FROM works ORDER BY k"):
            record = intake_record(json.loads(row["body"]), row["query"], row["date"])
            if record["title"].strip():
                yield record
            else:
                excluded.append({"record_id": row["k"], "query_id": row["query"], "reason": "not_retrievable",
                                 "title": "", "note": "OpenAlex returned no title"})
    csv_write(output / "records.csv", contract.RECORD_COLUMNS + ["cited_by_count"], records())
    for row in store.db.execute("SELECT d.q,d.w FROM discoveries d JOIN works w ON d.w=w.k WHERE d.q<>w.query ORDER BY d.q,d.w"):
        excluded.append({"record_id": row["w"], "query_id": row["q"], "reason": "duplicate_in_lane",
                         "title": "", "note": "same OpenAlex ID; all routes preserved in edges.csv"})
    csv_write(output / "excluded.csv", contract.EXCLUDED_COLUMNS, excluded)
    incomplete = [{"unit": r["k"], "reason": r["stop"] or "query not completed"}
                  for r in store.db.execute("SELECT * FROM queries WHERE completed=0")]
    incomplete += [{"unit": r["k"], "reason": r["note"]} for r in store.db.execute("SELECT * FROM unresolved")]
    registry = [{"query_id": r["k"], "platform": "openalex", "query": r["filter"],
                 "run_at": r["run_at"] or now(), "n_received": r["received"], "n_expected": r["expected"],
                 "completed": "true" if r["completed"] else "false", "stop_reason": r["stop"] or ("not run" if not r["completed"] else ""),
                 "pages": r["pages"], "direction": r["kind"]} for r in store.db.execute("SELECT * FROM queries ORDER BY k")]
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
    new_lookup = {r["work_key"]: r for r in new_rows}
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
            candidates = {c for c in candidates if normalize_title(new_lookup[c]["title"]) == normalize_title(old["title"])
                          and new_lookup[c]["year"] == old["year"]}
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["seeds", "harvest", "export", "rekey"])
    parser.add_argument("--output-dir", required=True, help="multi-output round checkpoint")
    parser.add_argument("--pool")
    parser.add_argument("--view")
    parser.add_argument("--sentinel", action="append", default=[])
    parser.add_argument("--budget-usd", type=float, default=20)
    parser.add_argument("--delivery")
    parser.add_argument("--budget-ledger", help="shared cumulative ledger across every round and screening route")
    parser.add_argument("--old-pool")
    parser.add_argument("--table")
    parser.add_argument("--dimensions-table")
    args = parser.parse_args()
    store = Store(args.output_dir, args.budget_ledger)
    try:
        if args.action == "seeds":
            init_seeds(store, args.pool, args.view, args.sentinel, args.budget_usd)
        elif args.action == "harvest":
            harvest(store)
        elif args.action == "export":
            export_delivery(store, args.delivery)
        else:
            migrate_labels(store, args.old_pool, args.pool, args.table, args.dimensions_table)
    except (ChainError, requests.RequestException) as exc:
        log.error("checkpoint preserved: %s", exc)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
