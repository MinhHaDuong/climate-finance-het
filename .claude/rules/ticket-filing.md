---
paths:
  - "tickets/**"
---

# Ticket filing (project-specific)

Split from `git.md`: the fast path for tickets-only PRs and the ID-collision scan that is its gate.

- **Ticket-filing PRs take the fast path.** A PR whose diff is only `tickets/*.erg` merges on `erg check` plus an ID-collision scan: no draft, no `/verify`, no review request. `main` is unprotected and there is no CI, so nothing gates such a PR and `allow_auto_merge` would wait on an empty requirement set. Use `Ticket-ref:` so the filing PR does not close the ticket it files. Code PRs follow the checks and review requirements in `AGENTS.md`.
- **The ID-collision scan is the one real risk on that fast path, and it has three failure modes worth naming** (all three fired on 2026-07-27: one filing collided three times, and `origin/main` failed `erg check` on a duplicate ID twice).
  - *Scanning open PRs with `gh pr list --json files` is not scanning.* `gh pr list` does not populate `files`, so a list-plus-filter returns empty regardless of content — "no collision" and "I never looked" are the same output. Enumerate, then query each PR:
    ```bash
    for n in $(gh pr list --state open --limit 60 --json number --jq '.[].number'); do
      gh pr view "$n" --json files --jq '.files[].path' | grep -q "tickets/$ID" && echo "PR $n uses $ID"
    done
    ```
  - *On collision, renumber clear of the frontier — never to the next free ID.* Every parallel session computes the same next-free value and races for it, so that renumber is as collision-prone as the original allocation. 0384 → 0385 → 0386 each collided in turn; 0400, twelve above the frontier, held first try. IDs are free and a gap costs nothing.
  - *Verify after merging, against `origin/main`.* Since this repo has no CI, `erg check` on the branch is the only gate — and it passes by construction, because each branch's IDs are unique within itself. It structurally cannot see a cross-PR duplicate. Run `erg check tickets/` against `origin/main` once the PR lands; that is the only check that catches a duplicate which has already shipped.
