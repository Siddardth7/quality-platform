"""Streamlit theming — the CSS injector. Imports streamlit, so it is kept
separate from ``palette`` and loaded lazily from the package root."""

from __future__ import annotations

import streamlit as st

from quality_core.theme.palette import (
    AMBER,
    BG_CARD,
    BG_PRIMARY,
    BG_SECONDARY,
    BORDER,
    DANGER,
    SUCCESS,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    VIOLET,
)

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* {{ font-family: 'Inter', sans-serif !important; }}

[data-testid="stSidebar"] {{
    background-color: {BG_SECONDARY} !important;
    border-right: 1px solid {BORDER};
}}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{
    color: {AMBER} !important;
    font-weight: 600;
}}

h1 {{
    color: {TEXT_PRIMARY} !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
    border-bottom: 2px solid {AMBER};
    padding-bottom: 8px;
    margin-bottom: 4px;
}}
h2 {{ color: {AMBER} !important; font-weight: 600 !important; }}
h3 {{ color: {TEXT_SECONDARY} !important; font-weight: 500 !important; }}

[data-testid="stMetric"] {{
    background-color: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    padding: 14px 18px !important;
}}
[data-testid="stMetricValue"] {{
    color: {AMBER} !important;
    font-weight: 600 !important;
    font-size: 1.35rem !important;
}}
[data-testid="stMetricLabel"] {{
    color: {TEXT_SECONDARY} !important;
    font-size: 0.76rem !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}}

.stButton > button {{
    background-color: transparent !important;
    border: 1px solid {AMBER} !important;
    color: {AMBER} !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    transition: all 0.15s ease !important;
}}
.stButton > button:hover {{
    background-color: {AMBER} !important;
    color: {BG_PRIMARY} !important;
}}

[data-testid="stInfo"] {{
    background-color: {BG_CARD} !important;
    border-left: 3px solid {VIOLET} !important;
}}
[data-testid="stSuccess"] {{
    background-color: {BG_CARD} !important;
    border-left: 3px solid {SUCCESS} !important;
}}
[data-testid="stWarning"] {{
    background-color: {BG_CARD} !important;
    border-left: 3px solid {AMBER} !important;
}}
[data-testid="stError"] {{
    background-color: {BG_CARD} !important;
    border-left: 3px solid {DANGER} !important;
}}

[data-testid="stPlotlyChart"] {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    overflow: hidden;
    background-color: {BG_SECONDARY};
}}

[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
}}

[data-testid="stCaptionContainer"] {{ color: {TEXT_SECONDARY} !important; }}
</style>
"""


def apply_theme() -> None:
    """Inject the shared dark theme CSS into the current Streamlit page."""
    st.markdown(_CSS, unsafe_allow_html=True)
