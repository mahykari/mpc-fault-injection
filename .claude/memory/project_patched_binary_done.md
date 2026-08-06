---
name: patched-mascot-party-x-built-mac-check-observed
description: "Container-built patched binary (check_program no-op'd) integrated into the pipeline; LDSI mutation now reaches and trips MASCOT's MAC check at OPEN"
metadata: 
  node_type: memory
  type: project
  originSessionId: cb94fbd6-51fc-4916-b29c-aecbc9c30155
---

**State as of 2026-05-12:** plumbing milestone complete; first real gadget
landed. The end-to-end loop runs against a patched `mascot-party.x`, the
Injector is a `GadgetTemplate` dispatcher, and the `SingleVariableBump`
gadget (BLUEPRINT catalog) trips MASCOT's MAC check at OPEN.

- `patches/mpspdz/0001-noop-check-program.patch` — `Machine::check_program()` body becomes `return;`.
- `docker/Dockerfile.mpspdz` + `docker/build.sh` — ubuntu:22.04 container build of `static/mascot-party.x` (need apt `zlib1g-dev` for `-lz`; the plain `mascot-party.x` target produces a libSPDZ.so-dependent dynamic binary that won't run on host). Output lands in `MP-SPDZ/bin/Linux-amd64-patched/`.
- `Config.use_patched_binary: bool` — `party_binary_path` picks `Linux-amd64-patched/` when true. `main.py` sets it to True.
- `pipeline/gadgets/` — `GadgetTemplate` and `Gadget` Protocols (`types.py`); first concrete template is `SingleVariableBumpTemplate` (`single_variable_bump.py`). Wiring: `main.py` → `pipeline/__init__.py` passes `(SingleVariableBumpTemplate(),)` into `Injector(toolkit, templates, config)`.
- `pipeline/mpspdz.py` — added IR adapter helpers (`find_first_instruction`, `get_dst`, `set_dst`, `insert_after`, `new_reg_like`, `make_addsi`). Gadgets use these instead of poking at `inst.args` directly ([[feedback_isolate_adapter_pokes]]).
- Pipeline run: honest twin → `result: 3`. Mutated twin (bump on `a`'s register, party 1) → both parties abort with `Fatal error at stub-0042-0:3 (OPEN): MacCheck Failure`.

**SSA gotcha for future gadgets:** MP-SPDZ's allocator enforces single-writer. The bump works because it redirects the LDSI to a fresh reg and writes the original via addsi (single-writer preserved, no downstream rewrites). For mid-tape bumps the mirror pattern is needed: keep the writer, splice `addsi r_new, r, δ` at the splice point, rename downstream reads of `r` to `r_new`. A def-use helper is the natural next adapter when the second gadget needs it.

**Why:** see [[project_check_program_blocker]] for what was blocking the harness; this entry records what unblocked it and what the next layer was.

**How to apply:** for the next experiment, the substrate is now ready — IR mutation flows through to the MAC layer, and MASCOT classifies as "caught" per the BLUEPRINT decision table. Real next steps:
- Replace the `pass` STUB oracle with the BLUEPRINT decision table (mac_fail = caught, silent divergence = bug, crash/timeout = inconclusive).
- Replace the hardcoded `a + b` program with a real Generator (python-circil integration) so we can fuzz programs not just mutations.
- Sample more gadgets per IR (currently one `immediate_swap`); see `pipeline/injector.py`.
- Reporter actually persisting per-party stdout/stderr + injection.json + report.json under `runs/<id>/`.

**Adding more C++ patches:** see `patches/mpspdz/README.md`. Discipline: only disable plumbing layers (things that exist in semi-honest too). Disabling MAC generation or sacrificing reduces the protocol to semi-honest and breaks the harness's premise.
