"""Pytest path setup for the FMEA app.

The apps are runnable Streamlit folders, not installed wheels (``package = false``),
so their top-level modules (``fmea_app`` / ``ui`` / ``app``) are not importable
unless this directory is on ``sys.path``. Adding it here lets the FMEA suite run
both standalone (``pytest`` from ``apps/fmea``) and under the unified root run
(``pytest`` from the repo root with ``--import-mode=importlib``).

Both apps ship a top-level ``app.py``, so a bare ``import app`` is ambiguous once
both app dirs are on ``sys.path`` in a unified run. A few FMEA tests do exactly
that (``from app import ...`` / ``inspect.getsource(app)``), so bind ``app`` to
*this* app's module by explicit path — deterministic regardless of collection
order. Importing it is side-effect-free: ``app.py`` only defines functions and
path constants at module scope (``set_page_config`` lives inside ``main()``).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_APP_DIR = Path(__file__).parent

if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

if "app" not in sys.modules:
    _spec = importlib.util.spec_from_file_location("app", _APP_DIR / "app.py")
    if _spec is not None and _spec.loader is not None:
        _app = importlib.util.module_from_spec(_spec)
        sys.modules["app"] = _app
        _spec.loader.exec_module(_app)
