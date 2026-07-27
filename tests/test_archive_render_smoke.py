"""Clean-room render smoke test for the manuscript archive (ticket 0292).

`test_archive_script_paths.py` proves every path the build script names resolves.
That is necessary and not sufficient: the archive that shipped before this ticket
listed paths which all existed, yet could not render, because it flattened them
into a `content/` tree where the manuscript's own `../_shared/...` references no
longer pointed at anything. Every path resolved in the repo; none resolved in the
archive.

So this test does the only thing that can catch that class: it builds the archive,
extracts it somewhere else entirely, and runs the reviewer's own Makefile there.
A reviewer with the tarball and nothing else must get a PDF.
"""

import os
import shutil
import subprocess
import tarfile

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BUILD_SCRIPT = os.path.join(REPO, "build", "build_manuscript_archive.sh")
TARBALL = os.path.join(REPO, "climate-finance-manuscript.tar.gz")
SHIPPED_PDF = os.path.join(REPO, "deliverables", "manuscript", "manuscript.pdf")
RENDERED = os.path.join("deliverables", "manuscript", "manuscript.pdf")


def _has_latex():
    """A LaTeX engine on PATH, or the TinyTeX distribution Quarto installs."""
    if shutil.which("xelatex"):
        return True
    return bool(
        os.path.isdir(os.path.expanduser("~/.TinyTeX"))
        or os.path.isdir(os.path.expanduser("~/.local/share/TinyTeX"))
    )


@pytest.mark.integration
def test_manuscript_archive_renders_in_clean_room(tmp_path):
    """The shipped archive must render a PDF outside the repo, from its own Makefile.

    Red before ticket 0292: the build script died copying a root `_quarto.yml`
    retired by the 0226 reorg, and the tree it assembled put the manuscript where
    its `../_shared/...` references resolved to nothing.
    """
    if not shutil.which("quarto"):
        pytest.skip("quarto not installed")
    if not _has_latex():
        pytest.skip("no LaTeX engine (xelatex or TinyTeX) available")
    if not os.path.isfile(SHIPPED_PDF):
        pytest.skip(f"no pre-built manuscript PDF — run `make manuscript` first ({SHIPPED_PDF})")

    # The build script writes the tarball into the repo root. Leave the tree as
    # we found it: a developer may have one there already.
    preexisting = os.path.isfile(TARBALL)
    backup = str(tmp_path / "preexisting.tar.gz")
    if preexisting:
        shutil.copy2(TARBALL, backup)

    try:
        build = subprocess.run(
            ["bash", BUILD_SCRIPT],
            cwd=REPO, capture_output=True, text=True, timeout=600,
        )
        assert build.returncode == 0, (
            "build_manuscript_archive.sh failed:\n"
            f"stdout:\n{build.stdout}\nstderr:\n{build.stderr}"
        )
        assert os.path.isfile(TARBALL), "build script reported success but wrote no tarball"

        cleanroom = tmp_path / "cleanroom"
        cleanroom.mkdir()
        with tarfile.open(TARBALL) as tar:
            # `filter=` landed in 3.12 and was backported to 3.10.12 / 3.11.4,
            # so a version comparison would be wrong on a patched 3.10. The
            # project declares requires-python >=3.10, and on 3.10.0-3.10.11
            # passing it raises TypeError — turning this guard into a hard
            # error. Key off the feature instead, per PEP 706.
            if hasattr(tarfile, "data_filter"):
                tar.extractall(cleanroom, filter="data")
            else:
                tar.extractall(cleanroom)
        root = cleanroom / "climate-finance-manuscript"
        assert root.is_dir(), f"unexpected archive top level: {os.listdir(cleanroom)}"

        # The reviewer's entry point, run exactly as the README documents it.
        render = subprocess.run(
            ["make"], cwd=str(root), capture_output=True, text=True, timeout=1800,
        )
        assert render.returncode == 0, (
            "the archive's own Makefile failed to render:\n"
            f"stdout:\n{render.stdout[-4000:]}\nstderr:\n{render.stderr[-4000:]}"
        )

        pdf = root / RENDERED
        assert pdf.is_file(), (
            f"make succeeded but produced no PDF at {RENDERED}. Make checks the "
            "recipe's exit code, not whether the target appeared, so a target "
            "naming a path Quarto never writes reports success while building "
            f"nothing. Archive tree: {sorted(os.listdir(root))}"
        )
        assert pdf.stat().st_size > 100_000, (
            f"rendered PDF is implausibly small ({pdf.stat().st_size} bytes)"
        )
    finally:
        if preexisting:
            shutil.move(backup, TARBALL)
        elif os.path.isfile(TARBALL):
            os.remove(TARBALL)
