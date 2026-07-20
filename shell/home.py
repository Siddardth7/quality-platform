"""Landing page for the unified Quality Platform shell.

``render_home()`` is a mountable render callable: it draws into the *current*
Streamlit container and owns no ``set_page_config`` / theming — the host shell
sets those once before mounting it via ``st.navigation``.
"""

from __future__ import annotations

import streamlit as st
from quality_core.theme import AMBER, BG_CARD, BORDER, TEXT_PRIMARY, TEXT_SECONDARY


def _section_card(title: str, body: str) -> str:
    """Return one feature card as themed HTML."""
    return (
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;'
        f"padding:18px 20px;height:100%;color:{TEXT_PRIMARY};font-size:0.9rem;"
        f'line-height:1.6;">'
        f'<div style="color:{AMBER};font-weight:700;font-size:1.02rem;'
        f'margin-bottom:6px;">{title}</div>'
        f'<div style="color:{TEXT_SECONDARY};">{body}</div>'
        f"</div>"
    )


def render_home() -> None:
    """Draw the platform landing page into the current container."""
    st.title("🏭 Quality Platform")
    st.caption(
        "One platform, one URL — FMEA risk prioritization, MSA gage capability, and "
        "SPC process control over a shared manufacturing-quality core."
    )

    st.markdown(
        f"""<div style="background:{BG_CARD};border:1px solid {AMBER};border-radius:10px;
        padding:16px 20px;color:{TEXT_PRIMARY};font-size:0.92rem;line-height:1.6;
        margin-bottom:0.5rem;">
        📐 Use the <strong style="color:{AMBER};">sidebar</strong> to move between the
        <strong>FMEA Risk Analyzer</strong>, <strong>MSA Gage R&amp;R</strong>, and the
        three <strong>SPC</strong> workflows — Control Charts, Process Capability, and
        Live Simulation. Each tool keeps its own controls; the platform shares one theme
        and one navigation surface.
        </div>""",
        unsafe_allow_html=True,
    )

    st.subheader("What's inside")
    cards = st.columns(3)
    cards[0].markdown(
        _section_card(
            "🛡️ FMEA Risk Analyzer",
            "Upload a process FMEA and rank failure modes by RPN with AIAG/VDA action "
            "priority. Pareto, risk heatmap, critical-item triage, and Excel/PDF export.",
        ),
        unsafe_allow_html=True,
    )
    cards[1].markdown(
        _section_card(
            "📏 MSA Gage R&R",
            "Validate a crossed gage study and compute %GRR, ndc, and an AIAG verdict "
            "(Average-and-Range method). Loop: the Control Plan names the measurement "
            "method → MSA proves the gage capable before the SPC chart is trusted.",
        ),
        unsafe_allow_html=True,
    )
    cards[2].markdown(
        _section_card(
            "📈 SPC Dashboard",
            "Variables and attributes control charts, Cp/Cpk/Pp/Ppk capability analysis, "
            "and a live disturbance simulator for shift, spike, and drift storytelling.",
        ),
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.subheader("Standards context")
    standards = st.columns(3)
    standards[0].metric("FMEA", "AIAG-VDA 2019")
    standards[1].metric("SPC", "AIAG SPC · 4th Ed.")
    standards[2].metric("Capability target", "Cpk ≥ 1.33")


if __name__ == "__main__":
    from quality_core.theme import apply_theme

    st.set_page_config(page_title="Quality Platform", page_icon="🏭", layout="wide")
    apply_theme()
    render_home()
