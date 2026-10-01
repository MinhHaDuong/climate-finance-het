"""Export the Jev-pilot Opus labels the recall pre-filter learns from (ticket 1810).

The Jev pilot (archive ``rel_jev_pilot/2026-09-30`` on doudou, read-only) holds
two label sets that exist nowhere else:

- ``router/opus_labels.jsonl``: Opus labels of a stratified random sample of
  800 catalogue works (``router/sample.jsonl``, strata Qwen label x language,
  inclusion weights N_h / n_h);
- ``reference/adjudicated.jsonl``: the four-judge adjudicated reference set
  (495 works: 400 of that random sample, 95 top-up), split ``tune`` /
  ``heldout``.

This writes their ids and labels, never their texts, to a small committed
register so that padme, where the embeddings are computed, gets them through
git (data flows padme to doudou only; a label register is an input, not
data). Texts are re-read on padme from the REL pool by OpenAlex id.

One row per work. A work of the reference set takes its adjudicated label
and split (``heldout`` = validation, never trained on); the other sample works
take their Opus label and split ``train``.

Usage (doudou):
    uv run python scripts/corpus_rel_prefilter_labels.py \\
        --archive ~/data/projets/climate-finance-het/rel_jev_pilot/2026-09-30 \\
        --output config/rel_prefilter_labels.csv
"""

import argparse
import csv
import hashlib
import json
import os
import sys

from utils import get_logger

log = get_logger('rel_prefilter_labels')

FIELDS = ["openalex_id", "label", "label_source", "split", "stratum", "weight"]
LABELS = {"icf", "aux", "out", "unsure"}


def _jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def build(archive: str) -> list[dict]:
    sample = {r["openalex_id"]: r for r in _jsonl(os.path.join(archive, "router", "sample.jsonl"))}
    opus = {r["openalex_id"]: r for r in _jsonl(os.path.join(archive, "router", "opus_labels.jsonl"))}
    ref = {r["openalex_id"]: r for r in _jsonl(os.path.join(archive, "reference", "adjudicated.jsonl"))}
    rows: dict[str, dict] = {}
    for k, r in ref.items():
        if r["label"] not in LABELS:
            raise ValueError(f"unknown label {r['label']!r} for {k}")
        rows[k] = {"openalex_id": k, "label": r["label"], "label_source": "jev_pilot_reference_adjudicated",
                   "split": "heldout" if r["split"] == "heldout" else "train",
                   "stratum": r.get("ref_stratum", ""), "weight": r.get("weight", "")}
    for k, r in opus.items():
        if k in rows:
            continue
        if r["label"] not in LABELS:
            raise ValueError(f"unknown label {r['label']!r} for {k}")
        s = sample.get(k, {})
        rows[k] = {"openalex_id": k, "label": r["label"], "label_source": "jev_pilot_router_opus",
                   "split": "train", "stratum": "random:" + s.get("stratum", ""),
                   "weight": s.get("weight", "")}
    return [rows[k] for k in sorted(rows)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--archive", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args(argv)
    rows = build(os.path.expanduser(a.archive))
    with open(a.output, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        w.writerows(rows)
    srcs = {}
    for name in ("router/sample.jsonl", "router/opus_labels.jsonl", "reference/adjudicated.jsonl"):
        with open(os.path.join(os.path.expanduser(a.archive), name), "rb") as fh:
            srcs[name] = hashlib.sha256(fh.read()).hexdigest()
    log.info(json.dumps({"rows": len(rows), "sources_sha256": srcs}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
