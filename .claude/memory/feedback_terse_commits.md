---
name: commit-messages-should-say-one-thing
description: "Commit messages are not for narrating every implementation note. One title line, optionally one short paragraph for the *why*. No multi-section commit bodies, no \"implementation note\" subsections, no \"deleted X because Y\" recaps."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cb94fbd6-51fc-4916-b29c-aecbc9c30155
  modified: 2026-08-04T15:50:04.260Z
---

**Rule.** A commit message says one thing — the headline (~50–70 chars), and at most one short paragraph for *why* the change exists if the title doesn't make it obvious. No multi-section bodies, no "implementation note:" subsections, no recap of what got deleted/added (the diff shows that).

**Why:** the user pushed back on a 16-line commit body covering the gadget rationale, the SSA workaround, the adapter-helpers pattern, and the deletion. Quote: "don't write books in the commits; just write one thing." Recent commits in the repo are short on purpose — `git log --oneline` should remain skimmable.

**How to apply:**
- Title: imperative, ≤70 chars, name the user-visible change.
- Body: **default to none.** Write the title, stop, and only add a body if the *why* is genuinely not inferable from it. When you do, ONE line. Never more than two.
- This has now been corrected twice. On 2026-06-29 an exactly-5-line body was rejected with "write a shorter commit message". On 2026-07-30 another 5-line body was rejected with "write a shorter commit. in general, short commits over longs." Five lines is not a budget to spend; treat anything past one line as a smell.
- Mechanics, workarounds, deleted-file justifications: in the code comments or notes, not the commit.
- If you're tempted to write a second paragraph, ask whether the second thing is a separate commit.

Related: [[feedback_terse_no_commentary]] (same instinct, different context).
