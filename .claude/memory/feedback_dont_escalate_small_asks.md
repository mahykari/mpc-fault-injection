---
name: feedback_dont_escalate_small_asks
description: "when the user asks for one small thing, do that thing — don't turn it into a design decision or menu of options"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cb0c2c4b-26ef-4ed8-bd81-48cd2ad94f40
---

When the user makes a small, concrete request ("add randomness", "rename this"), just do it. Don't escalate it into a design debate, a tradeoff analysis, or an AskUserQuestion menu of policies they didn't ask to weigh.

**Why:** On the parallel-runs launcher, the user said "add randomness" and got back a full seed-policy question (contiguous blocks vs random-sample vs block-offset). Their reaction: "i just asked you to add randomness. you're now talking about things i didn't even ask for. fine if you need it, but this is not something i wanted to think about at first."

**How to apply:** Implement the literal ask with a sensible default. If a deeper decision genuinely lurks, mention it in one line and proceed — don't block on it. Save the menu for when the default actually doesn't fit. Pairs with [[feedback_yap_less]] and [[feedback_suggest_dont_write]].

**Also: don't expand scope on your own.** A rhetorical aside ("hopefully no more docker baggage") is not a mandate to rewrite docs. The user: "don't overdo yourself. just do what i ask. if you find it confusing, just tell me. don't make decisions on your own." When something seems stale or off, surface it and ask — don't silently fix a pile of files you weren't asked to touch.

**Simplest possible, no predictory steps.** "write a script for X" means the simplest script that does X — not X plus the verification harness plus the docs plus the related-thing-you'll-probably-want. The user: "you are not expected to do beyond what i ask you to do ... don't do predictory steps." Stop at the boundary of the request; if a follow-on seems useful, name it in a line and let them ask.
