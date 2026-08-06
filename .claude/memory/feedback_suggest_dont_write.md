---
name: feedback-suggest-dont-write
description: "Default to suggesting, not writing. User implements; I point to files, propose precise changes, push back when they'd shoot themselves in the foot."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 636bf176-9417-477c-acc6-97c76330ccfc
---

**Default mode: don't write code.** Hands off until the user explicitly asks me to make a change. When they ask a "what should we do here" question or surface a problem, the answer is a suggestion, not an edit.

Specifics:

- Don't think 10 steps forward. Solve the one thing in front of us.
- No boilerplate. No "good-looking" code that's actually rubbish.
- Don't give *directions* either (change file X, rewrite line Y, add field Z) unless explicitly asked. User prefers to dig and find the spot. Answer the question on the table; let them choose what to touch.
- Be precise *when asked*: file paths, function names, line numbers when relevant.
- Stop the user when they're clearly shooting themselves in the foot (per [[feedback_push_back]]). "Look, that's going to break X" beats silent compliance.
- Track every step: the user wants to follow what's happening regardless of who's implementing. Be a navigator, not a driver.

**Why:** user 2026-06-01 — "from here on, you don't write anything unless i ask you to write. you don't think 10 steps forward, you don't write a lot of boilerplate and good-looking code that's all rubbish. i need to track every step we take, regardless of who implements it. so, don't run for yourself, just be precise, point me to the right files, and generate good suggestions." Follow-up: "this is mainly to let me write more, or at least think more, while still not getting stuck." So the rule exists to give the user space to think and write, *without* leaving them stuck waiting on me.

**How to apply:** when in doubt, suggest. When asked to write, write the minimum. "Let's do that" / "let's X" / "we should do Y" are *task-starting* phrases, not write permission — the user is naming the task, not delegating it. Wait for an explicit "write it" / "do it for me" / "fix this for me" before touching files. See also [[feedback_yap_less]], [[feedback_code_terseness]], [[feedback_delegation_scope]].
