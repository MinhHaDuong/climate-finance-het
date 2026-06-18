#!/usr/bin/env bash
# Rotate a real .venv directory into a symlink to the shared env on /data.
#
# New worktrees already get a symlinked .venv from the post-checkout hook, but
# checkouts that predate that fix still carry a full real .venv (the main
# checkout's is ~2 GB on /home). This reclaims that space by replacing each real
# .venv with a symlink to the shared env, the same end state the hook produces.
#
# Idempotent: an existing symlink or absent .venv is left alone. Safe: a real
# .venv is never removed unless the shared env exists and no process holds the
# venv open.
#
# Usage: rotate-venv-to-shared.sh [CHECKOUT_PATH...]   (default: current dir)
# Override the shared env with SHARED_ENV=/path (used by tests).
set -euo pipefail

SHARED_ENV="${SHARED_ENV:-/data/envs/venv/oeconomia}"

log() { printf 'rotate-venv: %s\n' "$*" >&2; }

# Best-effort: report whether a process holds files under the venv open.
# Test lsof's OUTPUT, not its exit status: `lsof +D` exits non-zero even when it
# successfully lists open files (it warns on dirs it cannot fully stat), so the
# exit code is useless here — non-empty output is the reliable "in use" signal.
venv_in_use() {
    if ! command -v lsof >/dev/null 2>&1; then
        log "warning: lsof not found — cannot verify $1 is idle; proceeding"
        return 1
    fi
    [ -n "$(lsof +D "$1" 2>/dev/null)" ]
}

rotate_one() {
    local target="$1"
    local venv="$target/.venv"

    if [ -L "$venv" ]; then
        log "skip $venv (already a symlink)"
        return 0
    fi
    if [ ! -e "$venv" ]; then
        log "skip $venv (absent)"
        return 0
    fi
    if [ ! -d "$venv" ]; then
        log "skip $venv (not a directory)"
        return 0
    fi
    if [ ! -d "$SHARED_ENV" ]; then
        log "skip $venv (shared env $SHARED_ENV absent — not removing real venv)"
        return 0
    fi
    if venv_in_use "$venv"; then
        log "skip $venv (in use by a running process)"
        return 0
    fi

    log "rotating $venv -> $SHARED_ENV"
    rm -rf -- "$venv"
    ln -sfn "$SHARED_ENV" "$venv"
}

main() {
    local -a targets=("$@")
    [ "${#targets[@]}" -gt 0 ] || targets=(".")
    for t in "${targets[@]}"; do
        rotate_one "$t"
    done
}

main "$@"
