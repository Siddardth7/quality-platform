import streamlit as st
from msa_app import __version__
from msa_app.pages import render_gage_study
from quality_core.theme import apply_theme

st.set_page_config(
    page_title="MSA — Measurement System Analysis",
    layout="wide",
)
apply_theme()

st.caption(f"v{__version__} · Gage R&R (Average-and-Range) per AIAG MSA, 4th Edition.")

render_gage_study()
