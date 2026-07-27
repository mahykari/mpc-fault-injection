---
description: Reset teaching-mode markers; a new problem starts now
allowed-tools: Bash(bash:*)
---

!`bash .claude/scripts/new-problem.sh`

A new problem has started. Teaching mode applies:
walk the setup (constraints, what's known, why the naive approach fails),
then STOP and ask Mahyar for his written guess. Do not spawn a contractor
subagent and do not propose a solution until guess.md exists.
