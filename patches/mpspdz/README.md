# MP-SPDZ source patches

Applied (numerically ordered) inside the container build
(`containers/Containerfile`) on top of a clean MP-SPDZ v0.4.3 source tree. Only
patches that need to land in the C++ binary live here — Python-side adapter
quirks stay in `pipeline/`.

| # | Target | Why |
|---|---|---|
| 0001 | `Processor/Machine.hpp` :: `check_program` | Disable startup bytecode-fingerprint check so corrupt parties can load mutated `.bc`. Plumbing, not malicious security. See `notes/mpspdz-patching.md`. |

## Seeded-bug overlay (`patches/mpspdz-seeded-bug/`)

Overlay applied on top of this base set when `./containers/build.sh seeded-bug`
is invoked; output lands in `MP-SPDZ/bin/Linux-amd64-patched-seeded-bug/`.
Used to verify the harness's Oracle can actually detect silent divergence
(intentionally violates the discipline below).

| # | Target | Why |
|---|---|---|
| 0002 | `Protocols/MAC_Check.hpp` :: `mac_fail_remove` | No-op the MAC-fail throw site so MASCOT silently accepts bumped shares. The harness should see most runs flip from `caught` → `bug`. |

## Adding a new patch

1. Re-extract the tarball to a temp dir:
   ```
   curl -L -o /tmp/mp-spdz.tar.xz \
     https://github.com/data61/MP-SPDZ/releases/download/v0.4.3/mp-spdz-0.4.3.tar.xz
   tar -xJf /tmp/mp-spdz.tar.xz -C /tmp
   ```
2. Edit the file inside `/tmp/mp-spdz-0.4.3/` (or copy it out, edit, copy back).
3. Generate the patch:
   ```
   diff -u /tmp/mp-spdz-0.4.3.orig/<path> /tmp/mp-spdz-0.4.3/<path> \
     | sed 's|/tmp/mp-spdz-0.4.3.orig|a|; s|/tmp/mp-spdz-0.4.3|b|'
   ```
4. Save as `patches/mpspdz/NNNN-short-name.patch` with a header explaining *why*.
5. Verify with `patch --dry-run -p1 < the.patch` from a clean source tree.
6. Add a row to the table above.
7. Rebuild: `./containers/build.sh`.

## Discipline

**Every patch needs a stated security reason. Convenience is not one.** A check
that gets in the way of the harness is not thereby a check we may switch off. If
a patch cannot name what security property is unaffected and why, it does not
land.

Only disable plumbing layers — things that exist in semi-honest protocols too.
Never disable the malicious-security mechanisms themselves (MAC generation,
sacrificing, consistency checks at OPEN). Disabling those would reduce the
protocol to semi-honest and make the harness meaningless.

The seeded-bug overlay violates this on purpose and is quarantined in its own
directory for that reason: its whole job is to confirm the Oracle can see a
silent divergence.

### Planned: a corrupt party that lies on the program check

Patch 0001 is weaker than it should be. It makes *every* party skip the
bytecode-fingerprint comparison, which models nothing: a real adversary cannot
make honest parties stop checking.

The faithful version has the corrupt party run the check and send the *honest*
program's hash while executing mutated bytecode. Honest parties keep checking
and still see agreement. That is what a real deviating party would do, and it
keeps the check in the protocol where it belongs instead of removing it from
the model.

Until then, be aware that results carry the current weaker assumption: honest
parties are not verifying program identity at all.
