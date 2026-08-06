#!/usr/bin/env bash
# Campaign entrypoint. Run it from the repo root on whichever machine is doing
# the work. Archives any prior results.db (so a new campaign doesn't mix with /
# retire an earlier experiment), rebuilds the pipeline image, then runs the
# continuous multi-protocol campaign. Uses system python3 for orchestration; the
# heavy work is inside the podman image.
#
# It runs in the foreground; detaching is the caller's business. Under tmux, or:
#   setsid bash containers/run-campaign.sh N > runs/continuous.log 2>&1 &
set -euo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAX_RUNS="${1:-500000}"

mkdir -p runs
if [ -f runs/results.db ]; then
  archive="runs/results-archived-$(date +%Y%m%d-%H%M).db"
  mv runs/results.db "$archive"
  echo "archived prior results.db -> $archive"
fi
# Clear prior per-run dirs too, else aggregate re-ingests an old campaign's
# reports into the fresh results.db (find, not a glob — 80k dirs overflow argv).
find runs -maxdepth 1 -name 'i*-case-*' -type d -exec rm -rf {} + 2>/dev/null || true
echo "cleared prior run dirs"

echo "==> building pipeline image"
./containers/build.sh pipeline

echo "==> launching continuous campaign (max_runs=$MAX_RUNS)"
python3 containers/continuous.py --memory 4g --max-runs "$MAX_RUNS"
