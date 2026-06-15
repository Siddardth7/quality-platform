"""Demo dataset generation for SPC dashboard scenarios."""

from __future__ import annotations

import numpy as np
import pandas as pd

_RNG = np.random.default_rng(42)


def generate_demo_dataset() -> pd.DataFrame:
    """Return a deterministic demo dataset covering five SPC process streams."""
    frames = [
        _ply_thickness(),
        _autoclave_temperature(),
        _hole_diameter(),
        _reject_proportion(),
        _surface_defects(),
    ]
    return pd.concat(frames, ignore_index=True)


def _ply_thickness() -> pd.DataFrame:
    rows = []
    for subgroup in range(1, 26):
        drift = 0.0012 * max(0, subgroup - 17) / 8
        values = _RNG.normal(loc=0.250 + drift, scale=0.0015, size=5)
        for value in values:
            rows.append(
                {
                    "stream": "ply_thickness",
                    "parameter": "Ply Thickness",
                    "chart_type": "xbar_r",
                    "subgroup": subgroup,
                    "value": round(float(value), 6),
                    "sample_size": 5,
                    "lsl": 0.245,
                    "usl": 0.255,
                }
            )
    return pd.DataFrame(rows)


def _autoclave_temperature() -> pd.DataFrame:
    values = _RNG.normal(loc=180.0, scale=1.8, size=30)
    return pd.DataFrame(
        {
            "stream": "autoclave_temp",
            "parameter": "Autoclave Cure Temperature",
            "chart_type": "imr",
            "subgroup": np.arange(1, 31),
            "value": np.round(values, 4),
            "sample_size": 1,
            "lsl": 175.0,
            "usl": 185.0,
        }
    )


def _hole_diameter() -> pd.DataFrame:
    rows = []
    for subgroup in range(1, 21):
        values = _RNG.normal(loc=10.000, scale=0.0042, size=12)
        for value in values:
            rows.append(
                {
                    "stream": "hole_diameter",
                    "parameter": "Hole Diameter",
                    "chart_type": "xbar_s",
                    "subgroup": subgroup,
                    "value": round(float(value), 6),
                    "sample_size": 12,
                    "lsl": 9.985,
                    "usl": 10.015,
                }
            )
    return pd.DataFrame(rows)


def _reject_proportion() -> pd.DataFrame:
    rows = []
    for subgroup in range(1, 26):
        sample_size = int(_RNG.integers(80, 121))
        base_rate = 0.025 + 0.003 * np.sin(subgroup / 4)
        defective_count = int(_RNG.binomial(sample_size, base_rate))
        rows.append(
            {
                "stream": "reject_proportion",
                "parameter": "Visual Inspection Reject Rate",
                "chart_type": "p",
                "subgroup": subgroup,
                "value": defective_count,
                "sample_size": sample_size,
                "lsl": np.nan,
                "usl": np.nan,
            }
        )
    return pd.DataFrame(rows)


def _surface_defects() -> pd.DataFrame:
    rows = []
    for subgroup in range(1, 21):
        sample_size = round(float(_RNG.uniform(0.8, 1.6)), 2)
        defects_per_unit = 1.2 + 0.15 * np.cos(subgroup / 5)
        defect_count = int(_RNG.poisson(defects_per_unit * sample_size))
        rows.append(
            {
                "stream": "surface_defects",
                "parameter": "Surface Defects per Unit Area",
                "chart_type": "u",
                "subgroup": subgroup,
                "value": defect_count,
                "sample_size": sample_size,
                "lsl": np.nan,
                "usl": 3.0,
            }
        )
    return pd.DataFrame(rows)
