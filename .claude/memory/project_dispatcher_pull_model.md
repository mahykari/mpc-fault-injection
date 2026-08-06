---
name: project_dispatcher_pull_model
description: 2026-07-30 — round barrier replaced by an HTTP dispatcher + long-lived pull workers; store.py is the queue and the results table
metadata: 
  node_type: memory
  type: project
  originSessionId: 626366ae-a574-406d-a593-42501340594b
  modified: 2026-08-04T16:15:51.813Z
---

Round barrier is gone (was the cause of 21k runs in 4 days, see
[[project_session_state_2026_07_13]]). Replaced by:

- **`pipeline/store.py`** — three tables, no JSON: `config` (grid point),
  `experiment` (fact table + lease + result fields), `injection` (child rows for
  the gadget tuples). The queue IS the set of experiment rows with no result
  yet, so there is no separate queue medium. `corrupt_set` is the one serialised
  container (sorted comma-separated string) — Mahyar's explicit call, accepting
  that "which |S| produces bugs" becomes a LIKE instead of a GROUP BY.
- **`containers/dispatch.py`** — single-threaded `HTTPServer`, sole sqlite
  writer. `GET /next` (204 = drained, makes workers exit), `POST /result`,
  `GET /status`. Own image, `mpspdz-dispatch:v0.4.2`, python:3.12-slim.
- **`pipeline/campaign.py`** — grid expansion + seed allocation. Deliberately
  NOT in Store: Mahyar's correction that Store is a data-interaction interface,
  not a planner.
- Workers are long-lived, pull one experiment at a time, rebuild `Config` per
  run, and never sit at a barrier.

Poison-pill guard: `attempts` column, k=3, incremented on claim; exhausted rows
retire as verdict `abandoned` once their lease expires.

Old `runs` table + `main.py aggregate` deliberately untouched; delete once this
proves out.

Landed on branch `dispatcher-pull-model` (pushed): `e077b45` the model itself,
`b032197` rate-limits the abandon sweep (it ran per-claim and pinned the
dispatcher at 97% CPU against 2M rows, starving `/status`), `020c776` fixes the
deploy ssh hang (`&` binds looser than `&&`, so the whole list backgrounded into
a subshell that held ssh's stdout). Permissions allowlist went to master
separately as `a8ef555`, unpushed as of 2026-07-30.

Deployed and running on mercury 2026-07-30. First campaign hit ~10 runs/sec
across 16 workers, vs 21k runs in 4 days under the round barrier.
