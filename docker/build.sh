#!/usr/bin/env bash
# Build a patched mascot-party.x inside Docker, extract to
# MP-SPDZ/bin/Linux-amd64-patched[-seeded-bug]/. Re-run any time
# patches change; rebuilds are fast thanks to Docker layer caching.
#
# Variants:
#   ./docker/build.sh             # base patches only      → Linux-amd64-patched/
#   ./docker/build.sh seeded-bug  # base + seeded-bug overlay → Linux-amd64-patched-seeded-bug/

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VARIANT="${1:-patched}"
case "$VARIANT" in
  patched)
    IMAGE_TAG="mpspdz-patched:v0.4.2"
    OUT_DIR="MP-SPDZ/bin/Linux-amd64-patched"
    APPLY_SEEDED_BUG=0
    ;;
  seeded-bug)
    IMAGE_TAG="mpspdz-patched-seeded-bug:v0.4.2"
    OUT_DIR="MP-SPDZ/bin/Linux-amd64-patched-seeded-bug"
    APPLY_SEEDED_BUG=1
    ;;
  *)
    echo "usage: $0 [patched|seeded-bug]" >&2
    exit 1
    ;;
esac

echo "==> Building $IMAGE_TAG (APPLY_SEEDED_BUG=$APPLY_SEEDED_BUG)"
docker build \
  --file docker/Dockerfile.mpspdz \
  --target builder \
  --tag "$IMAGE_TAG" \
  --build-arg APPLY_SEEDED_BUG="$APPLY_SEEDED_BUG" \
  .

echo "==> Extracting mascot-party.x to $OUT_DIR/"
mkdir -p "$OUT_DIR"
container_id="$(docker create "$IMAGE_TAG")"
trap 'docker rm "$container_id" >/dev/null' EXIT
docker cp "$container_id:/src/mp-spdz-0.4.2/static/mascot-party.x" "$OUT_DIR/mascot-party.x"

echo "==> Done"
ls -la "$OUT_DIR/mascot-party.x"
file "$OUT_DIR/mascot-party.x"
