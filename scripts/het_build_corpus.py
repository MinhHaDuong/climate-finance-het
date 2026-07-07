#!/usr/bin/env python3
"""Build the HET "seven costumes" citation-overlap corpus via OpenAlex.

One-off companion pipeline for the HET paper in the sibling project
`polycentric_activity` ("Un theoreme, sept costumes" / "One Theorem, Seven
Guises"). Not part of the climate-finance corpus (Phase 1/2 contract) --
reads/writes only under data/het/.

Seeds (data/het/seeds.csv, 71 rows): every work cited in the HET manuscript,
extracted from its \\cite keys. 18 of the 71 are tagged with one of 8
"costume" branches (spatial, definetti, kantorovich, koopmans, gallai,
rockafellar, afriat, leontief_coda) -- the primary sources whose citation
overlap the figure is meant to show.

Hop 1: references of ALL 71 seeds (this is "tous les articles cites dans le
papier + toutes leurs references").
Hop 2: references of hop-1 works, but only for hop-1 works reachable from a
costume-branch seed -- bounds the crawl to what the overlap figure needs;
the ~53 context/methodology citations (Merton, Stigler, etc.) stop at hop 1.

Outputs:
  data/het/works.csv     -- openalex_id, doi, title, abstract, keywords,
                             year, hop, branches (pipe-separated), seed_key
  data/het/citations.csv -- source_id, ref_id edges (for transparency)
"""

import argparse
import json
import os
import re
from difflib import SequenceMatcher

import pandas as pd
from utils import (
    MAILTO,
    OPENALEX_API_KEY,
    get_logger,
    normalize_doi,
    reconstruct_abstract,
    retry_get,
)

log = get_logger("het_build_corpus")

_HERE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(_HERE)
HET_DIR = os.path.join(BASE_DIR, "data", "het")
POOL_DIR = os.path.join(HET_DIR, "pool")
CACHE_PATH = os.path.join(POOL_DIR, "works_cache.jsonl")

OA_WORKS = "https://api.openalex.org/works"
SELECT_FIELDS = (
    "id,doi,display_name,title,publication_year,"
    "abstract_inverted_index,referenced_works,concepts"
)
TITLE_MATCH_THRESHOLD = 0.55


def oa_params(extra):
    params = {"mailto": MAILTO, "select": SELECT_FIELDS}
    if OPENALEX_API_KEY:
        params["api_key"] = OPENALEX_API_KEY
    params.update(extra)
    return params


def record_from_json(w):
    concepts = sorted(w.get("concepts") or [], key=lambda c: -(c.get("score") or 0))
    keywords = "; ".join(
        c["display_name"] for c in concepts[:5] if c.get("display_name")
    )
    return {
        "openalex_id": w.get("id", ""),
        "doi": normalize_doi(w.get("doi")),
        "title": w.get("title") or w.get("display_name") or "",
        "abstract": reconstruct_abstract(w.get("abstract_inverted_index")),
        "keywords": keywords,
        "year": w.get("publication_year"),
        "referenced_works": w.get("referenced_works") or [],
    }


class Cache:
    """Append-only JSONL cache of resolved OpenAlex records, keyed by ID."""

    def __init__(self, path):
        self.path = path
        self.by_id = {}
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    self.by_id[rec["openalex_id"]] = rec
        self._fh = open(path, "a", encoding="utf-8")

    def get(self, oa_id):
        return self.by_id.get(oa_id)

    def put(self, rec):
        if rec["openalex_id"] in self.by_id:
            return
        self.by_id[rec["openalex_id"]] = rec
        self._fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._fh.flush()

    def close(self):
        self._fh.close()


def resolve_by_doi(doi, delay):
    url = f"{OA_WORKS}/doi:{doi}"
    resp = retry_get(url, params=oa_params({}), delay=delay)
    if resp.status_code != 200:
        return None
    return record_from_json(resp.json())


def resolve_by_title(title, delay):
    resp = retry_get(
        OA_WORKS, params=oa_params({"search": title, "per_page": 5}), delay=delay
    )
    if resp.status_code != 200:
        return None, 0.0
    results = resp.json().get("results", [])
    norm_title = re.sub(r"\s+", " ", title.lower()).strip()
    best, best_score = None, 0.0
    for w in results:
        cand = (w.get("title") or w.get("display_name") or "").lower()
        cand = re.sub(r"\s+", " ", cand).strip()
        score = SequenceMatcher(None, norm_title, cand).ratio()
        if score > best_score:
            best, best_score = w, score
    if best is None or best_score < TITLE_MATCH_THRESHOLD:
        return None, best_score
    return record_from_json(best), best_score


def batch_resolve(oa_ids, cache, delay, batch_size=50):
    """Fetch full records for OpenAlex IDs not already cached."""
    todo = [i for i in oa_ids if i and cache.get(i) is None]
    n_batches = (len(todo) + batch_size - 1) // batch_size or 1
    for i in range(0, len(todo), batch_size):
        batch = todo[i : i + batch_size]
        short_ids = [b.split("/")[-1] for b in batch]
        filt = "openalex_id:" + "|".join(short_ids)
        resp = retry_get(
            OA_WORKS,
            params=oa_params({"filter": filt, "per_page": len(batch)}),
            delay=delay,
        )
        if resp.status_code != 200:
            log.warning("Batch resolve failed (status %d), skipping %d ids",
                        resp.status_code, len(batch))
            continue
        for w in resp.json().get("results", []):
            cache.put(record_from_json(w))
        log.info("Resolved batch %d/%d (%d ids)", i // batch_size + 1, n_batches, len(batch))


def resolve_seeds(seeds, cache, delay):
    """Resolve every seed row to an OpenAlex ID (by DOI, else title search)."""
    seed_oa_id = {}
    unresolved = []
    for _, row in seeds.iterrows():
        key, doi, title = row["key"], row["doi"], row["title"]
        rec = resolve_by_doi(doi, delay) if doi else None
        if rec is None and title:
            rec, _score = resolve_by_title(title, delay)
        if rec is None:
            unresolved.append(key)
            continue
        cache.put(rec)
        seed_oa_id[key] = rec["openalex_id"]

    log.info("Seeds resolved: %d/%d", len(seed_oa_id), len(seeds))
    if unresolved:
        log.warning("Unresolved seeds (%d): %s", len(unresolved), ", ".join(unresolved))
    return seed_oa_id, unresolved


def _add_reach(reach, oa_id, branches):
    reach.setdefault(oa_id, set()).update(b for b in branches if b is not None)


def expand_hop1(seed_oa_id, branch_of_seed, cache, delay):
    """Fetch references of every seed; track which costume branch(es) reach each."""
    reach = {}
    hop1_ids = set()
    citations_edges = []
    for key, oa_id in seed_oa_id.items():
        refs = cache.get(oa_id)["referenced_works"]
        hop1_ids.update(refs)
        citations_edges.extend((oa_id, r) for r in refs)
        seed_branch = branch_of_seed.get(key, "")
        _add_reach(reach, oa_id, {seed_branch})
        for r in refs:
            _add_reach(reach, r, {seed_branch})

    log.info("Hop-1 candidate IDs: %d", len(hop1_ids))
    batch_resolve(hop1_ids, cache, delay)
    return hop1_ids, reach, citations_edges


def expand_hop2(hop1_ids, seed_oa_ids, reach, cache, delay):
    """Fetch references of hop-1 works reachable from a costume-branch seed."""
    hop1_branch_reachable = [i for i in hop1_ids if any(reach.get(i, set()))]
    hop2_ids = set()
    citations_edges = []
    for i in hop1_branch_reachable:
        rec = cache.get(i)
        if rec is None:
            continue
        refs = rec["referenced_works"]
        hop2_ids.update(refs)
        for r in refs:
            citations_edges.append((i, r))
            _add_reach(reach, r, reach.get(i, set()))

    hop2_ids -= hop1_ids
    hop2_ids -= set(seed_oa_ids)
    log.info("Hop-1 works reachable from a branch seed: %d/%d",
             len(hop1_branch_reachable), len(hop1_ids))
    log.info("Hop-2 candidate IDs: %d", len(hop2_ids))
    batch_resolve(hop2_ids, cache, delay)
    return hop2_ids, citations_edges


def assemble_works(seed_oa_id, hop1_ids, hop2_ids, reach, cache):
    """Build the final works table: one row per resolved work, tagged with hop and branches."""
    all_ids = set(seed_oa_id.values()) | hop1_ids | hop2_ids
    key_of_oa_id = {oa_id: key for key, oa_id in seed_oa_id.items()}
    rows = []
    for oa_id in all_ids:
        rec = cache.get(oa_id)
        if rec is None:
            continue
        seed_key = key_of_oa_id.get(oa_id, "")
        hop = 0 if seed_key else (1 if oa_id in hop1_ids else 2)
        branches = sorted(b for b in reach.get(oa_id, set()) if b)
        rows.append({
            "openalex_id": oa_id,
            "doi": rec["doi"],
            "title": rec["title"],
            "abstract": rec["abstract"],
            "keywords": rec["keywords"],
            "year": rec["year"],
            "hop": hop,
            "branches": "|".join(branches),
            "seed_key": seed_key,
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default=os.path.join(HET_DIR, "seeds.csv"))
    parser.add_argument("--output-works", default=os.path.join(HET_DIR, "works.csv"))
    parser.add_argument("--output-citations", default=os.path.join(HET_DIR, "citations.csv"))
    parser.add_argument("--delay", type=float, default=0.15)
    parser.add_argument("--limit-seeds", type=int, default=0, help="For smoke testing")
    args = parser.parse_args()

    seeds = pd.read_csv(args.seeds).fillna("")
    if args.limit_seeds:
        seeds = seeds.head(args.limit_seeds)

    cache = Cache(CACHE_PATH)
    seed_oa_id, _unresolved = resolve_seeds(seeds, cache, args.delay)
    branch_of_seed = dict(zip(seeds["key"], seeds["branch"]))

    hop1_ids, reach, edges1 = expand_hop1(seed_oa_id, branch_of_seed, cache, args.delay)
    hop2_ids, edges2 = expand_hop2(hop1_ids, seed_oa_id.values(), reach, cache, args.delay)

    works_df = assemble_works(seed_oa_id, hop1_ids, hop2_ids, reach, cache)
    os.makedirs(os.path.dirname(args.output_works), exist_ok=True)
    works_df.to_csv(args.output_works, index=False)
    log.info("Wrote %d works -> %s", len(works_df), args.output_works)

    cit_df = pd.DataFrame(edges1 + edges2, columns=["source_id", "ref_id"]).drop_duplicates()
    cit_df.to_csv(args.output_citations, index=False)
    log.info("Wrote %d citation edges -> %s", len(cit_df), args.output_citations)

    cache.close()


if __name__ == "__main__":
    main()
