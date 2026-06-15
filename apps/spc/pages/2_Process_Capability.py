"""Standalone multipage wrapper — delegates to the mountable render callable.

The page body lives in ``spc_app.pages.process_capability`` so the unified shell
can mount it. This wrapper supplies the standalone-only chrome (page config + theme).
"""

from __future__ import annotations

import streamlit as st
from quality_core.theme import apply_theme

from spc_app.pages import render_capability

st.set_page_config(page_title="Process Capability", layout="wide")
apply_theme()

render_capability()
