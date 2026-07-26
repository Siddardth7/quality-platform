"""Path shim so the throwaway spike can import the real SPC engine + palette
*unchanged*, without installing the uv workspace (which would touch the lockfile
and the gate — issue #108 forbids both).

Adds the two source roots to sys.path:
  - apps/spc                     -> `spc_app`      (engine, visualizer, exporter)
  - packages/quality-core/src    -> `quality_core` (pure palette tokens)

Nothing here is imported into `main`; this file exists only inside spikes/.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

for _rel in ("apps/spc", "packages/quality-core/src"):
    _p = str(_REPO_ROOT / _rel)
    if _p not in sys.path:
        sys.path.insert(0, _p)
