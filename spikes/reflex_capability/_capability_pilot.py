"""Streamlit-free capability core for the Reflex pilot (issue #108).

This is the honest shape of a migrated page: the render layer is rewritten
(Reflex here, Streamlit before), but every *computation* is the unchanged SPC
engine. `spc_app.pages.process_capability` couldn't be imported directly — its
package `__init__` eagerly pulls the Streamlit `control_charts` page — so the
~15 lines of demo-load + stability-gate logic are reproduced here calling the
same engine functions. No engine/quality_core code is modified.
"""

from __future__ import annotations

import _engine_bridge  # noqa: F401  -- adds engine + palette roots to sys.path

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from spc_app.spc_engine.capability import compute_capability_study, normality_test
from spc_app.spc_engine.control_charts import compute_imr, compute_xbar_r, compute_xbar_s
from spc_app.spc_engine.rule_detection import detect_violations
from spc_app.spc_engine.utils import subgroup_rows
from spc_app.visualizer import build_cpk_gauge
from spc_app.exporter import (
    CapabilityReport,
    build_capability_report_excel,
    build_capability_report_pdf,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEMO_PATH = _REPO_ROOT / "apps/spc/data/demo_composites_aerospace.csv"

STREAM_OPTIONS: dict[str, str] = {
    "Ply Thickness": "ply_thickness",
    "Autoclave Cure Temperature": "autoclave_temp",
    "Hole Diameter": "hole_diameter",
}


def load_demo_data() -> pd.DataFrame:
    return pd.read_csv(_DEMO_PATH)


def _assess_control(stream_name: str, frame: pd.DataFrame) -> list[dict]:
    """Western-Electric stability gate — the unchanged engine path from the
    Streamlit page's ``assess_control_chart`` (routed through the central gate)."""
    if stream_name == "ply_thickness":
        subgroups = subgroup_rows(frame)
        xr = compute_xbar_r(subgroups)
        points, cl, sigma = xr["subgroup_means"], xr["xbarbar"], xr["sigma_hat"] / (len(subgroups[0]) ** 0.5)
        chart = "Xbar-R"
    elif stream_name == "hole_diameter":
        subgroups = subgroup_rows(frame)
        xs = compute_xbar_s(subgroups)
        points, cl, sigma = xs["subgroup_means"], xs["xbarbar"], xs["sigma_hat"] / (len(subgroups[0]) ** 0.5)
        chart = "Xbar-S"
    else:
        im = compute_imr(frame.sort_values("subgroup")["value"].tolist())
        points, cl, sigma = im["values"], im["xbar"], im["sigma_hat"]
        chart = "I-MR"
    return detect_violations(chart, points, cl=cl, sigma=sigma, rule_set="Western Electric")


def compute_pilot(stream_label: str) -> dict:
    """Full pilot computation for one stream: study + gauge figure + OOS gate."""
    stream = STREAM_OPTIONS[stream_label]
    frame = load_demo_data()
    sframe = frame[frame["stream"] == stream].copy().sort_values("subgroup")
    values = sframe["value"].to_numpy()
    lsl = float(sframe["lsl"].dropna().iloc[0]) if "lsl" in sframe else None
    usl = float(sframe["usl"].dropna().iloc[0]) if "usl" in sframe else None

    oos = _assess_control(stream, sframe)
    study = compute_capability_study(values, lsl=lsl, usl=usl, force_method="auto")
    normality = normality_test(values)
    fig: go.Figure = build_cpk_gauge(study["cpk"])

    return {
        "stream": stream,
        "stream_label": stream_label,
        "values": values,
        "lsl": lsl,
        "usl": usl,
        "study": study,
        "normality": normality,
        "oos": oos,
        "figure": fig,
    }


def report_bytes(stream_label: str, kind: str) -> bytes:
    """Export payload via the UNCHANGED exporter — feeds rx.download."""
    p = compute_pilot(stream_label)
    report = CapabilityReport(
        stream_label=stream_label,
        values=p["values"].tolist(),
        capability=p["study"],
        lsl=p["lsl"],
        usl=p["usl"],
        normality=p["normality"],
        oos_signal_count=len(p["oos"]),
    )
    return build_capability_report_excel(report) if kind == "xlsx" else build_capability_report_pdf(report)
