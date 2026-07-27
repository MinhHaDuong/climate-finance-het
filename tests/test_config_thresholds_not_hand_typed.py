"""No shared include hand-types a filtering threshold that config declares (ticket 0357).

A threshold typed into prose is a copy that nothing keeps in step: recalibrate
`config/corpus_filter.yaml` and the pipeline moves while the document does not.
The reranker threshold has already been recalibrated once, 0.0049 to 0.002, so
this is a defect the project has lived through rather than a hypothetical.

**Scope, and why it is narrow.** The guard scans for config values whose
literal form is a decimal fraction, and only for values the vars layer already
exposes as a `{{< meta >}}` macro — a number the prose *could* have resolved
through the pipeline and chose not to. It deliberately does not scan for the
integer thresholds (sigma 2, min_cited_by 50, prefix_length 200). Measured on
this corpus of prose, a standalone-token scan for "2" returns 138 hits across
the shared includes and "50" returns 29, essentially all of them section
numbers, tier labels, sample sizes, and unrelated cutoffs. A guard whose
signal-to-noise is that bad is an allowlist with a test wrapped around it, and
an allowlist that large rots into a mute skip.

What the guard *is* general over: the value comes from config at test time, so
recalibrating 0.002 to 0.003 re-aims the scan at 0.003 rather than blessing the
stale number. Any future float threshold exposed as a var is covered the day it
lands, with no edit here.

The registry side of the same ticket — that every macro a deliverable names
actually resolves — is `test_doc_vars_completeness.py` and
`test_meta_macro_resolution.py`. This guard covers the other direction: a number
that never became a macro at all.
"""

import re
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "corpus_filter.yaml"
INCLUDES_DIR = REPO_ROOT / "deliverables" / "_shared" / "_includes"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "analysis"))
from _vars_retrieval import retrieval_protocol_stats

#: Literals that only look like a config threshold. Each entry is
#: (include file, literal, why it is not the config value), and
#: `test_no_allowlist_entry_is_redundant` deletes it for you by failing once the
#: match is gone — so an entry cannot outlive the text it excuses.
ALLOWED = [
    (
        "temporal-structure.md",
        "0.002",
        "a k=2 EN/non-English silhouette score in the language-structure table, "
        "not the cross-encoder relevance threshold",
    ),
]


def _config_values() -> dict[str, str]:
    """Config-derived vars, as the string a macro would render."""
    values: dict[str, str] = {}
    retrieval_protocol_stats(values)
    return values


def _guarded_values() -> dict[str, str]:
    """The subset this guard scans for: decimal fractions (see module docstring)."""
    return {k: v for k, v in _config_values().items() if re.fullmatch(r"\d+\.\d+", v)}


def _includes() -> list[Path]:
    return sorted(INCLUDES_DIR.rglob("*.md"))


def _pattern(value: str) -> re.Pattern:
    """Match `value` as a standalone numeric token.

    The lookarounds exclude `.` on both sides so that 0.002 does not match
    inside 10.0025 or a DOI suffix.
    """
    return re.compile(r"(?<![\w.])" + re.escape(value) + r"(?![\w.])")


def _hits(value: str) -> list[tuple[str, int, str]]:
    """Every (file, line number, line) in the shared includes carrying `value`."""
    pattern = _pattern(value)
    found = []
    for path in _includes():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                found.append((path.name, lineno, line.strip()))
    return found


def _is_allowed(filename: str, value: str) -> bool:
    return any(f == filename and v == value for f, v, _ in ALLOWED)


def test_the_guard_scans_for_something():
    """A scan over an empty value set passes vacuously and forever.

    `retrieval_protocol_stats` is the only source of the guarded values; a
    rename there would silently empty the set, and every assertion below would
    then report an all-clear it never earned.
    """
    guarded = _guarded_values()
    assert guarded, (
        "no config-derived value has a decimal-fraction form — has "
        "_vars_retrieval stopped exposing the reranker threshold?"
    )
    assert _includes(), f"no shared include found under {INCLUDES_DIR}"


def test_the_guard_would_see_a_hand_typed_threshold(tmp_path):
    """Red-test the guard itself: it must find the value it is looking for.

    A scan that matches nothing is indistinguishable from a scan that found
    nothing, so prove the pattern fires on a line built to carry the defect
    before trusting it on the real includes.
    """
    value = _guarded_values()["filter_reranker_threshold"]
    line = f"Papers scoring below the calibrated threshold ({value}) are flagged."
    assert _pattern(value).search(line)
    assert not _pattern(value).search(line.replace(value, "{{< meta x >}}"))


@pytest.mark.parametrize("var", sorted(_guarded_values()))
def test_no_include_hand_types_a_config_threshold(var):
    """Every occurrence of a config threshold is a macro or an excused twin."""
    value = _guarded_values()[var]
    offenders = [h for h in _hits(value) if not _is_allowed(h[0], value)]
    assert not offenders, (
        f"{var} is {value} in config/corpus_filter.yaml, but {len(offenders)} "
        f"line(s) type it by hand — use {{{{< meta {var} >}}}} instead, or add "
        f"an ALLOWED entry saying why the number is unrelated:\n"
        + "\n".join(f"  {f}:{n}  {t}" for f, n, t in offenders)
    )


@pytest.mark.parametrize("entry", ALLOWED, ids=lambda e: f"{e[0]}-{e[1]}")
def test_no_allowlist_entry_is_redundant(entry):
    """An excuse outlives its line silently; make it fail loudly instead."""
    filename, value, _reason = entry
    assert any(h[0] == filename for h in _hits(value)), (
        f"ALLOWED entry ({filename}, {value}) matches nothing — the line it "
        f"excused is gone, so drop the entry"
    )
