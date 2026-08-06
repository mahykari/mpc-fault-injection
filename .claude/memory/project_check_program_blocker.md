---
name: check-program-blocks-twin-run-design-resolved
description: "Historical — MP-SPDZ's startup bytecode-fingerprint check used to block twin-run; bypassed via patches/mpspdz/0001-noop-check-program.patch and a container-built mascot-party.x. Kept for context on what the patch is for."
metadata: 
  node_type: memory
  type: project
  originSessionId: cb94fbd6-51fc-4916-b29c-aecbc9c30155
---

**RESOLVED 2026-05-12.** See [[project_patched_binary_done]] for the current state. Below is the original problem statement.


`Processor/Machine.hpp:769`'s `check_program()` hashes raw `.bc` bytes per tape, broadcasts hashes among parties, aborts on mismatch. Called in `prepare()` at line 162, before any computation. Runs in **every** protocol (semi-honest too) — it's a baseline integrity check, not malicious-security.

**Why:** BLUEPRINT's design has corrupt parties load mutated bytecode while honest parties load original. The hash check catches this at startup with `Fatal error: program differs between parties` — before MASCOT's actual malicious-security mechanisms (MACs at OPEN) get a chance to run. So the harness can't probe what we want to probe.

**How to apply:** Don't waste time on IR mutations that survive finalize but trip `check_program` — they'll all trip it. The next move is the container-built patched `mascot-party.x` plan (see `notes/mpspdz-patching.md`). Both parties run the patched binary; `check_program` becomes `return;`. Then the next thing to probe is the MAC layer at `Protocols/MAC_Check.hpp:197`.

LD_PRELOAD bypass ruled out: `mascot-party.x` is stripped + statically linked (only libc/libdl/libm/libpthread dynamic). Internal symbols not exported. Host source build also ruled out: Boost 1.90 / libOTe ASIO incompatibility on Ubuntu 26.04. Container (Ubuntu 22.04 + Boost 1.74) is the path.
