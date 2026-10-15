#!/usr/bin/env bash
# Cut a LanguageLab release: bump the version, merge the bump through a PR, tag it and wait for
# release.yml to attach the wheel.
#
# Usage: scripts/cut_release.sh X.Y.Z
#
# Run it on the development machine, from a clean checkout. Steps:
#   1. update main; refuse if the tag already exists or the new version isn't higher
#   2. on branch release-X.Y.Z: bump pyproject.toml, `uv lock`, move the wheel URLs in the docs
#   3. lint and the docs-consistency test, then commit, push and open a PR
#   4. wait for the PR's checks, merge it, tag main as vX.Y.Z and push the tag
#   5. wait for release.yml and print the wheel URL
# It asks once before pushing anything.

set -euo pipefail

REPO_URL="https://github.com/shapovalex/language-learner"

die() { echo "error: $*" >&2; exit 1; }

[[ $# -eq 1 ]] || die "usage: scripts/cut_release.sh X.Y.Z"
new="$1"
[[ "$new" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "version must look like 1.2.3, got '$new'"
tag="v$new"
branch="release-$new"

for tool in git gh uv make; do
  command -v "$tool" >/dev/null || die "$tool is not installed"
done

cd "$(git rev-parse --show-toplevel)"

git diff --quiet && git diff --cached --quiet || die "commit or stash your changes first"

echo "==> Updating main"
git fetch --quiet --tags origin
git checkout --quiet main
git pull --quiet --ff-only origin main

old="$(sed -n 's/^version = "\(.*\)"$/\1/p' pyproject.toml)"
[[ -n "$old" ]] || die "cannot read the version from pyproject.toml"
[[ "$(printf '%s\n%s\n' "$old" "$new" | sort -V | tail -1)" == "$new" && "$old" != "$new" ]] \
  || die "$new is not higher than the current version $old"
git rev-parse -q --verify "refs/tags/$tag" >/dev/null && die "tag $tag already exists"
git ls-remote --exit-code --heads origin "$branch" >/dev/null && die "branch $branch already exists on origin"

open_prs="$(gh pr list --base main --state open --json number,title --jq '.[] | "  #\(.number) \(.title)"')"
echo
echo "About to release $old -> $new: open a bump PR, merge it, push tag $tag."
if [[ -n "$open_prs" ]]; then
  echo "These PRs are still open and will NOT be in $tag:"
  echo "$open_prs"
fi
read -r -p "Continue? [y/N] " answer
[[ "$answer" == "y" || "$answer" == "Y" ]] || die "cancelled"

echo "==> Bumping $old -> $new on $branch"
git checkout --quiet -b "$branch"
sed -i.bak "s/^version = \"$old\"$/version = \"$new\"/" pyproject.toml && rm pyproject.toml.bak
uv lock --quiet
# The uvx lines in the docs point at the release wheel (tests/unit/test_docs_consistency.py)
old_path="v$old/language_lab-$old-"
new_path="v$new/language_lab-$new-"
while IFS= read -r doc; do
  sed -i.bak "s#$old_path#$new_path#g" "$doc" && rm "$doc.bak"
done < <(git grep -l -F "$old_path" -- README.md docs/)

echo "==> Checking"
make lint
uv run pytest -q tests/unit/test_docs_consistency.py

git add pyproject.toml uv.lock README.md docs/
git commit --quiet -m "chore(release): bump version to $new"

echo "==> Opening the bump PR"
git push --quiet -u origin "$branch"
pr_url="$(gh pr create --base main --head "$branch" \
  --title "chore(release): bump version to $new" \
  --body "Bumps the version to $new and moves the wheel URLs in the docs. Opened by scripts/cut_release.sh, which tags $tag after merging.")"
echo "$pr_url"

echo "==> Waiting for the PR's checks"
sleep 10 # let GitHub register the checks before watching them
gh pr checks "$pr_url" --watch --fail-fast || die "the PR's checks failed: $pr_url"

echo "==> Merging and tagging"
gh pr merge "$pr_url" --merge --delete-branch
git checkout --quiet main
git pull --quiet --ff-only origin main
[[ "$(sed -n 's/^version = "\(.*\)"$/\1/p' pyproject.toml)" == "$new" ]] \
  || die "main does not have version $new after the merge"
git tag "$tag"
git push --quiet origin "$tag"

echo "==> Waiting for release.yml on $tag"
run_id=""
for _ in $(seq 1 30); do
  run_id="$(gh run list --workflow release.yml --branch "$tag" --limit 1 \
    --json databaseId --jq '.[0].databaseId // empty')"
  [[ -n "$run_id" ]] && break
  sleep 5
done
[[ -n "$run_id" ]] || die "release.yml did not start for $tag; check the Actions tab"
gh run watch "$run_id" --exit-status || die "release.yml failed: $REPO_URL/actions/runs/$run_id"

echo
echo "Released $tag. Wheel:"
echo "$REPO_URL/releases/download/$tag/language_lab-$new-py3-none-any.whl"
