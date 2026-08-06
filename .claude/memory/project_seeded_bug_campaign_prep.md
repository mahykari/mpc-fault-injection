---
name: seeded-bug-campaign-prep
description: Prepping 8-combo Check() toggling campaign with SQLite aggregator
metadata: 
  node_type: memory
  type: project
  originSessionId: 70ba8c5a-e9e9-4eda-80b1-3a35697ae85c
---

## Current state (2026-06-25)

PR #4 merged — treesitter-based Check() site disabling. Three sites:
- `subprocessor_check` (Processor.hpp)
- `beaver_check` (Beaver.hpp)
- `private_output_check` (PrivateOutput.hpp)

Controlled via `--disabled-sites` flag in `containers/launch.py` → `MPSPDZ_DISABLED_SITES` env var.

## Next steps

1. **Fix reporter.py** — currently writes only `RunResult` to report.json, not `Verdict`. Change to write full `Report` (includes `fault`, `verdict`, `duration_ms`). One-liner fix:
   ```python
   json.dump(dataclasses.asdict(Report(
     fault=mutated.record,
     verdict=verdict,
     duration_ms=run.duration_ms,
   )), f, indent=2)
   ```

2. **Write SQLite aggregator** — `aggregate.py` that:
   - Reads `runs/<case>/report.json` files
   - Inserts into `runs/results.db`
   - Schema:
     ```sql
     CREATE TABLE runs (
       id TEXT PRIMARY KEY,
       seed INTEGER,
       combo TEXT,
       verdict TEXT,
       wall_ms INTEGER,
       instance_id INTEGER,
       created_at TEXT DEFAULT CURRENT_TIMESTAMP
     );
     CREATE INDEX idx_combo_verdict ON runs(combo, verdict);
     ```

3. **Campaign kickoff script** — loop over 8 combos:
   ```bash
   combos=(
     ""
     "subprocessor_check"
     "beaver_check"
     "private_output_check"
     "subprocessor_check,beaver_check"
     "subprocessor_check,private_output_check"
     "beaver_check,private_output_check"
     "subprocessor_check,beaver_check,private_output_check"
   )
   ```
   10k runs per combo, 2 instances × 5k each, same seed (0) across all for apples-to-apples.

4. **Build seeded-bug image** — `./containers/build.sh pipeline-seeded-bug` before running.

**Why:** Validate that disabling checks → bugs surface. Baseline (no disabled sites) should show 0 bugs; all-disabled should show bugs.
