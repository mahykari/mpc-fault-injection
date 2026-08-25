"""Adapters around MP-SPDZ's CLI tools (compiler module + party binary).

MP-SPDZ was built as a CLI, not a library. These adapters wrap its
quirks — CWD-bound output paths, fake-argv option parsing, per-process
compiler singleton, party-binary launch shape, and instruction-list
mutation — so the pipeline components above never see them. Keep the
business-logic call sites (gadgets, oracles, ...) free of `inst.args`
and `type(inst).__name__` pokes; surface clean intent here instead.
"""
from __future__ import annotations

import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator

from pipeline.config import (
  NeedsCompilerToolkit,
  NeedsPartyBinary,
  NeedsSslProvisioner,
)
from pipeline.types import PartyOutput


@contextmanager
def _working_directory(target: Path) -> Iterator[None]:
  previous = Path.cwd()
  target.mkdir(parents=True, exist_ok=True)
  os.chdir(target)
  try:
    yield
  finally:
    os.chdir(previous)


class MpSpdzCompilerToolkit:
  """Library-shaped wrapper around MP-SPDZ's CLI compiler module.

  `compile` runs the DSL and returns the in-memory Program object
  (one per call — Compiler enforces a per-process singleton, which we
  reset before each call so the Injector can recompile from source for
  the mutated twin). `finalize_into` runs optimization passes and
  writes `.bc`/`.sch` under `output_dir/Programs/`.
  """

  def __init__(self, config: NeedsCompilerToolkit) -> None:
    self._config = config
    if str(config.mpspdz_root) not in sys.path:
      sys.path.insert(0, str(config.mpspdz_root))

  def compile(self, program_id: str, source: str) -> Any:
    compiler_cls = self._load_compiler_class()
    compiler_cls.singleton = None
    custom_args = [*self._config.spec.domain.compile_args, program_id]
    compiler = compiler_cls(custom_args=custom_args)
    compiler.prep_compile(name=program_id)
    exec(source, compiler.VARS)
    return compiler.prog

  def finalize_into(self, program: Any, output_dir: Path) -> None:
    with _working_directory(output_dir):
      for subdir in ("Programs/Bytecode", "Programs/Schedules"):
        Path(subdir).mkdir(parents=True, exist_ok=True)
      # Optimization re-emits instructions through MP-SPDZ's module-level
      # `program` reference (set in Program.__init__). If we compiled
      # twice, that reference points at the most-recent Program, and
      # finalizing the earlier one would route its optimized
      # instructions into the later tape. Restore globals to *this*
      # program before finalize.
      self._bind_module_globals(program)
      program.finalize()

  def _bind_module_globals(self, program: Any) -> None:
    from Compiler import comparison, instructions, instructions_base, types  # type: ignore[import-not-found]
    from Compiler.program import Program  # type: ignore[import-not-found]
    Program.prog = program
    instructions.program = program
    instructions_base.program = program
    types.program = program
    comparison.program = program

  def _load_compiler_class(self) -> Any:
    from Compiler.compilerLib import Compiler as MpCompiler  # type: ignore[import-not-found]
    return MpCompiler


class MpSpdzPartyBinary:
  """One MP-SPDZ party binary (e.g. `mascot-party.x`).

  Knows the binary's argv shape and how to run N copies of itself
  concurrently.
  """

  def __init__(self, config: NeedsPartyBinary) -> None:
    self._config = config

  def run_parties(
    self,
    party_cwds: tuple[Path, ...],
  ) -> tuple[PartyOutput, ...]:
    """Spawn one party per cwd, then collect each output.

    The parties have to run concurrently: each one connects to its
    peers over sockets at startup and won't make progress until every
    peer has connected. Sequential starts would deadlock party 0
    waiting for party 1.

    So we spawn all N first (Popen returns immediately), then walk
    the list collecting each output. By the time we call communicate
    on party 0, every party is already up and talking to its peers.
    """
    n_parties = len(party_cwds)
    port = self._pick_port(n_parties)
    processes = [
      self._spawn(
        party_id=i, n_parties=n_parties,
        port=port, cwd=party_cwds[i])
      for i in range(n_parties)
    ]
    # One deadline for the whole run: a watchdog kills every party's process
    # group at once on expiry. Parties run concurrently, so a per-party timeout
    # would serialise to n * timeout_s and leave the still-hung peers running.
    killed = threading.Event()

    def _reap_all() -> None:
      for proc in processes:
        self._kill_group(proc)

    def _watchdog() -> None:
      killed.set()
      _reap_all()

    timer = threading.Timer(self._config.timeout_s, _watchdog)
    timer.start()
    try:
      collected = [proc.communicate() for proc in processes]
    finally:
      timer.cancel()
      _reap_all()

    return tuple(
      self._party_output(i, processes[i], collected[i], timed_out=killed.is_set())
      for i in range(n_parties)
    )

  def _spawn(
    self,
    *,
    party_id: int,
    n_parties: int,
    port: int,
    cwd: Path,
  ) -> "subprocess.Popen[str]":
    spec = self._config.spec
    cmd = [
      str(self._config.party_binary_path),
      "-p", str(party_id),
      "-N", str(n_parties),
      *spec.domain.runtime_args,
      *spec.threshold_args(n_parties),
      "-h", "localhost",
      "-pn", str(port),
      self._config.program_id,
    ]
    return subprocess.Popen(
      cmd, cwd=cwd,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True,
      start_new_session=True,
    )

  @staticmethod
  def _kill_group(proc: "subprocess.Popen[str]") -> None:
    """SIGKILL the party's whole process group (start_new_session gave it its
    own), so a hung party and any children die together. No-op if it's gone."""
    if proc.poll() is not None:
      return
    try:
      os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
      try:
        proc.kill()
      except ProcessLookupError:
        pass

  def _party_output(
    self,
    party_id: int,
    proc: "subprocess.Popen[str]",
    collected: tuple[str, str],
    *,
    timed_out: bool,
  ) -> PartyOutput:
    stdout, stderr = collected
    if timed_out:
      note = f"\n[party {party_id}] timed out after {self._config.timeout_s}s"
      return PartyOutput(
        party_id=party_id, stdout=stdout or "",
        stderr=(stderr or "") + note, exit_code=-1,
      )
    return PartyOutput(
      party_id=party_id, stdout=stdout, stderr=stderr,
      exit_code=proc.returncode,
    )

  @staticmethod
  def _pick_port(n_parties: int, attempts: int = 50) -> int:
    """Find a base port P such that P..P+n_parties-1 are all bindable
    with SO_REUSEADDR set — matching MP-SPDZ's ServerSocket behavior
    (Networking/ServerSocket.cpp:40), so TIME_WAIT ports are accepted.
    MP-SPDZ uses `port + player_id` per party (Networking/Player.h:50),
    hence the contiguous-window requirement.
    """
    for _ in range(attempts):
      with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", 0))
        base: int = s.getsockname()[1]
      probes: list[socket.socket] = []
      ok = True
      try:
        for offset in range(n_parties):
          t = socket.socket()
          t.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
          try:
            t.bind(("", base + offset))
            probes.append(t)
          except OSError:
            t.close()
            ok = False
            break
        if ok:
          return base
      finally:
        for t in probes:
          t.close()
    raise RuntimeError(
      f"could not find a free {n_parties}-port window after {attempts} attempts"
    )


class SslProvisioner:
  """Shared SSL PKI for protocols that use encrypted channels.

  Malicious-shamir talks over `CryptoPlayer` and verifies each peer's
  certificate against the certs in its own `Player-Data/`. Every party
  cwd must therefore carry the *same* cert set: we generate one set for
  `n_parties` once (MP-SPDZ's `Scripts/setup-ssl.sh`), cache it, then copy
  it identically into each cwd. Generating per-cwd independently would
  hand each party a different CA and the TLS handshake would fail.
  """

  def __init__(self, config: NeedsSslProvisioner) -> None:
    self._config = config
    self._shared: Path | None = None

  def provision(self, party_cwds: Iterable[Path]) -> None:
    shared = self._shared_certs()
    for cwd in {Path(c) for c in party_cwds}:
      dest = cwd / "Player-Data"
      dest.mkdir(parents=True, exist_ok=True)
      for cert in shared.iterdir():
        shutil.copy(cert, dest / cert.name)

  def _shared_certs(self) -> Path:
    if self._shared is None:
      staging = Path(tempfile.mkdtemp(prefix="mpspdz-ssl-"))
      self._generate(staging)
      self._shared = staging
    return self._shared

  def _generate(self, ssl_dir: Path) -> None:
    script = self._config.mpspdz_root / "Scripts" / "setup-ssl.sh"
    subprocess.run(
      ["bash", str(script), str(self._config.n_parties), str(ssl_dir)],
      check=True, capture_output=True, text=True,
    )


# ────────────────────────────────────────────────────────────────────────────
# IR navigation / mutation helpers.
#
# Small functions that reach into MP-SPDZ's `Compiler.program` objects so
# gadget code doesn't have to. Each helper does one thing on a tape / an
# instruction / a register. Stay terse; intent in the name, mechanism in
# the body.
# ────────────────────────────────────────────────────────────────────────────


def find_secret_writers(tape: Any) -> list[Any]:
  """Every instruction on `tape` whose destination (`args[0]`) is a secret register.

  Covers anything we can splice a bump after: LDSI, ADDSI/SUBSI/MULSI,
  ADDS/SUBS, MULS, TRIPLE, SQUARE, INPUT — whatever produces an `s`
  register. The dst-redirection trick (see `single_variable_bump.py`)
  works uniformly on all of them.
  """
  return [
    inst
    for block in tape.basicblocks
    for inst in block.instructions
    if _writes_secret(inst)
  ]


def _writes_secret(inst: Any) -> bool:
  if not inst.args:
    return False
  dst = inst.args[0]
  return hasattr(dst, "reg_type") and dst.reg_type == "s"


def get_dst(inst: Any) -> Any:
  """The destination register of an instruction (arg slot 0 by MP-SPDZ convention)."""
  return inst.args[0]


def set_dst(inst: Any, reg: Any) -> None:
  """Redirect an instruction's destination register in place."""
  inst.args[0] = reg


def insert_after(tape: Any, anchor: Any, new_inst: Any) -> None:
  """Splice `new_inst` immediately after `anchor` in `tape`'s instruction list."""
  for block in tape.basicblocks:
    if anchor in block.instructions:
      idx = block.instructions.index(anchor)
      block.instructions.insert(idx + 1, new_inst)
      return
  raise RuntimeError(f"anchor not found on tape: {anchor}")


def new_reg_like(tape: Any, reg: Any) -> Any:
  """Allocate a fresh register of the same type as `reg` on `tape`."""
  return tape.new_reg(reg.reg_type)


def sync_signature(tape: Any) -> tuple[str, ...]:
  """Ordered list of network-touching opcodes on `tape`.

  An instruction is sync-relevant iff it transmits or consumes
  preprocessed correlation between parties — MP-SPDZ's `DataInstruction`
  base class covers exactly that set: `asm_open`, `triple`, `square`,
  `bit`, `dabit`, `inputmask*`. Equal signatures across two compiled
  programs (honest vs mutated) → identical message-exchange shape, so
  honest parties see the same protocol they would have anyway.

  Jumps deliberately not in the signature: all MP-SPDZ jumps are over
  public values (`int` or `ci` register), so every party traverses the
  same path. The dynamic sync sequence equals the static one on every
  party, regardless of jump structure.
  """
  from Compiler.instructions_base import DataInstruction  # type: ignore[import-not-found]
  return tuple(
    type(inst).__name__
    for block in tape.basicblocks
    for inst in block.instructions
    if isinstance(inst, DataInstruction)
  )


def make_addsi(dst: Any, src: Any, imm: int) -> Any:
  """Build an `addsi dst, src, imm` instruction not attached to any tape.

  MP-SPDZ's `Instruction.__init__` normally appends itself to the active
  program's current basic block. `add_to_prog=False` keeps it free so the
  caller can splice it where they want.
  """
  from Compiler.instructions import addsi  # type: ignore[import-not-found]
  return addsi(dst, src, imm, add_to_prog=False)


def make_mulsi(dst: Any, src: Any, imm: int) -> Any:
  """Build a `mulsi dst, src, imm` instruction (computes `dst = src * imm`)."""
  from Compiler.instructions import mulsi
  return mulsi(dst, src, imm, add_to_prog=False)


def share_offline_cache(source: Path, target: Path) -> None:
  """Copy MASCOT's cached offline key material from one run dir to another.

  The honest twin runs first and leaves an OT secrets cache behind. Without
  this the mutated twin has one party reading that cache and skipping base-OT
  setup while its peer regenerates it interactively, so the two are in
  different phases and the honest side reports `Timed out waiting for peer`.
  The cache is per-party material, not shared state; copying it only removes
  the timing asymmetry.
  """
  origin = source / "Player-Data"
  destination = target / "Player-Data"
  if not origin.is_dir():
    return
  destination.mkdir(parents=True, exist_ok=True)
  for cached in origin.glob("*-Secrets-*"):
    shutil.copy(cached, destination / cached.name)
