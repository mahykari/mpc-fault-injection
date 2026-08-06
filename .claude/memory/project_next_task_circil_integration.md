---
name: next-task-python-circil-integration
description: "CircIL integration shipped. Next: filter-by-divergence loop — inject blindly, keep programs where mutated output differs from honest, scrap the rest."
metadata: 
  node_type: memory
  type: project
  originSessionId: 636bf176-9417-477c-acc6-97c76330ccfc
---

**Status:** shipped to master (tip `d2e4e89`).

**What's wired in:**
- Generator drives `SimpleCircuitFuzzer` (Field, +/-/*, lets at p=0.3, depth 10, up to 10 inputs / 5 outputs).
- Translator (`pipeline/translator.py:MpspdzTranslation`) is an `EmptyVisitor` subclass that hoists lets to top-level assignments.
- Injector enforces a per-tape sync-signature invariant via `pipeline/mpspdz.py:sync_signature` (ordered `DataInstruction` opcodes). Honest and mutated tapes must match. Jumps are public-state, see [[project_mpspdz_jump_model]].
- `SingleVariableBumpTemplate` anchors on the first LDSI on tape 0.
- `exploration/dump_party_outputs.py`, `exploration/show_circil_programs.py` for poking.

**Known limitations** (now documented in `notes/mp-spdz.md`):
- Dead-anchor: bump often lands on `in0` which may not feed any output → twins identical for trivial reasons.
- Asymmetric public-constant load (`SemiShare::constant` returns 0 for non-P_0): ADDSI on non-P_0 corrupt shifts MAC but not value share.

**Design pivot 2026-05-26:** no live-path / def-use analysis. Fuzzer mindset — inject blindly; if honest vs. mutated outputs differ, keep the program as a test case; if identical, scrap and regenerate. Matches [[feedback_testing_not_verifying]].

**Workflow becomes:**
1. Generate circuit.
2. Compile honest.
3. Inject (blind anchor).
4. Twin-run.
5. Identical outputs → discard, regenerate.
6. `mac_fail` / `SECURITY BUG` → caught (desired).
7. Silent divergence → soundness candidate.

**Next pickup:** wire the discard-on-identical-output loop into the pipeline. Reporter / Oracle needs the "inert mutation → scrap, regenerate" branch.
