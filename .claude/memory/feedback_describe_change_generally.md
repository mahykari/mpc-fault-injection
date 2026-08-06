---
name: describe-a-change-by-its-general-capability-not-the-example
description: "When writing commit messages / docs about a code change, scope language to what the change actually does, not just the smoke-test mutation we used to verify it"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cb94fbd6-51fc-4916-b29c-aecbc9c30155
---

When describing a change (commit messages, PR titles, doc updates), lead with what the change actually does in its full generality, not with the specific example used to verify it.

**Why:** I framed a `check_program` no-op patch as "lets LDSI mutation through to MAC check" — but `check_program` hashes the whole tape, so the patch lets *any* bytecode divergence through. Framing it around the LDSI smoke test made the change sound narrower than it is, which is misleading both for future-me reading the commit and for anyone deciding whether the patch is relevant to a different mutation.

**How to apply:** for each commit/doc, ask "is this scope statement true for variations of the mutation/example I happened to test?" If the change is more general than the test case, the description should match the general capability. Mention the smoke test as evidence, not as the headline.
