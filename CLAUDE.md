# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.


## Response style

- Regular responses (answers to a question, explanations, small requests, etc.) get 500 words max per response.
  Design or implementation tasks have no word limit.
- Lead with the point instead of a wind-up or a summary.
- Avoid using filler openers ("Great", "Sure", "Got it") and start with substance.
- Avoid using dashes of any kind (em or en). Hyphenated words are fine.
  Use periods, semicolons, and other equivalent punctuation instead.
- If my approach is bad or wrong, and you have a reason for believing so, push back and don't concede.
- Plain words over jargon.
- Short questions get short answers.


## Working process

1. Phase separation. Do ALL exploration (grep, read, search) first,
   silently. Then present findings and the proposed change set as one
   plan. No edits during exploration, no exploration after edits begin.
2. Batched edits. Apply file changes as one grouped batch per approved
   plan, ordered by file. Announce the batch as a short diff summary
   before applying. Never interleave a search between two edits.
3. If new information mid-batch invalidates the plan, STOP, say what
   broke, and re-plan. Don't silently patch around it.
4. Bash discipline. One command, one purpose.
   Avoid inline multi-line bash, && chains longer than two, and piped awk/sed monsters.
   Anything bigger goes in a named script under scripts/, shown to me
   before it runs. State the purpose of every command in one line.


## Design work

Design discussions and refactors have no word budget. Spell the rationale out
in full sentences; diagrams welcome.

- A name must evoke the thing to a stranger. Write the one sentence a class or
  module should evoke, then check the name alone lands on it. Generic nouns
  (Site, Run, Cell, Config, Serve) fail.
- "What is X?" in a review means discard X, not explain X.
- No cheap tricks to get code running: blanking a package `__init__` inside an
  image, `sys.path.insert` to import siblings, passing `argparse.Namespace`
  around. Fix the package, not the import.
- Accretion gets restructured, not patched locally.
- Helpers that isolate MP-SPDZ internals still read as code, not witchcraft.


## Librarian mode

When making claims about what a paper, protocol, tool, or system says, promises, or defines,
emit the CLAIM format below.
The Stop hook at `.claude/hooks/librarian.sh` enforces the format when it is present in a response.

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

Do NOT wrap the claim in a CLAIM block. State it in prose and mark it clearly (e.g., `(unverified)`) so the reader knows it's from memory, not source. Prefer to fetch first; mark unverified only when a fetch is not possible.


## What this project is

Fault injection for malicious-secure MPC protocols; the MPC analogue of Arguzz. Where things live:

- `README.md`: motivation, framing, targets table. Build on it, don't restate it.
- `BLUEPRINT.md`: design source of truth. Substrate, scope, threat model, components, repo layout, MP-SPDZ distribution and re-fetch.
- `notes/mp-spdz.md`: MP-SPDZ architecture map, injection seam, anchor files, grep recipes. Start there before your own codebase sweep.

Invariants: `uv run python main.py` always works, `uv run mypy` always green. See `BLUEPRINT.md` § "Development invariants".

## Subagents

`.claude/agents/mpc-explore.md` is the MPC-protocols exploration subagent (Sonnet by default). Dispatch it via the Agent tool with `subagent_type: mpc-explore` when a question needs deep MPC knowledge + code inspection in `./MP-SPDZ/` (tracing a check, explaining a protocol step, mapping injection points, translating paper notation). Use Opus only if the user asks for it.

## Machines and memory

Project memory lives in the repo at `.claude/memory/`, not in `~/.claude`. The
harness derives its memory path from the cwd, so each machine and worktree gets
a different slug; `.claude/scripts/link-memory.sh` symlinks that path at the
cwd worktree's own `.claude/memory`. **Run it once per worktree.** After that,
memories are ordinary tracked files: they move by `git pull` / `git push` /
`git merge`, and conflicts show up in `MEMORY.md` like any other merge.

**mercury is a peer clone, not a deploy target.** It has its own checkout and
its own GitHub key. There is no rsync, no remote invoke, no deploy script; ssh
in and work there. `containers/run-campaign.sh` is the campaign entrypoint, run
from the repo root on whichever machine is doing the work.

## Working conventions from the notes

- `notes/reading-list.md` explicitly marks papers as "read now", "read if needed", and "don't read". Respect this — don't push the user toward papers flagged as not-our-problem (FHE internals, ZK).
- Notes use terse, opinionated markdown with WHY/WHEN framing. Match that style when editing them; don't bloat with generic summaries.
