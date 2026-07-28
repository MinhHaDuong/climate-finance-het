#!/usr/bin/env bash
# dvc_lock_gate.sh — report what a corpus re-run changed; never publish it.
#
# Ticket 0362. This used to be the tail of run_corpus_pipeline.sh, where it
# branched, committed dvc.lock, merged into main and `git push origin main`.
# That bypassed the branch-and-PR gate every other change in this repo goes
# through, and it removed the checkpoint a pending corpus change relies on:
# a config or code edit that alters the corpus would be executed *and*
# published by the next `make corpus`, with no human confirmation.
#
# The refusal lives in its own file so it can be driven directly by a test —
# the pipeline script's own guards (padme, dvc, GROBID, main) make its tail
# unreachable in a throwaway repo.
#
# Exit status: 0 when nothing changed or when files other than dvc.lock
# changed (the pre-existing warning path, unchanged); 1 when dvc.lock changed,
# so `make corpus` fails loudly and the operator commits it via branch + PR.
#
# Usage: bash scripts/dvc_lock_gate.sh   (run from the repository root)

set -euo pipefail

changed=$(git status --porcelain)

if [ -z "$changed" ]; then
    echo "dvc.lock unchanged, nothing to commit."
elif [ "$(echo "$changed" | sed 's/^...//')" = "dvc.lock" ]; then
    echo ""
    echo "REFUSING to publish: the pipeline re-run changed dvc.lock."
    echo ""
    git --no-pager diff -- dvc.lock || true
    echo ""
    echo "dvc.lock is left uncommitted in the working tree. Publishing a corpus"
    echo "change is a human decision (ticket 0362): review the diff above, then"
    echo "land it on a branch and open a merge request —"
    echo ""
    echo "    git switch -c data-dvclock-\$(date +%Y%m%d)"
    echo "    git add dvc.lock && git commit -m 'data: update dvc.lock after pipeline re-run'"
    echo "    git push -u origin HEAD && gh pr create"
    echo ""
    exit 1
else
    echo ""
    echo "WARNING: files other than dvc.lock changed:"
    echo "$changed"
    echo "Stage and commit manually."
fi
