"""
ui/components.py
FMEA Risk Prioritization Tool — Presentational render functions for Streamlit.

All functions here are purely presentational: they receive data and write to
Streamlit. No session state mutation, no I/O. Orchestration logic stays in app.py.

Exports:
    render_header()
    render_metric_badges(df)
    render_insights(df)
    render_validation_summary(df)
    render_landing(template_csv_path)
    render_table(df, dark)
    render_pareto(pareto_fig)
    render_heatmap(heatmap_fig)
    render_critical_panel(df)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from fmea_app.ap_engine import BASIS_AP, BASIS_RPN, HIGH, LOW, MEDIUM
from fmea_app.rating_scales import RatingScaleSet

# ---------------------------------------------------------------------------
# Risk tier CSS row colors — light and dark variants
# ---------------------------------------------------------------------------

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

# AP High/Medium/Low share the Red/Yellow/Green visual buckets so the table
# reads the same whichever basis is active.
_AP_TO_TIER = {HIGH: "Red", MEDIUM: "Yellow", LOW: "Green"}


def _style_table(
    df: pd.DataFrame, dark: bool, basis: str = BASIS_RPN
) -> pd.io.formats.style.Styler:
    colors = DARK_TIER_ROW_COLORS if dark else TIER_ROW_COLORS
    use_ap = basis == BASIS_AP and "AP" in df.columns

    def row_style(row):
        if use_ap:
            tier = _AP_TO_TIER.get(str(row.get("AP", "")), "Green")
        else:
            tier = str(row.get("Risk_Tier", "Green"))
        return [colors.get(tier, "")] * len(row)

    # RPN and AP sit side by side so both bases stay visible regardless of toggle.
    display_cols = [
        "Failure_Mode", "Process_Step", "Component",
        "Severity", "Occurrence", "Detection", "RPN", "AP",
        "Risk_Tier", "Flag_High_RPN", "Flag_High_Severity", "Flag_Action_Priority_H",
    ]
    available = [c for c in display_cols if c in df.columns]
    return df[available].style.apply(row_style, axis=1)


# ---------------------------------------------------------------------------
# render_header
# ---------------------------------------------------------------------------

def render_header() -> None:
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
# render_metric_badges
# ---------------------------------------------------------------------------

def render_metric_badges(df: pd.DataFrame, basis: str = BASIS_RPN) -> None:
    total    = len(df)
    high_sev = int(df["Flag_High_Severity"].sum()) if "Flag_High_Severity" in df.columns else 0

    if basis == BASIS_AP and "AP" in df.columns:
        ap_high = int((df["AP"] == HIGH).sum())
        ap_med  = int((df["AP"] == MEDIUM).sum())
        ap_low  = int((df["AP"] == LOW).sum())
        cards = [
            ("Total Modes",  total,   "#1B4F8A", "#EBF2FB", "All failure modes in current view"),
            ("🔴 AP High",   ap_high, "#c0392b", "#FDEDEC", "AIAG/VDA Action Priority = High — act first"),
            ("🟡 AP Medium", ap_med,  "#d68910", "#FEF9E7", "Action Priority = Medium — should act"),
            ("🟢 AP Low",    ap_low,  "#1e8449", "#EAFAF1", "Action Priority = Low — monitor"),
            ("Severity ≥ 9", high_sev, "#c0392b", "#FDEDEC", "Safety-critical per AIAG/VDA"),
        ]
    else:
        red      = int((df["Risk_Tier"] == "Red").sum())
        yellow   = int((df["Risk_Tier"] == "Yellow").sum())
        green    = int((df["Risk_Tier"] == "Green").sum())
        high_rpn = int(df["Flag_High_RPN"].sum())
        action_h = int(df["Flag_Action_Priority_H"].sum())
        cards = [
            ("Total Modes",       total,    "#1B4F8A", "#EBF2FB", "All failure modes in current view"),
            ("🔴 Red",            red,      "#c0392b", "#FDEDEC", "RPN > 100 OR Severity ≥ 9 — immediate action"),
            ("🟡 Yellow",         yellow,   "#d68910", "#FEF9E7", "RPN 50–100 — corrective action recommended"),
            ("🟢 Green",          green,    "#1e8449", "#EAFAF1", "RPN < 50 — monitor"),
            ("High RPN (>100)",   high_rpn, "#7d3c98", "#F5EEF8", "Flag_High_RPN = True"),
            ("Severity ≥ 9",      high_sev, "#c0392b", "#FDEDEC", "Safety-critical per AIAG FMEA-4"),
            ("Action Priority H", action_h, "#922b21", "#FDEDEC", "RPN ≥ 200 OR Severity ≥ 9"),
        ]

    html_parts = ["<div style='display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:10px; margin:0.75rem 0 1rem;'>"]
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
# render_insights
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

    st.info("   ".join(parts))


# ---------------------------------------------------------------------------
# render_validation_summary
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
            long = int((df[col].astype(str).str.len() > 120).sum())
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
# render_landing
# ---------------------------------------------------------------------------

def render_landing(template_csv_path: Path) -> None:
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
            if template_csv_path.exists():
                st.download_button(
                    label="⬇️  Download fmea_input_template.csv",
                    data=template_csv_path.read_bytes(),
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
# render_table
# ---------------------------------------------------------------------------

def render_table(df: pd.DataFrame, dark: bool, basis: str = BASIS_RPN) -> None:
    st.subheader("📋  Ranked Failure Mode Table")
    if df.empty:
        st.info("No failure modes match the current filter settings.")
        return

    use_ap = basis == BASIS_AP and "AP" in df.columns
    col_left, col_right = st.columns([3, 1])

    with col_left:
        st.dataframe(
            _style_table(df, dark, basis),
            use_container_width=True,
            height=520,
        )
        ranked_by = "Action Priority (AP)" if use_ap else "RPN"
        st.caption(
            f"{len(df)} failure mode(s) shown · ranked by {ranked_by}  |  "
            "🔴 immediate action  |  🟡 recommended  |  🟢 monitor"
        )

    with col_right:
        total = len(df)

        def _pct(n: int) -> str:
            return f"{n/total*100:.0f}%" if total else "0%"

        if use_ap:
            st.markdown("**Action Priority**")
            high = int((df["AP"] == HIGH).sum())
            med  = int((df["AP"] == MEDIUM).sum())
            low  = int((df["AP"] == LOW).sum())
            st.markdown(f"🔴 **High:** {high} ({_pct(high)})")
            st.progress(high / total if total else 0, text="")
            st.markdown(f"🟡 **Medium:** {med} ({_pct(med)})")
            st.progress(med / total if total else 0, text="")
            st.markdown(f"🟢 **Low:** {low} ({_pct(low)})")
            st.progress(low / total if total else 0, text="")
        else:
            st.markdown("**Risk Distribution**")
            red    = int((df["Risk_Tier"] == "Red").sum())
            yellow = int((df["Risk_Tier"] == "Yellow").sum())
            green  = int((df["Risk_Tier"] == "Green").sum())
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
# render_pareto
# ---------------------------------------------------------------------------

def render_pareto(pareto_fig) -> None:  # type: ignore[no-untyped-def]
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
# render_heatmap
# ---------------------------------------------------------------------------

def render_heatmap(heatmap_fig) -> None:  # type: ignore[no-untyped-def]
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
# render_rating_scales
# ---------------------------------------------------------------------------

def render_rating_scales(scale_set: RatingScaleSet) -> None:
    """Show the active S/O/D rating-scale reference tables."""
    st.subheader("📐  Rating Scale Reference")
    st.caption(
        f"Active scale: **{scale_set.name}**"
        + (f"  ·  {scale_set.source}" if scale_set.source else "")
    )
    st.markdown(
        "These 1–10 anchors define what each Severity, Occurrence, and Detection "
        "score *means* when you author an FMEA. They are reference only — the RPN "
        "and AP calculations use the numeric scores you provide."
    )

    c_sev, c_occ, c_det = st.columns(3)
    for col, factor, title in (
        (c_sev, "severity", "Severity (S)"),
        (c_occ, "occurrence", "Occurrence (O)"),
        (c_det, "detection", "Detection (D)"),
    ):
        with col:
            st.markdown(f"**{title}**")
            st.dataframe(
                scale_set.to_frame(factor),
                use_container_width=True,
                hide_index=True,
                height=390,
            )


# ---------------------------------------------------------------------------
# render_critical_panel
# ---------------------------------------------------------------------------

def render_critical_panel(df: pd.DataFrame, basis: str = BASIS_RPN) -> None:
    use_ap = basis == BASIS_AP and "AP" in df.columns

    if use_ap:
        critical = df[df["AP"] == HIGH]
        reason = "are Action Priority High (AIAG/VDA 2019)"
    else:
        critical = df[df["Flag_Action_Priority_H"].astype(bool)]
        reason = "have RPN ≥ 200 or Severity ≥ 9"

    if critical.empty:
        st.success("✅  No critical failure modes under current filters.")
        return

    st.warning(
        f"**{len(critical)} failure mode(s)** {reason} and require "
        "immediate corrective action per AIAG FMEA-4."
    )

    display_cols = [
        c for c in
        ["Failure_Mode", "Process_Step", "Component", "Cause",
         "Severity", "Occurrence", "Detection", "RPN", "AP", "Risk_Tier",
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
