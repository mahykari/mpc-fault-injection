---
name: project_session_state_2026_07_13
description: 2026-07-13 session — 2M campaign stopped at 21k; ~20% honest_invalid (likely timeouts) at n=9 on mascot/spdz2k; rewrite-rules next
metadata: 
  node_type: memory
  type: project
  originSessionId: c1054474-6333-4611-ab13-f111e461510d
---

Mercury campaign STOPPED partway through (~21k of 2M target after ~4 days). Killed via `kill -TERM -<PGID>` of `_remote-run.sh` on mercury, then `podman stop`. Runner lives on mercury (`python3 containers/continuous.py --memory 4g --max-runs 2000000`), not on the laptop. See [[project_mercury_deploy]].

Why so few runs: round barrier + only 3 live containers per round (i00/i08/i12). Matches the open thread from [[project_session_state_2026_07_09]] — the fix (more instances / drop barrier) never landed.

Verdict split on the 21k: caught 13938 (~66%), honest_invalid 4208 (~20%), inert 3066 (~14%), bug 0.

honest_invalid concentrates on mascot (~2200) and spdz2k (~2003), roughly tied. malicious-shamir clean (5 total). n=9 dominates. Working theory: honest baseline timing out at n=9. Not confirmed by wall_ms yet.

Reporter persistence gap — retracted. Case-dir naming is `iNN-case-<global-seed>`, so total case dirs ≈ DB row count. [[project_open_threads]] item 2 was wrong.

Next block this session: rewrite rules (source-level, CircIL-based, semantic-deviating type-safe rewrites).
