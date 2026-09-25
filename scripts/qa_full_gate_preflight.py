#!/usr/bin/env python3
"""Check the machine-owned prerequisites of the complete test gate."""

import argparse
import logging
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

REQUIRED_CORPUS_ARTIFACTS = (
    "catalogs/refined_works.csv", "catalogs/corpus_audit.csv",
    "catalogs/embeddings.npz", "catalogs/citations.csv",
    "catalogs/refined_embeddings.npz", "catalogs/refined_citations.csv",
)
RERANKER_CACHE = "catalogs/llm_relevance_cache.csv"
EXPECTED_CRS_MICRO_FILES = 80


def _default_cache_dir() -> Path:
    configured = os.environ.get("UV_CACHE_DIR")
    if configured:
        return Path(configured)
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "uv"


def _is_writable_directory(path: Path) -> bool:
    """Return whether a cache directory can receive uv's task files."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=path):
            pass
    except OSError:
        return False
    return True


def _can_bind_local_socket() -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
    except OSError:
        return False
    return True


def _git_worktree_area_is_available(repo: Path) -> bool:
    """Check Git's administrative directory without creating a worktree."""
    result = subprocess.run(
        ["git", "rev-parse", "--git-path", "worktrees"], cwd=repo,
        capture_output=True, text=True,
    )
    return not result.returncode and _is_writable_directory(Path(result.stdout.strip()))


def check(args: argparse.Namespace) -> list[str]:
    """Return unmet full-gate prerequisites as human-actionable messages."""
    failures: list[str] = []
    missing = [item for item in REQUIRED_CORPUS_ARTIFACTS if not (args.data_dir / item).is_file()]
    if missing:
        failures.append(
            "Corpus artifacts are not materialized in this worktree: "
            + ", ".join(missing)
            + ". Provision existing DVC data locally with `make data` "
            + "(`uv run dvc checkout`); use `make corpus-sync` only when the "
            + "shared cache lacks the current data."
        )
    if not (args.data_dir / RERANKER_CACHE).is_file():
        failures.append(
            "Reranker cache is absent: llm_relevance_cache.csv. It is required "
            "by the existing acceptance check but is not a DVC artifact; its "
            "source ownership and recovery route are tracked by ticket 0592."
        )
    crs_dir = args.data_dir / "jetp/crs"
    crs_files = list(crs_dir.glob("*_micro.csv.gz")) if crs_dir.is_dir() else []
    if len(crs_files) != EXPECTED_CRS_MICRO_FILES:
        failures.append(
            f"Pinned JETP CRS inputs are incomplete: found {len(crs_files)} of "
            f"{EXPECTED_CRS_MICRO_FILES} *_micro.csv.gz files in {crs_dir}. "
            "Run `make jetp-crs-data` to pull the archived DVC inputs before "
            "the full gate."
        )
    if not _is_writable_directory(args.uv_cache_dir):
        failures.append(
            f"Configured UV_CACHE_DIR is not writable: {args.uv_cache_dir}. "
            "Set UV_CACHE_DIR to a directory you own (for example "
            "`$XDG_CACHE_HOME/uv`) before running the full gate."
        )
    if not args.skip_local_socket_check and not _can_bind_local_socket():
        failures.append(
            "The full gate needs permission to bind a local TCP socket for its "
            "local-server integration test. Run it outside the socket-restricted sandbox."
        )
    if not args.skip_git_check and not _git_worktree_area_is_available(args.repo):
        failures.append(
            "The full gate needs write access to Git worktree administration "
            "for post-checkout integration tests. Run it from a writable clone "
            "outside the Git-metadata-restricted sandbox."
        )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("CLIMATE_FINANCE_DATA", "data")))
    parser.add_argument("--uv-cache-dir", type=Path, default=_default_cache_dir())
    parser.add_argument("--skip-local-socket-check", action="store_true")
    parser.add_argument("--skip-git-check", action="store_true")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    failures = check(args)
    if not failures:
        return 0
    logging.basicConfig(format="%(message)s", level=logging.ERROR, stream=sys.stderr)
    logging.error("Full-gate preflight failed:")
    for failure in failures:
        logging.error("- %s", failure)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
