---
name: Terse responses, no commentary
description: User wants change-and-why output without editorial framing, alignment-praise, or "this means X" exposition.
type: feedback
originSessionId: cb3a55c1-60d2-419f-b7b2-31bbd64bbd23
---
Lead with what changed and why. Don't follow up with "this aligns with the blueprint", "this preserves invariants", "net effect is...", or other meta-commentary the user can verify themselves. Skip section headers when the answer is short.

**Why:** User explicitly said "Only tell me what changes and why. Don't comment on things." Their feedback through the day consistently rewarded terse, decisive output and pushed back on my longer expository paragraphs. They read diffs and verify themselves; my job is to surface decisions, not to narrate them.

**How to apply:** When asked to plan or describe a change, list bullets like "rename X → Y because Z" — one why-clause per change. Don't tack on summaries of what the user can already infer from the list. End-of-turn summary should be one sentence or omitted entirely if the work itself is the answer.
