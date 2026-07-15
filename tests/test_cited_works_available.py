"""Exit condition: every cited work has local fulltext (or an accepted exception).

Encodes the harness norm "cite only what you keep locally": every work cited
(`@key`) in the manuscripts must either carry a `file=` field in main.bib — its
PDF is in docs/articles/ — or be listed in config/no-fulltext-allowlist.txt as a
genuinely unattainable exception (paywalled book, closed article, tool/blog cite).

Reads files only; no subprocess, no network — a unit test, runs in check-fast.

When the harness is extracted, this test and the allowlist travel with it.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIB = ROOT / "deliverables" / "_shared" / "bibliography" / "main.bib"
ALLOWLIST = ROOT / "config" / "no-fulltext-allowlist.txt"
QMD_GLOBS = [
    "deliverables/*/*.qmd",
    "deliverables/**/*.qmd",
    "deliverables/_shared/_includes/**/*.md",
]

# pandoc citation key: @ at a word boundary, then key chars (Better BibTeX set).
CITE = re.compile(r"(?<!\w)@([\w][\w:.\-+/]*)")
ENTRY_HEAD = re.compile(r"(?m)^@[a-zA-Z]+\{([^,]+),")


def _bib_keys_and_fulltext() -> tuple[set[str], set[str]]:
    text = BIB.read_text(encoding="utf-8")
    all_keys, has_file = set(), set()
    for chunk in re.split(r"(?m)^(?=@[a-zA-Z]+\{)", text):
        m = ENTRY_HEAD.match(chunk)
        if not m:
            continue
        key = m.group(1)
        all_keys.add(key)
        if re.search(r"(?mi)^\s*file\s*=", chunk):
            has_file.add(key)
    return all_keys, has_file


def _cited_keys() -> set[str]:
    keys = set()
    for pat in QMD_GLOBS:
        for f in ROOT.glob(pat):
            for m in CITE.findall(f.read_text(encoding="utf-8", errors="ignore")):
                keys.add(m.rstrip(".,;:"))
    return keys


def _allowlist() -> set[str]:
    if not ALLOWLIST.exists():
        return set()
    out = set()
    for line in ALLOWLIST.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(line)
    return out


def test_cited_works_have_local_fulltext():
    """Every cited bib entry has a file= field or is allowlisted."""
    all_keys, has_file = _bib_keys_and_fulltext()
    cited_in_bib = _cited_keys() & all_keys
    allowed = _allowlist()
    missing = sorted(cited_in_bib - has_file - allowed)
    assert not missing, (
        f"{len(missing)} cited work(s) lack local fulltext and are not allowlisted:\n  "
        + "\n  ".join(missing)
        + "\n\nEither add docs/articles/<key>.pdf + a file= field in main.bib, "
        "or add the key to config/no-fulltext-allowlist.txt if it is genuinely "
        "unattainable (paywalled book, closed article, tool/blog cite)."
    )


def test_allowlist_has_no_redundant_entries():
    """An allowlisted key that now has fulltext should be removed from the list."""
    _, has_file = _bib_keys_and_fulltext()
    redundant = sorted(_allowlist() & has_file)
    assert not redundant, (
        f"{len(redundant)} allowlist entr(y/ies) now have local fulltext — "
        f"remove from config/no-fulltext-allowlist.txt:\n  " + "\n  ".join(redundant)
    )


def test_allowlist_entries_are_real_bib_keys():
    """Guard against typos: every allowlist entry must exist in main.bib."""
    all_keys, _ = _bib_keys_and_fulltext()
    unknown = sorted(_allowlist() - all_keys)
    assert not unknown, (
        f"{len(unknown)} allowlist entr(y/ies) are not bib keys (typo/stale?):\n  "
        + "\n  ".join(unknown)
    )
