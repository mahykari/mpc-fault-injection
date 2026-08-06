---
name: Code structure rules
description: Four mandatory code-style rules — config-as-source-of-truth, no string assembly at call sites, derived values as properties, no long arg lists
type: feedback
originSessionId: 9b62c8c3-6b2f-4e1a-bd0e-ae575334439d
---
Four rules the user requires for all code in this project:

1. **No string assembly at call sites.** Every path, command, and protocol name lives in the config or is derived from it in one place. If you find yourself writing an f-string inside a method call, extract it to a `@property` or function on a dataclass.

2. **Single config, multiple views.** One master `Config` dataclass (`frozen=True`). Each component defines a `typing.Protocol` describing only the fields it needs. Pass the full config, type-annotate with the protocol view. Mypy then documents which fields each function actually touches.

3. **Derived values are properties, not reconstructions.** If a value (e.g. `mutated_id`) is derived from another (`program_id`), the derivation lives in exactly one place — a `@property` on the dataclass. Downstream code never rebuilds the relation.

4. **No 10-argument functions.** If a function needs more than 3–4 arguments, those arguments probably belong together in a dataclass. Group them.

**Why:** User wants structure to convey intent without comments doing the heavy lifting. Long arg lists and inline string assembly hide the real shape of the code; config + per-component protocol views make dependencies explicit and let mypy document them.

**How to apply:** Default to building/extending a `Config` dataclass with `@property` derivations for any computed value (paths, ids, binary locations, derived sets of cwds). Add a `typing.Protocol` per component declaring its slice. When a method signature reaches 4 args, pause and bundle.
