"""Tests for the Process Capability stability gate."""

import pandas as pd

from spc_app.pages.process_capability import assess_control_chart


def _imr_frame(values: list[float], stream: str = "autoclave_temp") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "stream": stream,
            "subgroup": range(1, len(values) + 1),
            "value": values,
        }
    )


def _subgrouped_frame(subgroups: list[list[float]], stream: str) -> pd.DataFrame:
    rows = []
    for index, group in enumerate(subgroups, start=1):
        for value in group:
            rows.append({"stream": stream, "subgroup": index, "value": value})
    return pd.DataFrame(rows)


def test_stable_individuals_series_has_no_signals():
    # Small, centered oscillation well within +/-1 sigma -> in control.
    values = [1.0, 2.0] * 5
    sigma_hat, signals = assess_control_chart("autoclave_temp", _imr_frame(values))
    assert sigma_hat > 0
    assert signals == []


def test_out_of_control_series_is_flagged():
    # A gross outlier trips Western Electric Rule 1 (point beyond +/-3 sigma).
    values = [1.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 2.0, 1.0, 20.0]
    _, signals = assess_control_chart("autoclave_temp", _imr_frame(values))
    assert len(signals) >= 1


def test_xbar_r_path_returns_sigma_and_signals():
    subgroups = [
        [10.0, 11.0, 12.0, 13.0, 14.0],
        [11.0, 12.0, 13.0, 14.0, 15.0],
        [9.0, 10.0, 11.0, 12.0, 13.0],
    ]
    sigma_hat, signals = assess_control_chart(
        "ply_thickness", _subgrouped_frame(subgroups, "ply_thickness")
    )
    assert sigma_hat > 0
    assert isinstance(signals, list)


def test_xbar_s_path_returns_sigma_and_signals():
    subgroups = [list(range(1, 13)), list(range(2, 14)), list(range(3, 15))]
    sigma_hat, signals = assess_control_chart(
        "hole_diameter", _subgrouped_frame([[float(v) for v in g] for g in subgroups], "hole_diameter")
    )
    assert sigma_hat > 0
    assert isinstance(signals, list)
