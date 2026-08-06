---
name: Use SSH form for git clone
description: When cloning private repos in this project, use git@github.com:owner/repo.git form so the user's SSH key authenticates automatically.
type: feedback
originSessionId: cb3a55c1-60d2-419f-b7b2-31bbd64bbd23
---
For private repos, clone via SSH (`git@github.com:owner/repo.git`), not HTTPS. The user has an SSH key configured; HTTPS prompts for username/token and fails non-interactively.

**Why:** First time I tried `git clone https://github.com/Rigorous-Software-Engineering/python-circil.git`, it failed with "could not read Username". User pushed back asking why I couldn't use their SSH key. SSH form worked first try.

**How to apply:** Default to SSH URLs for any GitHub clone in this project unless the repo is explicitly public *and* read-only access is fine. If unsure whether a repo is private, try SSH first — it works for both.
