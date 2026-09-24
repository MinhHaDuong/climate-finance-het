#!/usr/bin/env bash
# Publish the JETP observatory's public bundle to the gh-pages branch (ticket 0915).
#
#   bash scripts/jetp/publish_observatory_pages.sh [--push] [REF]
#
# The bundle is the tracked tree of deliverables/jetp-observatory at REF
# (default: the local origin/main, the tree `make jetp-observatory-bundle`
# extracts for preview). The script commits that very tree object, unchanged,
# as the next gh-pages commit: no checkout, no index, no file rewritten.
# documents/ is git-ignored, so the tree cannot hold it; the script still
# refuses a tree that does.
#
# Without --push it only builds the commit and prints what it holds and the
# command that would push it: no network, no ref moved. With --push it fetches
# gh-pages to chain onto it and pushes without force, so a concurrent publish
# is refused rather than overwritten.
#
# Pushing gh-pages publishes nothing while GitHub Pages is disabled. Enabling
# Pages is the author's step, described in deliverables/jetp-observatory/README.md.
# There is no CI in this repository (ticket 0321): this script is the whole path.
set -euo pipefail

push=0
ref=origin/main
remote=origin
branch=gh-pages
site=deliverables/jetp-observatory

while [ $# -gt 0 ]; do
    case "$1" in
        --push) push=1 ;;
        -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
        -*) echo "unknown option: $1" >&2; exit 2 ;;
        *) ref=$1 ;;
    esac
    shift
done

source_commit=$(git rev-parse --verify "$ref^{commit}")
tree=$(git rev-parse --verify "$source_commit:$site")
if [ "$(git cat-file -t "$tree")" != tree ]; then
    echo "$site is not a directory at $ref" >&2
    exit 1
fi
# Listed first, then searched: under pipefail, `ls-tree | grep -q` can read as
# "absent" when grep exits early and ls-tree dies of SIGPIPE.
top=$(git ls-tree --name-only "$tree")
if grep -qx documents <<<"$top"; then
    echo "documents/ is tracked in the site tree at $ref; refusing to publish." >&2
    exit 1
fi
for required in index.html app.js .nojekyll data/overview.json; do
    git cat-file -e "$tree:$required" 2>/dev/null || {
        echo "$required is missing from the site tree at $ref; refusing to publish." >&2
        exit 1
    }
done

parent=
if [ "$push" -eq 1 ]; then
    if git ls-remote --exit-code --heads "$remote" "$branch" >/dev/null; then
        git fetch --quiet "$remote" "$branch"
        parent=$(git rev-parse --verify FETCH_HEAD^{commit})
    fi
else
    parent=$(git rev-parse --verify --quiet "refs/remotes/$remote/$branch^{commit}" || true)
fi

if [ -n "$parent" ] && [ "$(git rev-parse "$parent^{tree}")" = "$tree" ]; then
    echo "$branch already carries site tree $tree; nothing to publish."
    exit 0
fi

message="Publish the JETP observatory from $(git rev-parse --short "$source_commit")

Site tree $tree of $site at $source_commit ($ref)."
commit=$(git commit-tree "$tree" ${parent:+-p "$parent"} -m "$message")

echo "Publication commit $commit"
echo "  site tree $tree from $ref ($source_commit)"
files=$(git ls-tree -r --name-only "$commit")
echo "  $(wc -l <<<"$files") files; parent: ${parent:-none, first publication}"
if grep -q '^documents/' <<<"$files"; then
    echo "The publication commit holds documents/; refusing it." >&2
    exit 1
fi

if [ "$push" -eq 1 ]; then
    git push "$remote" "$commit:refs/heads/$branch"
    echo "Pushed to $remote/$branch. Pages stays off until the author enables it."
else
    echo "Dry run: nothing pushed. To publish: make jetp-observatory-publish JETP_PAGES_REF=$ref"
fi
