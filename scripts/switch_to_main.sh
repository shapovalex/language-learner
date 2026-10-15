#!/usr/bin/env bash

set -euo pipefail

REPO_URL="https://github.com/shapovalex/language-learner"

die() { echo "error: $*" >&2; exit 1; }

for tool in git gh; do
  command -v "$tool" >/dev/null || die "$tool is not installed"
done

cd "$(git rev-parse --show-toplevel)"

git diff --quiet && git diff --cached --quiet || die "commit or stash your changes first"

echo "==> Updating main"
git fetch --quiet --tags origin
git checkout --quiet main
git pull --quiet --ff-only origin main
