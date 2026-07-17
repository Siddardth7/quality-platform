"""Pytest path setup for the MSA app.

The apps are runnable Streamlit folders, not installed wheels (``package = false``),
so their top-level modules (``msa_app`` / ``app``) are not importable unless this
directory is on ``sys.path``. Adding it here lets the MSA suite run both standalone
(``pytest`` from ``apps/msa``) and under the unified root run (``pytest`` from the
repo root with ``--import-mode=importlib``).
"""

from __future__ import annotations

import sys
from pathlib import Path

_APP_DIR = str(Path(__file__).parent)
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)
