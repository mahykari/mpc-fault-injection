#!/usr/bin/env bash
# Deploy the repo to mercury and launch the continuous multi-protocol campaign
# backgrounded (survives ssh disconnect). The host runs system python3 (mercury
# has no uv); the heavy work happens inside the podman image. MP-SPDZ/ is
# excluded — the Containerfile curl-fetches MP-SPDZ source itself. A cold builder
# cache means a ~20 min Boost/libOTe compile, but it runs on mercury, so this
# script returns as soon as the campaign is launched.
#
# The argument is runs PER GRID POINT, not the campaign total: the dispatcher
# owns the grid, and 3 protocols x 4 party counts = 12 points, so the default
# 166000 is ~2M runs overall.
#
#   ./containers/deploy-mercury.sh [runs_per_grid_point]   # default 166000
#   MERCURY_HOST=... MERCURY_DEST=... ./containers/deploy-mercury.sh   # override
set -euo pipefail

HOST="${MERCURY_HOST:-mkarimi@mercury.se.tuwien.ac.at}"
DEST="${MERCURY_DEST:-mpc-fault-injection}"
RUNS="${1:-166000}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> rsync -> $HOST:~/$DEST  (excludes: .venv MP-SPDZ runs .git .claude)"
rsync -az \
  --exclude .venv --exclude MP-SPDZ --exclude runs \
  --exclude .git --exclude .claude --exclude '*.pyc' \
  ./ "$HOST:$DEST/"

echo "==> launch remote campaign (backgrounded on mercury, runs/point=$RUNS)"
# setsid + ssh -n so the remote job detaches into its own session and ssh
# returns immediately (a plain nohup&  left the ssh — and this script — hung).
# The launch is its own statement: `&` binds looser than `&&`, so folding it
# into the cd/mkdir chain backgrounds the whole list in a subshell that keeps
# ssh's stdout open and waits for the campaign, hanging the ssh anyway.
ssh -n "$HOST" "cd $DEST && mkdir -p runs || exit 1
setsid bash containers/_remote-run.sh $RUNS > runs/continuous.log 2>&1 < /dev/null &"

echo "==> launched. follow it:"
echo "    ssh $HOST 'tail -f $DEST/runs/continuous.log'"
echo "==> live verdict tallies (the dispatcher serves them; no aggregate step):"
echo "    ssh $HOST 'curl -s localhost:8080/status'"
