#!/usr/bin/env bash
# run_corpus_pipeline.sh — Run the full DVC corpus pipeline on padme.
#
# Env policy: .env holds no secret (ticket 0343). Credentials live in
# ~/.config/keys/<provider>.env, are selected by the KEYS= line in .env, and
# reach the environment through the keystore loader that the Makefile wires in
# via BASH_ENV. Never via command-line KEY=value — that leaks to `ps`.
#
# Guards: hostname must be padme, dvc must be installed, branch must be main.
# After dvc repro + push, scripts/dvc_lock_gate.sh reports what changed. It
# never commits and never pushes: a dvc.lock change exits non-zero so the
# operator lands it via branch + merge request (ticket 0362).
#
# Usage: bash scripts/run_corpus_pipeline.sh
#   (or invoked via `make corpus`)

set -euo pipefail

PROJ_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJ_ROOT"

# --- Credentials (ticket 0343) ---
# `make corpus` gets these from the loader the Makefile wires in via BASH_ENV.
# The documented direct invocation does not: a plain terminal has no BASH_ENV
# set, so nothing would apply the KEYS= selection and every API call would run
# unauthenticated. Load it here so both entry points behave the same.
# Must follow the cd — the loader reads $PWD/.env to find the KEYS= line.
KEYSTORE_LOADER="${KEYSTORE_LOADER:-$HOME/.claude/scripts/bash-env.sh}"
if [ -z "${OPENALEX_API_KEY:-}" ] && [ -f "$KEYSTORE_LOADER" ]; then
    # shellcheck source=/dev/null
    . "$KEYSTORE_LOADER"
fi

# --- Guard: hostname ---
if [ "$(hostname)" != "padme" ]; then
    echo "error: make corpus runs on padme only. Use 'make corpus-sync' on $(hostname)."
    exit 1
fi

# --- Guard: dvc installed ---
if ! uv run --env-file .env dvc version >/dev/null 2>&1; then
    echo "error: dvc not found. Install with: uv tool install 'dvc[ssh]'"
    exit 1
fi

# --- Guard: GROBID reachable (start the container if not) ---
# The GROBID parse step degrades silently to cached parses when the service
# is down (2026-07-24: container had been exited for 3 months; the new
# keydoc fulltexts got no reference extraction until a forced re-run).
if ! curl -sf http://localhost:8070/api/isalive >/dev/null 2>&1; then
    echo "GROBID not reachable — starting the podman container..."
    podman start grobid || {
        echo "error: could not start the grobid container (podman start grobid)."
        exit 1
    }
    for _ in $(seq 1 30); do
        curl -sf http://localhost:8070/api/isalive >/dev/null 2>&1 && break
        sleep 2
    done
    if ! curl -sf http://localhost:8070/api/isalive >/dev/null 2>&1; then
        echo "error: GROBID container started but not answering on :8070."
        exit 1
    fi
    echo "GROBID up."
fi

# --- Guard: must be on main ---
current_branch="$(git rev-parse --abbrev-ref HEAD)"
if [ "$current_branch" != "main" ]; then
    echo "error: make corpus must run on main (currently on $current_branch)."
    exit 1
fi

# --- Run pipeline ---
ret=0
uv run --env-file .env dvc repro || ret=$?
uv run --env-file .env dvc push

if [ "$ret" -ne 0 ]; then
    exit "$ret"
fi

# --- Publication gate (ticket 0362) ---
# Reports what changed; never commits or pushes. Exits non-zero when dvc.lock
# changed, so publishing a corpus change stays a deliberate human step.
bash "$PROJ_ROOT/scripts/dvc_lock_gate.sh"
