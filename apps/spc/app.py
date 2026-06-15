import streamlit as st

from quality_core.theme import apply_theme, AMBER, BG_CARD, TEXT_PRIMARY

st.set_page_config(
    page_title="SPC Manufacturing Quality Dashboard",
    layout="wide",
)
apply_theme()

st.title("SPC Manufacturing Quality Dashboard")
st.caption("A manufacturing-focused SPC portfolio app for composites, curing, and aerospace machining workflows.")

intro_left, intro_right = st.columns([2, 1])

with intro_left:
    st.markdown(
        """
        This dashboard combines control charts, capability analysis, and a live disturbance simulator
        into one Streamlit app. The goal is to make SPC behavior visible, not just numerically correct:
        you can inspect real process streams, compare rule sets, and watch special-cause patterns emerge.
        """
    )

with intro_right:
    st.markdown(
        f"""<div style="background:{BG_CARD};border:1px solid {AMBER};border-radius:10px;
        padding:18px 20px;color:{TEXT_PRIMARY};font-size:0.9rem;line-height:1.6;">
        📐 Use the <strong style="color:{AMBER};">sidebar</strong> to navigate
        between <strong>Control Charts</strong>, <strong>Process Capability</strong>,
        and <strong>Live Simulation</strong>.
        </div>""",
        unsafe_allow_html=True,
    )

feature_cols = st.columns(3)
feature_cols[0].subheader("Control Charts")
feature_cols[0].write(
    "Variables and attributes charts using Xbar-R, Xbar-S, I-MR, p, and u workflows with rule overlays."
)
feature_cols[1].subheader("Process Capability")
feature_cols[1].write(
    "Cp, Cpk, Pp, and Ppk metrics with histogram fit, gauge feedback, and Shapiro-Wilk normality checks."
)
feature_cols[2].subheader("Live Simulation")
feature_cols[2].write(
    "Real-time subgroup generation with mean shift, spike, and drift disturbances for SPC storytelling."
)

st.markdown("---")
st.subheader("Standards Context")
standards_cols = st.columns(3)
standards_cols[0].metric("AIAG SPC", "4th Edition")
standards_cols[1].metric("Nelson Rules", "Rules 1–8")
standards_cols[2].metric("Capability Target", "Cpk ≥ 1.33")

st.markdown(
    """
    **Reference areas**

    - AIAG SPC constants and capability indices
    - Western Electric and Nelson run rules
    - Aerospace-oriented demo processes for layup, curing, and machining
    """
)
