---
name: feedback-plan-mode-short
description: "User uses plan mode as a no-changes guardrail / brainstorming space, not as a \"produce a detailed plan doc\" request. Keep plan files short."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 636bf176-9417-477c-acc6-97c76330ccfc
---

When the user invokes `/plan`, they usually mean "stop making changes
and let's talk it through," not "produce a multi-page plan doc."
Default to a short plan file (a handful of bullets) and continue
discussion conversationally.

**Why:** user 2026-05-28 — "i just turned on plan mode to brainstorm
with you, and stop you from making changes. i don't want to read all
of that." The long, sectioned plan was overkill.

**How to apply:** plan file = problem in 1-2 sentences, recommended
approach in 3-5 bullets, files touched as a one-liner. Skip
verification sections unless asked. Treat plan mode as conversation
with a brake, not as document production.
