"""Tests for the Control Plan -> SPC config derivation (pure module, no Streamlit)."""

import pandas as pd
import pytest

from spc_app.control_plan_config import (
    _VALID_CHART_KEYS,
    PLAN_STATE_KEY,
    chart_type_index,
    config_for,
    plan_characteristics,
)
from spc_app.pages.control_charts import CHART_OPTIONS

BASE_ROW = {
    "characteristic": "Ply thickness",
    "lsl": 0.10,
    "usl": 0.20,
    "target": 0.15,
    "sample_size": 5,
    "frequency": "hourly",
    "recommended_chart": "Xbar-R",
}


def _plan(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_plan_state_key_contract():
    # Guards the cross-app string contract with
    # controlplan_app.pages.control_plan._PLAN_STATE_KEY.
    assert PLAN_STATE_KEY == "_controlplan_plan_df"


@pytest.mark.parametrize("chart", ["Xbar-R", "Xbar-S", "I-MR", "p", "c", "u"])
def test_config_for_recommended_chart_pass_through(chart):
    row = {**BASE_ROW, "recommended_chart": chart}
    plan_df = _plan([row])
    cfg = config_for(plan_df, "Ply thickness")
    assert cfg.chart_key == chart


@pytest.mark.parametrize(
    "recommended_chart",
    [None, "", "   ", float("nan"), "Bogus-Chart"],
)
def test_config_for_chart_key_none_cases(recommended_chart):
    row = {**BASE_ROW, "recommended_chart": recommended_chart}
    plan_df = _plan([row])
    cfg = config_for(plan_df, "Ply thickness")
    assert cfg.chart_key is None


def test_config_for_tolerance_and_sample_pass_through():
    plan_df = _plan([BASE_ROW])
    cfg = config_for(plan_df, "Ply thickness")
    assert cfg.lsl == 0.10
    assert cfg.usl == 0.20
    assert cfg.target == 0.15
    assert cfg.sample_size == 5
    assert cfg.frequency == "hourly"


def test_config_for_nan_cells_normalise_to_none():
    row = {
        **BASE_ROW,
        "lsl": float("nan"),
        "usl": float("nan"),
        "target": float("nan"),
        "sample_size": float("nan"),
        "frequency": float("nan"),
    }
    plan_df = _plan([row])
    cfg = config_for(plan_df, "Ply thickness")
    assert cfg.lsl is None
    assert cfg.usl is None
    assert cfg.target is None
    assert cfg.sample_size is None
    assert cfg.frequency is None


def test_config_for_blank_string_cells_normalise_to_none():
    row = {**BASE_ROW, "frequency": "   "}
    plan_df = _plan([row])
    cfg = config_for(plan_df, "Ply thickness")
    assert cfg.frequency is None


def test_config_for_missing_columns_yield_none():
    # No lsl/usl/target/sample_size/frequency/recommended_chart columns at all.
    plan_df = _plan([{"characteristic": "Ply thickness"}])
    cfg = config_for(plan_df, "Ply thickness")
    assert cfg.lsl is None
    assert cfg.usl is None
    assert cfg.target is None
    assert cfg.sample_size is None
    assert cfg.frequency is None
    assert cfg.chart_key is None


def test_config_for_unknown_characteristic_raises():
    plan_df = _plan([BASE_ROW])
    with pytest.raises(KeyError):
        config_for(plan_df, "Does not exist")


def test_plan_characteristics_order_preserved():
    plan_df = _plan(
        [
            {**BASE_ROW, "characteristic": "Ply thickness"},
            {**BASE_ROW, "characteristic": "Hole diameter"},
            {**BASE_ROW, "characteristic": "Autoclave temp"},
        ]
    )
    assert plan_characteristics(plan_df) == [
        "Ply thickness",
        "Hole diameter",
        "Autoclave temp",
    ]


def test_plan_characteristics_empty_plan():
    assert plan_characteristics(pd.DataFrame()) == []


def test_plan_characteristics_no_characteristic_column():
    plan_df = pd.DataFrame([{"lsl": 0.1, "usl": 0.2}])
    assert plan_characteristics(plan_df) == []


def test_chart_type_index_valid_key():
    options = list(CHART_OPTIONS)
    assert chart_type_index("I-MR", options) == options.index("I-MR")


def test_chart_type_index_none_defaults_to_zero():
    assert chart_type_index(None, list(CHART_OPTIONS)) == 0


def test_chart_type_index_key_not_in_options_defaults_to_zero():
    assert chart_type_index("Xbar-R", ["p", "c", "u"]) == 0


def test_chart_options_keys_match_valid_chart_keys_as_a_set():
    # Belt-and-suspenders: the two 6-key chart-key sets stay in sync (order need
    # not match -- chart_type_index resolves against whatever list it is given).
    assert set(CHART_OPTIONS) == set(_VALID_CHART_KEYS)
