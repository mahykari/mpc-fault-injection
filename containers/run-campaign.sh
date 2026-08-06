#!/usr/bin/env bash
# Campaign entrypoint. Run it from the repo root on whichever machine is doing
# the work. Archives any prior campaign.db (so a new campaign doesn't mix with an
# earlier experiment), rebuilds both images, then runs the continuous
# multi-protocol campaign. Uses system python3 for orchestration; the heavy work
# is inside the podman image.
#
# It runs in the foreground; detaching is the caller's business. Under tmux, or:
#   setsid bash containers/run-campaign.sh N > runs/continuous.log 2>&1 &
set -euo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNS="${1:-166000}"

mkdir -p runs
# Archiving matters more than it used to: the dispatcher reattaches to a live
# campaign.db rather than replacing it, so a stale one would silently resume.
# results.db is the pre-dispatcher path, still retired here so a redeploy leaves
# no live DB of either generation behind.
stamp="$(date +%Y%m%d-%H%M)"
for db in campaign results; do
  if [ -f "runs/$db.db" ]; then
    mv "runs/$db.db" "runs/$db-archived-$stamp.db"
    echo "archived prior $db.db -> runs/$db-archived-$stamp.db"
  fi
done
# Clear prior per-run dirs too. Workers still write them, and a stale set both
# fills the disk and lets `main.py aggregate` re-ingest an old campaign's
# reports (find, not a glob — 80k dirs overflow argv).
find runs -maxdepth 1 -name 'i*-case-*' -type d -exec rm -rf {} + 2>/dev/null || true
echo "cleared prior run dirs"

echo "==> building pipeline image"
./containers/build.sh pipeline
echo "==> building dispatcher image"
./containers/build.sh dispatch

echo "==> launching continuous campaign (runs per grid point=$RUNS)"
python3 containers/continuous.py --memory 4g --runs "$RUNS"
