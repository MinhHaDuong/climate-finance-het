"""Reuse of completed citation directions from an archived round (t1654 lane).

Split from ``_rel_chaining`` for the module size cap. The dependency is one-way:
this module imports ``_rel_chaining``, never the reverse at load time. Verifies archived native
cursor pages offline, without provider calls or source writes.
"""

import gzip
import hashlib
import json
import re
import sqlite3
from pathlib import Path

from _rel_chaining import OA, ChainError, oid, reference_diagnostic, reference_ids, sha


def _completed_direction_evidence(source, native_root, query, native_index):
    """Verify every original native cursor page, without provider calls or source writes."""
    seeds = json.loads(query["seeds"])
    field = {"backward": "openalex_id", "forward": "cites"}.get(query["kind"])
    if not field or not seeds or len(set(seeds)) != len(seeds) or query["filter"] != field + ":" + "|".join(seeds):
        raise ChainError("native reuse seed/filter binding mismatch")
    cursor, seen, received, pages, returned, backward_usable = "*", set(), 0, [], set(), set()
    reference_gaps = []
    while cursor:
        if cursor in seen:
            raise ChainError("repeated native reuse cursor")
        seen.add(cursor)
        params = {"filter": query["filter"], "per_page": 100, "cursor": cursor}
        key = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
        indexed = source.execute("SELECT path FROM api_pages WHERE k=?", (key,)).fetchone()
        if not indexed:
            raise ChainError("native reuse page absent from source index")
        path = (native_root / indexed["path"]).resolve()
        if not path.is_relative_to(native_root.resolve()) or not path.is_file():
            raise ChainError("native reuse page absent or outside original archive")
        digest = sha(path)
        indexed_proof = native_index["pages"].get(indexed["path"])
        if not indexed_proof or indexed_proof.get("sha256") != digest or indexed_proof.get("request_sha256") != key:
            raise ChainError("native reuse page/index hash binding mismatch")
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            native = json.load(stream)
        if native.get("status") != 200 or native.get("query") != params:
            raise ChainError("native reuse page does not match exact query")
        if not native.get("retrieved_at"):
            raise ChainError("native reuse page lacks retrieval date")
        body = native["body"]
        results, meta = body["results"], body["meta"]
        if not isinstance(results, list) or meta.get("count") != query["expected"]:
            raise ChainError("native reuse count changed or invalid results")
        page_ids = {oid(work["id"]) for work in results}
        if len(page_ids) != len(results) or returned.intersection(page_ids) or not all(re.fullmatch(r"W\d+", key) for key in page_ids):
            raise ChainError("native reuse duplicate or invalid work identities")
        received += len(results)
        returned.update(page_ids)
        backward_usable.update(oid(work["id"]) for work in results if reference_ids(work)[0] is not None)
        reference_gaps.extend(gap for work in results
                              if (gap := reference_diagnostic(work, query["k"])) is not None)
        pages.append({"path": str(path), "sha256": digest, "request_sha256": key,
                      "request_method": "GET", "request_endpoint": OA,
                      "endpoint_basis": "archived collector routing contract; public params preserved",
                      "public_request": params, "cursor": cursor, "retrieved_at": native["retrieved_at"],
                      "canonical_body_sha256": hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True,
                                                                          separators=(",", ":")).encode()).hexdigest(),
                      "body_basis": "archived parsed provider JSON, not raw HTTP wire bytes"})
        cursor = meta.get("next_cursor")
    if received != query["received"] or received != query["expected"] or len(pages) != query["pages"]:
        raise ChainError("native reuse full cursor/count coverage mismatch")
    query_record = dict(query)
    return {"source_query": query_record,
            "source_query_sha256": hashlib.sha256(json.dumps(query_record, sort_keys=True).encode()).hexdigest(),
            "native_pages": pages, "native_reference_diagnostics": reference_gaps, "fresh_retrieval": False,
            "source_query_as_of": max(page["retrieved_at"] for page in pages)}, backward_usable


def reuse_completed_directions(store, snapshot, native_root, expected_sha256, *, native_index_path, native_index_sha256):
    """Record exact proven reuse separately from newly retrieved queries and edges."""
    snapshot, native_root = Path(snapshot), Path(native_root)
    if sha(snapshot) != expected_sha256:
        raise ChainError("previous round snapshot changed")
    if sha(native_index_path) != native_index_sha256:
        raise ChainError("previous native index changed")
    native_index = json.loads(Path(native_index_path).read_text())
    if native_index["snapshot_sha256"] != expected_sha256:
        raise ChainError("previous native index belongs to another snapshot")
    routing = native_index.get("acquisition_source", {})
    if (routing.get("endpoint") != OA or routing.get("method") != "GET"
            or not re.fullmatch(r"[0-9a-f]{40}", routing.get("recorded_revision", ""))
            or not routing.get("artifact") or sha(routing["artifact"]) != routing.get("artifact_sha256")):
        raise ChainError("native reuse acquisition routing source binding mismatch")
    source = sqlite3.connect(snapshot.resolve().as_uri() + "?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    wanted = {r[0] for r in store.db.execute("SELECT DISTINCT oa FROM seeds WHERE oa<>''")}
    prepared = {}
    verified_gaps = {}
    try:
        for query in source.execute("SELECT * FROM queries WHERE kind IN ('backward','forward') AND completed=0"):
            if wanted.intersection(json.loads(query["seeds"])):
                raise ChainError("previous direction interrupted: resume original checkpoint before frontier activation")
        for query in source.execute("SELECT * FROM queries WHERE kind IN ('backward','forward') AND completed=1 ORDER BY k"):
            identities = wanted.intersection(json.loads(query["seeds"]))
            if not identities:
                continue
            evidence, returned = _completed_direction_evidence(source, native_root, query, native_index)
            if query["kind"] == "backward":
                identities.intersection_update(returned)
            source_edges = [dict(row) for row in source.execute("SELECT * FROM edges WHERE q=? ORDER BY seed,candidate,direction", (query["k"],))]
            source_gaps = {row["k"]: dict(row) for row in source.execute("SELECT * FROM unresolved ORDER BY k")
                           if row["k"].startswith(query["k"] + ":")}
            source_gaps = {**{gap["k"]: gap for gap in evidence["native_reference_diagnostics"]}, **source_gaps}
            source_gaps = [source_gaps[key] for key in sorted(source_gaps)]
            evidence.update(source_unresolved=source_gaps, source_edge_count=len(source_edges),
                            source_edges_sha256=hashlib.sha256(json.dumps(source_edges, sort_keys=True).encode()).hexdigest())
            evidence.update(source_snapshot=str(snapshot.resolve()), source_snapshot_sha256=expected_sha256,
                            native_index=str(Path(native_index_path).resolve()), native_index_sha256=native_index_sha256,
                            acquisition_source=routing,
                            source_revision_basis="recorded operator source pointer, not per-response execution attestation")
            verified_gaps.update((gap["k"], gap) for gap in source_gaps)
            for identity in sorted(identities):
                prepared.setdefault((identity, query["kind"]), json.dumps(evidence, sort_keys=True))
    finally:
        source.close()
    # All native pages validate before any reuse disposition is recorded.
    for (identity, direction), evidence in prepared.items():
        old = store.db.execute("SELECT evidence FROM direction_reuse WHERE seed=? AND direction=?", (identity, direction)).fetchone()
        if old and old[0] != evidence:
            raise ChainError("changed completed direction reuse evidence")
    gaps = verified_gaps
    for key, row in gaps.items():
        old = store.db.execute("SELECT kind,note FROM unresolved WHERE k=?", (key,)).fetchone()
        if old and tuple(old) != (row["kind"], row["note"]):
            raise ChainError("changed reused source diagnostic")
    store.db.executemany("INSERT OR IGNORE INTO unresolved VALUES(?,?,?)",
                         [(key, row["kind"], row["note"]) for key, row in gaps.items()])
    store.db.executemany("INSERT OR IGNORE INTO direction_reuse VALUES(?,?,?)",
                         [(identity, direction, evidence) for (identity, direction), evidence in prepared.items()])
    store.db.commit()
