"""Yield / DPPM + failing-signal Pareto page (W09-5, #69, OQ2 added scope).

Thin renderer only — all yield/DPPM and Pareto logic lives in
`secom_app.yield_dppm`; this page loads the vendored SECOM dataset, runs the
existing selection screen, and displays the engine's typed output. Mirrors
`msa_app/pages/gage_study.py`: a `render_*()` callable that owns no page-level
chrome (`set_page_config` / theming), so a host entry script can mount it.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from secom_app.ingest import SecomDataset, load_secom
from secom_app.selection import select_signals
from secom_app.yield_dppm import failing_signal_pareto, yield_summary


@st.cache_data
def _load_dataset() -> SecomDataset:
    return load_secom()


@st.cache_data
def _load_audit(dataset: SecomDataset) -> pd.DataFrame:
    return select_signals(dataset.features)


def render_yield_dppm() -> None:
    st.title("Yield / DPPM")
    st.caption(
        "Wafer-level yield and DPPM from the SECOM pass/fail label, plus an "
        "association Pareto of which kept signals were most often out of "
        "control on failed wafers."
    )

    dataset = _load_dataset()
    summary = yield_summary(dataset.labels)

    col1, col2, col3 = st.columns(3)
    col1.metric("Yield", f"{summary.yield_pct:.3f}%")
    col2.metric("DPPM", f"{summary.dppm:,.2f}")
    col3.metric("Wafers", f"{summary.n_pass:,} pass / {summary.n_fail:,} fail")
    st.caption(
        "DPPM here is defective **units** per million (one pass/fail verdict per "
        "wafer) — not DPMO (defects per million opportunities), which SECOM "
        "cannot support."
    )

    st.subheader("Failing-signal Pareto")
    st.info(
        "Association / screening only — a signal ranking high means it was most "
        "often out-of-control on failed wafers, not a proven cause of any failure."
    )
    audit = _load_audit(dataset)
    pareto = failing_signal_pareto(dataset, audit)
    if pareto.empty:
        st.write("No kept signal had any SPC violation on a failed wafer.")
        return

    st.dataframe(pareto, use_container_width=True)
    st.bar_chart(pareto.set_index("signal")["n_fail_violations"])
