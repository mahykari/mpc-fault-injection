"""Per rewrite rule: how often it changes the preprocessing a program needs.

Applies one rule at a time across a range of seeds and reports, for each,
how many applications shifted the sync signature and in which opcode. A
rule that shows any drift here will desynchronise a twin run.

Run from the repo root:  PYTHONPATH=. uv run python exploration/rule_sync_deltas.py
"""
from tests.support import generated
import contextlib, io
from collections import Counter
from pathlib import Path
from random import Random

from pipeline.config import Config
from pipeline.mpspdz import MpSpdzCompilerToolkit, sync_signature
from pipeline.rewrite.inject import INJECTIONS, Site, _sites
from pipeline.rewrite import REARRANGEMENTS, rewrite_circuit
from pipeline.translator import translate_to_mpspdz
from pipeline.types import CircilProgram, Seed
from circil.ir.visitor import NodeReplacer

ROOT = Path("/home/mkarimi/matrix-rewrites")
toolkit = MpSpdzCompilerToolkit(Config(
  mpspdz_root=ROOT / "MP-SPDZ", runs_root=Path("/tmp/tdiff"), seed=Seed(0),
  protocol="mascot", n_parties=2, malicious_parties=[1], timeout_s=60.0,
  program_family="matrix", injection_layer="source"))

def sig(circuit, tag):
  with contextlib.redirect_stdout(io.StringIO()):
    src = translate_to_mpspdz(CircilProgram(circuit=circuit))
    prog = toolkit.compile(tag, src.source)
  return Counter(sync_signature(prog.tapes[0]))

def apply_one(circuit, rule, seed):
  root = circuit.copy()
  sites = _sites(root, rule)
  if not sites:
    return None
  rng = Random(seed)
  site = sites[rng.randrange(len(sites))]
  built = rule.build(site, root, rng)
  if built is None or not NodeReplacer().replace(root, site.node, built):
    return None
  return root

stats = {}
for seed in range(12):
  with contextlib.redirect_stdout(io.StringIO()):
    circuit = generated(seed)
  base = sig(circuit, "pr-base-%d" % seed)
  for rule in INJECTIONS:
    out = apply_one(circuit, rule, seed)
    if out is None:
      continue
    after = sig(out, "pr-%s-%d" % (rule.name, seed))
    tally = stats.setdefault(rule.name, Counter())
    tally["applied"] += 1
    if after != base:
      tally["changed"] += 1
      for k in set(base) | set(after):
        if base[k] != after[k]:
          tally["%s %+d" % (k, after[k] - base[k])] += 1
  for kind in ("rearrange",):
    res = rewrite_circuit(circuit, seed=seed, amount=1)
    if not res.rule_names:
      continue
    after = sig(res.circuit, "pr-re-%d" % seed)
    tally = stats.setdefault("rearrange:" + res.rule_names[0], Counter())
    tally["applied"] += 1
    if after != base:
      tally["changed"] += 1
      for k in set(base) | set(after):
        if base[k] != after[k]:
          tally["%s %+d" % (k, after[k] - base[k])] += 1

for name in sorted(stats):
  t = stats[name]
  print("%-34s applied=%-3d changed=%-3d %s" % (
    name, t["applied"], t["changed"],
    {k: v for k, v in t.items() if k not in ("applied", "changed")}))
