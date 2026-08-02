"""Pytest path setup for the SECOM app.

secom-app and spc-app are both installed (editable) workspace packages (#204), so
``secom_app`` and the remaining ``spc_app.spc_engine.capability`` reuse in
``secom_app.capability`` resolve without any ``sys.path`` help. (``charts.py`` took
its SPC math from ``spc_app`` until #205 PR 2 moved it to ``quality_core.spc``.)
Confirmed at the time of #204 by running the suite with the old
``apps/secom``-onto-``sys.path`` entry removed (130 passed then; the count has grown
since — do not read it as current).

# ponytail: apps/msa is not an installable package (still `package = false`), so
# tests/test_msa.py's `from msa_app.gage_rr_engine import compute_gage_rr` (W09-4,
# #68) still needs the sys.path entry below. Ceiling: every app stays path-hacked
# until made installable like spc-app/secom-app; upgrade path is #205 / a follow-up
# to this issue that flips apps/msa the same way.
"""

from __future__ import annotations

import sys
from pathlib import Path

_MSA_APP_DIR = str(Path(__file__).parent.parent / "msa")
if _MSA_APP_DIR not in sys.path:
    sys.path.insert(0, _MSA_APP_DIR)
