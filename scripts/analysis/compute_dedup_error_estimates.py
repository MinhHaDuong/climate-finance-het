#!/usr/bin/env python3
"""Estimate the error rates of the two exact dedup passes (ticket 0301, R1-12).

The RDJ-26561 referee's remark R1-12 concerns the *errors* of the exact
deduplication, not its removal counts (ticket 0284 delivered those): working
paper vs published pairs that escape both passes (false negatives), and
distinct works wrongly merged by a shared DOI or a degenerate title+year key
(false positives). This script reproduces the 2026-07-22 read-only pilot as a
pipeline-traceable artifact; ticket 0276 quotes it in the data-paper prose.

False negatives are estimated over refined_works (post-dedup):
  - exact-title pairs: same normalized title, same first author, different
    years at most ``year_gap_max`` apart — the referee's predicted WP/journal
    version class;
  - candidate families: union of the exact tier and a fuzzy tier (title token
    Jaccard >= ``fuzzy_jaccard_threshold``, same author) — an upper bound,
    dominated by editorial variants and report series that are not duplicates.

False positives are estimated over the pre-dedup combined catalogs, re-forming
the exact group keys of scripts/harvest/catalog_merge.py:
  - DOI pass: groups with non-identical normalized titles (mostly benign
    subtitle/translation variants) and, within those, groups whose title token
    overlap is near zero (Jaccard < ``collision_jaccard_threshold``) — DOI
    collisions between unrelated works;
  - title+year pass: groups mixing different first-author lastnames, and
    groups keyed on an EMPTY year — the degenerate key that merges same-title
    works across all unknown years.

Inputs:
  - refined_works.csv (via load_refined_works, or --input[0])
  - the catalog_merge source catalogs declared in dvc.yaml (read-only,
    no Phase-1 trigger; or --input[1:])

Output:
  - deliverables/_shared/tables/tab_dedup_error_estimates.csv (long
    metric/value, committed artifact)

Usage:
    uv run python scripts/analysis/compute_dedup_error_estimates.py \
        --output deliverables/_shared/tables/tab_dedup_error_estimates.csv
"""

import itertools
import os
import re
from collections import defaultdict

import pandas as pd
from pipeline_io import save_csv
from pipeline_text import normalize_title
from schemas import DedupErrorEstimatesSchema
from script_io_args import parse_io_args, validate_io
from utils import BASE_DIR, get_logger, normalize_doi

log = get_logger("compute_dedup_error_estimates")

# Fallback thresholds; production runs read the dedup_error_estimates block of
# config/analysis.yaml (rule 6) — keep the two in sync.
DEFAULT_THRESHOLDS = {
    "year_gap_max": 5,
    "fuzzy_jaccard_threshold": 0.7,
    "collision_jaccard_threshold": 0.1,
}


def _author_tokens(name: str | None) -> frozenset[str]:
    """Name parts (lowercase, length >= 2) as an order-free set.

    First-author metadata is noisy across sources — given/family name order
    swaps are common — so 'Jane Doe' and 'Doe, Jane' must compare equal.
    """
    if not name or not isinstance(name, str):
        return frozenset()
    return frozenset(
        t for t in re.split(r"[^\w]+", name.lower()) if len(t) >= 2
    )


def _same_author(a: frozenset[str], b: frozenset[str]) -> bool:
    return bool(a) and bool(b) and bool(a & b)


def _title_tokens(title_norm: str) -> frozenset[str]:
    return frozenset(title_norm.split())


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class _UnionFind:
    """Minimal union-find over integer ids, for candidate families."""

    def __init__(self):
        self.parent: dict[int, int] = {}

    def find(self, x: int) -> int:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def compute_false_negatives(works: pd.DataFrame, thresholds: dict) -> dict:
    """Residual-duplicate estimates over the post-dedup corpus.

    Blocks candidate pairs on shared author-name tokens (keeps the pairwise
    comparison tractable at ~31k docs and matches across name-order swaps),
    then tiers them into exact-title/different-year pairs and fuzzy-title
    families.
    """
    year_gap_max = thresholds["year_gap_max"]
    fuzzy_thr = thresholds["fuzzy_jaccard_threshold"]

    df = works.reset_index(drop=True)
    title_norm = df["title"].apply(normalize_title)
    years = pd.to_numeric(df["year"], errors="coerce")
    authors = df["first_author"].apply(_author_tokens)
    titles_tok = title_norm.apply(_title_tokens)

    # Blocking: docs sharing any author-name token are candidate pairs.
    blocks: dict[str, list[int]] = defaultdict(list)
    for i, toks in authors.items():
        if title_norm.iloc[i] == "":
            continue
        for t in toks:
            blocks[t].append(i)

    exact_pairs: set[tuple[int, int]] = set()
    uf = _UnionFind()
    family_members: set[int] = set()
    seen_pairs: set[tuple[int, int]] = set()
    for members in blocks.values():
        if len(members) < 2:
            continue
        for i, j in itertools.combinations(members, 2):
            pair = (i, j)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            if not _same_author(authors.iloc[i], authors.iloc[j]):
                continue
            ti, tj = title_norm.iloc[i], title_norm.iloc[j]
            if ti == tj:
                yi, yj = years.iloc[i], years.iloc[j]
                if (
                    pd.notna(yi)
                    and pd.notna(yj)
                    and yi != yj
                    and abs(yi - yj) <= year_gap_max
                ):
                    exact_pairs.add(pair)
                    uf.union(i, j)
                    family_members.update(pair)
            elif _jaccard(titles_tok.iloc[i], titles_tok.iloc[j]) >= fuzzy_thr:
                uf.union(i, j)
                family_members.update(pair)

    n_docs = len(df)
    n_family = len(family_members)
    return {
        "n_refined_docs": n_docs,
        "fn_exact_title_pairs": len(exact_pairs),
        "fn_exact_title_pairs_share": (
            len(exact_pairs) / n_docs if n_docs else float("nan")
        ),
        "fn_candidate_family_docs": n_family,
        "fn_candidate_family_docs_share": (
            n_family / n_docs if n_docs else float("nan")
        ),
    }


def _doi_group_flags(titles: pd.Series, collision_thr: float) -> tuple[bool, bool]:
    """(divergent_title, near_zero_overlap) for one DOI group's titles."""
    norm = [normalize_title(t) for t in titles]
    divergent = len(set(norm)) > 1
    near_zero = False
    if divergent:
        toks = [_title_tokens(t) for t in norm]
        near_zero = any(
            _jaccard(a, b) < collision_thr
            for a, b in itertools.combinations(toks, 2)
        )
    return divergent, near_zero


def compute_false_positives(combined: pd.DataFrame, thresholds: dict) -> dict:
    """Wrong-merge estimates over the pre-dedup combined catalogs.

    Re-forms the two group keys of catalog_merge.deduplicate() — normalized
    DOI, then normalized title + year[:4] for no-DOI rows — and flags the
    groups where the key visibly degrades.
    """
    collision_thr = thresholds["collision_jaccard_threshold"]

    df = combined.copy()
    df["_doi_norm"] = df["doi"].apply(normalize_doi)
    has_doi = df[df["_doi_norm"] != ""]

    fp_doi_groups = 0
    fp_doi_removals = 0
    fp_doi_divergent = 0
    fp_doi_near_zero = 0
    for _, grp in has_doi.groupby("_doi_norm"):
        if len(grp) < 2:
            continue
        fp_doi_groups += 1
        fp_doi_removals += len(grp) - 1
        divergent, near_zero = _doi_group_flags(grp["title"], collision_thr)
        fp_doi_divergent += int(divergent)
        fp_doi_near_zero += int(near_zero)

    no_doi = df[df["_doi_norm"] == ""].copy()
    no_doi["_title_norm"] = no_doi["title"].apply(normalize_title)
    no_doi = no_doi[no_doi["_title_norm"] != ""]
    no_doi["_year4"] = no_doi["year"].astype(str).str[:4]

    fp_ty_groups = 0
    fp_ty_removals = 0
    fp_ty_author_conflict = 0
    empty_year_groups = 0
    empty_year_docs = 0
    empty_year_max = 0
    for (_, year4), grp in no_doi.groupby(["_title_norm", "_year4"]):
        if len(grp) < 2:
            continue
        fp_ty_groups += 1
        fp_ty_removals += len(grp) - 1
        author_sets = [
            _author_tokens(a) for a in grp["first_author"]
        ]
        nonempty = [s for s in author_sets if s]
        conflict = any(
            not (a & b) for a, b in itertools.combinations(nonempty, 2)
        )
        fp_ty_author_conflict += int(conflict)
        if year4 == "":
            empty_year_groups += 1
            empty_year_docs += len(grp)
            empty_year_max = max(empty_year_max, len(grp))

    return {
        "fp_doi_groups": fp_doi_groups,
        "fp_doi_removals": fp_doi_removals,
        "fp_doi_groups_divergent_title": fp_doi_divergent,
        "fp_doi_groups_near_zero_overlap": fp_doi_near_zero,
        "fp_titleyear_groups": fp_ty_groups,
        "fp_titleyear_removals": fp_ty_removals,
        "fp_titleyear_groups_author_conflict": fp_ty_author_conflict,
        "fp_empty_year_groups": empty_year_groups,
        "fp_empty_year_docs_merged": empty_year_docs,
        "fp_empty_year_max_group_size": empty_year_max,
    }


def compute_dedup_error_estimates(
    works: pd.DataFrame, combined: pd.DataFrame, thresholds: dict
) -> pd.DataFrame:
    """Full estimate table in long metric/value format."""
    rows = {}
    rows.update(compute_false_negatives(works, thresholds))
    rows.update(compute_false_positives(combined, thresholds))
    rows.update(
        {
            "threshold_year_gap_max": thresholds["year_gap_max"],
            "threshold_fuzzy_jaccard": thresholds["fuzzy_jaccard_threshold"],
            "threshold_collision_jaccard": thresholds[
                "collision_jaccard_threshold"
            ],
        }
    )
    return pd.DataFrame(
        [(k, float(v)) for k, v in rows.items()], columns=["metric", "value"]
    )


def _catalog_files_from_dvc() -> list[str]:
    """The catalog_merge source deps from dvc.yaml — single source of truth.

    Duplicated from scripts/harvest/catalog_merge.py rather than imported:
    Phase-2 scripts do not put scripts/harvest on the path.
    """
    import yaml

    with open(os.path.join(BASE_DIR, "dvc.yaml")) as f:
        dvc = yaml.safe_load(f)
    deps = dvc["stages"]["catalog_merge"]["deps"]
    return [
        os.path.join(BASE_DIR, d) for d in deps if d.endswith("_works.csv")
    ]


def _load_thresholds() -> dict:
    from pipeline_loaders import load_analysis_config

    cfg = load_analysis_config().get("dedup_error_estimates", {})
    return {**DEFAULT_THRESHOLDS, **cfg}


def main():
    io_args, _extra = parse_io_args()
    os.makedirs(os.path.dirname(io_args.output) or ".", exist_ok=True)
    validate_io(output=io_args.output, inputs=io_args.input)

    inputs = io_args.input or []
    if len(inputs) >= 2:
        log.info("Reading from --input: %s + %d catalogs",
                 inputs[0], len(inputs) - 1)
        works = pd.read_csv(inputs[0], dtype=str, keep_default_na=False)
        catalog_paths = inputs[1:]
    elif inputs:
        raise SystemExit(
            "compute_dedup_error_estimates needs refined_works.csv plus at "
            "least one source catalog as --input, or no --input at all."
        )
    else:
        from pipeline_loaders import load_refined_works

        works = load_refined_works()
        catalog_paths = _catalog_files_from_dvc()

    frames = []
    for path in catalog_paths:
        if not os.path.exists(path):
            log.warning("missing catalog (skipped): %s", path)
            continue
        frames.append(
            pd.read_csv(path, dtype=str, keep_default_na=False)[
                ["doi", "title", "first_author", "year"]
            ]
        )
    if not frames:
        raise SystemExit("No source catalog readable — nothing to estimate.")
    combined = pd.concat(frames, ignore_index=True)

    thresholds = _load_thresholds()
    result = compute_dedup_error_estimates(works, combined, thresholds)
    DedupErrorEstimatesSchema.validate(result)
    save_csv(result, io_args.output)
    log.info("Wrote %d metrics to %s", len(result), io_args.output)
    for _, row in result.iterrows():
        log.info("  %s = %g", row["metric"], row["value"])


if __name__ == "__main__":
    main()
