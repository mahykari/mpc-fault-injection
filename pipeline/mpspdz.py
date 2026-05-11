"""Adapters around MP-SPDZ's CLI tools (compiler module + party binary).

MP-SPDZ was built as a CLI, not a library. These two adapters wrap
its quirks — CWD-bound output paths, fake-argv option parsing,
party-binary launch shape — so pipeline components above never see them.
"""
from __future__ import annotations

import os
import random
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from pipeline.config import NeedsCompilerToolkit, NeedsPartyBinary
from pipeline.types import PartyOutput


@dataclass(frozen=True)
class TwinRunPlan:
  """One twin to launch: the program, one cwd per party, and a timeout."""
  program_id: str
  party_cwds: tuple[Path, ...]
  timeout_s: float

  @property
  def n_parties(self) -> int:
    return len(self.party_cwds)


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

  Encapsulates: sys.path injection so the package is importable;
  synthetic argv so MP-SPDZ's OptionParser populates its defaults;
  chdir to the destination because `Program` resolves output paths
  relative to CWD.
  """

  def __init__(self, config: NeedsCompilerToolkit) -> None:
    self._config = config
    if str(config.mpspdz_root) not in sys.path:
      sys.path.insert(0, str(config.mpspdz_root))

  def compile_dsl_into(
    self, program_id: str, source: str, output_dir: Path,
  ) -> None:
    compiler_cls = self._load_compiler_class()
    with _working_directory(output_dir):
      compiler = compiler_cls(custom_args=[program_id])
      compiler.prep_compile(name=program_id)
      exec(source, compiler.VARS)
      compiler.finalize_compile()

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

  def run_parties(self, plan: TwinRunPlan) -> tuple[PartyOutput, ...]:
    """Spawn one party per cwd in `plan`, then collect each output.

    The parties have to run concurrently: each one connects to its
    peers over sockets at startup and won't make progress until every
    peer has connected. Sequential starts would deadlock party 0
    waiting for party 1.

    So we spawn all N first (Popen returns immediately), then walk
    the list collecting each output. By the time we call communicate
    on party 0, every party is already up and talking to its peers.
    """
    port = self._pick_port()
    processes = [
      self._spawn(plan.program_id,
                  party_id=i, n_parties=plan.n_parties,
                  port=port, cwd=plan.party_cwds[i])
      for i in range(plan.n_parties)
    ]
    return tuple(
      self._collect(proc, party_id=i, timeout_s=plan.timeout_s)
      for i, proc in enumerate(processes)
    )

  def _spawn(
    self,
    program_id: str,
    *,
    party_id: int,
    n_parties: int,
    port: int,
    cwd: Path,
  ) -> "subprocess.Popen[str]":
    cmd = [
      str(self._config.party_binary_path),
      "-p", str(party_id),
      "-N", str(n_parties),
      "-h", "localhost",
      "-pn", str(port),
      program_id,
    ]
    return subprocess.Popen(
      cmd, cwd=cwd,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True,
    )

  def _collect(
    self,
    proc: "subprocess.Popen[str]",
    *,
    party_id: int,
    timeout_s: float,
  ) -> PartyOutput:
    try:
      stdout, stderr = proc.communicate(timeout=timeout_s)
      return PartyOutput(
        party_id=party_id,
        stdout=stdout, stderr=stderr,
        exit_code=proc.returncode,
      )
    except subprocess.TimeoutExpired:
      proc.kill()
      stdout, stderr = proc.communicate()
      return PartyOutput(
        party_id=party_id,
        stdout=stdout,
        stderr=stderr + f"\n[party {party_id}] timed out after {timeout_s}s",
        exit_code=-1,
      )

  @staticmethod
  def _pick_port() -> int:
    return random.randint(20000, 60000)
