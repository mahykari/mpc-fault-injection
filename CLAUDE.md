# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Research repo exploring **fault injection for malicious-secure MPC protocols**. The MPC analogue of ARGUZZ (which fault-injects zkVM provers). Motivation and framing live in `README.md`; do not restate them, build on them.

The project is in the **reading + scoping phase**. There is no build system, no test suite, and no production code. `exploration/` is currently empty except for a placeholder. Do not invent commands, fabricate tests, or scaffold infrastructure until the user asks — expect early sessions to be reading MP-SPDZ source, writing small probes, and editing notes.

## Primary target: MP-SPDZ

MP-SPDZ (https://github.com/data61/MP-SPDZ) is the main SUT. It lives at `./MP-SPDZ/` as a **plain clone** and is **gitignored** (see `.gitignore`) — deliberately not a submodule. Assume `./MP-SPDZ/` may or may not exist on a given checkout; check before grepping it.

Clone command (from repo root):
```bash
git clone https://github.com/data61/MP-SPDZ.git
```

`notes/mp-spdz-exploration.md` has the canonical list of places to look (Protocols/, Processor/, Compiler/, Math/, OT/, FHE/) and ready-to-run `grep` recipes for MAC checks, opening, sacrificing, and truncation. **Start there** before doing your own codebase sweep — the user has already thought through what matters.

## The mental model driving every task

The attack surface is the **delta between semi-honest and malicious protocols** in MP-SPDZ. Per the project README, Semi/Semi2k = MASCOT/SPDZ2k with these stripped out: amplifying, sacrificing, MAC generation, OT correlation checks. That stripped set IS the fault-injection target — anywhere malicious-only code runs, ask "what if a corrupt party skips, corrupts, or races this step?"

Methodology is the MPC port of **Arguzz** (arXiv 2509.10819): mutate instruction semantics at the bytecode-dispatch layer on one corrupt party; check whether the protocol's malicious-security mechanisms detect it. Oracles:
- **Soundness bug** = deviation produces wrong output silently (no abort). This is what we hunt.
- **Completeness** = honest run succeeds. Already covered by BabelFuzz; not our focus.
- **Fairness** = all-or-nothing output delivery.

Ground truth for real bugs: "Rushing at SPDZ" (ePrint 2025/789) — missing MAC checks (notably in truncation), thread races around opening. When judging whether an injection point is interesting, cross-reference that paper's attacks.

## Design decisions locked in round 1

These are in `notes/fault-injection-design.md`; don't re-derive them:

- **Injection layer = VM bytecode dispatch**, not the protocol abstraction. Primary patch site: `Processor/Instruction.hpp:1530` (opcode switch in `Program::execute_with_errors`). Secondary shim at register access for macro-expanded opcodes. MP-SPDZ bytecode is protocol-agnostic, so one injector covers all malicious protocols.
- **Oracle = twin-run with pinned randomness.** Baseline vs mutated, diff outputs, classify exceptions. `mac_fail`/`consistency_check_fail` = caught (no bug); silent divergence = soundness bug; crash = triage.
- **Synchronisation invariant:** mutate *values*, not *calls* — round counts and message volumes must match across parties. Never skip MULS/OPEN; OK to skip CHECK/TRUNC_PR/local arithmetic.
- **Propagation filter:** backward def-use slice from OPEN/CHECK/PRIVATEOUTPUT — only mutate PCs in the slice.
- **Party-role coverage** is a harness concern, not injector concern. Symmetric families (SPDZ, SPDZ2k, MASCOT, MaliciousShamir) need one party index; role-asymmetric families (Rep3, Astra, Trio, Dealer, Rep4) need iteration across distinct roles. Table in the design note.
- **First concrete target:** reproduce the Rushing-at-SPDZ truncation bug via "skip CHECK around TRUNC_PR" — if the harness catches it, the design works.

## Subagents

`.claude/agents/mpc-explore.md` is the MPC-protocols exploration subagent (Sonnet by default). Dispatch it via the Agent tool with `subagent_type: mpc-explore` when a question needs deep MPC knowledge + code inspection in `./MP-SPDZ/` (tracing a check, explaining a protocol step, mapping injection points, translating paper notation). Use Opus only if the user asks for it.

## Working conventions from the notes

- `notes/reading-list.md` explicitly marks papers as "read now", "read if needed", and "don't read". Respect this — don't push the user toward papers flagged as not-our-problem (FHE internals, ZK).
- Notes use terse, opinionated markdown with WHY/WHEN framing. Match that style when editing them; don't bloat with generic summaries.
- Protocol families to know by name: SPDZ/MASCOT (dishonest-majority, MAC-based), Malicious Shamir (honest-majority, RS-based reconstruction), BMR. The targets table in `README.md` lists other frameworks (EMP, EzPC, Silph, ABY3, MOTION, CrypTen) as secondary — MP-SPDZ is where effort goes first.

## Directory intent

- `notes/` — reading notes, protocol analysis, design thinking. Markdown only.
- `exploration/` — scratch code for poking at MP-SPDZ. Expect ad-hoc scripts, not a library.
- `MP-SPDZ/` — gitignored clone of the SUT when present.
