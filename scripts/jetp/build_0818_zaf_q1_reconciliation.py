"""Reconcile the bounded ZAF Q1-2026 register into reviewable candidates.

This is deliberately a source-layer extraction.  The JET PMU register's
``Date of Financing Agreement Signed*`` label is retained verbatim but is not
promoted to an event, signature, or payment in the comparative account.
"""

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from jetp.build_zaf_investment_register import (
    _project_id,
    _text,
    excluded_register_rows,
    parse_register_html,
)

# The 21 field names the dashboard's embedded ``Overall - Data`` array ships,
# verbatim and in source order.  They are appended to the derived columns so
# the extraction carries the whole register row, never a selection of it.
SOURCE_FIELDS = (
    "Unique ID",
    "Project Name",
    "Portfolios",
    "Purpose",
    "Priority Areas",
    "Funder/Source",
    "Funding Instrument",
    "Disbursement Channel",
    "Co-Financing: Name",
    "Currency: Pledged",
    "Amount: Pledged",
    "Total US$",
    "Total ZAR",
    "Funding Partners",
    "Implementing Entity",
    "Institutional / South African Partner",
    "Beneficiary",
    "Status",
    "Project Description",
    "Date of Financing Agreement Signed*",
    "End Date",
)

FIELDS = (
    "ordinal",
    "project_id",
    "official_unique_id",
    "project_name",
    "portfolios",
    "funding_partners",
    "funding_instrument",
    "amount_pledged_original",
    "currency_pledged",
    "amount_reported_usd",
    "amount_reported_zar",
    "implementation_status",
    "register_financing_agreement_label",
    "source_id",
    "document_sha256",
    "locator",
    "disposition",
    "date_role",
    "transition_date",
    "payment_amount",
    "eligible_for_account",
)

# The sidecar table's columns: the join key, then the 21 source labels verbatim.
# The register's own fields ride in a second file and not in ``FIELDS`` because
# the derived table is a content-hashed input of the 0822 comparative freeze;
# widening it would mutate a frozen artifact.
FIELD_TABLE_FIELDS = ("ordinal",) + SOURCE_FIELDS


def _register_source(policy: dict) -> dict:
    matches = [item for item in policy["sources"] if item["role"] == "register"]
    if len(matches) != 1:
        raise ValueError("policy must identify exactly one register source")
    return matches[0]


def _register(document: Path, policy: dict) -> tuple[dict, str, list[dict]]:
    """Return the pinned register source, its hash and its material rows."""
    source = _register_source(policy)
    actual_hash = hashlib.sha256(document.read_bytes()).hexdigest()
    if actual_hash != source["document_sha256"]:
        raise ValueError("unexpected register source bytes")
    register = parse_register_html(document.read_text(encoding="utf-8"))
    if len(register) != policy["register_row_count"]:
        raise ValueError("incomplete selected register inventory")
    return source, actual_hash, register


def build_rows(document: Path, policy: dict) -> list[dict[str, str]]:
    """Return one unadmitted source candidate per material official row."""
    source, actual_hash, register = _register(document, policy)

    return [
        {
            "ordinal": str(ordinal),
            "project_id": _project_id(_text(row["Unique ID"])),
            "official_unique_id": _text(row["Unique ID"]),
            "project_name": _text(row.get("Project Name")),
            "portfolios": _text(row.get("Portfolios")),
            "funding_partners": _text(row.get("Funding Partners")) or _text(row.get("Funder/Source")),
            "funding_instrument": _text(row.get("Funding Instrument")),
            "amount_pledged_original": _text(row.get("Amount: Pledged")),
            "currency_pledged": _text(row.get("Currency: Pledged")),
            "amount_reported_usd": _text(row.get("Total US$")),
            "amount_reported_zar": _text(row.get("Total ZAR")),
            "implementation_status": _text(row.get("Status")),
            "register_financing_agreement_label": _text(row.get("Date of Financing Agreement Signed*")),
            "source_id": source["source_id"],
            "document_sha256": actual_hash,
            "locator": f"Overall - Data, Unique ID {_text(row['Unique ID'])}",
            "disposition": "unadmitted_candidate",
            "date_role": "register_date_label_retained_not_transition",
            "transition_date": "",
            "payment_amount": "",
            "eligible_for_account": "false",
        }
        for ordinal, row in enumerate(register, 1)
    ]


def build_field_rows(document: Path, policy: dict) -> list[dict[str, str]]:
    """Return the whole source row per material register row, under its own labels.

    Same rows, same order and the same ``ordinal`` key as :func:`build_rows`, so
    the two tables join 1:1.  Values get the ``_text`` treatment the derived
    columns get and nothing more: absence stays empty, nothing is converted,
    summed or promoted.  ``Unique ID`` stays a string here as everywhere else —
    the one raw entry whose identifier is an ``int`` is excluded upstream and
    documented in the report, never coerced into this table.
    """
    _source, _actual_hash, register = _register(document, policy)
    return [
        {"ordinal": str(ordinal), **{key: _text(row.get(key)) for key in SOURCE_FIELDS}}
        for ordinal, row in enumerate(register, 1)
    ]


def _excluded_section(rows: list[dict[str, str]], excluded: list[dict]) -> list[str]:
    """Name each raw entry the material-row predicate drops, and say why.

    The reason is a Python type, not a value, so the type is spelled out: an
    ``int`` identifier is the dashboard's own aggregate line, never a project.
    """
    lines = [
        "",
        "## Excluded rows",
        "",
        f"The embedded `Overall - Data` array carries {len(rows) + len(excluded)} raw entries.  {len(rows)} are material register rows; the {'entry' if len(excluded) == 1 else 'entries'} below {'is' if len(excluded) == 1 else 'are'} not.  Exclusion is decided by the source types alone, before any string conversion.",
        "",
    ]
    for entry in excluded:
        unique_id = entry["unique_id_raw"]
        lines.append(
            f"- `Unique ID` = `{unique_id}` at ordinal {entry['ordinal']} "
            f"(raw index {entry['raw_index']}): excluded because that value is a "
            f"Python `{type(unique_id).__name__}`, not a `str` — the dashboard's own "
            f"aggregate line, whose `Project Name` is "
            f"`{entry['project_name_raw']}` and whose `Portfolios` is "
            f"`{entry['portfolios_raw']}`.  It reports `Total US$` "
            f"`{entry['amount_reported_usd_raw']}` and `Total ZAR` "
            f"`{entry['amount_reported_zar_raw']}`; these totals are the register's "
            "own, are not recomputed here, and are not admitted to any account."
        )
    return lines


def _report(rows: list[dict[str, str]], excluded: list[dict], policy: dict) -> str:
    statuses = Counter(row["implementation_status"] or "blank" for row in rows)
    source = _register_source(policy)
    lines = [
        "# 0818 — ZAF Q1-2026 register reconciliation",
        "",
        "## Result",
        "",
        f"The retained `{source['edition_id']}` snapshot yields **{len(rows)}** material register rows, exactly the manifest target.  Every row is retained as an unadmitted source candidate; none is admitted to an account or used as payment, signature, or transition evidence.",
        "",
        "## Evidence and boundary",
        "",
        f"- Source: `{source['source_id']}`; SHA-256 `{source['document_sha256']}`.",
        "- Locator: `Overall - Data, Unique ID <official id>` for each row.",
        "- The Q1 edition and the field labelled `Date of Financing Agreement Signed*` are retained source wording. They do not establish an independently verified event date.",
        "- `Amount: Pledged`, currencies, reported USD/ZAR, funder, instrument and implementation status are source positions; they are not summed across perimeters and are not payments.",
        "",
        "## Dispositions",
        "",
        f"- `unadmitted_candidate`: {len(rows)}",
        "- duplicate / excluded / unavailable / lost_visibility: 0 within this retained table; those dispositions belong to the country census outside this bounded extraction.",
        "",
        "## Register implementation labels",
        "",
    ]
    lines.extend(f"- `{label}`: {count}" for label, count in sorted(statuses.items()))
    lines.extend(_excluded_section(rows, excluded))
    lines.extend([
        "",
        "## Handoff",
        "",
        "The reconciled CSV is a replayable source-layer input for 0822. A later review may link candidates to operations only with explicit evidence; it must preserve this table's identifiers and must not infer payments or causality from register status.",
        "",
        "The 21 register fields are carried verbatim in the sidecar table `0818-zaf-q1-2026-fields.csv`, one row per candidate and keyed by the same `ordinal`. It is a second file, not a widening of the reconciled CSV, because that CSV is a content-hashed input of the 0822 comparative freeze.",
        "",
    ])
    return "\n".join(lines)


def write_outputs(
    rows: list[dict[str, str]],
    output: Path,
    report: Path,
    policy: dict,
    excluded: list[dict] | None = None,
) -> None:
    """Write a deterministic candidate table and concise reconciliation report."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(_report(rows, excluded or [], policy), encoding="utf-8")


def write_field_table(field_rows: list[dict[str, str]], output: Path) -> None:
    """Write the sidecar table of raw register fields, keyed by ``ordinal``."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELD_TABLE_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(field_rows)


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=root / "docs/jetp-study/0818-zaf-q1-2026-rows.csv")
    parser.add_argument("--report", type=Path, default=root / "docs/jetp-study/0818-zaf-q1-2026-report.md")
    parser.add_argument("--fields", type=Path, default=root / "docs/jetp-study/0818-zaf-q1-2026-fields.csv")
    args = parser.parse_args()
    policy = json.loads((root / "config/jetp-zaf-migration.json").read_text(encoding="utf-8"))
    source = _register_source(policy)
    document = root / "data/jetp/documents" / source["storage_path"]
    rows = build_rows(document, policy)
    excluded = excluded_register_rows(document.read_text(encoding="utf-8"))
    write_outputs(rows, args.output, args.report, policy, excluded)
    write_field_table(build_field_rows(document, policy), args.fields)


if __name__ == "__main__":
    main()
