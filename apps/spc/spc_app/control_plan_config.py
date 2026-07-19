"""Derive an SPC Control Charts view config from a loaded Control Plan row.

Config-only wiring (OQ#1): a Control Plan characteristic presets the chart type
and surfaces its spec/tolerance + sample size/frequency; the user still picks the
matching data stream. `recommended_chart` is the already-derived output of
`controlplan_app.connector.recommend_chart` (the AIAG rule table) — this module
is a pass-through, it does not re-derive the rule.

Pure functions only: no Streamlit import, no `controlplan_app` import (the
standalone SPC app never has `controlplan_app` on `sys.path` — see
`apps/spc/CLAUDE.md` / the shell's `app.py:43` sys.path wiring).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

#: Session-state key holding the current (possibly edited) Control Plan
#: DataFrame, set by `controlplan_app.pages.control_plan`.
# ponytail: string contract mirrored from
# controlplan_app.pages.control_plan._PLAN_STATE_KEY — duplicated (not imported)
# so the standalone SPC app, which never has controlplan_app on sys.path, still
# imports cleanly.
PLAN_STATE_KEY = "_controlplan_plan_df"

#: The chart keys the SPC Control Charts page can actually render
#: (`CHART_OPTIONS` in `spc_app/pages/control_charts.py`) — identical to
#: `controlplan_app.schema.SPCChart`.
_VALID_CHART_KEYS = ("Xbar-R", "Xbar-S", "I-MR", "p", "c", "u")


@dataclass(frozen=True)
class SPCViewConfig:
    """SPC Control Charts config derived from one Control Plan characteristic."""

    characteristic: str
    chart_key: str | None
    lsl: float | None
    usl: float | None
    target: float | None
    sample_size: int | None
    frequency: str | None


def plan_characteristics(plan_df: pd.DataFrame) -> list[str]:
    """Characteristic names available to pick from a loaded Control Plan.

    Order preserved (plan row order). Empty/missing ``characteristic`` column
    yields an empty list.
    """
    if plan_df.empty or "characteristic" not in plan_df.columns:
        return []
    return [str(value) for value in plan_df["characteristic"].tolist()]


def _clean(value: object) -> object:
    """Normalise a plan cell to ``None``, else return it unchanged."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _chart_key(value: object) -> str | None:
    value = _clean(value)
    if value not in _VALID_CHART_KEYS:
        return None
    return str(value)


def config_for(plan_df: pd.DataFrame, characteristic: str) -> SPCViewConfig:
    """Derive the SPC view config for one characteristic row.

    Raises ``KeyError`` if ``characteristic`` is not a row in the plan (a guard,
    not a UI path — callers pass only names from :func:`plan_characteristics`).
    """
    matches = plan_df[plan_df["characteristic"] == characteristic]
    if matches.empty:
        raise KeyError(f"characteristic not found in plan: {characteristic!r}")
    row = matches.iloc[0]

    def cell(column: str) -> Any:
        return _clean(row[column]) if column in row else None

    lsl, usl, target = cell("lsl"), cell("usl"), cell("target")
    sample_size, frequency = cell("sample_size"), cell("frequency")
    return SPCViewConfig(
        characteristic=characteristic,
        chart_key=_chart_key(cell("recommended_chart")),
        lsl=float(lsl) if lsl is not None else None,
        usl=float(usl) if usl is not None else None,
        target=float(target) if target is not None else None,
        sample_size=int(sample_size) if sample_size is not None else None,
        frequency=str(frequency) if frequency is not None else None,
    )


def chart_type_index(chart_key: str | None, chart_options: list[str]) -> int:
    """Selectbox index for the Chart Type control, preselecting ``chart_key``.

    ``None`` (manual fallback, OQ#2) or a key absent from ``chart_options``
    both default to ``0``.
    """
    if chart_key is None or chart_key not in chart_options:
        return 0
    return chart_options.index(chart_key)
