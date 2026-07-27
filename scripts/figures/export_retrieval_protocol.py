"""Export the deposited retrieval-protocol appendix (ticket 0329).

All four RDJ-26561 external reviewers said the same thing: the paper describes
its retrieval at a level that forces a referee to reverse-engineer the harvest
code. This script renders the protocol from the very config files the harvest
read, so the deposit cannot describe a run that did not happen.

Produces, from config only (no corpus data, no network):

- ``tab_retrieval_protocol.csv`` — one row per source: retrieval mode, the
  fields the query searched, the term or seed count, and language coverage.
- ``tab_retrieval_protocol.md`` — the same table for human reading, plus the
  enumeration of the curated grey-literature reports.

Deliberately absent: harvest date and per-query record counts. Neither has a
machine-readable source, and hand-typing them would recreate the drift this
artifact exists to prevent.

Usage:
    uv run python scripts/figures/export_retrieval_protocol.py \
        --output deliverables/_shared/tables/tab_retrieval_protocol.csv
"""

import os

import pandas as pd
import yaml
from script_io_args import parse_io_args, validate_io
from utils import CONFIG_DIR, get_logger, save_csv

log = get_logger("export_retrieval_protocol")

COLUMNS = ["Source", "Retrieval", "Query fields", "Query terms", "Languages"]

CAPTION = (
    ": Retrieval protocol per source, rendered from the deposited"
    " configuration files. *Retrieval*: how records enter the corpus."
    " *Query fields*: the index fields the query matched. *Query terms*:"
    " search terms, or curated seed documents where the source is a"
    " hand-assembled list. *Languages*: the languages the query terms are"
    " written in. Records returned and retained per source are in the corpus"
    " composition table; harvest-run counts are not reported here because no"
    " machine-readable record of them exists."
)

GREY_CAPTION = (
    ": The curated grey-literature seed list, in full"
    " (`config/grey_sources.yaml`). The World Bank Open Knowledge Repository"
    " contributes further records by API query and is not enumerated."
)


def _load(name):
    with open(os.path.join(CONFIG_DIR, name), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _escape(value) -> str:
    """Make a cell safe for a pipe table: a bare pipe would split the row."""
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def target_languages(queries: dict) -> list[str]:
    """Language display names declared by the Tier-1 term tags."""
    return sorted({lang for lang in queries["term_languages"].values() if lang})


def _openalex_terms(queries: dict) -> str:
    tiers = queries["tiers"]
    total = sum(len(t["terms"]) for t in tiers.values())
    breakdown = ", ".join(
        f"T{tier} {len(cfg['terms'])}" for tier, cfg in sorted(tiers.items())
    )
    return f"{total} ({breakdown})"


def _tier_filter_note(queries: dict) -> str:
    groups = len(queries["concept_groups"])
    rules = [
        f"T{tier} {cfg['min_concept_groups']}"
        for tier, cfg in sorted(queries["tiers"].items())
        if cfg["min_concept_groups"]
    ]
    return f"co-occurrence filter, {' / '.join(rules)} of {groups} concept groups"


def build_protocol_rows() -> list[dict]:
    """One row per corpus source, every count read from config."""
    queries = _load("openalex_queries.yaml")
    collect = _load("corpus_collect.yaml")
    grey = _load("grey_sources.yaml")
    unfccc = _load("unfccc_sources.yaml")["documents"]
    oecd = _load("oecd_dac_sources.yaml")["documents"]

    languages = target_languages(queries)
    worldbank = collect["queries"]["worldbank"]

    return [
        {
            "Source": "OpenAlex",
            "Retrieval": f"Four-tier keyword search ({_tier_filter_note(queries)})",
            "Query fields": "default.search (title, abstract, indexed fulltext)",
            "Query terms": _openalex_terms(queries),
            "Languages": f"{len(languages)}: " + ", ".join(languages),
        },
        {
            "Source": "ISTEX",
            "Retrieval": "Boolean phrase search",
            "Query fields": "ISTEX default index",
            "Query terms": collect["queries"]["istex"],
            "Languages": "English, French",
        },
        {
            "Source": "Grey literature",
            "Retrieval": "Curated seed list plus World Bank repository API",
            "Query fields": "seed identifiers; repository full-text search",
            "Query terms": (
                f"{len(grey)} curated reports, {len(worldbank)} API queries"
            ),
            "Languages": "English",
        },
        {
            "Source": "UNFCCC key documents",
            "Retrieval": "Curated seed list (config/unfccc_sources.yaml)",
            "Query fields": "document symbol",
            "Query terms": f"{len(unfccc)} seed documents",
            "Languages": "English",
        },
        {
            "Source": "OECD DAC key documents",
            "Retrieval": "Curated seed list (config/oecd_dac_sources.yaml)",
            "Query fields": "document symbol",
            "Query terms": f"{len(oecd)} seed documents",
            "Languages": "English",
        },
        {
            "Source": "bibCNRS",
            "Retrieval": "Hand-harvested export (CNRS credentials)",
            "Query fields": "aggregator native search (Gale, Wanfang, NewsBank)",
            "Query terms": "not machine-readable",
            "Languages": "French, Chinese, Japanese, German",
        },
        {
            "Source": "SciSpace",
            "Retrieval": "AI-assisted systematic review, hand-exported",
            "Query fields": "vendor native search",
            "Query terms": "not machine-readable",
            "Languages": "English",
        },
        {
            "Source": "Teaching canon",
            "Retrieval": "Syllabus scraping plus LLM reference extraction",
            "Query fields": "syllabus full text",
            "Query terms": "not machine-readable",
            "Languages": "English",
        },
    ]


def build_grey_rows() -> list[dict]:
    """The curated grey-literature seed list, one row per report."""
    return [
        {
            "Title": entry["title"],
            "Author": entry.get("author", ""),
            "Year": entry.get("year", ""),
            "Organisation": entry.get("source_org", ""),
        }
        for entry in _load("grey_sources.yaml")
    ]


def _pipe_table(rows: list[dict], columns: list[str], caption: str) -> list[str]:
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join([":---"] * len(columns)) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_escape(row[c]) for c in columns) + " |")
    lines += ["", caption, ""]
    return lines


def render_markdown() -> str:
    """The human-readable appendix: protocol table then grey enumeration."""
    queries = _load("openalex_queries.yaml")
    collect = _load("corpus_collect.yaml")
    lines = [
        "## Retrieval protocol {.unnumbered}",
        "",
        f"All API queries are bounded to publication years {collect['year_min']}"
        f"--{collect['year_max']}. Terms, concept groups, and the title"
        " blacklist are in `config/openalex_queries.yaml` and"
        " `config/corpus_filter.yaml`; the curated seed lists are in"
        " `config/grey_sources.yaml`, `config/unfccc_sources.yaml`, and"
        " `config/oecd_dac_sources.yaml`. Tier 3 and Tier 4 terms are retained"
        " only when the abstract mentions at least"
        f" {queries['tiers'][3]['min_concept_groups']} and"
        f" {queries['tiers'][4]['min_concept_groups']} respectively of the"
        f" {len(queries['concept_groups'])} concept groups"
        f" ({', '.join(sorted(queries['concept_groups']))}).",
        "",
    ]
    lines += _pipe_table(build_protocol_rows(), COLUMNS, CAPTION)
    lines += [
        "",
        "### Curated grey-literature seed list {.unnumbered}",
        "",
    ]
    lines += _pipe_table(
        build_grey_rows(), ["Title", "Author", "Year", "Organisation"], GREY_CAPTION
    )
    return "\n".join(lines) + "\n"


def main(output: str) -> None:
    """Write both group members, whichever one Make asked for.

    The Makefile rule is a grouped target (``X.csv X.md &:``) and passes
    ``$@``, which GNU Make sets to the member that triggered the rule. Keying
    off the stem rather than the given suffix means a stale ``.md`` alone
    still rebuilds the CSV, instead of writing CSV bytes to the ``.md`` path
    and leaving the ``.csv`` absent while Make counts the group as built.
    """
    stem = os.path.splitext(output)[0]
    save_csv(pd.DataFrame(build_protocol_rows(), columns=COLUMNS), stem + ".csv")
    with open(stem + ".md", "w", encoding="utf-8") as fh:
        fh.write(render_markdown())
    log.info("Wrote %s.csv and %s.md", stem, stem)


if __name__ == "__main__":
    io_args, _extra = parse_io_args()
    validate_io(output=io_args.output)
    main(io_args.output)
