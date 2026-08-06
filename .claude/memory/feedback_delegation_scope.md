---
name: feedback-delegation-scope
description: "When the user says 'give me something to do' or 'let me write some of this', they want a small wire-connecting / small-logic piece — NOT the substantive design or implementation. Don't offload meaty work onto them."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f2a091fa-b56a-4655-90bc-5449ebb07127
---

When the user signals they want to write some code themselves, they
mean **small, well-scoped pieces** — connect two wires, name a helper,
write a small predicate, pick a constant, fill in a stub body. They
are NOT asking to take on the substantive design or implementation
work; that's still the assistant's job.

**Why:** they want to stay tactile with the codebase ("so I don't
forget how to write code") — engagement, not workload offloading.
Routing a multi-step feature ("you write the live-path analysis +
gadget catalog") misreads the request.

**How to apply:** keep the design, planning, and substantive
implementation. When they ask for "something to do", peel off a
small, isolated piece from the current work — ideally something
where the surrounding scaffolding is already done and they're filling
in a hole. Don't hand over the whole feature.
