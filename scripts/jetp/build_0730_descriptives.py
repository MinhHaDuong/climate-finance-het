"""Build descriptive handoff tables from the frozen 0822 comparative snapshot.

This is deliberately a *descriptive* layer.  Atomic source assertions remain
atomic; the small reconciliation layer is reported separately; no currency
conversion, source-amount pooling, event inference, or causal comparison is
performed here.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


SNAPSHOT = Path("docs/jetp-study/0822-comparative-snapshot.json.gz")
SNAPSHOT_MANIFEST = Path("docs/jetp-study/0822-comparative-snapshot-manifest.json")
SCHEMA_VERSION = "jetp-0730-descriptives/1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load only the frozen archive and verify it against its 0822 manifest."""
    archive = root / SNAPSHOT
    manifest_path = root / SNAPSHOT_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    snapshot = json.loads(gzip.decompress(archive.read_bytes()))
    # 0822 pins the canonical JSON content signature (not gzip container bytes).
    actual = snapshot.get("snapshot_sha256")
    if actual != manifest["snapshot_sha256"]:
        raise ValueError("0822 snapshot hash does not match its frozen manifest")
    return snapshot, manifest


def _function_label(row: dict[str, Any]) -> str | None:
    fields = row["source_fields"]
    # These are source-provided labels, intentionally not an analyst taxonomy.
    return fields.get("portfolios") or fields.get("technology_group") or None


def _instrument_label(row: dict[str, Any]) -> str | None:
    fields = row["source_fields"]
    return fields.get("funding_instrument") or fields.get("instrument") or None


def _ownership_evidence(row: dict[str, Any]) -> str:
    """Classify only literal public/private/mixed wording in the frozen source row.

    A financier name alone is not ownership evidence in this snapshot.  This
    intentionally leaves nearly all observations uncoded rather than deriving
    ownership from institutional reputation or an external lookup.
    """
    fields = row["source_fields"]
    wording = " ".join(
        str(fields.get(key, "")) for key in ("funder", "instrument")
    ).lower()
    has_public = "publique" in wording or "(public)" in wording
    has_private = "privée" in wording or "(privé)" in wording
    if has_public and has_private:
        return "source_stated_mixed_unallocated"
    if has_public:
        return "source_stated_public"
    if has_private:
        return "source_stated_private"
    return "not_documented"


def _counter_rows(counter: Counter[str], *, label: str, denominator: int) -> list[dict[str, Any]]:
    return [
        {
            label: value,
            "observations": count,
            "denominator": denominator,
            "share_of_documented_observations": round(count / denominator, 6)
            if denominator
            else None,
        }
        for value, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def build_analysis(root: Path) -> dict[str, Any]:
    """Return pinned, non-additive descriptive statistics for 0730."""
    snapshot, manifest = _snapshot(root)
    atomic = snapshot["atomic_observations"]
    events = snapshot["event_journal"]
    positions = snapshot["position_journal"]
    coverage = [row for row in atomic if row["journal"] == "coverage"]

    reconciled_ids = {
        source_id
        for reconciliation in snapshot["reconciliations"]
        for source_id in reconciliation["input_candidate_ids"]
    }
    country_rows: dict[str, dict[str, Any]] = {}
    for country in ("ZAF", "IDN", "VNM", "SEN"):
        rows = [row for row in atomic if row["country"] == country]
        country_rows[country] = {
            "atomic_observations": len(rows),
            "event_assertions": sum(row["journal"] == "events" for row in rows),
            "position_assertions": sum(row["journal"] == "positions" for row in rows),
            "coverage_assertions": sum(row["journal"] == "coverage" for row in rows),
            "source_function_labels": sum(_function_label(row) is not None for row in rows),
            "source_finance_instrument_labels": sum(_instrument_label(row) is not None for row in rows),
            "source_reported_money_positions": sum(
                row["financial_bound_type"] != "unknown" for row in rows
            ),
            "reconciled_atomic_observations": sum(
                row["source_candidate_id"] in reconciled_ids for row in rows
            ),
            "unreconciled_atomic_observations": sum(
                row["source_candidate_id"] not in reconciled_ids for row in rows
            ),
        }

    function_rows = [row for row in atomic if _function_label(row) is not None]
    finance_rows = [row for row in atomic if _instrument_label(row) is not None]
    function_labels = Counter(_function_label(row) for row in function_rows)
    instruments = Counter(_instrument_label(row) for row in finance_rows)
    ownership = Counter(_ownership_evidence(row) for row in finance_rows)

    # A join requires all three explicitly coded dimensions in one frozen atomic
    # assertion.  None qualifies: do not link labels across documents by name.
    common_rows = [
        row
        for row in atomic
        if _function_label(row) is not None
        and _instrument_label(row) is not None
        and row["journal"] == "events"
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "snapshot_path": str(SNAPSHOT),
            "snapshot_sha256": manifest["snapshot_sha256"],
            "snapshot_schema_version": snapshot["schema_version"],
            "snapshot_input_git_sha": snapshot["input_git_sha"],
            "method": "Frozen 0822 atomic journals plus named reconciliations; no external acquisition.",
        },
        "denominators": {
            "atomic_observations": len(atomic),
            "event_journal": len(events),
            "position_journal": len(positions),
            "document_coverage": len(coverage),
            "reconciled_atomic_observations": sum(
                row["source_candidate_id"] in reconciled_ids for row in atomic
            ),
            "unreconciled_atomic_observations": sum(
                row["source_candidate_id"] not in reconciled_ids for row in atomic
            ),
        },
        "countries": country_rows,
        "money": {
            "source_reported_positions": sum(
                row["financial_bound_type"] != "unknown" for row in atomic
            ),
            "unknown_money_observations": sum(
                row["financial_bound_type"] == "unknown" for row in atomic
            ),
            "currency_counts": _counter_rows(
                Counter(
                    row["currency"]
                    for row in atomic
                    if row["financial_bound_type"] != "unknown"
                ),
                label="currency",
                denominator=sum(row["financial_bound_type"] != "unknown" for row in atomic),
            ),
            "pooled_total": "not_computable",
            "note": "Amounts are source positions in multiple currencies and may overlap; no cross-source or cross-country sum is valid.",
        },
        "dimensions": {
            "function": {
                "documented_observations": len(function_rows),
                "unknown_or_uncoded_observations": len(atomic) - len(function_rows),
                "source_label_counts": _counter_rows(
                    function_labels, label="source_label", denominator=len(function_rows)
                ),
                "note": "Portfolio and technology labels are retained as source labels, not harmonised just-transition functions.",
            },
            "finance": {
                "documented_observations": len(finance_rows),
                "unknown_or_uncoded_observations": len(atomic) - len(finance_rows),
                "instrument_counts": _counter_rows(
                    instruments, label="instrument", denominator=len(finance_rows)
                ),
                "ownership_evidence_counts": _counter_rows(
                    ownership, label="ownership_evidence", denominator=len(finance_rows)
                ),
                "note": "Ownership is only source-stated wording; a funder name is not recoded into public or private ownership.",
            },
            "history": {
                "documented_observations": len(events),
                "unknown_or_uncoded_observations": len(atomic) - len(events),
                "event_date_precision": _counter_rows(
                    Counter(
                        "point_date"
                        if row["date_lower"] == row["date_upper"] and len(row["date_lower"] or "") >= 10
                        else "bounded_or_year_only"
                        if row["date_lower"]
                        else "unknown"
                        for row in events
                    ),
                    label="date_precision",
                    denominator=len(events),
                ),
                "note": "Events are reported assertions pending independent operation identity; dates are not transition clocks.",
            },
            "common_explicit_unit_observations": len(common_rows),
            "common_explicit_unit_note": "No atomic assertion contains all three frozen, explicitly coded dimensions; this is a coverage result, not evidence of absence in JETPs.",
        },
        "history": {
            "event_assertions": len(events),
            "point_dated_event_assertions": sum(
                row["date_lower"] == row["date_upper"] and len(row["date_lower"] or "") >= 10
                for row in events
            ),
            "transition_duration": "not_computable",
            "note": "No operation has comparable, evidenced pre/post transition endpoints in this frozen snapshot.",
        },
        "reconciliations": {
            "named_records": len(snapshot["reconciliations"]),
            "status_counts": _counter_rows(
                Counter(row["status"] for row in snapshot["reconciliations"]),
                label="status",
                denominator=len(snapshot["reconciliations"]),
            ),
            "note": "Reconciliations identify compatibility or conflict; they do not pool monetary amounts unless their rule explicitly permits it. None does here.",
        },
        "result_candidates": [
            {
                "candidate_id": "coverage-asymmetry",
                "claim": "The frozen corpus supports distinct descriptive panels, not a common operation-level A/B/C panel.",
                "result": "null_common_sample",
                "evidence": "1,399 source function labels, 303 source instrument labels, and 7 event assertions; 0 atomic assertions contain all three dimensions.",
                "scope": "Atomic assertions, not operations or JETP portfolios.",
            },
            {
                "candidate_id": "zaf-reported-lifecycle",
                "claim": "South African register positions expose reported implementation-status coverage without establishing transition timing or payment.",
                "result": "reported_lifecycle_labels_only",
                "evidence": "257 source-register positions with an implementation-status field; all retain a non-transition register date label.",
                "scope": "ZAF source-register candidates only.",
            },
            {
                "candidate_id": "vnm-finance-history-pedigree",
                "claim": "Vietnam provides the only event assertions, alongside explicit financial conflicts that cannot be pooled.",
                "result": "mixed_and_nonadditive",
                "evidence": "7 event assertions; 4 named reconciliations, all incompatible or unavailable; 15 atomic inputs are named by reconciliation records.",
                "scope": "VNM staged observations and their named reconciliations; not a national finance total.",
            },
        ],
        "limitations": [
            "No causal acceleration, additionality, payment, social outcome, or absence claim is identified.",
            "Unknown values and unresolved identities remain in denominators rather than becoming zero or exclusions.",
            "Country coverage is structurally uneven; cross-country count comparisons are documentary coverage comparisons.",
        ],
    }


def build_manifest(root: Path, analysis: dict[str, Any]) -> dict[str, Any]:
    """Describe an exact 0730 run without claiming a new canonical fact store."""
    return {
        "schema_version": "jetp-0730-run-manifest/1",
        "input_snapshot": str(SNAPSHOT),
        "input_snapshot_sha256": analysis["source"]["snapshot_sha256"],
        "input_snapshot_manifest": str(SNAPSHOT_MANIFEST),
        "output_schema_version": SCHEMA_VERSION,
        "reproduction": "python3 scripts/jetp/build_0730_descriptives.py --root .",
        "scope": "Descriptive analysis of frozen 0822 source assertions and reconciliations only; no acquisition or currency conversion.",
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0]) if rows else ["no_rows"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _report(analysis: dict[str, Any]) -> str:
    """A compact human-readable companion to the machine-readable handoff."""
    den = analysis["denominators"]
    dim = analysis["dimensions"]
    countries = analysis["countries"]
    lines = [
        "# 0730 — Descriptifs JETP à partir du snapshot gelé",
        "",
        "## Résultat préliminaire",
        "",
        f"Le snapshot conserve {den['atomic_observations']:,} assertions atomiques : "
        f"{den['event_journal']} événements, {den['position_journal']:,} positions et "
        f"{den['document_coverage']} assertions de couverture. Il ne produit pas une "
        "cohorte commune opérationnelle A/B/C : le nombre d'assertions atomiques "
        f"explicitement codées sur les trois dimensions est {dim['common_explicit_unit_observations']}.",
        "",
        "C'est un résultat de couverture documentaire, non une absence de fonctions, "
        "de finance ou d'histoire dans les JETP.",
        "",
        "## Couverture des trois dimensions",
        "",
        "| Dimension | Assertions documentées | Assertions non codées/inconnues | Sens |",
        "| --- | ---: | ---: | --- |",
    ]
    for panel, label in (("function", "Fonction"), ("finance", "Instrument financier"), ("history", "Histoire événementielle")):
        row = dim[panel]
        lines.append(
            f"| {label} | {row['documented_observations']:,} | "
            f"{row['unknown_or_uncoded_observations']:,} | {row['note']} |"
        )
    lines.extend(
        [
            "",
            "## Pays et journaux",
            "",
            "| Pays | Atomiques | Événements | Positions | Couverture | Rapprochées | Non rapprochées |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for country in ("ZAF", "IDN", "VNM", "SEN"):
        row = countries[country]
        lines.append(
            f"| {country} | {row['atomic_observations']:,} | {row['event_assertions']} | "
            f"{row['position_assertions']:,} | {row['coverage_assertions']} | "
            f"{row['reconciled_atomic_observations']} | {row['unreconciled_atomic_observations']:,} |"
        )
    lines.extend(
        [
            "",
            "## Interprétation financière et temporelle",
            "",
            f"{analysis['money']['source_reported_positions']} positions monétaires sont rapportées, "
            f"avec {analysis['money']['unknown_money_observations']:,} valeurs monétaires inconnues. "
            "Les devises, objets financiers, périmètres et doublons possibles empêchent tout total de portefeuille. "
            "Les 7 assertions événementielles sont des assertions sourcées, pas des horloges de transition ; "
            "aucune durée de transition n'est calculable.",
            "",
            "L'attribution public/privé n'est littérale dans le snapshot que pour 4 des 303 observations "
            "avec instrument : 1 publique, 2 privées et 1 mixte non ventilée. Les 299 autres restent "
            "non documentées pour la propriété : un nom de financeur ne suffit pas à l'inférer.",
            "",
            "## Handoff 0823",
            "",
            "Trois candidats restent ouverts : asymétrie de couverture (résultat nul du join), cycle de vie "
            "rapporté ZAF, et pedigree finance/histoire VNM. La sélection de la figure centrale doit comparer "
            "leur intérêt substantiel et leur lisibilité, sans transformer l'un en résultat causal ou en total financier.",
            "",
            "Fichiers associés : `0730-descriptives.json`, `0730-run-manifest.json`, les tables CSV et "
            "`0730-plot-data.csv`. Tous sont régénérables via le script 0730 à partir du snapshot 0822 épinglé.",
            "",
        ]
    )
    return "\n".join(lines)


def render_outputs(root: Path, output_dir: Path) -> dict[str, Any]:
    """Write the checked-in handoff plus flat tables usable by 0823 plotting."""
    output_dir.mkdir(parents=True, exist_ok=True)
    analysis = build_analysis(root)
    manifest = build_manifest(root, analysis)
    (output_dir / "0730-descriptives.json").write_text(
        json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "0730-run-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    country_table = [dict(country=country, **values) for country, values in analysis["countries"].items()]
    _write_csv(output_dir / "0730-country-coverage.csv", country_table)
    _write_csv(
        output_dir / "0730-source-function-labels.csv",
        analysis["dimensions"]["function"]["source_label_counts"],
    )
    _write_csv(
        output_dir / "0730-source-instruments.csv",
        analysis["dimensions"]["finance"]["instrument_counts"],
    )
    _write_csv(
        output_dir / "0730-ownership-evidence.csv",
        analysis["dimensions"]["finance"]["ownership_evidence_counts"],
    )
    _write_csv(output_dir / "0730-result-candidates.csv", analysis["result_candidates"])
    plot_rows = [
        {
            "panel": panel,
            "documented_observations": analysis["dimensions"][panel]["documented_observations"],
            "unknown_or_uncoded_observations": analysis["dimensions"][panel]["unknown_or_uncoded_observations"],
            "atomic_denominator": analysis["denominators"]["atomic_observations"],
            "interpretation": analysis["dimensions"][panel]["note"],
        }
        for panel in ("function", "finance", "history")
    ]
    plot_rows.append(
        {
            "panel": "common_explicit_unit",
            "documented_observations": analysis["dimensions"]["common_explicit_unit_observations"],
            "unknown_or_uncoded_observations": None,
            "atomic_denominator": analysis["denominators"]["atomic_observations"],
            "interpretation": analysis["dimensions"]["common_explicit_unit_note"],
        }
    )
    _write_csv(output_dir / "0730-plot-data.csv", plot_rows)
    (output_dir / "0730-descriptives-report.md").write_text(
        _report(analysis), encoding="utf-8"
    )
    return analysis


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("docs/jetp-study")
    )
    args = parser.parse_args()
    root = args.root.resolve()
    output_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    render_outputs(root, output_dir)


if __name__ == "__main__":
    main()
