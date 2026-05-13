"""sys.path setup for the python-circil sibling clone.

python-circil is a gitignored clone at `<repo>/python-circil/`, not a
pip-installable dependency. Importing this module inserts that path
into sys.path so subsequent `from circil.* import ...` calls in the
Generator and Translator resolve. Mirrors how `pipeline.mpspdz`
inserts `MP-SPDZ/` into sys.path inside `MpSpdzCompilerToolkit.__init__`.
"""
from __future__ import annotations

import sys
from pathlib import Path

_CIRCIL_ROOT = Path(__file__).resolve().parent.parent / "python-circil"
if str(_CIRCIL_ROOT) not in sys.path:
  sys.path.insert(0, str(_CIRCIL_ROOT))
