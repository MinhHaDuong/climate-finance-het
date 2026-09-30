"""Merge report of the REL pool: per-delivery counts and reconciliation (1731, 1655).

Per delivery, before cross-source deduplication, the fields of the contract's
merge-report table (``docs/rel-intake-contract.md``); then pool totals, works
per number of sources and a reconciliation that must add up
(``RelPoolError`` otherwise).
"""

from collections import Counter, defaultdict

from _rel_pool_dedup import compatible, keys_of
from qa_rel_intake import DOI
from utils import normalize_title

CATALOGUE = "catalogue"


class RelPoolError(Exception):
    """A refused input: wrong catalogue, failing delivery, broken reconciliation."""


def _direct_catalogue_method(row, cat_index):
    """How a lane row matches the catalogue directly, cascade order, or None."""
    doi, oa, ty = keys_of(row)
    if doi and doi in cat_index["doi"]:
        return "by_doi"
    if oa and oa in cat_index["openalex_id"]:
        return "by_openalex_id"
    if row.get("handle") and row["handle"] in cat_index["handle"]:
        return "by_handle"
    if ty and any(compatible(row, c) for c in cat_index["title"].get(ty, [])):
        return "by_title_year"
    if row.get("title_only") and normalize_title(row["title"]) in cat_index["title_any_year"]:
        return "by_title_only"
    return None


def _catalogue_index(rows):
    """Catalogue keys, for naming the method of a direct catalogue match."""
    index = {"doi": set(), "openalex_id": set(), "handle": set(), "title": defaultdict(list),
             "title_any_year": set()}
    for r in rows:
        if r["origin"] != CATALOGUE:
            continue
        doi, oa, ty = keys_of(r)
        if doi:
            index["doi"].add(doi)
        if oa:
            index["openalex_id"].add(oa)
        if r.get("handle"):
            index["handle"].add(r["handle"])
        if ty:
            index["title"][ty].append(r)
        if normalize_title(r["title"]):
            index["title_any_year"].add(normalize_title(r["title"]))
    return index


def delivery_counts(did, idx, rows, roots, comp, cat_index):
    """Contract merge-report counts of one delivery.

    A delivery's works are the pool works its rows land in, so the counts
    always add up with the pool; ``dup_within_delivery`` counts rows that land
    in the same work as another row of the delivery. Each work is placed with
    a catalogue row (named by the first direct match method of the delivery's
    rows, cascade order, ``by_title_only`` for a ``no_dedup_key`` row joined on
    the catalogue row's title; ``via_other_lane`` when only another lane's
    record bridges them), with another delivery only, or alone (``new_to_pool``).
    """
    drows = [rows[i] for i in idx if not rows[i].get("title_only")]
    title_only = [i for i in idx if rows[i].get("title_only")]
    works = defaultdict(list)
    for i in idx:
        works[roots[i]].append(i)
    in_cat = Counter({"by_doi": 0, "by_openalex_id": 0, "by_handle": 0, "by_title_year": 0,
                      "by_title_only": 0, "via_other_lane": 0})
    other_lane_only = new = 0
    for root, members in works.items():
        full = comp[root]
        if any(rows[j]["origin"] == CATALOGUE for j in full):
            method = next((m for m in (_direct_catalogue_method(rows[i], cat_index)
                                       for i in members) if m), "via_other_lane")
            in_cat[method] += 1
        elif any(rows[j]["delivery"] != did for j in full):
            other_lane_only += 1
        else:
            new += 1
    return {
        "records": len(drows),
        "with_doi": sum(bool(r["doi"]) for r in drows),
        "doi_malformed": sum(bool(r["doi"]) and not DOI.match(r["doi"]) for r in drows),
        "with_openalex_id": sum(bool(r["openalex_id"]) for r in drows),
        "with_handle": sum(bool(r.get("handle")) for r in drows),
        "title_year_only": sum(not r["doi"] and not r["openalex_id"] and not r.get("handle")
                               for r in drows),
        "title_only_from_excluded": len(title_only),
        "title_only_joined": sum(len(comp[roots[i]]) > 1 and any(
            not rows[j].get("title_only") for j in comp[roots[i]]) for i in title_only),
        "dup_within_delivery": len(idx) - len(works),
        "works": len(works),
        "in_catalogue": {"total": sum(in_cat.values()), **dict(in_cat)},
        "in_other_lane_only": other_lane_only,
        "new_to_pool": new,
    }


def make_report(rows, roots, deliveries, excluded, catalogue_meta, superseded, stats=None):
    """Assemble merge_report.json; raise if the reconciliation does not add up."""
    comp = defaultdict(list)
    for i, root in enumerate(roots):
        comp[root].append(i)
    cat_index = _catalogue_index(rows)
    by_delivery = defaultdict(list)
    for i, r in enumerate(rows):
        if r["origin"] != CATALOGUE:
            by_delivery[r["delivery"]].append(i)

    per = {}
    for did, _, manifest in deliveries:
        counts = delivery_counts(did, by_delivery.get(did, []), rows, roots, comp, cat_index)
        per[did] = {"lane": did.split("/")[0], "coverage": manifest.get("coverage"),
                    "records": counts.pop("records"), "excluded": excluded[did],
                    **counts, "already_screened": None}

    n_cat_rows = sum(r["origin"] == CATALOGUE for r in rows)
    comps_with_cat = [c for c in comp.values() if any(rows[j]["origin"] == CATALOGUE for j in c)]
    lane_only = [c for c in comp.values() if not any(rows[j]["origin"] == CATALOGUE for j in c)]
    multi_delivery_lane_only = sum(len({rows[j]["delivery"] for j in c}) > 1 for c in lane_only)
    n_sources = Counter(len({rows[j]["origin"] for j in c}) for c in comp.values())
    conflicting = sum(len({rows[j]["doi"] for j in c if rows[j]["doi"]}) > 1 for c in comp.values())

    recon = {
        "pool_works": len(comp),
        "catalogue_rows": n_cat_rows,
        "catalogue_works": len(comps_with_cat),
        "catalogue_rows_joined": n_cat_rows - len(comps_with_cat),
        "lane_only_works": len(lane_only),
        "lane_only_works_single_delivery": len(lane_only) - multi_delivery_lane_only,
        "lane_only_works_several_deliveries": multi_delivery_lane_only,
        "works_with_several_dois": conflicting,
        "ambiguous_title_groups": (stats or {}).get("ambiguous_title_groups"),
        "ambiguous_title_only": (stats or {}).get("ambiguous_title_only"),
        "generic_title_only": (stats or {}).get("generic_title_only"),
        "catalogue_doi_malformed": sum(r["origin"] == CATALOGUE and bool(r["doi"])
                                       and not DOI.match(r["doi"]) for r in rows),
    }
    checks = {
        "pool = catalogue works + lane-only works":
            recon["pool_works"] == recon["catalogue_works"] + recon["lane_only_works"],
        "sum of new_to_pool = lane-only works from a single delivery":
            sum(p["new_to_pool"] for p in per.values()) == recon["lane_only_works_single_delivery"],
        "works per n_sources sum to the pool": sum(n_sources.values()) == recon["pool_works"],
    }
    for did, p in per.items():
        checks[f"{did}: records + title_only_from_excluded - dup_within_delivery = works"] = (
            p["records"] + p["title_only_from_excluded"] - p["dup_within_delivery"] == p["works"])
        checks[f"{did}: works = in_catalogue + in_other_lane_only + new_to_pool"] = (
            p["works"] == p["in_catalogue"]["total"] + p["in_other_lane_only"] + p["new_to_pool"])
    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        raise RelPoolError("merge report does not reconcile: " + "; ".join(failed))
    recon["checks"] = {k: "ok" for k in checks}

    return {
        "catalogue": catalogue_meta,
        "deliveries": per,
        "superseded_deliveries": superseded,
        "pool": {
            "works": len(comp),
            "in_catalogue": len(comps_with_cat),
            "lane_only": len(lane_only),
            "works_per_n_sources": {str(k): n_sources[k] for k in sorted(n_sources)},
            "still_to_screen": None,
        },
        "reconciliation": recon,
        "notes": ("Per-delivery counts are per source, before cross-source deduplication: a "
                  "work two lanes found counts in both. "
                  "in_catalogue.by_title_only: a no_dedup_key row joined a catalogue work on "
                  "its title alone (any year). "
                  "in_catalogue.via_other_lane: the delivery's work joins a catalogue work only "
                  "through another lane's record. already_screened and still_to_screen wait for "
                  "the icf_screen table (ticket 1732)."),
    }


def report_markdown(report):
    head = ["delivery", "records", "excluded", "title_only_from_excluded", "with_doi", "doi_malformed", "with_openalex_id",
            "title_year_only", "dup_within_delivery", "in_catalogue (doi/oa/handle/title/title-only/via lane)",
            "in_other_lane_only", "new_to_pool"]
    lines = ["# REL pool merge report", "",
             f"Catalogue: `{report['catalogue']['path']}`, md5 `{report['catalogue']['md5']}`, "
             f"{report['catalogue']['rows']} rows.", "",
             "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for did, p in report["deliveries"].items():
        c = p["in_catalogue"]
        exc = ", ".join(f"{k} {v}" for k, v in p["excluded"].items()) or "0"
        lines.append("| " + " | ".join(map(str, [
            did, p["records"], exc, p["title_only_from_excluded"], p["with_doi"], p["doi_malformed"], p["with_openalex_id"], p["title_year_only"],
            p["dup_within_delivery"],
            f"{c['total']} ({c['by_doi']}/{c['by_openalex_id']}/{c['by_handle']}/{c['by_title_year']}/"
            f"{c['by_title_only']}/{c['via_other_lane']})",
            p["in_other_lane_only"], p["new_to_pool"]])) + " |")
    pool = report["pool"]
    lines += ["", f"Pool: {pool['works']} works ({pool['in_catalogue']} with a catalogue row, "
              f"{pool['lane_only']} from lanes only).",
              "Works per number of sources: "
              + ", ".join(f"{k}: {v}" for k, v in pool["works_per_n_sources"].items()) + ".", ""]
    return "\n".join(lines)
