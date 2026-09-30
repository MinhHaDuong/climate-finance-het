"""Check one REL lane delivery against the intake contract (ticket 1730).

The contract is ``docs/rel-intake-contract.md``. A delivery is a directory
holding ``records.csv``, ``registry.csv``, ``excluded.csv`` and
``manifest.json``. Every violation is reported, not only the first, so a lane
fixes its delivery in one pass. Standard library only, so a lane can run it
from any checkout.

Usage:
    python scripts/qa_rel_intake.py data/rel_intake/<lane>/<delivery>

Exit 0 when the delivery meets the contract, 1 otherwise.
"""

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter

RECORD_COLUMNS = [
    "record_id", "query_id", "platform", "retrieved_at", "title",
    "platform_record_id", "doi", "openalex_id", "title_original",
    "first_author", "all_authors", "year", "publication_date", "journal",
    "issn", "doc_type", "language", "abstract", "abstract_provenance", "url",
    "affiliation_countries", "version_hint", "lane_status", "lane_note",
]
RECORD_REQUIRED = ["record_id", "query_id", "platform", "retrieved_at", "title"]

REGISTRY_REQUIRED = ["query_id", "platform", "query", "run_at", "n_received",
                     "completed"]
EXCLUDED_COLUMNS = ["record_id", "query_id", "reason", "title", "note"]
EXCLUSION_REASONS = {"duplicate_in_lane", "front_matter", "not_retrievable"}

MANIFEST_KEYS = ["lane", "ticket", "delivery", "delivered_at", "producer",
                 "counts", "coverage", "incomplete", "needs_human"]
COVERAGE_VALUES = {"complete", "incomplete"}

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ][0-9:.]+(Z|[+-]\d{2}:?\d{2})?)?$")
DOI = re.compile(r"^10\.\d{4,9}/\S+$")
OPENALEX_ID = re.compile(r"^W\d+$")
YEAR = re.compile(r"^\d{4}$")
LANE = re.compile(r"^t\d{4}-[a-z0-9][a-z0-9-]*$")
DELIVERY = re.compile(r"^\d{4}-\d{2}-\d{2}[a-z]?$")

FILES = ["records.csv", "registry.csv", "excluded.csv", "manifest.json"]


def _read_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        rows = list(reader)
    return header, rows


def _missing_columns(header, wanted, name):
    missing = [c for c in wanted if c not in header]
    return [f"{name}: missing column(s) {', '.join(missing)}"] if missing else []


def check_records(header, rows, query_ids):
    """Return the violations of records.csv."""
    errors = _missing_columns(header, RECORD_COLUMNS, "records.csv")
    if errors:
        return errors
    seen = Counter(r["record_id"] for r in rows)
    for rid, n in seen.items():
        if rid and n > 1:
            errors.append(f"records.csv: record_id {rid!r} appears {n} times")
    for i, r in enumerate(rows, start=2):
        where = f"records.csv line {i}"
        for col in RECORD_REQUIRED:
            if not (r.get(col) or "").strip():
                errors.append(f"{where}: {col} is empty")
        if r["query_id"] and r["query_id"] not in query_ids:
            errors.append(f"{where}: query_id {r['query_id']!r} not in registry.csv")
        if r["retrieved_at"] and not ISO_DATE.match(r["retrieved_at"]):
            errors.append(f"{where}: retrieved_at {r['retrieved_at']!r} is not ISO 8601")
        if r["doi"] and not DOI.match(r["doi"]):
            errors.append(f"{where}: doi {r['doi']!r} is not a bare 10.xxxx/... DOI")
        if r["openalex_id"] and not OPENALEX_ID.match(r["openalex_id"]):
            errors.append(f"{where}: openalex_id {r['openalex_id']!r} is not W + digits")
        if r["year"] and not YEAR.match(r["year"]):
            errors.append(f"{where}: year {r['year']!r} is not four digits")
        if not (r["doi"] or r["openalex_id"] or r["year"]):
            errors.append(f"{where}: needs at least one of doi, openalex_id, year")
    return errors


def check_registry(header, rows):
    """Return the violations of registry.csv and the set of its query ids."""
    errors = _missing_columns(header, REGISTRY_REQUIRED, "registry.csv")
    if errors:
        return errors, set()
    ids = Counter(r["query_id"] for r in rows)
    for qid, n in ids.items():
        if n > 1:
            errors.append(f"registry.csv: query_id {qid!r} appears {n} times")
    for i, r in enumerate(rows, start=2):
        where = f"registry.csv line {i}"
        for col in REGISTRY_REQUIRED:
            if not (r.get(col) or "").strip():
                errors.append(f"{where}: {col} is empty")
        completed = (r.get("completed") or "").strip().lower()
        if completed and completed not in {"true", "false"}:
            errors.append(f"{where}: completed {r['completed']!r} is not true/false")
        if completed == "false" and not (r.get("stop_reason") or "").strip():
            errors.append(f"{where}: incomplete query needs a stop_reason")
        if (r.get("n_received") or "").strip() and not r["n_received"].strip().isdigit():
            errors.append(f"{where}: n_received {r['n_received']!r} is not a count")
    return errors, set(ids)


def check_excluded(header, rows, query_ids, record_ids):
    """Return the violations of excluded.csv."""
    errors = _missing_columns(header, EXCLUDED_COLUMNS, "excluded.csv")
    if errors:
        return errors
    for i, r in enumerate(rows, start=2):
        where = f"excluded.csv line {i}"
        if r["reason"] not in EXCLUSION_REASONS:
            errors.append(
                f"{where}: reason {r['reason']!r} is not one of "
                f"{', '.join(sorted(EXCLUSION_REASONS))} (relevance is never a reason)")
        if r["query_id"] and r["query_id"] not in query_ids:
            errors.append(f"{where}: query_id {r['query_id']!r} not in registry.csv")
        if (r["reason"] != "duplicate_in_lane" and r["record_id"]
                and r["record_id"] in record_ids):
            errors.append(f"{where}: record_id {r['record_id']!r} is also delivered")
    return errors


def _check_identity(manifest, delivery_dir):
    """Lane and delivery must be well formed and match the directory path."""
    errors = []
    lane_dir = os.path.basename(os.path.dirname(os.path.abspath(delivery_dir)))
    delivery = os.path.basename(os.path.abspath(delivery_dir))
    if not LANE.match(str(manifest["lane"])):
        errors.append(f"manifest.json: lane {manifest['lane']!r} is not t<ticket>-<slug>")
    elif manifest["lane"] != lane_dir:
        errors.append(f"manifest.json: lane {manifest['lane']!r} differs from directory {lane_dir!r}")
    if not DELIVERY.match(str(manifest["delivery"])):
        errors.append(f"manifest.json: delivery {manifest['delivery']!r} is not YYYY-MM-DD[suffix]")
    elif manifest["delivery"] != delivery:
        errors.append(f"manifest.json: delivery {manifest['delivery']!r} differs from directory {delivery!r}")
    if not ISO_DATE.match(str(manifest["delivered_at"])):
        errors.append("manifest.json: delivered_at is not ISO 8601")
    producer = manifest["producer"]
    if not isinstance(producer, dict) or not all(
            str(producer.get(k) or "").strip() for k in ("script", "commit", "machine")):
        errors.append("manifest.json: producer needs script, commit and machine")
    return errors


def _check_counts(manifest, n_records, excluded_counts):
    """Declared counts must equal the rows actually delivered and excluded."""
    errors = []
    counts = manifest["counts"] if isinstance(manifest["counts"], dict) else {}
    if counts.get("records") != n_records:
        errors.append(
            f"manifest.json: counts.records is {counts.get('records')!r}, "
            f"records.csv has {n_records} rows")
    declared = {k: v for k, v in (counts.get("excluded") or {}).items() if v}
    if declared != dict(excluded_counts):
        errors.append(
            f"manifest.json: counts.excluded {declared} differs from "
            f"excluded.csv {dict(excluded_counts)}")
    return errors


def _check_coverage(manifest):
    """Coverage and the incomplete list must agree; each unit carries a reason."""
    errors = []
    if manifest["coverage"] not in COVERAGE_VALUES:
        errors.append(f"manifest.json: coverage {manifest['coverage']!r} is not complete/incomplete")
    incomplete = manifest["incomplete"]
    if not isinstance(incomplete, list):
        return errors + ["manifest.json: incomplete must be a list"]
    if manifest["coverage"] == "incomplete" and not incomplete:
        errors.append("manifest.json: coverage incomplete but nothing listed in incomplete")
    if manifest["coverage"] == "complete" and incomplete:
        errors.append("manifest.json: coverage complete but incomplete lists units")
    for item in incomplete:
        if not (isinstance(item, dict) and item.get("unit") and item.get("reason")):
            errors.append("manifest.json: each incomplete item needs unit and reason")
    return errors


def _check_needs_human(manifest):
    needs_human = manifest["needs_human"]
    if not isinstance(needs_human, list) or not all(
            isinstance(x, dict) and x.get("item") and x.get("reason") for x in needs_human):
        return ["manifest.json: needs_human must list {item, reason} objects"]
    return []


def check_manifest(manifest, delivery_dir, n_records, excluded_counts):
    """Return the violations of manifest.json."""
    errors = [f"manifest.json: missing key {k!r}" for k in MANIFEST_KEYS
              if k not in manifest]
    if errors:
        return errors
    return (_check_identity(manifest, delivery_dir)
            + _check_counts(manifest, n_records, excluded_counts)
            + _check_coverage(manifest)
            + _check_needs_human(manifest))


def check_delivery(delivery_dir):
    """Return every contract violation of the delivery at ``delivery_dir``."""
    missing = [f for f in FILES if not os.path.isfile(os.path.join(delivery_dir, f))]
    if missing:
        return [f"missing file(s): {', '.join(missing)}"]
    errors = []
    reg_header, reg_rows = _read_csv(os.path.join(delivery_dir, "registry.csv"))
    reg_errors, query_ids = check_registry(reg_header, reg_rows)
    errors += reg_errors
    rec_header, rec_rows = _read_csv(os.path.join(delivery_dir, "records.csv"))
    errors += check_records(rec_header, rec_rows, query_ids)
    exc_header, exc_rows = _read_csv(os.path.join(delivery_dir, "excluded.csv"))
    record_ids = {r.get("record_id") for r in rec_rows}
    errors += check_excluded(exc_header, exc_rows, query_ids, record_ids)
    try:
        with open(os.path.join(delivery_dir, "manifest.json"), encoding="utf-8") as fh:
            manifest = json.load(fh)
    except json.JSONDecodeError as exc:
        return errors + [f"manifest.json: not valid JSON ({exc})"]
    if not isinstance(manifest, dict):
        return errors + ["manifest.json: top level must be an object"]
    excluded_counts = Counter(r.get("reason") for r in exc_rows)
    errors += check_manifest(manifest, delivery_dir, len(rec_rows), excluded_counts)
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("delivery", help="data/rel_intake/<lane>/<delivery>")
    args = parser.parse_args(argv)
    if not os.path.isdir(args.delivery):
        print(f"FAIL {args.delivery}: not a directory")
        return 1
    errors = check_delivery(args.delivery)
    if errors:
        for e in errors:
            print(e)
        print(f"FAIL {args.delivery}: {len(errors)} violation(s)")
        return 1
    print(f"OK {args.delivery}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
