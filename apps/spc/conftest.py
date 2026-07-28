"""Pytest path setup for the SPC app.

Since #204 ``spc_app`` is an installed (editable) package, but ``app`` — the top-level
Streamlit module — is not part of the wheel, and the insert keeps coverage attributed
to ``apps/spc/spc_app/...`` rather than to the editable install. Adding it here lets
the SPC suite run both standalone
(``pytest`` from ``apps/spc``) and under the unified root run (``pytest`` from the
repo root with ``--import-mode=importlib``).
"""

from __future__ import annotations

import sys
from pathlib import Path

_APP_DIR = str(Path(__file__).parent)
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)
