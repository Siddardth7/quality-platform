"""Headless proof for spike #108 — validates every reuse claim the Reflex pilot
depends on, WITHOUT a browser or a running dev server.

The Reflex app (`reflex_capability/reflex_capability.py`) wires the same
`_capability_pilot` core into UI; this harness asserts that core end-to-end and
is the CI-speed evidence for acceptance criteria 1, 2, 3 and 5.

Run:  spikes/reflex_capability/.venv-spike/bin/python spikes/reflex_capability/proof_headless.py
"""

from __future__ import annotations

import plotly.graph_objects as go

from _capability_pilot import compute_pilot, report_bytes

# criterion 3: brand tokens are pure data, importable unchanged (no UI framework)
from quality_core.theme.palette import AMBER, VIOLET, BG_PRIMARY, TEXT_PRIMARY


def run() -> None:
    # 1. real demo data -> real capability study (engine, no streamlit) -------
    p = compute_pilot("Ply Thickness")
    study = p["study"]
    assert study["cpk"] is not None, "expected a Cpk from the demo stream"
    print(f"[1] engine study OK  cpk={study['cpk']:.3f}  method={study['method']}  oos={len(p['oos'])}")

    # 2. criterion 1: existing builder returns a Plotly figure for rx.plotly ---
    fig = p["figure"]
    assert isinstance(fig, go.Figure), "gauge builder must return a go.Figure"
    bar_color = fig.data[0].gauge.bar.color
    assert bar_color == AMBER, f"gauge should carry brand amber, got {bar_color}"
    print(f"[2] rx.plotly figure OK  type={type(fig).__name__}  amber-bar={bar_color}")

    # 3. criterion 2: unchanged exporter yields real download bytes ------------
    xlsx = report_bytes("Ply Thickness", "xlsx")
    pdf = report_bytes("Ply Thickness", "pdf")
    assert xlsx[:2] == b"PK", "xlsx must be a real zip payload"
    assert pdf[:4] == b"%PDF", "pdf must be a real PDF payload"
    print(f"[3] export bytes OK  xlsx={len(xlsx)}B  pdf={len(pdf)}B  (rx.download-ready)")

    # 4. criterion 3: brand tokens present and non-default ---------------------
    assert (AMBER, VIOLET, BG_PRIMARY, TEXT_PRIMARY) == (
        "#f59e0b", "#8b5cf6", "#0e1117", "#f1f5f9",
    ), "palette tokens drifted"
    print(f"[4] brand tokens OK  amber={AMBER} violet={VIOLET} bg={BG_PRIMARY}")

    print("\nALL HEADLESS CLAIMS PASS — import, gauge figure, export bytes, tokens.")


if __name__ == "__main__":
    run()
