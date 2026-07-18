"""MSA page bodies as mountable render callables.

Each ``render_*()`` draws one page into the *current* Streamlit container and owns
no page-level chrome (``set_page_config`` / theming) — the host shell sets those once.
The unified shell imports these and calls them.
"""

from __future__ import annotations

from msa_app.pages.gage_study import render_gage_study

__all__ = ["render_gage_study"]
