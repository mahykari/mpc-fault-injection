---
name: All corrupt parties run the same mutated bytecode (for now)
description: Current design decision — the Injector produces ONE mutated IR per run; every party in the corrupt set loads it. Not per-party variation.
type: project
originSessionId: bca48558-f79c-4fde-9eb1-14776414cc7e
---
For now, every party in the corrupt set `S` loads the **same** mutated `.bc` — one gadget choice, one insertion point, applied uniformly. Not one mutation per corrupt party.

**Why:** User's call (2026-05-08): "all corrupt parties run the same deviation; for now." Cheaper to implement, simpler InjectionRecord, and step 1 has `|S|=1` anyway so the simplification is invisible at the milestone level. The blueprint's `Threat model` section reflects this; the Injector's `Out` shape is `original IR + one mutated IR + InjectionRecord`.

**How to apply:**
- Injector signature: `(MpspdzProgram, Seed) → MutatedProgram` — no `corrupt_parties` parameter.
- `MutatedProgram` carries one mutated IR, not a per-party dict.
- Executor reads `corrupt_parties` separately and routes those parties to a single `mutated/` dir.
- Per-party gadget variation and coordinated collusion are explicitly future work; don't proactively add per-party slots in types.
