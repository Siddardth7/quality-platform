"""Quality Platform — unified Streamlit shell.

One app, one URL: a single ``st.navigation`` sidebar mounts the landing page,
the FMEA Risk Analyzer, and the three SPC workflows (Control Charts, Process
Capability, Live Simulation). This module owns the platform chrome —
``st.set_page_config`` and ``apply_theme`` are called here exactly once; every
mounted page is a render callable that draws into the current container and
sets no page config of its own.

Run with::

    uv run streamlit run app.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Callable

import streamlit as st

# ---------------------------------------------------------------------------
# Make all first-party code importable from the checked-out repo
# ---------------------------------------------------------------------------
# The apps are workspace members built as runnable Streamlit folders, not wheels
# (``package = false``), so ``fmea_app`` / ``ui`` / ``spc_app`` are not on
# ``sys.path`` by default. quality-core IS an installed (editable) package locally,
# but on a plain ``pip install -r requirements.txt`` host (Streamlit Cloud) it is
# not installed — requirements.txt carries only third-party deps. Putting its
# source root on the path too lets the shell run from the repo with no editable
# install, the same way the apps are resolved.

_ROOT = Path(__file__).resolve().parent
_FMEA_DIR = _ROOT / "apps" / "fmea"
_SPC_DIR = _ROOT / "apps" / "spc"
_CORE_SRC = _ROOT / "packages" / "quality-core" / "src"

for _src_dir in (_CORE_SRC, _SPC_DIR, _FMEA_DIR):
    _path = str(_src_dir)
    if _path not in sys.path:
        sys.path.insert(0, _path)


def _load_module_from_path(name: str, path: Path) -> ModuleType:
    """Import a module from an explicit file path under a unique name.

    FMEA's render body lives in ``apps/fmea/app.py`` alongside source-pinned
    test fixtures, so it cannot move into a package. Loading it by path under a
    unique name avoids colliding with this shell's own ``app`` module and with
    SPC's standalone ``app.py``. The module sets no page config at import time.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"Cannot load module {name!r} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Mounted render callables
# ---------------------------------------------------------------------------

from quality_core.theme import apply_theme  # noqa: E402  (after sys.path setup)

from shell.home import render_home  # noqa: E402
from spc_app.pages import (  # noqa: E402
    render_capability,
    render_control_charts,
    render_simulation,
)

_fmea_entry = _load_module_from_path("_fmea_entry", _FMEA_DIR / "app.py")
render_fmea: Callable[[], None] = _fmea_entry.render_fmea


# ---------------------------------------------------------------------------
# Shell chrome (set once, here only)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Quality Platform",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

navigation = st.navigation(
    {
        "Platform": [
            st.Page(render_home, title="Home", icon="🏠", default=True),
        ],
        "FMEA": [
            st.Page(render_fmea, title="Risk Analyzer", icon="🛡️", url_path="fmea"),
        ],
        "SPC": [
            st.Page(
                render_control_charts,
                title="Control Charts",
                icon="📈",
                url_path="control-charts",
            ),
            st.Page(
                render_capability,
                title="Process Capability",
                icon="📊",
                url_path="capability",
            ),
            st.Page(
                render_simulation,
                title="Live Simulation",
                icon="🎛️",
                url_path="simulation",
            ),
        ],
    }
)
navigation.run()
