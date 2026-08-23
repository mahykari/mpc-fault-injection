---
name: project-patch-discipline
description: every MP-SPDZ patch needs a stated security reason; noop-ing an inconvenient check is not allowed
metadata:
  type: project
---

Mahyar's rule, stated 2026-08-23: **any patch we apply to MP-SPDZ must have a
clear security reason behind it. We cannot simply noop an inconvenient check.**

A check that blocks the harness is not thereby a check we may switch off. If a
patch cannot name which security property is unaffected and why, it does not
land. The full policy lives in `patches/mpspdz/README.md` under "Discipline",
which is the tracked home for it.

**Known violation of the rule, already in the tree.** Patch
`0001-noop-check-program.patch` makes *every* party skip the bytecode
fingerprint comparison. That models nothing, because a real adversary cannot
make honest parties stop checking. The wanted version has the corrupt party run
the check and send the honest program's hash while executing mutated bytecode,
so honest parties keep checking and still see agreement. Written up as
"Planned: a corrupt party that lies on the program check" in the same README.

Until that lands, every result carries the weaker assumption that honest parties
are not verifying program identity at all.

The seeded-bug overlay breaks the rule deliberately and is quarantined in
`patches/mpspdz-seeded-bug/` for exactly that reason. See
[[project-seeded-bug-campaign-result]].
