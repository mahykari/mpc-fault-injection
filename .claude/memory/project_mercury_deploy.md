---
name: project_mercury_deploy
description: "How to deploy + run campaigns on mercury — no uv there, host orchestrates on system python3"
metadata: 
  node_type: memory
  type: project
  originSessionId: db3d86a0-5d48-40b3-8aa5-55b9590cdbf6
---

Deploy target **mercury** = `mkarimi@mercury.se.tuwien.ac.at`, repo at `~/mpc-fault-injection`. Podman 5.4.2, rsync, python3 **3.13** present. SSH from the agent sandbox works (user's keys are available — `ssh -o BatchMode=yes` connects).

**Key gotcha: mercury has NO `uv` and no `.venv`.** The host orchestration runs on **system python3** — the 80k campaign launched with `python3 containers/launch.py ...` (from `.bash_history`), NOT `uv run`. The heavy pipeline deps live inside the podman image; the host scripts (`launch.py`, `continuous.py`, `main.py aggregate`) are import-light enough to run on bare python3. So never assume `uv` on a remote box — check.

**Deploy script: `./containers/deploy-mercury.sh [max_runs]`** (default 500000). It rsyncs (excludes `.venv MP-SPDZ runs .git .claude`), then ssh-fires `containers/_remote-run.sh` backgrounded on mercury → `runs/continuous.log`. `_remote-run.sh` archives any prior `results.db` (so a new campaign doesn't retire an old experiment), runs `./containers/build.sh pipeline`, then `python3 containers/continuous.py --memory 4g --max-runs N`.
- `MP-SPDZ/` excluded is safe — the Containerfile curl-fetches MP-SPDZ v0.4.2 source itself (line 37). `python-circil/` IS synced (Containerfile COPYs it from context).
- Cold builder cache on mercury = ~20 min Boost/libOTe compile; runs on mercury so the local script returns fast.
- Overridable: `MERCURY_HOST=... MERCURY_DEST=...`.

Follow: `ssh $HOST 'tail -f mpc-fault-injection/runs/continuous.log'`. Roll up: `ssh $HOST 'cd mpc-fault-injection && python3 main.py aggregate'`.
