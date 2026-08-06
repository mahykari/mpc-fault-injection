---
name: feedback-code-terseness
description: "Code I write must match the terseness I aim for in comms. No inline magic strings, no manual dispatch chains, no inconsistent capitalisation across labels."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 636bf176-9417-477c-acc6-97c76330ccfc
---

The yap-less rule for comms applies to code too. Specifically:

- No inline magic strings as control labels. If the same string appears in two places (e.g. a string-typed `reason` field re-checked in a switch), it's an enum or a constant or a typed `Literal`, not a string.
- No chunky if/elif chains that are really dynamic dispatch. Use a dict, a `Literal` enum on the value being switched, or a property on the dataclass that already computes the classification.
- Capitalisation is consistent: `"honest_invalid"` and `"BUG"` mixed in one bucket dict is a smell.

**Why:** user 2026-06-01 — "i've grown white hair because of you. does this really look like a clean way of handling this? inline strings with different capitalisation formats? a chunky if that's just a dynamic dispatch?"

**How to apply:** when classifying / dispatching, prefer a typed field at the source (e.g. an enum on the dataclass that already holds the input). Re-deriving the same classification at the call site = wrong layer. See also [[feedback_code_structure]], [[feedback_yap_less]].
