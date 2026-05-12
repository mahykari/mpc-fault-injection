#!/usr/bin/env bash
# Build the patched mascot-party.x inside Docker, extract to
# MP-SPDZ/bin/Linux-amd64-patched/. Re-run any time patches change;
# subsequent rebuilds are fast thanks to Docker layer caching.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

IMAGE_TAG="mpspdz-patched:v0.4.2"
OUT_DIR="MP-SPDZ/bin/Linux-amd64-patched"

echo "==> Building $IMAGE_TAG"
docker build \
  --file docker/Dockerfile.mpspdz \
  --target builder \
  --tag "$IMAGE_TAG" \
  .

echo "==> Extracting mascot-party.x to $OUT_DIR/"
mkdir -p "$OUT_DIR"
container_id="$(docker create "$IMAGE_TAG")"
trap 'docker rm "$container_id" >/dev/null' EXIT
docker cp "$container_id:/src/mp-spdz-0.4.2/static/mascot-party.x" "$OUT_DIR/mascot-party.x"

echo "==> Done"
ls -la "$OUT_DIR/mascot-party.x"
file "$OUT_DIR/mascot-party.x"
