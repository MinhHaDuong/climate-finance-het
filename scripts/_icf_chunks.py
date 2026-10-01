"""REL view and stage-2 chunk files, shared by the ICF stage-2 and catch-up commands.

``corpus_icf_stage2.py`` (stage 2 and audit, ticket 1732) and
``corpus_rel_discipline_catchup.py`` (discipline catch-up, ticket 1842) select
works from the same in-memory REL view and write them in the same 1530 chunk
format, so a chunk shown to a labeller is the same whichever command built it.
"""

import csv
import glob
import json
import os

import _icf_screen as ics
import _rel_view as rv
from pipeline_loaders import load_rel_review_config
from utils import normalize_title

WORKS_COLUMNS = ["work_key", "openalex_id", "doi", "title_norm_year", "chunk", "n"]
# REL-view status of a work with a stage-2 label -> that final stage-2 label.
FINAL_STAGE2 = {"icf": "icf", "aux": "aux", "out": "out", "unsure_unresolved": "unsure"}


class Stage2Error(Exception):
    """A refused build or parse."""


def view(pool_path: str, table_path: str, rule: dict) -> tuple[list[dict], list[dict]]:
    """The pool and the REL view rows, computed from the pool and ``icf_screen``."""
    pool = rv.read_pool(pool_path)
    rows, _ = rv.build_view(pool, ics.read_table(table_path), load_rel_review_config(), rule)
    return pool, rows


def _record(p: dict) -> dict:
    return {"language": p["language"], "year": p["year"], "journal": p["journal"],
            "countries": [c for c in p["affiliation_countries"].split(";") if c],
            "title": p["title"], "abstract": p["abstract"]}


def write_chunks(out_dir: str, works: list[dict], s2cfg: dict, manifest: dict) -> list[str]:
    """Chunk files, ids and works.csv for ``works`` (pool rows, in order)."""
    if os.path.isdir(out_dir) and glob.glob(os.path.join(out_dir, "chunk*")):
        raise Stage2Error(f"{out_dir} already holds chunk files; choose a new directory")
    os.makedirs(out_dir, exist_ok=True)
    size = s2cfg["chunk_size"]
    names, table = [], []
    for c in range(0, len(works), size):
        chunk = works[c:c + size]
        name = f"chunk{c // size + 1:02d}"
        with open(os.path.join(out_dir, f"{name}.txt"), "w", encoding="utf-8") as fh:
            for n, p in enumerate(chunk, 1):
                fh.write(ics.format_stage2_record(n, _record(p), s2cfg["title_max_chars"],
                                                  s2cfg["abstract_max_chars"]))
        with open(os.path.join(out_dir, f"{name}.ids.json"), "w", encoding="utf-8") as fh:
            json.dump([p["work_key"] for p in chunk], fh)
        for n, p in enumerate(chunk, 1):
            title = normalize_title(p["title"])
            table.append({"work_key": p["work_key"], "openalex_id": p["openalex_id"],
                          "doi": p["doi"], "title_norm_year": f"{title}|{p['year']}" if title else "",
                          "chunk": name, "n": n})
        names.append(name)
    with open(os.path.join(out_dir, "works.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=WORKS_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(table)
    with open(os.path.join(out_dir, "build.json"), "w", encoding="utf-8") as fh:
        json.dump({**manifest, "works": len(works), "chunks": names}, fh, indent=2,
                  ensure_ascii=False)
        fh.write("\n")
    return names
