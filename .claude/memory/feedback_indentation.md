---
name: Use two-space indentation in Python
description: User prefers 2-space indentation in Python (and consistently elsewhere) over PEP 8's 4-space.
type: feedback
originSessionId: cb3a55c1-60d2-419f-b7b2-31bbd64bbd23
---
In this project, indent Python with **two spaces**, not four.

**Why:** User explicitly told me they find it nicer. Style preference, applies project-wide. mypy/ruff don't care; this is purely aesthetic.

**How to apply:** When writing or editing any `.py` file in this repo, use 2-space indents. Don't auto-format to PEP 8's 4-space default. If linting comes up later, configure ruff/black with `indent-width = 2` accordingly.
