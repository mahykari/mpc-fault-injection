"""Per-protocol facts the pipeline varies on.

One `ProtocolSpec` per protocol literal, keyed in `PROTOCOL_SPECS`. A spec
carries the domain (field prime vs ring width), the threshold model
(dishonest- vs honest-majority), the stderr strings that mean the
protocol's malicious-security check caught a deviation, and whether the
protocol runs over encrypted channels (`needs_ssl`, so the executor seeds
each party cwd with a shared cert set before launch).

The domain feeds both the compiler (ring bytecode differs from field) and
the party-binary argv; the threshold model feeds the corrupt-set guard
(`Config.__post_init__`) and Shamir's runtime `-T`.
"""
from __future__ import annotations

from dataclasses import dataclass

from pipeline.types import Protocol

PRIME_MERSENNE_M127 = 2**127 - 1


@dataclass(frozen=True)
class Prime:
  prime: int

  @property
  def compile_args(self) -> list[str]:
    return []

  @property
  def runtime_args(self) -> list[str]:
    return ["-P", str(self.prime)]


@dataclass(frozen=True)
class Ring:
  k: int

  @property
  def compile_args(self) -> list[str]:
    return ["-R", str(self.k)]

  @property
  def runtime_args(self) -> list[str]:
    return ["-R", str(self.k)]


Domain = Prime | Ring


@dataclass(frozen=True)
class ProtocolSpec:
  domain: Domain
  honest_majority: bool
  catch_signatures: tuple[str, ...]
  needs_ssl: bool = False

  def max_corrupt(self, n_parties: int) -> int:
    return (n_parties - 1) // 2 if self.honest_majority else n_parties - 1

  def threshold_args(self, n_parties: int) -> list[str]:
    if not self.honest_majority:
      return []
    return ["-T", str(self.max_corrupt(n_parties))]


PROTOCOL_SPECS: dict[Protocol, ProtocolSpec] = {
  "mascot": ProtocolSpec(
    domain=Prime(PRIME_MERSENNE_M127),
    honest_majority=False,
    catch_signatures=("MacCheck Failure",),
  ),
  "spdz2k": ProtocolSpec(
    domain=Ring(64),
    honest_majority=False,
    catch_signatures=("MacCheck Failure",),
  ),
  "malicious-shamir": ProtocolSpec(
    domain=Prime(PRIME_MERSENNE_M127),
    honest_majority=True,
    catch_signatures=("inconsistent Shamir secret sharing",),
    needs_ssl=True,
  ),
}
