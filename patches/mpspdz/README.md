# MP-SPDZ source patches

Applied (numerically ordered) inside the Docker build (`docker/Dockerfile.mpspdz`)
on top of a clean MP-SPDZ v0.4.2 source tree. Only patches that need to land
in the C++ binary live here — Python-side adapter quirks stay in `pipeline/`.

| # | Target | Why |
|---|---|---|
| 0001 | `Processor/Machine.hpp` :: `check_program` | Disable startup bytecode-fingerprint check so corrupt parties can load mutated `.bc`. Plumbing, not malicious security. See `notes/mpspdz-patching.md`. |

## Seeded-bug overlay (`patches/mpspdz-seeded-bug/`)

Overlay applied on top of this base set when `./docker/build.sh seeded-bug`
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
     https://github.com/data61/MP-SPDZ/releases/download/v0.4.2/mp-spdz-0.4.2.tar.xz
   tar -xJf /tmp/mp-spdz.tar.xz -C /tmp
   ```
2. Edit the file inside `/tmp/mp-spdz-0.4.2/` (or copy it out, edit, copy back).
3. Generate the patch:
   ```
   diff -u /tmp/mp-spdz-0.4.2.orig/<path> /tmp/mp-spdz-0.4.2/<path> \
     | sed 's|/tmp/mp-spdz-0.4.2.orig|a|; s|/tmp/mp-spdz-0.4.2|b|'
   ```
4. Save as `patches/mpspdz/NNNN-short-name.patch` with a header explaining *why*.
5. Verify with `patch --dry-run -p1 < the.patch` from a clean source tree.
6. Add a row to the table above.
7. Rebuild: `docker/build.sh`.

## Discipline

Only disable plumbing layers — things that exist in semi-honest protocols too.
Never disable the malicious-security mechanisms themselves (MAC generation,
sacrificing, consistency checks at OPEN). Disabling those would reduce the
protocol to semi-honest and make the harness meaningless.
