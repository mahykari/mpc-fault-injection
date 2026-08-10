---
name: project_session_state_2026_08_06
description: Pending task as of 2026-08-10 — restore the tree, rebuild the image, run a ~1000-case sanity campaign
metadata:
  type: project
---

**Next task, agreed 2026-08-10:** restore the working tree to HEAD, then fire a
very small campaign (~1000 cases) to sanity-check the memory-dump fix, driven by
a dynamic workflow. Read [[project_campaign_launch_gotchas]] before sizing or
launching it.

What the fix has and has not been through: one case was smoke-tested by
bind-mounting `pipeline/` over the image copy — 0 `Memory-*` files, run dir 68K,
verdict unchanged. It has never run through a rebuilt image or a real campaign.
`./containers/build.sh pipeline` is the blocker. See
[[project_campaign_disk_blowup]].

On `dispatcher-pull-model`: `cdf5540` (`-o no_memory_output`), `a44e875`
(settings: `bypassPermissions` + deny list, absolute librarian hook path),
`d5fab13` (memory). `3270fde` is the same settings commit on `master`, from
before the cherry-pick. Nothing is pushed.

Working tree carries a stale `.gitignore` / `CLAUDE.md` diff that would revert
`0b72e99` — `git restore` those two, they are not real work.
`.claude/contractor` is present and untracked, which short-circuits
`edit-gate.sh` and keeps teaching mode off; delete it to re-arm.

Disk: 59% used, 1.4T free on `/home`, all 305k run dirs gone.
