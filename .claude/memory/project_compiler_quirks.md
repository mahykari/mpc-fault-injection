---
name: MP-SPDZ Compiler quirks the adapter works around
description: Singleton enforcement, module-level program globals that mutate finalize behavior, CWD-bound output paths, deepcopy-resistant Program — what our pipeline/mpspdz.py wraps
type: project
originSessionId: 9b62c8c3-6b2f-4e1a-bd0e-ae575334439d
---
MP-SPDZ's `Compiler` Python module is CLI-shaped, not library-shaped. Our `pipeline/mpspdz.py` adapter encapsulates four quirks that bit us during integration:

1. **One-Compiler-per-process** — `compilerLib.Compiler.singleton` raises on second instantiation. Reset to `None` before each compile (we compile twice per pipeline run: honest + mutated).

2. **Module-level `program` references go stale.** `Program.__init__` sets `Program.prog`, `instructions.program`, `instructions_base.program`, `types.program`, `comparison.program` — all to `self`. Compile-twice means the second compile clobbers them. Then finalizing the FIRST program causes its optimization to re-emit instructions through the stale globals, routing them into the SECOND program's tape (leaves first tape empty, doubles second tape). Fix: rebind all 5 before each `finalize()`. Verified complete by grep across `Compiler/` — no other module-level `program` references exist.

3. **`Program.programs_dir = "Programs"` is relative.** All output paths resolve against CWD. Chdir into the destination before finalize; restore on exit (contextmanager).

4. **`Program` resists `copy.deepcopy`.** Instruction objects have read-only descriptors (e.g. `arg_format`). That's why the Injector recompiles from source for the mutated copy rather than deep-copying the honest IR.

**Why:** these aren't bugs to file upstream — they're the cost of treating a CLI tool as a library. The wrappers are load-bearing for the pipeline to work at all.

**How to apply:** when something weird happens during compile/finalize (empty bytecode, instructions in wrong tape, files in wrong place), suspect one of these first. The fixes are localized in `pipeline/mpspdz.py` (see `MpSpdzCompilerToolkit.compile`, `finalize_into`, `_bind_module_globals`, `_working_directory`).
