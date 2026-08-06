---
name: project_shamir_ssl_gap
description: malicious-shamir SSL cert gap — RESOLVED; per-run cert provisioning committed to more-protocols branch (ca07dd0)
metadata: 
  node_type: memory
  type: project
  originSessionId: db3d86a0-5d48-40b3-8aa5-55b9590cdbf6
---

**RESOLVED 2026-07-07** — SSL cert provisioning written, verified (shamir 3/3 `caught`, spdz2k 3/3, mypy green), committed to `worktree-more-protocols` as `ca07dd0`. Fix: `needs_ssl` on `ProtocolSpec`; the Executor seeds each per-run party cwd's `Player-Data` via an `mpspdz.py` helper (generate a shared cert set for n parties once, copy identically). **PR #5 MERGED to master as `2d738ff`** (2026-07-09). One real conflict, in `types.py`: more-protocols had *dropped* `"semi"` from the `Protocol` literal (it's not a fuzz target — no detection mechanism), but semi-rerun (`rerun-inert`, merged earlier this session) sets `protocol="semi"` in `_semi_config_for`. Resolution: keep `semi` in the literal AND add a defense-free `PROTOCOL_SPECS["semi"]` (Prime domain, honest_majority=False, empty catch_signatures, no SSL) — else `Config.__post_init__` → `self.spec` → `PROTOCOL_SPECS["semi"]` KeyErrors on every rerun. Verified semi constructs/resolves, uses stock `semi-party.x`, runtime `-P <M127>` (same path mascot proves). mypy green. Container image still needs a `./containers/build.sh pipeline` rebuild to pick up the merge before a real campaign (image bundles repo code). Original diagnosis below.

Smoke-testing the more-protocols branch (2026-07-07, [[project_more_protocols_plan]]):

- **spdz2k: works.** In-container smoke, 3/3 `caught`, `"MacCheck Failure"` matched, ~314 ms/run. Ready to merge/campaign.
- **malicious-shamir: BLOCKED on SSL certs.** It's the first protocol that uses SSL (CryptoPlayer) — needs `Player-Data/P<i>.pem` for all N parties **in each per-run party cwd** (`runs/<id>/{honest,mutated}/`). The container only runs `setup-ssl.sh 2` at the MP-SPDZ root; per-run cwds have empty `Player-Data/`, so the honest baseline dies with `Cannot access Player-Data/P0.pem`. mascot/spdz2k use plaintext channels, so this never mattered before.
- Manually dropping a shared 3-party cert set into the cwds confirmed the spec is otherwise correct: honest produces output, mutated twin fires `inconsistent Shamir secret sharing` → oracle would return `caught`. So prime, `-T`, and catch signature are all right; ONLY cert provisioning is missing.

**Fix (unwritten, feature source):** provision a *shared* SSL cert set into each per-run party cwd's `Player-Data/` before launching SSL protocols. Certs must be identical across all party cwds (shared PKI). Natural shape: `needs_ssl` flag on `ProtocolSpec` + a setup step in the Executor, and the container should `setup-ssl.sh` for n≥3 (or generate per-run).

**Also:** the container build flow is worktree-hostile — `COPY python-circil/` fails when python-circil is a symlink pointing outside the build context (`too many levels of symbolic links`); on master it's a real clone so it's fine. Workaround: materialize a real dir for the build.
