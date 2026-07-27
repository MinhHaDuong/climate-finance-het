"""CONSORT-style corpus flow table (ticket 0327).

The data paper's construction ledger has to close: pooled source records minus
every documented removal must equal the refined corpus, with no residue. Two
gaps in the submitted version (19 works and 399 works) both traced to one
omission — `corpus_audit.csv` carries *three* action buckets (`keep`,
`remove`, `deduped`) and only two were ever counted.

These tests pin:
- the stage arithmetic of `tab_corpus_flow.csv` (each `Out` = `In` - `Removed`,
  each `In` = the previous `Out`, final `Out` = the refined corpus size);
- that the audit's action buckets are exhaustive and sum to the raw count —
  the guard that would have caught the original defect;
- that an unknown action bucket is a hard error, not a silent exclusion.
"""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "analysis"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "figures"))

import compute_corpus_flow

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MAKEFILE = os.path.join(REPO, "Makefile")
FLOW_CSV = os.path.join(REPO, "deliverables", "_shared", "tables", "tab_corpus_flow.csv")
FLOW_MD = os.path.join(REPO, "deliverables", "_shared", "tables", "tab_corpus_flow.md")

# A merge run report shaped like data/catalogs/run_reports/catalog_merge__*.json.
MERGE_REPORT = {
    "script": "catalog_merge",
    "records_total": 1000,
    "doi_duplicates_removed": 40,
    "dropped_empty_title": 5,
    "title_year_duplicates_removed": 15,
    "records_unified": 940,
}
BUCKETS = {"keep": 700, "remove": 200, "deduped": 40}
# The refined corpus the ledger must land on — an anchor outside the audit.
REFINED_N = 700


# ── Pure logic (fast tier) ───────────────────────────────────


class TestAuditBuckets:
    def test_counts_all_three_actions(self):
        audit = pd.DataFrame(
            {"action": ["keep"] * 3 + ["remove"] * 2 + ["deduped"]}
        )
        assert compute_corpus_flow.audit_buckets(audit) == {
            "keep": 3,
            "remove": 2,
            "deduped": 1,
        }

    def test_absent_bucket_reads_zero_not_missing(self):
        audit = pd.DataFrame({"action": ["keep", "remove"]})
        buckets = compute_corpus_flow.audit_buckets(audit)
        assert buckets["deduped"] == 0

    def test_unknown_action_is_an_error(self):
        """A fourth bucket must fail loudly — silently dropping one is the
        defect this ticket exists to fix."""
        audit = pd.DataFrame({"action": ["keep", "remove", "quarantined"]})
        with pytest.raises(ValueError, match="quarantined"):
            compute_corpus_flow.audit_buckets(audit)

    def test_dry_run_audit_says_rerun_the_filter(self):
        """corpus_filter's dry-run path writes `would_remove` to the same
        corpus_audit.csv and performs no deduplication, so the ledger is not
        buildable from it. The error must send the reader to rerun the filter,
        not to add a stage that does not exist."""
        audit = pd.DataFrame({"action": ["keep", "would_remove", "keep"]})
        with pytest.raises(ValueError, match="dry-run"):
            compute_corpus_flow.audit_buckets(audit)


class TestBuildFlow:
    def test_stage_arithmetic_closes(self):
        flow = compute_corpus_flow.build_flow(MERGE_REPORT, BUCKETS, REFINED_N)
        for _, row in flow.iterrows():
            assert row["Out"] == row["In"] - row["Removed"], row["Stage"]
        outs = flow["Out"].tolist()
        ins = flow["In"].tolist()
        assert ins[1:] == outs[:-1], "each stage must start where the previous ended"

    def test_starts_at_pooled_records_ends_at_refined_corpus(self):
        flow = compute_corpus_flow.build_flow(MERGE_REPORT, BUCKETS, REFINED_N)
        assert flow["In"].iloc[0] == MERGE_REPORT["records_total"]
        assert flow["Out"].iloc[-1] == REFINED_N

    def test_unified_count_is_a_checkpoint(self):
        flow = compute_corpus_flow.build_flow(MERGE_REPORT, BUCKETS, REFINED_N)
        assert MERGE_REPORT["records_unified"] in flow["Out"].tolist()

    def test_every_bucket_appears_as_a_removal_or_the_final_out(self):
        """`deduped` must be a stage of its own — the omission that produced
        both reported gaps."""
        flow = compute_corpus_flow.build_flow(MERGE_REPORT, BUCKETS, REFINED_N)
        removed = flow["Removed"].tolist()
        assert BUCKETS["remove"] in removed
        assert BUCKETS["deduped"] in removed

    def test_buckets_not_summing_to_unified_is_an_error(self):
        bad = dict(BUCKETS, deduped=39)
        with pytest.raises(ValueError, match="audit"):
            compute_corpus_flow.build_flow(MERGE_REPORT, bad, REFINED_N)

    def test_merge_report_not_closing_is_an_error(self):
        bad = dict(MERGE_REPORT, records_unified=939)
        with pytest.raises(ValueError, match="merge"):
            compute_corpus_flow.build_flow(bad, BUCKETS, REFINED_N)

    def test_an_audit_that_filtered_nothing_cannot_close(self):
        """The closing check must come from outside the audit.

        An all-`keep` audit satisfies the bucket-sum check by construction, and
        comparing the last Out to buckets["keep"] is algebraically implied by
        it. Before the refined-corpus anchor, such an audit produced a
        publishable-looking ledger ending at the unified count.
        """
        unfiltered = {"keep": 940, "remove": 0, "deduped": 0}
        with pytest.raises(ValueError, match="refined_works"):
            compute_corpus_flow.build_flow(MERGE_REPORT, unfiltered, REFINED_N)

    def test_missing_action_is_an_error(self):
        audit = pd.DataFrame({"action": ["keep", None, "remove"]})
        with pytest.raises(ValueError, match="no action"):
            compute_corpus_flow.audit_buckets(audit)


class TestRenderTable:
    """Rendering lives in scripts/figures/export_corpus_flow.py — compute and
    export stay separate, so each Make rule has a single output."""

    def test_markdown_table_carries_a_label_and_thousands_separators(self):
        import export_corpus_flow

        flow = compute_corpus_flow.build_flow(MERGE_REPORT, BUCKETS, REFINED_N)
        md = export_corpus_flow.render_table(flow)
        assert "{#tbl-flow}" in md
        assert "1,000" in md
        assert md.count("\n|") >= len(flow)

    @pytest.mark.integration
    def test_a_piped_stage_label_keeps_its_four_cells(self, tmp_path):
        """A `|` in a stage label must not drop the row's last count.

        `Stage` is prose authored by hand in `compute_corpus_flow`, so it is
        the same free-text-into-a-pipe-table shape as the corpus-sources table
        (ticket 0370). Asserted on the rendered page: the renderer is the only
        thing that sees the split, and it reports it by silently dropping the
        overflow rather than erroring.
        """
        import export_corpus_flow
        from _gfm_render import cell_texts, render_gfm, require_pandoc, row_with

        require_pandoc()
        label = "Quality filtering | protection criteria applied"
        flow = pd.DataFrame(
            [{"Stage": label, "In": 1000, "Removed": 40, "Out": 960}]
        )

        row = row_with(
            render_gfm(export_corpus_flow.render_table(flow), tmp_path),
            "Quality filtering",
        )

        assert cell_texts(row) == [label, "1,000", "40", "960"], (
            f"the stage label split the row:\n{row}"
        )

    def test_shipped_stage_labels_are_untouched_by_the_escaper(self):
        """Escaping must be a no-op on the labels the ledger actually emits.

        A fix that churns `tab_corpus_flow.md` on the next regeneration would
        put a diff on every row and hide the one that changed for a reason.
        """
        import export_corpus_flow

        flow = compute_corpus_flow.build_flow(MERGE_REPORT, BUCKETS, REFINED_N)
        md = export_corpus_flow.render_table(flow)

        assert "\\" not in md, f"escaping churned a shipped stage label:\n{md}"
        for label in flow["Stage"]:
            assert f"| {label} |" in md, f"label {label!r} was rewritten"


def _logical_lines(text: str):
    """Makefile lines with backslash continuations joined, keeping the line
    number of each logical line's first physical line."""
    joined = []
    buf, start = None, 0
    for n, raw in enumerate(text.splitlines(), start=1):
        if buf is None:
            buf, start = raw, n
        else:
            buf = buf[:-1] + " " + raw.lstrip()
        if buf.endswith("\\"):
            continue
        joined.append((start, buf))
        buf = None
    if buf is not None:
        joined.append((start, buf))
    return joined


def grouped_targets_using_bare_at(makefile_text: str) -> list[str]:
    """Grouped Make targets (`a b &: …`) whose recipe passes a bare `$@`.

    `$@` binds to whichever member make was *asked* for, so a recipe handing it
    to a script that derives its other outputs writes them all to the requested
    member's path and leaves the rest stale — while make records the whole
    group as updated. `make …tab_corpus_flow.md` reproduced exactly that.

    Any grouped target is checked, not only mixed-extension ones: two members
    sharing an extension are just as substitutable. Continuation lines are
    joined first, since a multi-line target list is the common shape and a
    line-at-a-time scan silently skips it. Echo lines are exempt — printing
    `$@` is not writing to it.
    """
    lines = _logical_lines(makefile_text)
    offenders = []
    for idx, (_, line) in enumerate(lines):
        if "&:" not in line or line.lstrip().startswith("#"):
            continue
        members = line.split("&:")[0].split()
        if len(members) < 2:
            continue
        for _, recipe in lines[idx + 1:]:
            if not recipe.startswith("\t"):
                break
            body = recipe.lstrip("\t@-")
            if body.startswith(("echo ", "printf ")):
                continue
            if "$@" in recipe:
                offenders.append(members[0])
                break
    return offenders


class TestOutputPathContract:
    """Guard for the grouped-target `$@` trap (see the helper's docstring)."""

    @pytest.mark.adherence
    def test_grouped_recipes_name_their_output_explicitly(self):
        with open(MAKEFILE) as f:
            offenders = grouped_targets_using_bare_at(f.read())
        assert not offenders, (
            f"grouped targets passing a bare $@ to their recipe: {offenders}"
        )

    def test_guard_catches_a_multi_line_target_list(self):
        """The shape that silently escaped the first version of this guard."""
        makefile = (
            "a/one.csv a/two.json \\\n"
            "\t\tb/three.csv &: \\\n"
            "\t\tscripts/x.py\n"
            "\t$(PYTHON) $< --output $@\n"
        )
        assert grouped_targets_using_bare_at(makefile) == ["a/one.csv"]

    def test_guard_catches_same_extension_members(self):
        makefile = "a.csv b.csv &: scripts/x.py\n\t$(PYTHON) $< --output $@\n"
        assert grouped_targets_using_bare_at(makefile) == ["a.csv"]

    def test_guard_scans_the_whole_recipe_not_a_fixed_window(self):
        makefile = (
            "a.csv b.md &: scripts/x.py\n"
            + "\t@echo step\n" * 8
            + "\t$(PYTHON) $< --output $@\n"
        )
        assert grouped_targets_using_bare_at(makefile) == ["a.csv"]

    def test_guard_ignores_echoed_at_and_plain_targets(self):
        makefile = (
            "a.csv b.md &: scripts/x.py\n"
            "\t@echo building $@\n"
            "\t$(PYTHON) $< --output a.csv\n"
            "\nc.csv: scripts/y.py\n"
            "\t$(PYTHON) $< --output $@\n"
        )
        assert grouped_targets_using_bare_at(makefile) == []


# ── Generated artifact (slow tier — needs the built table) ───


@pytest.fixture
def flow_table():
    if not os.path.exists(FLOW_CSV):
        pytest.skip(f"{FLOW_CSV} not built here — run make corpus-tables")
    return pd.read_csv(FLOW_CSV)


@pytest.mark.slow
def test_generated_flow_closes_to_the_refined_corpus(flow_table):
    """Load-bearing: the published ledger must reconcile exactly."""
    from pipeline_loaders import load_refined_works

    for _, row in flow_table.iterrows():
        assert row["Out"] == row["In"] - row["Removed"], row["Stage"]
    ins = flow_table["In"].tolist()
    outs = flow_table["Out"].tolist()
    assert ins[1:] == outs[:-1]
    assert int(flow_table["Out"].iloc[-1]) == len(load_refined_works())


@pytest.mark.slow
def test_flagged_minus_protected_equals_the_filtering_removal(flow_table):
    """Gap 1: `filter_protected` was counted after deduplication while
    `filter_flagged` was counted before it, so the paper's subtraction was
    19 short. Both must now be measured at the filtering stage."""
    import compute_vars
    from utils import CATALOGS_DIR

    if not os.path.exists(os.path.join(CATALOGS_DIR, "corpus_audit.csv")):
        pytest.skip("corpus data not present here")
    v = {}
    compute_vars.filter_stats(v)
    flagged = int(v["filter_flagged"].replace(",", ""))
    protected = int(v["filter_protected"].replace(",", ""))
    stage = flow_table[flow_table["Stage"].str.contains("Quality filtering")].iloc[0]
    assert flagged - protected == stage["Removed"]


@pytest.mark.slow
def test_audit_buckets_are_exhaustive_and_sum_to_raw():
    """The guard that would have caught the original defect: every audit row
    belongs to one of the three known buckets, and together they account for
    every raw record."""
    from utils import CATALOGS_DIR

    audit_path = os.path.join(CATALOGS_DIR, "corpus_audit.csv")
    unified_path = os.path.join(CATALOGS_DIR, "unified_works.csv")
    if not (os.path.exists(audit_path) and os.path.exists(unified_path)):
        pytest.skip("corpus data not present here")

    audit = pd.read_csv(audit_path, usecols=["action"])
    buckets = compute_corpus_flow.audit_buckets(audit)
    n_unified = len(pd.read_csv(unified_path, usecols=["source"]))
    assert sum(buckets.values()) == len(audit) == n_unified
