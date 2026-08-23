#!/usr/bin/env bash
# Build MP-SPDZ artifacts with podman, reusing layer caching across re-runs.
#
#   ./containers/build.sh             # base patches → binaries into MP-SPDZ/bin/Linux-amd64-patched/
#   ./containers/build.sh seeded-bug  # base + seeded-bug overlay → Linux-amd64-patched-seeded-bug/
#   ./containers/build.sh pipeline    # fuzz-pipeline image (runtime stage, base patches)
#   ./containers/build.sh pipeline-seeded-bug  # fuzz-pipeline image with seeded-bug patches
#
# The binary variants build the `builder` stage and extract the static party
# binaries to the host. `pipeline` builds the `runtime` stage into a runnable
# image. PARTY_BINARIES (per variant) selects which protocols to build: the
# base/pipeline variants build all malicious targets; the seeded-bug variants
# stay mascot-only (that campaign toggles mascot's Check() sites).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

CONTAINERFILE="containers/Containerfile"
VARIANT="${1:-patched}"

ALL_PROTOCOLS="mascot-party.x spdz2k-party.x malicious-shamir-party.x"

# bare names ("a-party.x b-party.x") -> make targets ("static/a-party.x static/b-party.x")
make_targets() { local t=""; for b in $1; do t="$t static/$b"; done; echo "$t"; }

if [ "$VARIANT" = "pipeline" ] || [ "$VARIANT" = "pipeline-seeded-bug" ]; then
  if [ "$VARIANT" = "pipeline-seeded-bug" ]; then
    IMAGE_TAG="mpspdz-pipeline-seeded-bug:v0.4.3"
    APPLY_SEEDED_BUG=1
    PARTY_BINARIES="mascot-party.x"
  else
    IMAGE_TAG="mpspdz-pipeline:v0.4.3"
    APPLY_SEEDED_BUG=0
    PARTY_BINARIES="$ALL_PROTOCOLS"
  fi
  echo "==> Building $IMAGE_TAG (runtime stage, APPLY_SEEDED_BUG=$APPLY_SEEDED_BUG)"
  podman build \
    --file "$CONTAINERFILE" \
    --target runtime \
    --tag "$IMAGE_TAG" \
    --build-arg APPLY_SEEDED_BUG="$APPLY_SEEDED_BUG" \
    --build-arg PARTY_BINARIES="$(make_targets "$PARTY_BINARIES")" \
    .
  echo "==> Done: $IMAGE_TAG"
  exit 0
fi

case "$VARIANT" in
  patched)
    IMAGE_TAG="mpspdz-patched:v0.4.3"
    OUT_DIR="MP-SPDZ/bin/Linux-amd64-patched"
    APPLY_SEEDED_BUG=0
    PARTY_BINARIES="$ALL_PROTOCOLS"
    ;;
  seeded-bug)
    IMAGE_TAG="mpspdz-patched-seeded-bug:v0.4.3"
    OUT_DIR="MP-SPDZ/bin/Linux-amd64-patched-seeded-bug"
    APPLY_SEEDED_BUG=1
    PARTY_BINARIES="mascot-party.x"
    ;;
  *)
    echo "usage: $0 [patched|seeded-bug|pipeline|pipeline-seeded-bug]" >&2
    exit 1
    ;;
esac

echo "==> Building $IMAGE_TAG (APPLY_SEEDED_BUG=$APPLY_SEEDED_BUG)"
podman build \
  --file "$CONTAINERFILE" \
  --target builder \
  --tag "$IMAGE_TAG" \
  --build-arg APPLY_SEEDED_BUG="$APPLY_SEEDED_BUG" \
  --build-arg PARTY_BINARIES="$(make_targets "$PARTY_BINARIES")" \
  .

echo "==> Extracting party binaries to $OUT_DIR/"
mkdir -p "$OUT_DIR"
container_id="$(podman create "$IMAGE_TAG")"
trap 'podman rm "$container_id" >/dev/null' EXIT
for b in $PARTY_BINARIES; do
  podman cp "$container_id:/src/mp-spdz-0.4.3/static/$b" "$OUT_DIR/$b"
done

echo "==> Done"
ls -la "$OUT_DIR"/*-party.x
file "$OUT_DIR"/*-party.x
