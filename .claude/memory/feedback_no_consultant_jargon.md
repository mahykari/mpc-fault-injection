---
name: No consultant-jargon framings ("blast radius", etc.)
description: Avoid jargon that sounds like advice without saying anything ("clean blast radius", "single source of truth as a benefit"). Be direct about what changes and why.
type: feedback
originSessionId: bca48558-f79c-4fde-9eb1-14776414cc7e
---
Avoid framings like "cleanest blast radius," "single source of truth as a virtue," "clean separation of concerns" when they're standing in for an actual technical reason.

**Why:** I wrote "Single source of truth for the IR; cleanest blast radius" in BLUEPRINT.md as the closing rationale on the substrate decision. User rejected the edit twice with "still not addressing it. Drop the blast radius thing, too." The phrase wasn't doing work — it was decorative.

**How to apply:**
- Say what concretely changes (e.g. "Two `.bc` files come out of one run") instead of why it sounds nice ("clean blast radius").
- If a sentence could be lifted into a generic management slide unmodified, delete it.
- Reasons live in *technical specifics*: "we want one mutated bytecode for all corrupt parties for now because we haven't sampled per-party gadgets yet." Not in metaphors.
