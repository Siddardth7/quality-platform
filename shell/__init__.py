"""Unified platform shell — landing page and shared chrome.

The host shell (``app.py`` at the repo root) sets ``st.set_page_config`` and
``apply_theme`` exactly once, then mounts the FMEA and SPC sections plus the
landing page in ``shell.home`` under a single ``st.navigation`` sidebar.
"""
