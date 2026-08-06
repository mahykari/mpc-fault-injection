---
name: project_mercury_deploy
description: "mercury is a peer clone you ssh into, not a deploy target — git is the only transport; no uv there"
metadata: 
  node_type: memory
  type: project
  originSessionId: db3d86a0-5d48-40b3-8aa5-55b9590cdbf6
---

**mercury** = `mkarimi@mercury.se.tuwien.ac.at`, repo at `~/mpc-fault-injection`. Podman 5.4.2, python3 3.13.

As of 2026-08-06 it is a **peer git clone, not a deploy target**. Nothing is pushed at it from the laptop: no rsync, no remote invoke, no deploy script (`containers/deploy-mercury.sh` is deleted). You ssh in and work there. Code and memory both move by `git pull` / `git push` against origin, which means mercury has its own GitHub key with write access. See [[project_memory_in_repo]].

- Campaign entrypoint is `containers/run-campaign.sh` (was `_remote-run.sh`), run from the repo root. It runs in the foreground; detach with tmux or `setsid ... &` yourself.
- **No `uv` on mercury.** Host orchestration runs on **system python3** (`python3 containers/continuous.py ...`, `python3 main.py aggregate`). Heavy deps live inside the podman image; host scripts are import-light. Never assume `uv` on a remote box.
- `python-circil/` and `MP-SPDZ/` are gitignored. mercury's copies came from the old rsync era; a fresh machine needs python-circil cloned separately. The Containerfile curl-fetches MP-SPDZ itself.
- Cold podman builder cache = ~20 min Boost/libOTe compile.

Follow a campaign: `tail -f runs/continuous.log`. Live tallies: `curl -s localhost:8080/status`.
