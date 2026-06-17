#!/usr/bin/env bash
# Build MP-SPDZ artifacts with podman, reusing layer caching across re-runs.
#
#   ./containers/build.sh             # base patches → binary into MP-SPDZ/bin/Linux-amd64-patched/
#   ./containers/build.sh seeded-bug  # base + seeded-bug overlay → Linux-amd64-patched-seeded-bug/
#   ./containers/build.sh pipeline    # full fuzz-pipeline image (runtime stage); needs SSH agent
#
# The binary variants build the `builder` stage and extract static/mascot-party.x
# to the host. `pipeline` builds the `runtime` stage into a runnable image.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

CONTAINERFILE="containers/Containerfile"
VARIANT="${1:-patched}"

if [ "$VARIANT" = "pipeline" ]; then
  IMAGE_TAG="mpspdz-pipeline:v0.4.2"
  echo "==> Building $IMAGE_TAG (runtime stage)"
  podman build \
    --file "$CONTAINERFILE" \
    --target runtime \
    --tag "$IMAGE_TAG" \
    .
  echo "==> Done: $IMAGE_TAG"
  exit 0
fi

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
    echo "usage: $0 [patched|seeded-bug|pipeline]" >&2
    exit 1
    ;;
esac

echo "==> Building $IMAGE_TAG (APPLY_SEEDED_BUG=$APPLY_SEEDED_BUG)"
podman build \
  --file "$CONTAINERFILE" \
  --target builder \
  --tag "$IMAGE_TAG" \
  --build-arg APPLY_SEEDED_BUG="$APPLY_SEEDED_BUG" \
  .

echo "==> Extracting mascot-party.x to $OUT_DIR/"
mkdir -p "$OUT_DIR"
container_id="$(podman create "$IMAGE_TAG")"
trap 'podman rm "$container_id" >/dev/null' EXIT
podman cp "$container_id:/src/mp-spdz-0.4.2/static/mascot-party.x" "$OUT_DIR/mascot-party.x"

echo "==> Done"
ls -la "$OUT_DIR/mascot-party.x"
file "$OUT_DIR/mascot-party.x"
