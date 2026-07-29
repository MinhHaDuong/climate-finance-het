"""Render the corpus construction ledger for Quarto includes.

Reads: deliverables/_shared/tables/tab_corpus_flow.csv
Writes: deliverables/_shared/tables/tab_corpus_flow.md

This script renders; it does not measure. The ledger's arithmetic — and the
three independent checks that it closes — live once in
scripts/analysis/compute_corpus_flow.py (ticket 0327). Keeping the two apart
also gives each Make rule a single output, so neither can be handed the other's
path by a grouped target's `$@`.

Usage:
    uv run python scripts/figures/export_corpus_flow.py \
        --input deliverables/_shared/tables/tab_corpus_flow.csv \
        --output deliverables/_shared/tables/tab_corpus_flow.md
"""

import os

import pandas as pd
from _markdown_table import markdown_text_cell
from script_io_args import parse_io_args, validate_io
from utils import BASE_DIR, get_logger

log = get_logger("export_corpus_flow")

TABLES_DIR = os.path.join(BASE_DIR, "deliverables", "_shared", "tables")
DEFAULT_INPUT = os.path.join(TABLES_DIR, "tab_corpus_flow.csv")

CAPTION = (
    ": Corpus construction ledger. Each stage starts where the previous one"
    " ended; *In* less *Removed* equals *Out* on every row. The first *In* is"
    " the pooled source-catalog records, the last *Out* the refined corpus."
    " {#tbl-flow}"
)


def render_table(flow: pd.DataFrame, caption: str = CAPTION) -> str:
    """Render the ledger as a Quarto-includable markdown table."""
    lines = [
        "| Stage | In | Removed | Out |",
        # Pandoc maps delimiter-row dash counts to relative column widths:
        # give the prose Stage column the room, keep the count columns narrow.
        "|:----------------------------------------------------|----:|------:|----:|",
    ]
    # `Stage` is prose — the removal labels `compute_corpus_flow` authors by
    # hand. The counts are `int`-formatted and cannot carry a `|`, but the
    # label can, and a raw one would end its cell and drop the last count
    # (ticket 0370). Whether a label happens to contain one today is not the
    # question: the escaper exists so no emitter has to know.
    #
    # The unified-corpus count is bolded at the merge→filter pivot: readers
    # meet 43,179 in the prose first, and without the emphasis the ledger's
    # 44,174 opening reads as a contradiction rather than the pre-dedup pool.
    # Keyed on the quality-filtering boundary row, not a literal count.
    filtering = flow["Stage"].str.startswith("Quality filtering")
    milestone = int(flow.loc[filtering, "In"].iloc[0]) if filtering.any() else None

    def fmt(value: int) -> str:
        n = int(value)
        return f"**{n:,}**" if n == milestone else f"{n:,}"

    for _, row in flow.iterrows():
        lines.append(
            f"| {markdown_text_cell(row['Stage'])} | {fmt(row['In'])} | "
            f"{fmt(row['Removed'])} | {fmt(row['Out'])} |"
        )
    lines += ["", caption, ""]
    return "\n".join(lines)


def main():
    io_args, _extra = parse_io_args()
    validate_io(output=io_args.output)

    inputs = io_args.input or []
    source = inputs[0] if inputs else DEFAULT_INPUT
    flow = pd.read_csv(source)

    content = render_table(flow)
    os.makedirs(os.path.dirname(io_args.output), exist_ok=True)
    with open(io_args.output, "w") as f:
        f.write(content)

    log.info("Wrote %s", io_args.output)


if __name__ == "__main__":
    main()
