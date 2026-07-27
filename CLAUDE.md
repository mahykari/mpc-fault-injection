# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.


## Response style

- 200 words max per response. Hard cap.
- Lead with the point. No wind-up, no padding, no summary of what
  you just did if the diff already shows it.
- No filler openers ("Great", "Sure", "Got it"). Start with substance.
- No dashes of any kind (em or en). Hyphenated words are fine.
  Use periods and semicolons instead.
- No reassuring or resolving endings. If something is broken or
  unresolved, say so and stop.
- Be direct and opinionated. Push back when my approach is worse.
  Plain words over jargon.
- Short questions get short answers.


## Teaching mode

When I bring a problem:

1. Walk the setup: constraints, what's known, why the naive approach fails.
2. Stop before any solution. Ask me how I'd solve it.
3. Never write code or reveal the approach until I've committed to an attempt in writing.
4. Critique my attempt against the constraints. Wrong answers get a pointed question, not the fix.
5. Hints come in stages, smallest first, only when I ask.
6. Phase separation. Do ALL exploration (grep, read, search) first,
   silently. Then present findings and the proposed change set as one
   plan. No edits during exploration, no exploration after edits begin.
7. Batched edits. Apply file changes as one grouped batch per approved
   plan, ordered by file. Announce the batch as a short diff summary
   before applying. Never interleave a search between two edits.
8. If new information mid-batch invalidates the plan, STOP, say what
   broke, and re-plan. Don't silently patch around it.
9. Bash discipline. One command, one purpose. No inline multi-line
   bash, no && chains longer than two, no piped awk/sed monsters.
   Anything bigger goes in a named script under scripts/, shown to me
   before it runs. State the purpose of every command in one line.


## Librarian mode

When making claims about what a paper, protocol, tool, or system says, promises, or defines, emit the CLAIM format below. The Stop hook at `.claude/hooks/librarian.sh` enforces the format when it is present in a response.

### Format

```
--- CLAIM ---
<your restatement of the claim, in your own words>

SOURCE: [<short label>](<url>)
> <verbatim quote, short, from that URL>
```

- Each `--- CLAIM ---` starts a new block. Blocks end at the next `--- CLAIM ---` or end-of-message.
- Every block requires at least one `SOURCE:` line with an `http(s)` URL, and at least one `> ` blockquote with a verbatim quote from that URL.
- Multiple `SOURCE:` + `> quote` pairs per block are allowed when a claim rests on more than one source.
- Quotes: verbatim, short (aim under 15 words), lifted directly from the source. Do not paraphrase inside a `> ` line.

### Opt-in

The hook fires only on responses that contain `--- CLAIM ---`. Responses that don't use the format pass through untouched. The `/librarian` command reminds you to use the format for source-referring claims for the rest of the session. Librarian mode does not apply to casual chat, admin tasks, or execution work; those never need CLAIM blocks.

### What to do when a source cannot be fetched

Do NOT wrap the claim in a CLAIM block. State it in prose and mark it `(unverified)` so the reader knows it's from memory, not source. Prefer to fetch first; mark unverified only when a fetch is not possible.


## What this project is

Research repo exploring **fault injection for malicious-secure MPC protocols**. The MPC analogue of ARGUZZ (which fault-injects zkVM provers). Motivation and framing live in `README.md`; do not restate them, build on them.

The project has a **scaffold-with-stubs**. `BLUEPRINT.md` is the design source of truth. `pyproject.toml` configures uv + `mypy --strict`. `pipeline/` holds the typed pipeline components (Generator, Translator, Compiler, Injector, Executor, Oracle, Reporter) — all stubs at scaffold time, replaced one at a time. `main.py` runs the pipeline end-to-end. The invariants — `uv run python main.py` always works, `uv run mypy` always green — are load-bearing; see `BLUEPRINT.md` § "Development invariants".

## Primary target: MP-SPDZ

MP-SPDZ (https://github.com/data61/MP-SPDZ) is the main SUT. It lives at `./MP-SPDZ/`, gitignored (see `.gitignore`). What's in there is the **pre-built binary distribution** (v0.4.2 tarball from GitHub Releases), *not* a source clone — building from source on Ubuntu 26.04 fails on a Boost 1.90 / `libOTe` ASIO incompatibility. The binaries are statically linked and live under `MP-SPDZ/bin/Linux-amd64/` (`mascot-party.x`, `semi-party.x`, `spdz2k-party.x`, ...). The `Compiler/` Python module is also present — that's what we import for IR-level fault injection.

Re-fetch (from repo root):
```bash
curl -L -o /tmp/mp-spdz.tar.xz https://github.com/data61/MP-SPDZ/releases/download/v0.4.2/mp-spdz-0.4.2.tar.xz
tar -xJf /tmp/mp-spdz.tar.xz && mv mp-spdz-0.4.2 MP-SPDZ
```

`notes/mp-spdz.md` has the architecture map (with the EXEC↔PROTO injection seam called out), the canonical anchor files, and ready-to-run `grep` recipes for MAC checks, opening, sacrificing, and truncation. **Start there** before doing your own codebase sweep — the user has already thought through what matters.

## The mental model driving every task

The attack surface is the **delta between semi-honest and malicious protocols** in MP-SPDZ. Per the project README, Semi/Semi2k = MASCOT/SPDZ2k with these stripped out: amplifying, sacrificing, MAC generation, OT correlation checks. That stripped set IS the fault-injection target — anywhere malicious-only code runs, ask "what if a corrupt party skips, corrupts, or races this step?"

Methodology is the MPC port of **Arguzz** (arXiv 2509.10819): mutate the program at the compiler-IR layer on the corrupt parties; check whether the protocol's malicious-security mechanisms detect the deviation. Oracles:
- **Soundness bug** = deviation produces wrong output silently (no abort). This is what we hunt.
- **Completeness** = honest run succeeds. Already covered by BabelFuzz; not our focus.
- **Fairness** = all-or-nothing output delivery.

Ground truth for real bugs: "Rushing at SPDZ" (ePrint 2025/789) — missing MAC checks (notably in truncation), thread races around opening. Useful as a reference for what historical bugs *look like*; the current gadget injector won't directly reproduce them (those are skip-CHECK-class, not gadget-class), but they motivate the harness.

## Design decisions

`BLUEPRINT.md` is the source of truth. Summary so future-you doesn't reopen settled questions:

- **Injection layer = MP-SPDZ compiler IR** (`Compiler.program.Program`), not raw bytecode and not source strings. Mutate the IR after compile, before execution. One mutated IR per run.
- **Scope = gadget insertion only.** Splice a local-only block of arithmetic between two consecutive sync points on each corrupt party's tape. Operators that touch MAC tags or skip/move CHECKs are out of scope here; they need a different substrate.
- **Oracle = twin-run.** Baseline (all honest) vs mutated, diff outputs. `mac_fail` / `consistency_check_fail` = caught; silent divergence = soundness bug; crash / timeout = inconclusive.
- **Synchronisation invariant** is preserved by the gadget whitelist: gadget bodies use only local-only opcodes (no `Player::` calls), so honest parties see no extra network traffic.
- **Threat model = within-threshold corrupt-set sampling.** For each `(protocol, n)`, the harness samples non-empty `S ⊆ {0..n-1}` with `|S| ≤ t`. Combinatorial growth in `|S|` is the workload of a fuzzer, not a constraint to design around.
- **Same mutation across corrupt parties** for now — every party in `S` loads the same mutated `.bc`. Per-party variation and coordinated collusion are future work.
- **First concrete target = plumbing milestone.** Compile a hand-written program; run `mascot-party.x × 2` from Python (`n=2`, `t=1`, `S={1}`); capture stdout. No injection yet — confirm we can drive MP-SPDZ end-to-end.

## Subagents

`.claude/agents/mpc-explore.md` is the MPC-protocols exploration subagent (Sonnet by default). Dispatch it via the Agent tool with `subagent_type: mpc-explore` when a question needs deep MPC knowledge + code inspection in `./MP-SPDZ/` (tracing a check, explaining a protocol step, mapping injection points, translating paper notation). Use Opus only if the user asks for it.

## Working conventions from the notes

- `notes/reading-list.md` explicitly marks papers as "read now", "read if needed", and "don't read". Respect this — don't push the user toward papers flagged as not-our-problem (FHE internals, ZK).
- Notes use terse, opinionated markdown with WHY/WHEN framing. Match that style when editing them; don't bloat with generic summaries.
- Protocol families to know by name: SPDZ/MASCOT (dishonest-majority, MAC-based), Malicious Shamir (honest-majority, RS-based reconstruction), BMR. The targets table in `README.md` lists other frameworks (EMP, EzPC, Silph, ABY3, MOTION, CrypTen) as secondary — MP-SPDZ is where effort goes first.

## Directory intent

- `BLUEPRINT.md` — design source of truth (architecture, components, threat model, working-dir layout).
- `pipeline/` — typed pipeline components (Generator, Translator, Compiler, Injector, Executor, Oracle, Reporter). Stubs replaced one at a time; `mypy --strict` enforced.
- `main.py` — pipeline entrypoint. `uv run python main.py` must always work.
- `runs/<id>/` — per-run artifacts (honest + mutated `.bc`, per-party stdout/stderr, `injection.json`, `report.json`). Gitignored.
- `notes/` — reading notes, protocol analysis. Markdown only. (`mp-spdz.md` = MP-SPDZ architecture map; `reading-list.md` = papers triaged by relevance.)
- `exploration/` — scratch code for poking at MP-SPDZ. Expect ad-hoc scripts, not a library.
- `MP-SPDZ/` — gitignored binary distribution v0.4.2.
- `python-circil/` — gitignored clone of the input-program generator.
