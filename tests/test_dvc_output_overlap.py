"""DVC outputs must not nest inside one another (ticket 0430).

DVC forbids overlapping outputs: if two objects own a path, neither can
authoritatively restore or invalidate it. It enforces this at *graph
construction*, so an overlap does not degrade the pipeline — it refuses it.
``dvc repro`` and ``dvc dag`` both abort before running a single stage.

The failure that motivated this guard hid for weeks because every cheap check
sidesteps the graph. ``dvc status <path>.dvc``, ``dvc commit``, ``dvc push``
and even a bare ``dvc status`` all succeed while ``dvc repro`` is dead.

This guard reads the declarations rather than invoking DVC, so it runs in the
fast tier and needs neither the corpus nor a DVC remote.
"""

import os

import pytest
import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DVC_YAML = os.path.join(BASE_DIR, "dvc.yaml")


def _out_path(entry):
    """Extract the path from an out entry.

    Two shapes, and confusing them makes the guard pass vacuously. In
    ``dvc.yaml`` an out is a bare string or a single-key mapping of
    ``path -> options``. In a ``.dvc`` file it is a mapping carrying the hash
    fields *first* (``md5``, ``size``, ``nfiles``, ``hash``, ``path``), so
    taking the first key yields the checksum rather than the path.
    """
    if not isinstance(entry, dict):
        return entry
    if "path" in entry:
        return entry["path"]
    return next(iter(entry))


def declared_outputs():
    """Every DVC-tracked path: ``dvc.yaml`` stage outs plus every ``*.dvc`` file.

    Returns ``(path, owner)`` pairs, repo-relative and normalised, where owner
    names the declaring stage or ``.dvc`` file — the guard's message is only
    useful if it can say which two objects collide.
    """
    found = []

    with open(DVC_YAML, encoding="utf-8") as fh:
        pipeline = yaml.safe_load(fh) or {}
    for stage, spec in (pipeline.get("stages") or {}).items():
        for kind in ("outs", "metrics", "plots"):
            for entry in (spec.get(kind) or []):
                found.append((os.path.normpath(_out_path(entry)), stage))

    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in {".git", ".venv", ".dvc", "node_modules"}]
        for name in files:
            if not name.endswith(".dvc"):
                continue
            dvc_file = os.path.join(root, name)
            with open(dvc_file, encoding="utf-8") as fh:
                spec = yaml.safe_load(fh) or {}
            # A .dvc file's `path` is relative to the file's own directory.
            for entry in (spec.get("outs") or []):
                path = _out_path(entry)
                abs_path = os.path.normpath(os.path.join(root, path))
                rel_owner = os.path.relpath(dvc_file, BASE_DIR)
                found.append((os.path.relpath(abs_path, BASE_DIR), rel_owner))

    return found


def _nested_output_pairs():
    """Return ``"a (owner) contains b (owner)"`` for each nesting violation."""
    outs = declared_outputs()
    violations = []
    for parent, powner in outs:
        for child, cowner in outs:
            if parent == child and powner == cowner:
                continue
            if child == parent:
                continue
            if child.startswith(parent + os.sep):
                violations.append(f"{parent} ({powner}) contains {child} ({cowner})")
    return sorted(set(violations))


@pytest.mark.adherence
def test_no_dvc_output_nested_inside_another():
    """Overlapping outs make dvc repro refuse to build the graph at all.

    Not a style rule: DVC rejects the *declaration*, so the pipeline is
    unreproducible from the moment the overlap lands, whether or not the file
    exists yet. Ticket 0430 — `run_reports/` was tracked as a directory while
    `dvc.yaml` separately declared `run_reports/catalog_merge.json`.
    """
    overlaps = _nested_output_pairs()
    assert not overlaps, (
        "DVC forbids overlapping outputs; dvc repro and dvc dag abort at graph "
        "construction while every per-target command still reports healthy:\n  "
        + "\n  ".join(overlaps)
        + "\nDeclare the inner path outside the tracked directory, or let one "
        "object own it."
    )


@pytest.mark.adherence
def test_discovery_sees_both_declaration_sources():
    """A guard driven by discovery passes vacuously if discovery finds nothing.

    Both sources must be live: `dvc.yaml` stage outs and standalone `.dvc`
    files. The 0430 overlap spanned exactly those two, so a guard reading only
    one of them would have been blind to it.
    """
    outs = declared_outputs()
    owners = {owner for _, owner in outs}
    assert any(o.endswith(".dvc") for o in owners), "no .dvc file outputs discovered"
    assert any(not o.endswith(".dvc") for o in owners), "no dvc.yaml stage outputs discovered"

    # Paths, not just owners. The first draft read a .dvc entry's leading `md5`
    # key as its path, so every .dvc output was a 32-char hex string: discovery
    # looked populated, no path could ever nest, and the guard passed on a tree
    # that DVC itself rejects.
    paths = [p for p, _ in outs]
    assert all("/" in p or p.endswith((".csv", ".json", ".npz")) for p in paths), (
        f"outputs do not look like paths, discovery is misreading entries: {paths[:5]}"
    )
    assert any(p.startswith("data" + os.sep) for p in paths), (
        f"no output under data/, discovery is misreading entries: {paths[:5]}"
    )
