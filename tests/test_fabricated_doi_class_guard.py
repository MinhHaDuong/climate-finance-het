"""Standing class guard: no known-fabricated DOI may appear in any script.

The LLM-fabricated DOI ``10.1016/0301-4215(92)90024-V`` (an unrelated
energy-demand paper; Manne & Richels 1992 is a MIT Press *book* with no
Crossref DOI) was removed three times, each caught only after the fact:
``main.bib`` (0188/#928), ``scout_tradition_coupling.py`` ANCHORS (0201/#943),
and ``archive_traditions/detect_traditions_v3.py`` (0209). Three instances of
one fabricated string is a class, not a coincidence.

The prior guards are file-scoped: ``tests/test_bib_doi_title.py`` scans only
``main.bib``; ``tests/test_scout_anchors.py`` only the scout dict. Neither
covers ``archive_traditions/`` — and ``tests/test_script_hygiene.py`` explicitly
skips ``scripts/archive/`` (and would skip nothing under ``archive_traditions/``
only by accident of its walk). This guard scans **every** ``scripts/**/*.py``,
archived or not, against an extensible set. A future discovery adds one line to
``FABRICATED_DOIS``.

Matching is case-insensitive: the string appears as ``...90024-V`` in main.bib
and ``...90024-v`` in the archived detector.
"""

import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO / "scripts"

# Known LLM-fabricated DOIs. Add one line per confirmed fabrication.
# - 10.1016/0301-4215(92)90024-V: resolves to an unrelated energy-demand paper;
#   Manne & Richels 1992 ("Buying Greenhouse Insurance") is a MIT Press book
#   with no Crossref DOI. Removed by 0188/#928, 0201/#943, 0209.
FABRICATED_DOIS = [
    "10.1016/0301-4215(92)90024-V",
]


def _all_script_files():
    """Yield every .py file under scripts/, including archived subtrees.

    Unlike test_script_hygiene._all_scripts(), this deliberately does NOT
    skip archive/ or archive_traditions/: a fabricated DOI in dead code is a
    latent copy source and must be purged everywhere.
    """
    for dirpath, _dirnames, filenames in os.walk(SCRIPTS_DIR):
        for f in filenames:
            if f.endswith(".py"):
                yield Path(dirpath) / f


def test_no_fabricated_doi_in_any_script():
    """No script anywhere under scripts/ may contain a known-fabricated DOI."""
    needles = [d.casefold() for d in FABRICATED_DOIS]
    offenders = []
    for path in _all_script_files():
        text = path.read_text(encoding="utf-8", errors="replace").casefold()
        for needle, original in zip(needles, FABRICATED_DOIS):
            if needle in text:
                rel = path.relative_to(REPO)
                offenders.append(f"{rel}: {original}")
    assert not offenders, "Fabricated DOI(s) found in scripts:\n" + "\n".join(
        offenders
    )
