"""Export language distribution table for the data paper.

Produces:
- content/tables/tab_languages.md: Quarto-includable markdown table

Shows language distribution in the full enriched corpus with ISO 639-1 codes
normalised (e.g., en_US → en) and grouped into major languages + "Other".
"""

import os

import pandas as pd
from script_io_args import parse_io_args, validate_io
from utils import (
    BASE_DIR,
    CATALOGS_DIR,
    LANGUAGE_NAMES,
    get_logger,
    normalize_lang_display,
)

log = get_logger("export_language_table")

ENRICHED_PATH = os.path.join(CATALOGS_DIR, "enriched_works.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "deliverables", "_shared", "tables")
OUTPUT_MD = os.path.join(OUTPUT_DIR, "tab_languages.md")

# LANGUAGE_NAMES (ISO 639-1 → display name) moved to pipeline_text beside the
# normalisers, so this exporter and the retrieval-protocol table render the
# same name for the same code (ticket 0329).

# Minimum count to show individually (otherwise grouped as "Other")
MIN_COUNT = 200


def normalise_language(code: str) -> str:
    """Local name for the shared display normaliser.

    The body moved to `pipeline_text.normalize_lang_display` so the prose
    counts in `compute_vars.py` bucket codes exactly as this table does; they
    diverged on `arz` and `sco` while each held its own copy (PR #1141).
    """
    return normalize_lang_display(code)


def main() -> None:
    global OUTPUT_MD
    io_args, _extra = parse_io_args()
    validate_io(output=io_args.output)
    OUTPUT_MD = io_args.output

    input_path = io_args.input[0] if io_args.input else ENRICHED_PATH
    df = pd.read_csv(input_path, usecols=["language"])
    df["lang"] = df["language"].apply(normalise_language)

    counts = df["lang"].value_counts()
    total = len(df)

    rows = []
    other_count = 0
    other_langs = []

    for lang, count in counts.items():
        if count >= MIN_COUNT and lang != "unknown":
            name = LANGUAGE_NAMES.get(lang, lang.upper())
            rows.append({
                "Language": name,
                "Code": lang,
                "Works": count,
                "Share (%)": f"{100 * count / total:.1f}",
            })
        elif lang != "unknown":
            other_count += count
            other_langs.append(lang)

    unknown_count = counts.get("unknown", 0)

    rows.sort(key=lambda r: -int(r["Works"]))

    if other_count > 0:
        rows.append({
            "Language": f"Other ({len(other_langs)} languages)",
            "Code": "—",
            "Works": other_count,
            "Share (%)": f"{100 * other_count / total:.1f}",
        })

    if unknown_count > 0:
        rows.append({
            "Language": "Unclassified",
            "Code": "—",
            "Works": unknown_count,
            "Share (%)": f"{100 * unknown_count / total:.1f}",
        })

    rows.append({
        "Language": "**Total**",
        "Code": "",
        "Works": total,
        "Share (%)": "100.0",
    })

    table = pd.DataFrame(rows)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    lines = [
        f"| {' | '.join(table.columns)} |",
        "| :---------- | :---- | ----: | --------: |",
    ]
    for _, row in table.iterrows():
        lines.append(f"| {' | '.join(str(v) for v in row)} |")

    lines.append("")
    lines.append(": Language distribution in the refined corpus. {#tbl-languages}")

    md = "\n".join(lines) + "\n"
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(md)

    log.info("Wrote %s (%d language rows)", OUTPUT_MD, len(rows))

    for row in rows:
        log.info("  %s: %s (%s%%)", row["Language"], row["Works"], row["Share (%)"])


if __name__ == "__main__":
    main()
