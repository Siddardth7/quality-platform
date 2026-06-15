"""SPC page bodies as mountable render callables.

Each ``render_*()`` draws one page into the *current* Streamlit container and owns
no page-level chrome (``set_page_config`` / theming) — the host shell sets those once.
The unified shell (and the standalone multipage wrappers in ``apps/spc/pages/``)
import these and call them.
"""

from __future__ import annotations

from spc_app.pages.control_charts import render_control_charts
from spc_app.pages.live_simulation import render_simulation
from spc_app.pages.process_capability import render_capability

__all__ = ["render_control_charts", "render_capability", "render_simulation"]
