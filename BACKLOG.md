# BACKLOG

One line per item, tagged with the branch that owns it. Detail lives where the
tag points; this file only says what is open and who owns it.

## dispatcher-pull-model (PR #6)

- [ ] Cheap review batch: owner dataclasses, no `argparse.Namespace` past the
      parser, `apply_overrides` and the `CONFIG` spec file gone, one launcher,
      route table, `pipeline/__init__` empty, RNG streams by purpose.
- [ ] `store.py` rewrite: SQLAlchemy Core plus the in-memory queue (deque of
      pending ids, lease heap). Goes with the matryoshka below.
- [ ] Resolve the review threads once the code lands.

## matrix-rewrites (detail: `PROGRESS.md`, "Fix when merging to master")

- [ ] Runtime prime differs from compile prime (`Prime.runtime_args` vs
      `Prime.compile_args`). Pick one, pass it to both.
- [ ] Master's pipeline against upstream python-circil: apply the renames.
- [ ] MP-SPDZ 0.4.2 to 0.4.3; confirm patch 0001 still applies.
- [ ] Every generated matrix is constant-valued; bake per-entry values from the
      seed or read input files.
- [ ] Rename the verdict vocabulary (`VerdictCategory`).
- [ ] Agree master defaults for `injection_layer` and `mutation_kind`.
- [ ] 35 inert cases: compiler folding or prime mismatch. 2 honest_invalid
      uninvestigated.

## master, after both merge

- [ ] Matryoshka configs: GridPoint, Experiment, Toolchain, Assignment.
      Corrupt set and depth drawn per experiment from the seed; `--rng-seed`
      goes.
- [ ] `main.py aggregate`, `rerun-inert`, `results.db`: port to `campaign.db`
      or delete.
- [ ] `containers/check_sites_campaign.py` calls the pre-dispatcher launcher;
      port or delete.
- [ ] Logging instead of prints in launcher and dispatcher.

## Campaigns

- [ ] 2M campaign on mercury, launched 2026-08-10 after the PID fix: check
      whether it finished; harvest `campaign.db`.
