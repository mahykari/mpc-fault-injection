---
name: reference_settings_reload
description: settings.json allow/deny reload live mid-session, but defaultMode latches at session start
metadata:
  type: reference
---

Editing `.claude/settings.json` mid-session applies its `allow`/`deny` rules
immediately, but `permissions.defaultMode` is resolved once at session start and
does not change until restart (or until the mode is cycled in the UI).

This split is a trap when swapping one mechanism for the other. On 2026-08-06 an
allowlist was deleted in the same commit that set `defaultMode:
bypassPermissions`. The deletion took effect at once and the new mode did not,
so every command outside `settings.local.json` started prompting. It looked like
`bypassPermissions` was being rejected; it was simply not loaded yet.

Not the cause, but worth ruling out first when bypass really is refused:
`skipDangerousModePermissionPrompt` must be true (it is, in
`~/.claude/settings.json`), and managed settings can set
`disableBypassPermissionsMode` (there are none on mercury).

Change the mode and the rules in separate steps, or restart between them.
