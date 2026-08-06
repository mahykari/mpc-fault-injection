---
name: feedback_drop_it_means_drop_it
description: "When told to drop a mechanism, delete it — don't preserve it renamed or in a reduced form"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d937afb8-b804-48f4-98b3-cfaebe21cddc
  modified: 2026-08-06T13:24:41.064Z
---

When the user says a mechanism is no longer needed, remove it. Do not keep a slimmer version, a rename, or a wrapper that preserves the old shape.

**Why:** Planning the memory-in-repo work (2026-08-06), the user said git now syncs both machines so rsync is out of the way. I kept `deploy-mercury.sh` twice: first as a memory-sync script, then as a "launch-mercury.sh" that was the same file minus the rsync. Both got rejected. His point: "nothing happens outside the server anymore. there's no remote invoke." I was defending hard-won incantations (the `setsid` backgrounding trick) instead of noticing the whole category of remote-invoke had disappeared.

**How to apply:** When a change removes the *reason* a component exists, delete the component and follow the consequence outward rather than salvaging its internals. If a fiddly detail inside it is genuinely worth keeping, it goes in a comment on whatever survives, not in a shrunken script. Ask "what class of thing just stopped existing?" before "what can I preserve?"
