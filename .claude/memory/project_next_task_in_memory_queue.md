---
name: project_next_task_in_memory_queue
description: "Next task for 2026-07-31 — replace the dispatcher's per-request DB scan with an in-memory deque + lease heap"
metadata: 
  node_type: memory
  type: project
  originSessionId: 626366ae-a574-406d-a593-42501340594b
  modified: 2026-08-04T16:25:14.677Z
---

**Problem.** The dispatcher sits pinned at ~100% CPU during a campaign. Two
fixes already landed on `dispatcher-pull-model` and neither cured it: `b032197`
rate-limited the abandon sweep, and the sweep was not the (only) cause.

**Likely real cause.** `Store.claim`'s `ORDER BY id LIMIT 1` cannot use
`idx_experiment_available`, which orders by `claimed_at` before `id`. So sqlite
walks the table in primary-key order skipping every completed row to reach the
first pending one. That cost grows with each finished run, which matches a
dispatcher that never comes back down. The `OR` in the availability predicate
makes it worse.

**Agreed fix (Mahyar's call, 2026-07-30: "why try to read everything from the
db? why not use a proper queue?").** Stop *searching* for the next item; keep
the DB as the durable record only.

- Pending experiment ids in an in-memory `deque`, loaded once at boot with a
  single `SELECT id FROM experiment WHERE completed_at IS NULL`.
- In-flight items in a heap of `(lease_expiry, id)`; expired entries pop back
  onto the deque.
- `claim` pops the deque and writes the lease by primary key; `record` updates
  by primary key. Every operation O(1), no scan anywhere.

This deletes both experiment indexes and `_abandon_exhausted` / `_sweep_if_due`
entirely. ~20 lines net. NOT a broker — Redis/Rabbit buys nothing here: single
process, regenerable queue, durability already in sqlite. See
[[project_dispatcher_pull_model]].

Campaign was left running on mercury overnight; this throttles visibility
(`/status` starves), not results.
