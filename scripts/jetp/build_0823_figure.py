"""Render the non-causal central figure from the frozen 0730 descriptive run.

The figure is deliberately a *coverage* result.  It shows three separately
documented dimensions on the same atomic-assertion denominator, rather than
inventing an operation-level join from source labels.
"""

import argparse
import csv
import hashlib
import json
from html import escape
from pathlib import Path
from typing import Any

INPUT = Path("docs/jetp-study/0730-descriptives.json")
INPUT_MANIFEST = Path("docs/jetp-study/0730-run-manifest.json")
SCHEMA_VERSION = "jetp-0823-central-figure/1"
CENTRAL_RESULT = (
    "The frozen corpus documents the three dimensions at sharply different "
    "coverage levels and contains no atomic assertion explicitly coded on all three."
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_0730(root: Path) -> dict[str, Any]:
    """Load the already approved descriptive output, not the mutable source store."""
    data = json.loads((root / INPUT).read_text(encoding="utf-8"))
    if data["schema_version"] != "jetp-0730-descriptives/1":
        raise ValueError("0823 requires the frozen 0730 descriptive schema")
    return data


def build_figure_data(root: Path) -> dict[str, Any]:
    """Make the plotted values and candidate assessment explicit and replayable."""
    source = _load_0730(root)
    denominator = source["denominators"]["atomic_observations"]
    dimensions = source["dimensions"]
    panels = []
    for panel_id, source_key, title in (
        ("A_function_labels", "function", "A. Function labels"),
        ("B_finance_instruments", "finance", "B. Finance instruments"),
        ("C_event_history", "history", "C. Event history"),
    ):
        row = dimensions[source_key]
        panels.append(
            {
                "panel_id": panel_id,
                "title": title,
                "documented_observations": row["documented_observations"],
                "unknown_or_uncoded_observations": row["unknown_or_uncoded_observations"],
                "atomic_denominator": denominator,
                "panel_note": row["note"],
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "central_result": CENTRAL_RESULT,
        "unit": "Atomic source assertions; not operations, projects, finance totals, or JETP portfolios.",
        "common_explicit_unit_observations": dimensions["common_explicit_unit_observations"],
        "common_explicit_unit_note": dimensions["common_explicit_unit_note"],
        "panels": panels,
        "candidate_assessment": [
            {
                "candidate_id": "coverage-asymmetry",
                "rank": 1,
                "decision": "selected",
                "intrinsic_interest": "Shows whether the adopted three-part question can be answered jointly from the frozen public record, while retaining all incomplete observations.",
                "robustness": "High within the frozen snapshot: all panels use the same 1,740-assertion denominator; no currency conversion, ownership inference, operation matching, or date arithmetic enters the count.",
                "coverage": "1,399 function labels; 303 finance-instrument labels; 7 event assertions; 0 assertions carry all three explicit dimensions.",
                "contrary_evidence": "The result is about this frozen documentary corpus, not the underlying JETPs. Different source acquisition or operation-level identity work could change coverage.",
                "literature_context": "Extends Karg, Gupta & Chen (2025, ERSS 125:104103), which compares justice and climate-finance design across four JETPs, with a reproducible assertion-level account of which linked empirical claims the public record currently supports. It does not claim to supersede substantive justice analysis.",
            },
            {
                "candidate_id": "zaf-reported-lifecycle",
                "rank": 2,
                "decision": "context_panel",
                "intrinsic_interest": "A large South African register can describe reported implementation-status labels.",
                "robustness": "Moderate for label coverage (257 labels); low for timing because 235 source register dates are not transition dates and 22 positions lack a date value.",
                "coverage": "ZAF source-register candidates only; no event assertions or reconciled operation histories in this snapshot.",
                "contrary_evidence": "A status label can describe an administrative register without showing implementation, payment, speed, or a just-transition outcome.",
                "literature_context": "Complements work on JETP implementation and country platforms, including Daley & Lawrie (2026), but cannot evaluate their institutional arguments or estimate partnership effects.",
            },
            {
                "candidate_id": "vnm-finance-history-pedigree",
                "rank": 3,
                "decision": "context_panel",
                "intrinsic_interest": "The only frozen event assertions and named finance-history conflicts make provenance visible at source-assertion and named-reconciliation scale.",
                "robustness": "High for the existence of 7 events and 3 named incompatible reconciliations; low for a national interpretation because the cases are few and amounts are non-additive.",
                "coverage": "VNM staged observations: 7 events; 3 named reconciliations covering 14 atomic inputs; none permits pooling.",
                "contrary_evidence": "The global snapshot has 4 reconciliations/15 inputs because one Senegal record is also retained; Vietnam is not a finance total or representative national history.",
                "literature_context": "Adds auditable pedigree to debates about JETP finance and Indonesia/Vietnam country platforms; it neither resolves the justice comparison in Karg et al. (2025) nor establishes private-finance mobilisation.",
            },
        ],
        "limitations": source["limitations"],
    }


def _text(x: float, y: float, css_class: str, content: str, max_width: float) -> str:
    """Constrain every painted label within the viewBox, including long notes."""
    font_sizes = {"title": 25, "subtitle": 15, "panel": 17, "value": 15, "note": 13, "foot": 16}
    estimated_width = len(content) * font_sizes[css_class] * 0.62
    text_length = min(max_width, max(1, estimated_width))
    return (
        f'<text x="{x}" y="{y}" class="{css_class}" textLength="{text_length:.3f}" '
        f'lengthAdjust="spacingAndGlyphs">{escape(content)}</text>'
    )


def _svg(data: dict[str, Any]) -> str:
    """Render a compact, dependency-free SVG with legible zero and unknown states."""
    width, height, left, bar_width = 1160, 690, 82, 860
    max_text_width = width - 2 * left
    rows = []
    for index, panel in enumerate(data["panels"]):
        y = 150 + index * 130
        documented = panel["documented_observations"]
        unknown = panel["unknown_or_uncoded_observations"]
        denominator = panel["atomic_denominator"]
        doc_width = bar_width * documented / denominator
        unknown_width = bar_width * unknown / denominator
        rows.extend(
            [
                _text(left, y - 22, "panel", panel["title"], max_text_width),
                f'<rect x="{left}" y="{y}" width="{doc_width:.3f}" height="32" class="documented"/>',
                f'<rect x="{left + doc_width:.3f}" y="{y}" width="{unknown_width:.3f}" height="32" class="unknown"/>',
                _text(left, y + 56, "value", f"{documented:,} documented · {unknown:,} unknown/uncoded · n={denominator:,}", max_text_width),
                _text(left, y + 82, "note", panel["panel_note"], max_text_width),
            ]
        )
    common = data["common_explicit_unit_observations"]
    common_denominator = data["panels"][0]["atomic_denominator"]
    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            "<title id=\"title\">Documentary coverage of three JETP dimensions</title>",
            "<desc id=\"desc\">Three bars use the same denominator of frozen atomic source assertions. Their unequal coverage does not form a common operation-level sample.</desc>",
            "<style>.title{font:700 25px sans-serif;fill:#12233d}.subtitle{font:15px sans-serif;fill:#405266}.panel{font:700 17px sans-serif;fill:#12233d}.value{font:15px sans-serif;fill:#12233d}.note{font:13px sans-serif;fill:#405266}.foot{font:700 16px sans-serif;fill:#9a3412}.documented{fill:#147d92}.unknown{fill:#d6dce2}</style>",
            '<rect width="100%" height="100%" fill="white"/>',
            _text(82, 50, "title", "What the frozen JETP record can jointly describe", max_text_width),
            _text(82, 78, "subtitle", "Atomic source assertions, not operations or portfolio totals. Teal = documented; grey = unknown or uncoded.", max_text_width),
            *rows,
            _text(82, 586, "foot", f"No common explicit A/B/C atomic assertion: {common} / {common_denominator:,}", max_text_width),
            _text(82, 618, "note", "The panels share an assertion denominator but are not a joint operation-level sample; the zero is a coverage result, not absence in JETPs.", max_text_width),
            _text(82, 648, "note", "Source: frozen 0822 snapshot, rendered through approved 0730 descriptives. No amounts are pooled; no transition duration is calculated.", max_text_width),
            "</svg>",
        ]
    ) + "\n"


def _selection_report(data: dict[str, Any]) -> str:
    """Preserve the three-candidate comparison and literature caveat for 0732."""
    lines = [
        "# 0823 — Sélection du résultat central et figure",
        "",
        "## Résultat sélectionné",
        "",
        data["central_result"],
        "",
        "La figure centrale est `0823-central-figure.svg`. Elle compare trois couvertures documentaires sur le même dénominateur de 1 740 assertions atomiques. Elle ne constitue ni une cohorte d'opérations, ni un total financier, ni une estimation causale.",
        "",
        "## Comparaison des trois candidats",
        "",
        "| Rang | Candidat | Décision | Intérêt | Robustesse et couverture | Élément contraire | Contexte publié localement vérifié |",
        "| ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for item in data["candidate_assessment"]:
        lines.append(
            "| {rank} | {candidate_id} | {decision} | {intrinsic_interest} | {robustness} {coverage} | {contrary_evidence} | {literature_context} |".format(**item)
        )
    lines.extend(
        [
            "",
            "## Lecture des panneaux secondaires",
            "",
            "Le contexte ZAF rappelle que 257 libellés de statut de registre ne sont pas des jalons temporels. Le contexte VNM conserve 7 événements et trois rapprochements incompatibles à l'échelle des assertions et des rapprochements nommés, sans les agréger. Ces deux observations motivent le besoin de pedigree et de rapprochement ; elles ne modifient pas le résultat de couverture sélectionné.",
            "",
            "## Limites",
            "",
            *[f"- {item}" for item in data["limitations"]],
            "- La consultation de littérature est une vérification de contexte des références déjà archivées dans le dépôt ; elle n'est pas une revue systématique nouvelle.",
            "",
            "## Handoff 0732",
            "",
            "Présenter le résultat comme une contrainte empirique sur ce corpus gelé : les questions de fonction, de finance et d'histoire ne peuvent pas encore être croisées à l'échelle des opérations. Employer les panneaux ZAF et VNM comme illustrations de ce diagnostic. Ne pas écrire accélération, additionalité, effet catalytique, mobilisation privée inférée, total de portefeuille, ni absence de finance.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def render_outputs(root: Path, output_dir: Path) -> dict[str, Any]:
    """Write the figure, its flat data, selection record, and replay manifest."""
    output_dir.mkdir(parents=True, exist_ok=True)
    data = build_figure_data(root)
    plotted = output_dir / "0823-central-figure-data.csv"
    figure = output_dir / "0823-central-figure.svg"
    selection = output_dir / "0823-result-selection.md"
    _write_csv(plotted, data["panels"])
    figure.write_text(_svg(data), encoding="utf-8")
    selection.write_text(_selection_report(data), encoding="utf-8")
    manifest = {
        "schema_version": "jetp-0823-figure-manifest/1",
        "input_0730": str(INPUT),
        "input_0730_sha256": _sha256(root / INPUT),
        "input_0730_manifest": str(INPUT_MANIFEST),
        "input_0730_manifest_sha256": _sha256(root / INPUT_MANIFEST),
        "reproduction": "python3 scripts/jetp/build_0823_figure.py --root .",
        "scope": "Frozen 0730 descriptive output only; no acquisition, pooling, currency conversion, ownership inference, operation-level join, or causal estimation.",
        "files": {
            path.name: {"sha256": _sha256(path)} for path in (plotted, figure, selection)
        },
    }
    (output_dir / "0823-figure-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=Path("docs/jetp-study"))
    args = parser.parse_args()
    root = args.root.resolve()
    output_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    render_outputs(root, output_dir)


if __name__ == "__main__":
    main()
