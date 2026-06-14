"""
ui/styles.py
FMEA Risk Prioritization Tool — CSS design system for the Streamlit app.

Exports:
    apply_css(dark: bool) -> None   — inject base CSS + optional dark-mode overrides
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# CSS constants
# ---------------------------------------------------------------------------

_BASE_CSS = """
<style>
/* ── Global resets ───────────────────────────────────────────────── */
.block-container { padding-top: 1.5rem !important; }

/* ── Metric cards ────────────────────────────────────────────────── */
div[data-testid="metric-container"] {
    border-radius: 10px;
    padding: 14px 18px;
    border: 1px solid rgba(128,128,128,0.15);
    background: #ffffff;
    transition: box-shadow 0.2s, transform 0.15s;
}
div[data-testid="metric-container"]:hover {
    box-shadow: 0 4px 14px rgba(0,0,0,0.10);
    transform: translateY(-1px);
}

/* ── Tabs ────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab"] {
    font-size: 14px;
    font-weight: 500;
    padding: 10px 22px;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: transparent;
}

/* ── Download buttons ────────────────────────────────────────────── */
.stDownloadButton > button {
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: box-shadow 0.2s !important;
}
.stDownloadButton > button:hover {
    box-shadow: 0 3px 10px rgba(0,0,0,0.15) !important;
}

/* ── Expanders ───────────────────────────────────────────────────── */
.streamlit-expanderHeader {
    border-radius: 8px;
    font-weight: 500;
}

/* ── Sidebar refinements ─────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    border-right: 1px solid rgba(128,128,128,0.12);
}
section[data-testid="stSidebar"] .stButton > button {
    border-radius: 8px !important;
    font-weight: 500 !important;
}
</style>
"""

_DARK_CSS = """
<style>
.stApp { background-color: #0e1117 !important; }
section[data-testid="stSidebar"] { background-color: #161b27 !important; }
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] small { color: #c9d1d9 !important; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: #e6edf3 !important; }
.stApp p, .stApp li, .stApp span { color: #c9d1d9 !important; }
div[data-testid="metric-container"] {
    background-color: #161b27 !important;
    border-color: #30363d !important;
}
div[data-testid="stMetricLabel"] p { color: #8b949e !important; }
div[data-testid="stMetricValue"] { color: #58a6ff !important; }
.stTabs [data-baseweb="tab-list"] {
    background-color: #0e1117 !important;
    border-bottom: 1px solid #30363d !important;
}
.stTabs [data-baseweb="tab"] { color: #8b949e !important; }
.stTabs [aria-selected="true"] { color: #58a6ff !important; border-bottom: 2px solid #58a6ff !important; }
.streamlit-expanderHeader { background-color: #161b27 !important; color: #e6edf3 !important; }
.stCaption p { color: #8b949e !important; }
hr { border-color: #30363d !important; }
div[data-testid="stInfo"] { background-color: #1c2433 !important; border-color: #30363d !important; }
div[data-testid="stInfo"] p { color: #c9d1d9 !important; }
div[data-testid="stAlert"] p { color: #c9d1d9 !important; }
.stDownloadButton > button {
    background-color: #21262d !important;
    border-color: #30363d !important;
    color: #c9d1d9 !important;
}
.stDownloadButton > button:hover {
    background-color: #30363d !important;
    border-color: #58a6ff !important;
}
</style>
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def apply_css(dark: bool) -> None:
    """Inject base CSS and, if dark=True, dark-mode overrides via st.markdown."""
    st.markdown(_BASE_CSS, unsafe_allow_html=True)
    if dark:
        st.markdown(_DARK_CSS, unsafe_allow_html=True)
