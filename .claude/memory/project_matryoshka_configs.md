---
name: project_matryoshka_configs
description: Agreed config design for the master refactor — nested dolls by owner (GridPoint, Experiment, Toolchain, Assignment), one coin = the experiment seed
metadata:
  type: project
---

Mahyar's proposal (2026-09-08), accepted: configs nest like a matryoshka. Each
stage wraps the previous stage's config and adds its own fields. Every doll has
exactly one writer (owner model: one module sets a value, nobody overwrites),
frozen, so outer dolls cannot reach in. Plain composition; no canonical
pattern name.

**Dolls** (names are mine, proposed 2026-09-08 after Mahyar vetoed
Cell/Site/Run; see [[feedback_names_must_say_what]]; not yet confirmed):

- **GridPoint**: protocol, n_parties, combo, timeout_s, max_depth. Owns `spec`
  and the threshold validation. One row of the `config` table.
- **Experiment**: GridPoint + seed. Owns everything drawn from the seed:
  corrupt_set, depth, and the RNG streams by purpose. One row of the
  `experiment` table; exactly the `GET /next` payload.
- **Toolchain**: mpspdz_root, patched/seeded-bug flags. Machine-local. Owns
  `bin_dir`.
- **Assignment**: Experiment + Toolchain + instance_id + runs_root. Worker-side
  only. Owns program_id, run_dir, party cwds, report_path, party_binary_path.

Not a doll: `CampaignPlan` is the factory that fans out into grid points and
seed ranges; nothing wraps it. The chain forks once, at Assignment, which wraps
two dolls (one arrived over HTTP, one built on the worker).

**Who takes what:** Generator takes Experiment; Oracle takes GridPoint;
Injector, Compiler, Executor, Reporter take Assignment. Each component holds
the innermost doll that covers its needs, so the `Needs*` views mostly go.

**Randomness, settled:** one true coin, the experiment seed (a counter from
`--start-seed`). Streams derive by purpose, `Random(f"{seed}:{purpose}")`:
program, gadgets, corrupt_set, depth. Corrupt set and depth become
per-experiment draws (today one draw per grid point, so a campaign samples 12
corrupt sets total). `--rng-seed` disappears. The first half (program_rng,
gadget_rng properties on Config) landed in `70c42dc`.

**Change cost:** new knob at a stage = a field + a column default (cheap, and
everything on the roadmap is this); new outermost stage = wrap (cheap); a doll
inserted mid-chain = every path and both mirrors change (expensive; no roadmap
item is this).

**Landing:** one doll per merge, innermost first, with `Config` delegating to
the landed doll until the last one; every intermediate master ships.
