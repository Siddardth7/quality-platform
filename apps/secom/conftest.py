"""Pytest path setup for the SECOM app.

secom-app and spc-app are both installed (editable) workspace packages (#204), so
``secom_app`` and the ``spc_app.spc_engine`` reuse in ``secom_app.charts`` /
``.capability`` (W09-2, #66) resolve without any ``sys.path`` help — confirmed by
running the suite (130 passed) with the old ``apps/secom``-onto-``sys.path`` entry
removed.

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
