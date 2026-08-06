---
name: project_session_state_2026_08_06
description: Session end 2026-08-06 — where the branches, settings, and container image stand
metadata:
  type: project
---

Picking up from here:

- `cdf5540` on `dispatcher-pull-model` — the `-o no_memory_output` fix. See
  [[project_campaign_disk_blowup]].
- `3270fde` on `master` — permissions flattened to `bypassPermissions` plus a
  short deny list, and the Stop hook's librarian path made absolute. It was
  relative, resolved only from the repo root, and failed with "command not
  found", so librarian mode never fired.
- Cherry-picked onto `dispatcher-pull-model` as `a44e875`, so both fixes are on
  that branch and the settings are live there. Nothing is pushed.

**The settings only take effect on the branch that carries them.** A session
started on a branch without that commit reads the old allowlist.

`.claude/contractor` is untracked and present, which disarms `edit-gate.sh`
entirely — the main thread can edit and teaching mode is off. Delete the file
to put teaching mode back.

The container image still has the pre-fix code baked into `/app`. Workers keep
dumping memory until `./containers/build.sh pipeline` reruns.

Disk after the wipe: 59% used, 1.4T free on `/home`.
