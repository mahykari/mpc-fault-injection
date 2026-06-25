#!/usr/bin/env python3
"""Generate a patch to wrap Check() calls with runtime-disableable guards."""

import difflib
import json
from pathlib import Path

import tree_sitter_cpp as ts_cpp
from tree_sitter import Language, Parser

MPSPDZ = Path("MP-SPDZ")
PATCH_DIR = Path("patches/mpspdz-seeded-bug")

# Check() call sites to instrument
TARGETS = [
  ("Processor/Processor.hpp", "subprocessor_check"),
  ("Protocols/Beaver.hpp", "beaver_check"),
  ("Processor/PrivateOutput.hpp", "private_output_check"),
]

LANG = Language(ts_cpp.language())
PARSER = Parser(LANG)


def find_check_calls(source: bytes):
  """Yield (line_0indexed, caller) for each MC.Check() or MC->Check() call."""
  tree = PARSER.parse(source)

  def walk(node):
    if node.type == "call_expression":
      text = source[node.start_byte:node.end_byte].decode()
      # Match MC.Check( or MC->Check( but not other Check calls
      if (".Check(" in text or "->Check(") and "MC" in text:
        func = node.child_by_field_name("function")
        if func:
          func_text = source[func.start_byte:func.end_byte].decode()
          for sep in ["->", "."]:
            if sep + "Check" in func_text:
              caller = func_text.split(sep + "Check")[0] + sep
              yield (node.start_point[0], caller)
              break
    for child in node.children:
      yield from walk(child)

  yield from walk(tree.root_node)


def make_patch(original: str, modified: str, path: str) -> str:
  """Generate unified diff."""
  orig_lines = original.splitlines(keepends=True)
  mod_lines = modified.splitlines(keepends=True)
  diff = difflib.unified_diff(orig_lines, mod_lines, f"a/{path}", f"b/{path}")
  return "".join(diff)


def instrument_file(rel_path: str, site_id: str) -> tuple[str, dict]:
  """Instrument a file and return (patch, registry_entry)."""
  path = MPSPDZ / rel_path
  original = path.read_text()
  lines = original.splitlines(keepends=True)

  calls = list(find_check_calls(path.read_bytes()))
  if not calls:
    return "", {}

  call = calls[0]
  registry_entry = {"file": rel_path, "line": call[0] + 1}

  # Add include after last #include
  include_line = 0
  for i, line in enumerate(lines[:50]):
    if line.strip().startswith("#include"):
      include_line = i + 1

  modified_lines = lines[:include_line]
  modified_lines.append('#include "disabled_sites_iface.h"\n')
  modified_lines.extend(lines[include_line:])

  # Wrap the Check() call (adjust for inserted include)
  for line_idx, caller in calls:
    adj_idx = line_idx + 1
    orig_line = modified_lines[adj_idx]
    indent = len(orig_line) - len(orig_line.lstrip())
    ind = " " * indent

    # Extract the argument (usually just P)
    # The line looks like: MC.Check(P);
    replacement = (
      f'{ind}if (!MPSPDZ_SITE_DISABLED("{site_id}"))\n'
      f'{ind}  {orig_line.strip()}\n'
    )
    modified_lines[adj_idx] = replacement

  modified = "".join(modified_lines)
  return make_patch(original, modified, rel_path), {site_id: registry_entry}


def main():
  registry = {}
  patches = []

  for rel_path, site_id in TARGETS:
    patch, reg = instrument_file(rel_path, site_id)
    if patch:
      print(f"Instrumented {rel_path} ({site_id})")
      patches.append(patch)
      registry.update(reg)

  header = """Skip Check() calls for seeded-bug testing.

Sites: subprocessor_check, beaver_check, private_output_check
Usage: MPSPDZ_DISABLED_SITES=subprocessor_check ./mascot-party.x ...

"""
  patch_path = PATCH_DIR / "0003-skip-mac-staging.patch"
  patch_path.write_text(header + "\n".join(patches))
  print(f"Wrote {patch_path}")

  reg_path = PATCH_DIR / "site_registry.json"
  reg_path.write_text(json.dumps(registry, indent=2) + "\n")
  print(f"Wrote {reg_path}")


if __name__ == "__main__":
  main()
