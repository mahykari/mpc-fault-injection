---
name: feedback_bel_canto_for_design
description: For the refactor Mahyar wants "bel canto mode", design rationale spelled out, not compressed; he blames the terseness rules and word cap for tangled code
metadata:
  type: feedback
---

2026-09-16: "Your current config is too strict and makes you write tangled
soup more than necessary (I suspect because of the word count limit and the
many times you're asked to be precise.)" and "My refactoring needs you on bel
canto mode, instead of tangled prose mode."

Also from the PR #6 review (2026-09-08): "What is X?" in a review comment
usually means "this is bad design and should be discarded", not confusion.
And "cheap tricks" just to get code running (blanking `pipeline/__init__.py`
inside an image, `sys.path.insert` to import siblings, passing
`argparse.Namespace` around) are unacceptable: "I wasn't a bad programmer in
my days of programming. But I wouldn't do such tricks."

**Why:** compressed replies drop the design rationale, so accretion goes
unchallenged and gets patched locally instead of restructured. The rules that
actually push toward soup are "don't escalate small asks", "small
wire-connecting pieces", "helpers can stay ugly".

**How to apply:** in design discussions and the refactor, explain structure in
full sentences with the reasoning attached; diagrams welcome ("I have a big
enough screen"). Never fix a package or import problem at the image or
sys.path layer; fix the package. CLAUDE.md is being rewritten on branch
`claude-md` to say this; until it lands, treat the 200-word cap as a chat
rule, not a design-discussion rule. Supersedes the strictest reading of
[[feedback_yap_less]] and [[feedback_dont_escalate_small_asks]] for design
work.
