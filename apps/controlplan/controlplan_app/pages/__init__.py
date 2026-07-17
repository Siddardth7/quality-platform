"""Control Plan page bodies as mountable render callables.

Each ``render_*()`` draws one page into the *current* Streamlit container and owns
no page-level chrome (``set_page_config`` / theming) — the host shell sets those once.
The unified shell imports these and calls them.
"""

from __future__ import annotations

from controlplan_app.pages.control_plan import render_control_plan

__all__ = ["render_control_plan"]
