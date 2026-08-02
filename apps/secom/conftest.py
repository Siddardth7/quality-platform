"""Pytest path setup for the SECOM app.

secom-app is an installed (editable) workspace package (#204), so ``secom_app``
itself needs no ``sys.path`` help, and its engine math resolves downward through
``quality_core.spc`` (#205). Confirmed at the time of #204 by running the suite
with the old ``apps/secom``-onto-``sys.path`` entry removed (130 passed then; the
count has grown since — do not read it as current).

The only remaining reason this file exists is ``apps/msa``:

# ponytail: apps/msa is not an installable package (still `package = false`), so
# tests/test_msa.py's `from msa_app.gage_rr_engine import compute_gage_rr` (W09-4,
# #68) still needs the sys.path entry below. Ceiling: every app stays path-hacked
# until made installable like secom-app; upgrade path is #231, which flips
# apps/msa the same way and lets this file go entirely.
"""

from __future__ import annotations

import sys
from pathlib import Path

_MSA_APP_DIR = str(Path(__file__).parent.parent / "msa")
if _MSA_APP_DIR not in sys.path:
    sys.path.insert(0, _MSA_APP_DIR)
