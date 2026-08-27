"""Compile both twins for one seed and diff what preprocessing they need.

The first check to reach for when a mutated run desynchronises: if the two
sync signatures differ, the twins disagree about how much offline material
the program wants and the parties fall out of step before any real work.

Run from the repo root:  PYTHONPATH=. uv run python exploration/compare_twin_preprocessing.py
"""
from tests.support import generated
import contextlib, io
from collections import Counter
from pathlib import Path

from pipeline.config import Config
from pipeline.mpspdz import MpSpdzCompilerToolkit, sync_signature
from pipeline.rewrite.inject import inject_circuit
from pipeline.translator import translate_to_mpspdz
from pipeline.types import CircilProgram, Seed

ROOT = Path("/home/mkarimi/matrix-rewrites")
config = Config(
  mpspdz_root=ROOT / "MP-SPDZ", runs_root=Path("/tmp/tdiff"), seed=Seed(3),
  protocol="mascot", n_parties=2, malicious_parties=[1], timeout_s=60.0,
  program_family="matrix", injection_layer="source",
)
toolkit = MpSpdzCompilerToolkit(config)

with contextlib.redirect_stdout(io.StringIO()):
  circuit = generated(3)
  honest_src = translate_to_mpspdz(CircilProgram(circuit=circuit))
  result = inject_circuit(circuit, seed=3, amount=3)
  mutated_src = translate_to_mpspdz(CircilProgram(circuit=result.circuit))

print("rules fired:", result.rule_names)
print()

def compiled(tag, src):
  with contextlib.redirect_stdout(io.StringIO()):
    return toolkit.compile(tag, src.source)

h = compiled("tdiff-h", honest_src)
m = compiled("tdiff-m", mutated_src)

for tag, prog in (("honest", h), ("mutated", m)):
  sig = sync_signature(prog.tapes[0])
  print("%-8s sync ops: %d  %s" % (tag, len(sig), Counter(sig)))

print()
hs, ms = sync_signature(h.tapes[0]), sync_signature(m.tapes[0])
print("signature equal:", hs == ms)
dh, dm = Counter(hs), Counter(ms)
for key in sorted(set(dh) | set(dm)):
  if dh[key] != dm[key]:
    print("  %-16s honest=%d mutated=%d  (%+d)" % (key, dh[key], dm[key], dm[key] - dh[key]))
