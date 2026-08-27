#!/usr/bin/env bash
# Put python-circil on disk at the commit this repo's code expects.
#
# python-circil is gitignored: it is a sibling clone, not a tracked subtree, so
# nothing in git records which version the code needs. This script is that
# record. Run it after cloning the repo, and again whenever CIRCIL_COMMIT moves.
#
#   ./scripts/setup-circil.sh
#
# The API is not stable across circil commits. Two renames that will bite you
# if the checkout drifts: FuzzerConfig.enable_fixed_size_array became
# enable_array, and Custom.constructor() became a staticmethod returning a
# templated spec. Code written against one side of those does not run on the
# other, which is exactly why the version is pinned here.
set -euo pipefail

CIRCIL_REMOTE="git@github.com:Rigorous-Software-Engineering/python-circil.git"
CIRCIL_COMMIT="c9ad6876558a85c6bc5b3644328a07245392284f"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$REPO_ROOT/python-circil"

if [ ! -d "$TARGET/.git" ]; then
  echo "==> cloning python-circil into $TARGET"
  git clone "$CIRCIL_REMOTE" "$TARGET"
fi

echo "==> checking out $CIRCIL_COMMIT"
git -C "$TARGET" fetch --quiet origin
git -C "$TARGET" checkout --quiet "$CIRCIL_COMMIT"
git -C "$TARGET" --no-pager log --oneline -1
