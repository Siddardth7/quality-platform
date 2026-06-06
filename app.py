"""
app.py
FMEA Risk Prioritization Tool — Streamlit Web Application

Author: Siddardth | M.S. Aerospace Engineering, UIUC
Engineering reference: AIAG FMEA-4 + AIAG/VDA FMEA Handbook (5th Ed., 2019)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.rpn_engine import (
    run_pipeline,
    validate_input,
)
from ui.charts import get_or_build_charts
from ui.exports import render_export_buttons
from ui.filters import (
    apply_filters,
    render_process_filter,
    render_rpn_slider,
    render_severity_toggle,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="FMEA Risk Analyzer",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEMO_CSV      = Path(__file__).parent / "data" / "composite_panel_fmea_demo.csv"
TEMPLATE_CSV  = Path(__file__).parent / "data" / "fmea_input_template.csv"

TIER_ROW_COLORS = {
    "Red":    "background-color: #fde8e8; color: #922b21;",
    "Yellow": "background-color: #fef9e7; color: #7d6608;",
    "Green":  "background-color: #eafaf1; color: #1e8449;",
}

DARK_TIER_ROW_COLORS = {
    "Red":    "background-color: #3d1515; color: #ff8a80;",
    "Yellow": "background-color: #332500; color: #ffd54f;",
    "Green":  "background-color: #0d2e1a; color: #69f0ae;",
}

# ---------------------------------------------------------------------------
# CSS design system
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


def _inject_css(dark: bool) -> None:
    st.markdown(_BASE_CSS, unsafe_allow_html=True)
    if dark:
        st.markdown(_DARK_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_uploaded(file) -> pd.DataFrame:
    name = file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(file)
    elif name.endswith(".xlsx"):
        return pd.read_excel(file)
    else:
        raise ValueError(f"Unsupported file type: {file.name}. Please upload .csv or .xlsx.")


def _style_table(df: pd.DataFrame, dark: bool) -> pd.io.formats.style.Styler:
    colors = DARK_TIER_ROW_COLORS if dark else TIER_ROW_COLORS

    def row_style(row):
        return [colors.get(row.get("Risk_Tier", "Green"), "")] * len(row)

    display_cols = [
        "Failure_Mode", "Process_Step", "Component",
        "Severity", "Occurrence", "Detection", "RPN",
        "Risk_Tier", "Flag_High_RPN", "Flag_High_Severity", "Flag_Action_Priority_H",
    ]
    available = [c for c in display_cols if c in df.columns]
    return df[available].style.apply(row_style, axis=1)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar():
    """Render sidebar controls. Returns (raw_df, rpn_min, sev9_only, dark)."""
    st.sidebar.markdown(
        "<div style='padding:0.4rem 0 0.2rem; font-size:1.25rem; font-weight:700; "
        "letter-spacing:-0.3px;'>🛡️ FMEA Risk Analyzer</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.caption("Process FMEA · AIAG FMEA-4 · AIAG/VDA 2019")
    st.sidebar.divider()

    dark = st.sidebar.toggle(
        "🌙  Dark Mode",
        value=st.session_state.get("dark_mode", False),
        key="dark_mode",
    )

    st.sidebar.divider()
    st.sidebar.subheader("📂  Data Source")

    uploaded = st.sidebar.file_uploader(
        "Upload FMEA file",
        type=["csv", "xlsx"],
        help=(
            "CSV or Excel with 11 columns: ID, Process_Step, Component, "
            "Function, Failure_Mode, Effect, Severity, Cause, "
            "Occurrence, Current_Control, Detection  |  S/O/D must be integers 1–10"
        ),
    )
    use_demo = st.sidebar.button(
        "▶  Use Demo Dataset",
        help="Load 30-row composite panel aerospace FMEA",
        use_container_width=True,
    )

    if use_demo:
        st.session_state["use_demo"] = True
    if uploaded:
        st.session_state["use_demo"] = False

    raw_df       = None
    source_label = None
    source_ok    = False

    if uploaded and not st.session_state.get("use_demo"):
        try:
            raw_df       = _load_uploaded(uploaded)
            source_label = uploaded.name
            source_ok    = True
        except Exception as exc:
            st.sidebar.error(f"Failed to load: {exc}")
    elif st.session_state.get("use_demo"):
        raw_df       = pd.read_csv(DEMO_CSV)
        source_label = "Demo: composite panel FMEA (30 rows)"
        source_ok    = True

    if source_label:
        dot   = "🟢" if source_ok else "🔴"
        label = source_label[:42] + "…" if len(source_label) > 44 else source_label
        st.sidebar.markdown(
            f"<div style='font-size:0.82rem; padding:6px 10px; border-radius:6px; "
            f"background:rgba(39,174,96,0.08); border:1px solid rgba(39,174,96,0.25); "
            f"color:#1e7e45; margin-top:4px;'>"
            f"{dot} <b>{label}</b></div>",
            unsafe_allow_html=True,
        )

    st.sidebar.divider()
    st.sidebar.subheader("🔧  Filters")

    rpn_min  = render_rpn_slider()
    sev9_only = render_severity_toggle()

    return raw_df, rpn_min, sev9_only, dark


# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------

def render_header(source_active: bool) -> None:
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #1a2a4a 0%, #1d3461 55%, #152744 100%);
            border-radius: 14px;
            padding: 2rem 2.5rem 1.8rem;
            margin-bottom: 1.5rem;
            position: relative;
            overflow: hidden;
        ">
          <div style="position:relative; z-index:1;">
            <div style="font-size:0.78rem; font-weight:600; letter-spacing:1.5px;
                        color:#7ec8e3; text-transform:uppercase; margin-bottom:0.35rem;">
              Process FMEA &nbsp;·&nbsp; AIAG FMEA-4 &nbsp;·&nbsp; AIAG/VDA 2019
            </div>
            <div style="font-size:2rem; font-weight:800; color:#ffffff;
                        letter-spacing:-0.5px; line-height:1.15; margin-bottom:0.5rem;">
              FMEA Risk Prioritization Tool
            </div>
            <div style="font-size:0.95rem; color:#b8cce4; max-width:620px; line-height:1.6;">
              Calculate RPN scores, apply AIAG criticality flags, and visualize risk
              concentration across manufacturing failure modes — ready to export.
            </div>
          </div>
          <div style="position:absolute; right:2rem; top:50%; transform:translateY(-50%);
                      font-size:5rem; opacity:0.07;">🛡️</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Metric badges
# ---------------------------------------------------------------------------

def render_metric_badges(df: pd.DataFrame) -> None:
    total    = len(df)
    red      = int((df["Risk_Tier"] == "Red").sum())
    yellow   = int((df["Risk_Tier"] == "Yellow").sum())
    green    = int((df["Risk_Tier"] == "Green").sum())
    high_rpn = int(df["Flag_High_RPN"].sum())
    high_sev = int(df["Flag_High_Severity"].sum())
    action_h = int(df["Flag_Action_Priority_H"].sum())

    # Render as custom HTML cards for tier-aware coloring
    cards = [
        ("Total Modes",       total,    "#1B4F8A", "#EBF2FB", "All failure modes in current view"),
        ("🔴 Red",            red,      "#c0392b", "#FDEDEC", "RPN > 100 OR Severity ≥ 9 — immediate action"),
        ("🟡 Yellow",         yellow,   "#d68910", "#FEF9E7", "RPN 50–100 — corrective action recommended"),
        ("🟢 Green",          green,    "#1e8449", "#EAFAF1", "RPN < 50 — monitor"),
        ("High RPN (>100)",   high_rpn, "#7d3c98", "#F5EEF8", "Flag_High_RPN = True"),
        ("Severity ≥ 9",      high_sev, "#c0392b", "#FDEDEC", "Safety-critical per AIAG FMEA-4"),
        ("Action Priority H", action_h, "#922b21", "#FDEDEC", "RPN ≥ 200 OR Severity ≥ 9"),
    ]

    html_parts = ["<div style='display:grid; grid-template-columns:repeat(7,1fr); gap:10px; margin:0.75rem 0 1rem;'>"]
    for label, value, accent, bg, tip in cards:
        html_parts.append(
            f"""<div title="{tip}" style="
                background:{bg};
                border-radius:10px;
                border:1px solid rgba(0,0,0,0.07);
                border-left:4px solid {accent};
                padding:12px 14px;
                cursor:default;
                transition:box-shadow 0.2s;
            ">
              <div style="font-size:0.72rem; font-weight:600; color:#666; text-transform:uppercase;
                          letter-spacing:0.5px; margin-bottom:4px; white-space:nowrap; overflow:hidden;
                          text-overflow:ellipsis;">{label}</div>
              <div style="font-size:1.7rem; font-weight:800; color:{accent}; line-height:1.1;">{value}</div>
            </div>"""
        )
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Auto-insights
# ---------------------------------------------------------------------------

def render_insights(df: pd.DataFrame) -> None:
    if df.empty or len(df) < 2:
        return

    total_rpn  = df["RPN"].sum()
    top_n      = min(3, len(df))
    top_pct    = df.nlargest(top_n, "RPN")["RPN"].sum() / total_rpn * 100 if total_rpn else 0
    top_item   = df.iloc[0]
    red_count  = int((df["Risk_Tier"] == "Red").sum())
    sev9_count = int(df["Flag_High_Severity"].sum())

    parts = [
        f"**Top {top_n} failure modes account for {top_pct:.0f}% of total RPN.**",
        f"Highest risk: **{str(top_item['Failure_Mode'])[:60]}** "
        f"(RPN = {int(top_item['RPN'])}, {top_item['Process_Step']}).",
    ]
    if red_count:
        parts.append(f"**{red_count}** item(s) in the Red tier require immediate corrective action.")
    if sev9_count:
        parts.append(f"**{sev9_count}** safety-critical failure mode(s) flagged (Severity ≥ 9).")

    st.info("   ".join(parts))


# ---------------------------------------------------------------------------
# Risk Table tab
# ---------------------------------------------------------------------------

def render_table(df: pd.DataFrame, dark: bool) -> None:
    st.subheader("📋  Ranked Failure Mode Table")
    if df.empty:
        st.info("No failure modes match the current filter settings.")
        return

    col_left, col_right = st.columns([3, 1])

    with col_left:
        st.dataframe(
            _style_table(df, dark),
            use_container_width=True,
            height=520,
        )
        st.caption(
            f"{len(df)} failure mode(s) shown  |  "
            "🔴 Red = immediate action  |  🟡 Yellow = recommended  |  🟢 Green = monitor"
        )

    with col_right:
        st.markdown("**Risk Distribution**")
        red    = int((df["Risk_Tier"] == "Red").sum())
        yellow = int((df["Risk_Tier"] == "Yellow").sum())
        green  = int((df["Risk_Tier"] == "Green").sum())
        total  = len(df)

        def _pct(n): return f"{n/total*100:.0f}%" if total else "0%"

        st.markdown(f"🔴 **Red:** {red} ({_pct(red)})")
        st.progress(red / total if total else 0, text="")
        st.markdown(f"🟡 **Yellow:** {yellow} ({_pct(yellow)})")
        st.progress(yellow / total if total else 0, text="")
        st.markdown(f"🟢 **Green:** {green} ({_pct(green)})")
        st.progress(green / total if total else 0, text="")

        st.divider()
        if total:
            avg_rpn   = df["RPN"].mean()
            max_rpn   = df["RPN"].max()
            total_rpn = df["RPN"].sum()
            st.markdown(f"**Avg RPN:** {avg_rpn:.0f}")
            st.markdown(f"**Max RPN:** {int(max_rpn)}")
            st.markdown(f"**Total RPN:** {int(total_rpn)}")


# ---------------------------------------------------------------------------
# Pareto chart tab
# ---------------------------------------------------------------------------

def render_pareto(pareto_fig) -> None:
    st.subheader("📊  Pareto Chart — Failure Modes Ranked by RPN")
    st.markdown(
        "Bars sorted highest to lowest RPN. The **cumulative % line** shows where 80% of total "
        "risk is concentrated. Focus corrective action resources on failure modes to the **left** "
        "of the 80% threshold."
    )
    if pareto_fig is None:
        st.info("No data to display under current filters.")
        return
    st.plotly_chart(pareto_fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Heatmap tab
# ---------------------------------------------------------------------------

def render_heatmap(heatmap_fig) -> None:
    st.subheader("🗺️  Risk Heatmap — Severity × Occurrence")
    st.markdown(
        "Each cell shows the **count of failure modes** with that Severity × Occurrence combination. "
        "Color reflects the worst Risk Tier in the cell. Clustering in the **top-right** corner "
        "(high S, high O) indicates systemic process problems."
    )
    if heatmap_fig is None:
        st.info("No data to display under current filters.")
        return
    st.plotly_chart(heatmap_fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Critical items tab
# ---------------------------------------------------------------------------

def render_critical_panel(df: pd.DataFrame) -> None:
    critical = df[df["Flag_Action_Priority_H"].astype(bool)]

    if critical.empty:
        st.success("✅  No critical failure modes under current filters.")
        return

    st.warning(
        f"**{len(critical)} failure mode(s)** have RPN ≥ 200 or Severity ≥ 9 and require "
        "immediate corrective action per AIAG FMEA-4."
    )

    display_cols = [
        c for c in
        ["Failure_Mode", "Process_Step", "Component", "Cause",
         "Severity", "Occurrence", "Detection", "RPN", "Risk_Tier",
         "Current_Control"]
        if c in critical.columns
    ]
    st.dataframe(critical[display_cols].reset_index(drop=True), use_container_width=True)

    with st.expander("📌  What to do with these items"):
        st.markdown("""
**AIAG FMEA-4 Corrective Action Process:**
1. **Assign ownership** — every Action Priority H item needs a named engineer responsible
2. **Root cause analysis** — use 5-Why or Ishikawa diagram to identify the true cause
3. **Define actions** — target reducing Occurrence (process change) or improving Detection (control upgrade)
4. **Set a deadline** — action plans without dates don't get completed
5. **Re-score after action** — update S/O/D scores and verify Risk_Tier moves to Yellow or Green
6. **Document everything** — AIAG-compliant FMEA requires traceability of all corrective actions
        """)


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------

def render_landing() -> None:
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #EBF5FB 0%, #F5EEF8 100%);
            border: 1px solid rgba(27,79,138,0.15);
            border-radius: 14px;
            padding: 1.75rem 2rem;
            margin-bottom: 1.5rem;
        ">
          <div style="font-size:1.05rem; color:#1a2a3a; font-weight:500;">
            👈 &nbsp;Upload a CSV/Excel file or click <strong>Use Demo Dataset</strong>
            in the sidebar to begin.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 3-step workflow ──────────────────────────────────────────────────
    st.markdown("#### How it works")
    c1, c2, c3 = st.columns(3)

    _card_style = (
        "background:#ffffff; border-radius:12px; padding:1.4rem 1.5rem; "
        "border:1px solid #e2e8f0; height:100%; box-shadow:0 1px 4px rgba(0,0,0,0.06);"
    )

    with c1:
        st.markdown(
            f"<div style='{_card_style}'>"
            "<div style='font-size:1.7rem; margin-bottom:0.5rem;'>📂</div>"
            "<div style='font-weight:700; font-size:1rem; color:#1a2a3a; margin-bottom:0.4rem;'>"
            "1 · Upload your FMEA</div>"
            "<div style='font-size:0.88rem; color:#5a6a7a; line-height:1.55;'>"
            "Upload a CSV or Excel file with 11 columns, or try the 30-row composite panel "
            "aerospace demo dataset.</div></div>",
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"<div style='{_card_style}'>"
            "<div style='font-size:1.7rem; margin-bottom:0.5rem;'>⚙️</div>"
            "<div style='font-weight:700; font-size:1rem; color:#1a2a3a; margin-bottom:0.4rem;'>"
            "2 · Automated analysis</div>"
            "<div style='font-size:0.88rem; color:#5a6a7a; line-height:1.55;'>"
            "RPN = S × O × D is calculated, Risk Tiers assigned, and AIAG FMEA-4 criticality "
            "flags applied automatically.</div></div>",
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"<div style='{_card_style}'>"
            "<div style='font-size:1.7rem; margin-bottom:0.5rem;'>📊</div>"
            "<div style='font-weight:700; font-size:1rem; color:#1a2a3a; margin-bottom:0.4rem;'>"
            "3 · Visualize & export</div>"
            "<div style='font-size:0.88rem; color:#5a6a7a; line-height:1.55;'>"
            "Interactive Pareto chart, Severity × Occurrence heatmap, and one-click export "
            "to PDF, Excel, or CSV.</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

    # ── Schema + template ────────────────────────────────────────────────
    col_schema, col_template = st.columns([3, 2])

    with col_schema:
        with st.expander("📐  Required CSV/Excel schema", expanded=True):
            st.markdown("""
| Column | Type | Constraint |
|---|---|---|
| `ID` | int | Unique row identifier |
| `Process_Step` | str | Manufacturing process step |
| `Component` | str | Part or sub-assembly |
| `Function` | str | Intended function |
| `Failure_Mode` | str | How it can fail |
| `Effect` | str | Consequence of failure |
| `Severity` | int | 1–10 (AIAG scale) |
| `Cause` | str | Root cause |
| `Occurrence` | int | 1–10 (AIAG scale) |
| `Current_Control` | str | Existing controls |
| `Detection` | int | 1–10 (AIAG scale) |

**RPN = Severity × Occurrence × Detection** (range 1–1000)
""")

    with col_template:
        with st.expander("📥  Download starter template", expanded=True):
            st.markdown(
                "Download a pre-formatted CSV with correct column headers and one example row. "
                "Fill it in and upload to the sidebar."
            )
            if TEMPLATE_CSV.exists():
                st.download_button(
                    label="⬇️  Download fmea_input_template.csv",
                    data=TEMPLATE_CSV.read_bytes(),
                    file_name="fmea_input_template.csv",
                    mime="text/csv",
                    use_container_width=True,
                    help="Pre-formatted template with correct column headers",
                )
            else:
                st.caption("Template file not found.")

        with st.expander("📖  Risk tier thresholds"):
            st.markdown("""
| Tier | Condition | Action Required |
|---|---|---|
| 🔴 Red | RPN > 100 OR Severity ≥ 9 | Immediate corrective action |
| 🟡 Yellow | RPN 50–100 | Action recommended |
| 🟢 Green | RPN < 50 | Monitor |

**Action Priority H** is flagged when RPN ≥ 200 OR Severity ≥ 9.
""")


# ---------------------------------------------------------------------------
# Validation summary panel
# ---------------------------------------------------------------------------

def render_validation_summary(df: pd.DataFrame) -> None:
    """Show a compact dataset health panel immediately after upload."""
    score_cols = ["Severity", "Occurrence", "Detection"]
    text_cols  = ["Failure_Mode", "Effect", "Cause"]
    warnings: list[str] = []

    for col in score_cols:
        if col in df.columns:
            if (df[col] == 10).sum() > 0:
                warnings.append(f"{int((df[col] == 10).sum())} row(s) have {col} = 10 (maximum score)")
            if (df[col] == 1).sum() > 0:
                warnings.append(f"{int((df[col] == 1).sum())} row(s) have {col} = 1 (minimum score)")

    for col in text_cols:
        if col in df.columns:
            long = int((df[col].str.len() > 120).sum())
            if long > 0:
                warnings.append(f"{long} row(s) have long '{col}' text (>120 chars — may truncate in PDF)")

    with st.expander("📋  Dataset Health", expanded=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("Rows loaded",     len(df))
        c2.metric("Columns present", len(df.columns))
        c3.metric("Warnings",        len(warnings))
        if warnings:
            for w in warnings:
                st.caption(f"⚠️ {w}")
        else:
            st.caption("✅ No data quality warnings detected.")


# ---------------------------------------------------------------------------
# App entry point
# ---------------------------------------------------------------------------

def main() -> None:
    raw_df, rpn_min, sev9_only, dark = render_sidebar()

    _inject_css(dark)
    render_header(source_active=raw_df is not None)

    if raw_df is None:
        st.sidebar.divider()
        st.sidebar.caption(
            "Engineering ref: AIAG FMEA-4 (4th Ed.) + "
            "AIAG/VDA FMEA Handbook (5th Ed., 2019)"
        )
        render_landing()
        return

    # ── Validate ─────────────────────────────────────────────────────────
    try:
        validate_input(raw_df)
    except ValueError as exc:
        st.error(f"**Input validation failed:** {exc}")
        st.stop()

    # ── Pipeline ──────────────────────────────────────────────────────────
    try:
        df_analyzed = run_pipeline(raw_df)
        st.session_state["_dataset_rpn_max"] = int(df_analyzed["RPN"].max())
    except (ValueError, KeyError) as exc:
        st.error(f"**Pipeline error:** {exc}")
        st.stop()

    render_validation_summary(df_analyzed)

    # ── Process step filter (sidebar, needs data first) ───────────────────
    process_steps = render_process_filter(df_analyzed)

    # Sidebar footer
    st.sidebar.divider()
    st.sidebar.caption(
        "Engineering ref: AIAG FMEA-4 (4th Ed.) + "
        "AIAG/VDA FMEA Handbook (5th Ed., 2019)"
    )

    # ── Apply filters ─────────────────────────────────────────────────────
    df_filtered = apply_filters(df_analyzed, rpn_min, sev9_only, process_steps)

    # ── Build / cache charts ──────────────────────────────────────────────
    pareto_fig, heatmap_fig = get_or_build_charts(
        df_filtered, rpn_min, sev9_only, process_steps, dark
    )

    # ── Dashboard ─────────────────────────────────────────────────────────
    render_metric_badges(df_filtered)
    render_insights(df_filtered)
    st.divider()

    tab_table, tab_pareto, tab_heatmap, tab_critical = st.tabs([
        "📋  Risk Table",
        "📊  Pareto Chart",
        "🗺️  Risk Heatmap",
        "⚠️  Critical Items",
    ])

    with tab_table:
        render_table(df_filtered, dark)

    with tab_pareto:
        render_pareto(pareto_fig)

    with tab_heatmap:
        render_heatmap(heatmap_fig)

    with tab_critical:
        render_critical_panel(df_filtered)

    st.divider()
    render_export_buttons(df_filtered, rpn_min, sev9_only, process_steps)


if __name__ == "__main__":
    main()
