"""Reflex pilot — SPC Process Capability page (spike #108).

Rebuilds the Streamlit Capability page in Reflex, importing the SPC engine,
visualizer, and exporter UNCHANGED via `_capability_pilot`. Proves the four
migration mechanics on the simplest (stateless) page:

  1. engine import works           -> compute_pilot()
  2. rx.plotly renders the gauge   -> the existing build_cpk_gauge figure
  3. rx.download returns exports   -> the unchanged exporter bytes
  4. brand tokens apply            -> quality_core palette, not default Reflex

Throwaway; not wired into main. Run from this dir: `reflex run`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# spike root (holds _capability_pilot + _engine_bridge) on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import reflex as rx
import plotly.graph_objects as go

from _capability_pilot import STREAM_OPTIONS, compute_pilot, report_bytes
from quality_core.theme.palette import (
    AMBER,
    BG_CARD,
    BG_PRIMARY,
    BG_SECONDARY,
    BORDER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    VIOLET,
)


class State(rx.State):
    stream_label: str = "Ply Thickness"
    method: str = ""
    note: str = ""
    cp: str = "—"
    cpk: str = "—"
    pp: str = "—"
    ppk: str = "—"
    mean: str = "—"
    sigma: str = "—"
    oos_count: int = 0
    normal_msg: str = ""
    figure: go.Figure = go.Figure()

    @rx.event
    def recompute(self):
        p = compute_pilot(self.stream_label)
        s = p["study"]
        self.figure = p["figure"]
        self.method = s["method"]
        self.note = s["note"]
        self.cp = "N/A" if s["cp"] is None else f"{s['cp']:.3f}"
        self.cpk = "N/A" if s["cpk"] is None else f"{s['cpk']:.3f}"
        self.pp = "N/A" if s["pp"] is None else f"{s['pp']:.3f}"
        self.ppk = "N/A" if s["ppk"] is None else f"{s['ppk']:.3f}"
        self.mean = f"{s['mean']:.4f}"
        self.sigma = f"{s['sigma_overall']:.4f}"
        self.oos_count = len(p["oos"])
        n = p["normality"]
        verdict = "approximately normal" if n["is_normal"] else "may need non-normal review"
        self.normal_msg = f"Shapiro-Wilk p = {n['p_value']:.4f} — {verdict}."

    @rx.event
    def set_stream(self, label: str):
        self.stream_label = label
        return State.recompute

    @rx.event
    def download_xlsx(self):
        return rx.download(
            data=report_bytes(self.stream_label, "xlsx"),
            filename=f"spc_capability_{self.stream_label.replace(' ', '_')}.xlsx",
        )

    @rx.event
    def download_pdf(self):
        return rx.download(
            data=report_bytes(self.stream_label, "pdf"),
            filename=f"spc_capability_{self.stream_label.replace(' ', '_')}.pdf",
        )


def _metric(label: str, value) -> rx.Component:
    return rx.box(
        rx.text(label, color=TEXT_SECONDARY, font_size="0.8rem"),
        rx.text(value, color=AMBER, font_size="1.6rem", font_weight="700"),
        background=BG_CARD,
        border=f"1px solid {BORDER}",
        border_radius="10px",
        padding="0.75rem 1rem",
        min_width="7rem",
    )


def index() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.heading("Process Capability", color=AMBER, size="8"),
            rx.text(
                "Reflex pilot (#108) — engine, gauge, and export reused unchanged.",
                color=TEXT_SECONDARY,
            ),
            rx.select(
                list(STREAM_OPTIONS.keys()),
                value=State.stream_label,
                on_change=State.set_stream,
                color_scheme="amber",
            ),
            rx.cond(
                State.oos_count > 0,
                rx.callout(
                    "Process not in statistical control — capability indices are indicative only.",
                    icon="triangle_alert",
                    color_scheme="red",
                    variant="soft",
                ),
            ),
            rx.hstack(
                rx.box(
                    rx.plotly(data=State.figure),
                    background=BG_SECONDARY,
                    border=f"1px solid {BORDER}",
                    border_radius="12px",
                    padding="0.5rem",
                ),
                rx.vstack(
                    rx.hstack(_metric("Cp", State.cp), _metric("Cpk", State.cpk)),
                    rx.hstack(_metric("Pp", State.pp), _metric("Ppk", State.ppk)),
                    rx.hstack(_metric("Mean", State.mean), _metric("Sigma", State.sigma)),
                    rx.text(State.note, color=TEXT_SECONDARY, font_size="0.8rem"),
                    align="start",
                ),
                align="start",
                spacing="5",
                wrap="wrap",
            ),
            rx.text(State.normal_msg, color=TEXT_SECONDARY),
            rx.heading("Download Report", color=AMBER, size="5"),
            rx.hstack(
                rx.button("Excel (.xlsx)", on_click=State.download_xlsx, background=AMBER, color=BG_PRIMARY),
                rx.button("PDF (.pdf)", on_click=State.download_pdf, background=VIOLET, color=TEXT_PRIMARY),
            ),
            spacing="4",
            align="start",
            max_width="960px",
            margin="0 auto",
            padding="2rem",
        ),
        background=BG_PRIMARY,
        min_height="100vh",
        color=TEXT_PRIMARY,
        font_family="Inter, sans-serif",
    )


app = rx.App()
app.add_page(index, route="/", on_load=State.recompute, title="SPC Capability — Reflex pilot")
