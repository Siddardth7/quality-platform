"""SECOM page bodies as mountable render callables.

Each ``render_*()`` draws one page into the *current* Streamlit container and
owns no page-level chrome (``set_page_config`` / theming) — a host entry
script sets those once. Mirrors ``msa_app/pages/__init__.py``.
"""

from __future__ import annotations

from secom_app.pages.yield_dppm import render_yield_dppm

__all__ = ["render_yield_dppm"]
