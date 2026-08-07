"""The two #191 stability baselines that must stay in the SPC app's suite.

The gate itself now lives in `quality_core.spc.stability` (audit A12, #205 PR 2),
and the rest of its tests moved to `packages/quality-core/tests/test_spc_stability.py`.
These two stay here because they read the SPC app's committed demo dataset
(`apps/spc/data/demo_composites_aerospace.csv`) and the app's stream -> chart-type
map — the core suite imports no app and hard-codes no app path.
"""

from pathlib import Path

import pandas as pd
import pytest
from quality_core.spc.stability import assess_stability

# --- the caller-supplied chart context (#191 D3) ---


def test_imr_sort_is_stable_across_tied_subgroups():
    """The I-MR branch must not reorder rows that share a subgroup.

    A stream charted as I-MR can still carry several rows per subgroup
    (ply_misalignment has 5 across 20 subgroups), so `sort_values("subgroup")`
    is full of ties. pandas' default quicksort is unstable and permutes them
    differently on different platforms, which changes every moving range and
    moves sigma_hat enough to flip the verdict — this cost two red CI runs.

    Pinned two ways: the result must equal the already-ordered frame's result
    (a stable sort is a no-op on data that is already in subgroup order), and
    sigma_hat must match the stable value exactly. Switching the engine back to
    an unstable `kind` fails both.
    """
    demo_csv = Path(__file__).resolve().parents[1] / "data" / "demo_composites_aerospace.csv"
    frame = pd.read_csv(demo_csv)
    sub = frame[frame["stream"] == "ply_misalignment"]
    assert sub["subgroup"].is_monotonic_increasing, "fixture must already be in subgroup order"
    assert len(sub) > sub["subgroup"].nunique(), "fixture must contain tied subgroups"

    sigma_hat, signals = assess_stability(sub, "I-MR")
    assert sigma_hat == pytest.approx(0.24489039329464862, rel=1e-12)
    assert len(signals) == 19

    # Sorting an already-sorted frame must be a no-op, so re-sorting stably
    # changes nothing. An unstable sort inside the engine breaks this.
    resorted = sub.sort_values("subgroup", kind="stable")
    assert assess_stability(resorted, "I-MR") == (sigma_hat, signals)


def test_demo_stream_verdicts_match_the_recorded_baseline():
    # The engine does not derive the chart type, so this map is the only thing
    # tying a demo stream to its chart. Charting hole_diameter as I-MR (a lost
    # map entry) gives 5 signals instead of 0; ply_thickness as I-MR gives 0
    # instead of 1. Golden baseline for the A09 move — a change here means a
    # verdict flipped, not that the number needs updating.
    #
    # Reads the COMMITTED demo CSV, deliberately. generate_demo_dataset() is
    # fully reproducible on every call, but the committed CSV is tracked
    # in git, is byte-identical everywhere, and is what the app actually loads.
    #
    # ply_misalignment is 19, not 20. 20 was the WRONG answer, produced by the
    # unstable default sort in assess_stability's I-MR branch reordering tied
    # subgroup rows (see test_imr_sort_is_stable_across_tied_subgroups below).
    # Fixing that sort is what moved this number; the verdict did not drift.
    from spc_app.pages.process_capability import STREAM_CHART_TYPES

    demo_csv = Path(__file__).resolve().parents[1] / "data" / "demo_composites_aerospace.csv"
    assert demo_csv.exists(), f"committed demo dataset missing: {demo_csv}"
    frame = pd.read_csv(demo_csv)
    counts = {
        stream: len(
            assess_stability(
                frame[frame["stream"] == stream], STREAM_CHART_TYPES.get(stream, "I-MR")
            )[1]
        )
        for stream in sorted(frame["stream"].unique())
    }
    assert counts == {
        "autoclave_temp": 3,
        "hole_diameter": 0,
        "panel_defects": 0,
        "ply_misalignment": 19,
        "ply_thickness": 1,
        "reject_proportion": 0,
        "surface_defects": 0,
    }
