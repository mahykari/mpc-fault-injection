---
name: project_session_state_2026_07_09
description: "Live state at end of 2026-07-09 session — campaign running on mercury, underload finding, next levers"
metadata: 
  node_type: memory
  type: project
  originSessionId: db3d86a0-5d48-40b3-8aa5-55b9590cdbf6
---

**A full 2M-run campaign is RUNNING on mercury** (`continuous.py --memory 4g --max-runs 2000000`), fixed code, full grid = protocols {mascot, spdz2k, malicious-shamir} × party-counts {3,5,7,9}. Verified progressing (round 0: 13/16 instances done), not wedging. Let it ride ("free real estate"). See [[project_party_count_grid]], [[project_mercury_deploy]].

**Fixes landed today (all committed to master):**
- `53f683e` — party-count grid in continuous.py + `n_parties` column in results.db.
- `983a1ae` — timeout reaping fix: one `threading.Timer` watchdog + process-group SIGKILL (`start_new_session` + `killpg`) instead of the old per-party sequential `communicate(timeout)` that serialized to n×timeout and leaked hung parties (wedged n=9). `timeout_s` 30→120.
- `b3c15c5` — deploy clears old run dirs (else aggregate re-ingests an old campaign's reports).
- `c987376` — deploy uses `setsid` + `ssh -n` so it detaches and returns.

**Open finding — server underloaded.** `launch.py` spawns 16 containers/round and **waits for all 16** (round barrier). Runs inside a container are sequential; party procs are network-bound (latency, not CPU). n=9 instances are ~10-30× slower than n=3, so fast ones finish + exit and the box idles on the n=9 tail (saw only 3 containers up on a 192-thread box). **Next levers (pending user pick):** (1) bump `--instances` 16→48+ (work is network-bound, oversubscribe freely); (2) bigger win — drop the round barrier so instances run continuously instead of waiting for the slowest each round.

**Note:** CLAUDE.md gained a "Teaching mode" section 2026-07-09 (Socratic: walk setup, ask user's approach before revealing any solution, phase-separate explore/edit, batched edits with diff summary, strict one-purpose bash). Follow it.
