---
name: project_n9_pids_limit
description: "n=9 honest_invalid was podman's 2048 PID cap, not MPC cost; fixed with --pids-limit 0"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9cdfa210-f0b8-4fbe-8d76-f59031a05be4
  modified: 2026-08-10T16:44:43.786Z
---

Every n=9 case came back `honest_invalid` from the 2026-07-13 campaign onward.
Cause, found 2026-08-10: an MP-SPDZ party spawns ~230 threads, so nine parties
want 2043 and podman's default `--pids-limit 2048` denies the last few.
MP-SPDZ does not fail on `pthread_create` failure, it **deadlocks** — one
thread parked in `inet_csk_accept` waiting for a peer whose connection thread
was never created, the rest in `futex_wait`, zero CPU. From outside,
`podman exec` into the container also fails with `fork: Resource temporarily
unavailable`; that is the same ceiling and is the fastest tell.

A/B on one case: default 2048 -> `honest_invalid` after 180s of watchdog kills;
`--pids-limit 0` -> `caught` in 340 ms. n=9 MASCOT costs ~200 ms, not minutes.

**Why:** it looked like a protocol-cost problem for weeks and is not one. Bigger
timeouts and smaller n=9 sample counts both "fixed" nothing.

**How to apply:** thread ceilings, not MPC, are the first suspect when parties
sit at zero CPU with no output. `containers/launch.py` `resource_opts` now
always emits `--pids-limit 0`. Note the harness reports a watchdog-killed honest
run as `honest_invalid — test program invalid`, which actively misleads; the
program is fine, the harness starved it. See [[project_party_count_grid]] and
[[project_session_state_2026_08_10]].
