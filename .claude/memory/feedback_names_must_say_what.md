---
name: feedback_names_must_say_what
description: Mahyar vetoes names that don't say what the object is (Cell, Site, Run); a name must evoke the thing in one sentence to a stranger
metadata:
  type: feedback
---

On the matryoshka sketch (2026-09-08): "your names really suck. REALLY SUCK.
Not even remotely conveying the idea of what the object is doing. What would
even a site be? Injection site? Execution site? Computer site? Nuclear site?"

**Why:** he reviews by reading; a name that needs its definition looked up
costs him the same as no name. Generic nouns (Site, Run, Cell, Config, Serve)
fail the test.

**How to apply:** before proposing a class or module name, write the one
sentence it should evoke and check a stranger would land on that sentence
from the name alone. Prefer domain nouns already in his vocabulary (grid
point, experiment, toolchain, assignment, worker). Names introduced in
`70c42dc` without his review, to re-check in the refactor: `Serve`, `Launch`,
`Worker`. See [[project_matryoshka_configs]].
