---
description: Engage librarian mode. Every source-referring claim uses the CLAIM block format defined in CLAUDE.md.
---

Engage librarian mode for the rest of this session.

For every factual claim about what a paper, protocol, tool, or system says, promises, or defines, emit the CLAIM format:

```
--- CLAIM ---
<your restatement of the claim>

SOURCE: [<label>](<url>)
> <verbatim quote>
```

Rules:

- Fetch the source before making the claim. Do not cite from memory.
- Quote verbatim, short (aim under 15 words), attributed to a specific URL.
- Multiple `SOURCE:` + `> quote` pairs per CLAIM block are allowed.
- If a source cannot be fetched, do NOT wrap the claim in a CLAIM block. State it in prose and mark it `(unverified)`.
- The Stop hook at `.claude/hooks/librarian.sh` will reject any malformed CLAIM block; if that happens, fix the format and continue.

Librarian mode stays engaged until the session ends. Casual chat, admin, and pure execution tasks do not need CLAIM blocks.

Confirm engagement with one short line, then proceed with whatever task is next.
