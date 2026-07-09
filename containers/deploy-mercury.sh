#!/usr/bin/env bash
# Deploy the repo to mercury and launch the continuous multi-protocol campaign
# backgrounded (survives ssh disconnect). The host runs system python3 (mercury
# has no uv); the heavy work happens inside the podman image. MP-SPDZ/ is
# excluded — the Containerfile curl-fetches MP-SPDZ source itself. A cold builder
# cache means a ~20 min Boost/libOTe compile, but it runs on mercury, so this
# script returns as soon as the campaign is launched.
#
#   ./containers/deploy-mercury.sh [max_runs]        # default 2000000
#   MERCURY_HOST=... MERCURY_DEST=... ./containers/deploy-mercury.sh   # override
set -euo pipefail

HOST="${MERCURY_HOST:-mkarimi@mercury.se.tuwien.ac.at}"
DEST="${MERCURY_DEST:-mpc-fault-injection}"
MAX_RUNS="${1:-2000000}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> rsync -> $HOST:~/$DEST  (excludes: .venv MP-SPDZ runs .git .claude)"
rsync -az \
  --exclude .venv --exclude MP-SPDZ --exclude runs \
  --exclude .git --exclude .claude --exclude '*.pyc' \
  ./ "$HOST:$DEST/"

echo "==> launch remote campaign (backgrounded on mercury, max_runs=$MAX_RUNS)"
# setsid + ssh -n so the remote job detaches into its own session and ssh
# returns immediately (a plain nohup&  left the ssh — and this script — hung).
ssh -n "$HOST" "cd $DEST && mkdir -p runs && \
  setsid bash containers/_remote-run.sh $MAX_RUNS > runs/continuous.log 2>&1 < /dev/null &"

echo "==> launched. follow it:"
echo "    ssh $HOST 'tail -f $DEST/runs/continuous.log'"
echo "==> roll up + inspect results any time:"
echo "    ssh $HOST 'cd $DEST && python3 main.py aggregate'"
