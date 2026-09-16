---
name: project_session_state_2026_08_10
description: State as of 2026-08-10 evening — 2M campaign running clean after the PID fix
metadata: 
  node_type: memory
  type: project
  originSessionId: 9cdfa210-f0b8-4fbe-8d76-f59031a05be4
  modified: 2026-08-10T16:44:51.087Z
---

The full 2M campaign (12 grid points x 166000) launched 18:44 on 2026-08-10 via
`./containers/run-campaign.sh`, 16 workers, `planned=1992000 lease=600s`.
Poll with `curl -s localhost:8080/status`. At the smoke rate (~8 cases/sec)
it needs roughly 9 hours. 16 workers on a 192-core box is heavily underloaded;
`continuous.py --workers 64` would cut it to a couple of hours, but
`run-campaign.sh` hardcodes 16.

Preceding smoke test, 1008 cases, drained in ~2 minutes: 834 caught (82.7%),
174 inert (17.3%), **zero honest_invalid**, all 12 grid points full including
n=9 for all three protocols. That is the first clean n=9 result — see
[[project_n9_pids_limit]].

Disk: ~200K per run dir now that the memory dump is suppressed, so ~400G for
the full 2M against 1.4T free. The 1.1T blowup of
[[project_campaign_disk_blowup]] is settled.

Unpushed on `dispatcher-pull-model`: the `--pids-limit 0` fix in
`containers/launch.py`, plus `cdf5540` and `a44e875` from earlier. Still open:
[[project_next_task_in_memory_queue]] (dispatcher CPU) — untouched, and it will
matter more at 2M rows than it did at 1.69M.
