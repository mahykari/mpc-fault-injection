---
name: project_containerization_rationale
description: "Why the pipeline runs in podman containers — parallel fuzzers with minimal interference, not just the Compiler singleton race"
metadata: 
  node_type: memory
  type: project
  originSessionId: a26058fb-6cc7-452a-8afa-8b21c7479a2f
---

The podman-per-instance design (landed on master 2026-06-17, merge of worktree-parallel-runs) exists to **run multiple fuzzers in parallel with minimal interference** — isolated env, own netns, capped cpu/mem per instance.

The MP-SPDZ Compiler module-level singleton race (see [[project_compiler_quirks]]) is just *one* symptom of the interference; don't reduce the whole rationale to it. The user corrected this twice.

`containers/launch.py` is the puppeteer: fans out N instances over disjoint seed slices into a shared `runs/`. `pipeline/instance.py::run_instance` runs one instance's slice. A "campaign" = the puppeteer's fan-out over all instances. See [[project_shared_mutated_bytecode]].

**Deploy (not yet done):** rsync repo to server excluding `.venv`/`MP-SPDZ`/`runs`/`.git` (image rebuilds MP-SPDZ, uv rebuilds venv); then `containers/build.sh pipeline` + `containers/launch.py` on the server. Outstanding source tweak: flip the Containerfile's SSH clone of python-circil to `COPY python-circil/` so the server build needs no GitHub key (circil rides the rsync).
