"""Pytest path setup for the SECOM app.

The apps are runnable Streamlit folders, not installed wheels (``package = false``),
so their top-level modules (``secom_app`` / ``app``) are not importable unless this
directory is on ``sys.path``. Adding it here lets the SECOM suite run both standalone
(``pytest`` from ``apps/secom``) and under the unified root run (``pytest`` from the
repo root with ``--import-mode=importlib``).

W09-2 (#66): ``secom_app.charts`` reuses the SPC app's engine
(``spc_app.spc_engine``) read-only rather than reimplementing I-MR math, so
the SPC app dir also goes onto ``sys.path`` here — mirroring the precedent in
``apps/spc/tests/test_loop_integration.py`` (``from fmea_app import
rpn_engine``). The secom dir is inserted first so ``import app`` still
resolves to secom's own ``app.py``; only the unambiguous ``spc_app`` package
needs resolving from the second entry.

W09-4 (#68): a reuse-proof test in ``tests/test_msa.py`` needs
``from msa_app.gage_rr_engine import compute_gage_rr`` to show the *real*
AIAG engine also rejects SECOM-shaped frames, so the MSA app dir goes onto
``sys.path`` too, mirroring the ``spc_app`` block above.
"""

from __future__ import annotations

import sys
from pathlib import Path

_APP_DIR = str(Path(__file__).parent)
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

_SPC_APP_DIR = str(Path(__file__).parent.parent / "spc")
if _SPC_APP_DIR not in sys.path:
    sys.path.insert(1, _SPC_APP_DIR)

_MSA_APP_DIR = str(Path(__file__).parent.parent / "msa")
if _MSA_APP_DIR not in sys.path:
    sys.path.insert(2, _MSA_APP_DIR)
