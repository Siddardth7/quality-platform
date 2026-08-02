"""Tests for `quality_core.spc.constants` — the promoted AIAG constant tables and
`SPCChart`, the platform's single chart vocabulary (audit A12, #205 PR 1).

Why this file exists: `constants.py` is pure module-level assignment, so it reaches
100% line+branch coverage the moment ANY test imports `quality_core.spc` — the
`--cov=quality_core.spc` gate can therefore not tell "tested" from "imported".
These assertions are the actual test of its content (spec §4.4).

Three properties are pinned:

1. **Single source.** `spc_app.control_plan_config._VALID_CHART_KEYS` is *derived*
   from `SPCChart` via `typing.get_args`, not re-typed, and
   `controlplan_app.schema.SPCChart` is the same Literal.
2. **Constant tables intact.** Spot-checked against AIAG SPC Ref. Manual 4th Ed.
   as recorded in `apps/spc/docs/ASSUMPTIONS_LOG.md` RULES 1-3.
3. **`SHEWHART_CHART_TYPES` is NOT derived from `SPCChart`** (SME decision, #205):
   deriving it would silently validate WE/Nelson run-rules on EWMA/CUSUM.
"""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path
from typing import get_args

import pytest
from quality_core.spc import rule_detection
from quality_core.spc.constants import (
    IMR_D2,
    IMR_D4,
    IMR_E2,
    XBAR_R_CONSTANTS,
    XBAR_S_CONSTANTS,
    SPCChart,
)
from quality_core.spc.rule_detection import SHEWHART_CHART_TYPES, detect_we_violations
from quality_core.spc.utils import subgroup_rows

from spc_app import control_plan_config
from spc_app.spc_engine import constants as shim_constants
from spc_app.spc_engine import rule_detection as shim_rule_detection
from spc_app.spc_engine import utils as shim_utils

# `controlplan-app` is `package = false` (apps/controlplan/pyproject.toml:21), so it is
# not installed; its own conftest puts it on sys.path, and this suite runs alone under
# the Core SPC gate. `controlplan_app.schema` imports only quality_core/pandas/pydantic.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "apps" / "controlplan"))

from controlplan_app import schema as controlplan_schema  # noqa: E402

#: The chart vocabulary as it stands today. Written out longhand on purpose: this is
#: the value every other copy in the platform is checked against.
EXPECTED_CHART_KEYS = ("Xbar-R", "Xbar-S", "I-MR", "p", "c", "u")


# ---------------------------------------------------------------------------
# 1. SPCChart is the single source of the chart vocabulary.
# ---------------------------------------------------------------------------


def test_spcchart_members_are_the_documented_vocabulary():
    assert get_args(SPCChart) == EXPECTED_CHART_KEYS


def test_control_plan_config_derives_its_keys_instead_of_retyping_them():
    """`_VALID_CHART_KEYS` must BE `get_args(SPCChart)`, not merely equal it.

    `typing.get_args` on a Literal returns the alias's cached `__args__` tuple — the
    same object on every call — so an `is` check passes only while the derivation is
    live. Re-hardcoding the tuple in `control_plan_config` produces an equal but
    distinct object and fails here, which value equality alone would not catch.
    """
    assert control_plan_config._VALID_CHART_KEYS is get_args(SPCChart)
    assert control_plan_config._VALID_CHART_KEYS == EXPECTED_CHART_KEYS


def test_controlplan_schema_reexports_the_core_literal():
    """The Control Plan app's `SPCChart` is the core one, and stays in `__all__`.

    Note the limit of the `is` check: `typing` caches `Literal[...]`, so an identical
    re-declaration would also be this object. The value assertion below is what
    catches a *diverging* re-declaration; `connector.py` imports the name from here,
    so `__all__` membership is the part that must not regress.
    """
    assert controlplan_schema.SPCChart is SPCChart
    assert set(get_args(controlplan_schema.SPCChart)) == set(get_args(SPCChart))
    assert "SPCChart" in controlplan_schema.__all__


def test_all_three_chart_vocabularies_agree():
    assert (
        set(get_args(SPCChart))
        == set(control_plan_config._VALID_CHART_KEYS)
        == set(get_args(controlplan_schema.SPCChart))
    )


# ---------------------------------------------------------------------------
# 2. AIAG constant tables (ASSUMPTIONS_LOG RULES 1-3).
# ---------------------------------------------------------------------------


def test_imr_constants_match_assumptions_log_rule_3():
    # RULE 3 quotes these three values verbatim: E2 = 2.660, D4 = 3.267, d2 = 1.128.
    assert IMR_E2 == 2.660
    assert IMR_D4 == 3.267
    assert IMR_D2 == 1.128
    # RULE 3 also states the derivation `E2 = 3 / d2(2)`; check the two agree.
    assert round(3.0 / IMR_D2, 3) == IMR_E2


def test_xbar_r_constants_match_the_aiag_table():
    # RULE 1: AIAG constants keyed by subgroup size n = 2..10.
    assert sorted(XBAR_R_CONSTANTS) == list(range(2, 11))
    assert XBAR_R_CONSTANTS[2] == {"A2": 1.880, "D3": 0.000, "D4": 3.267, "d2": 1.128}
    assert XBAR_R_CONSTANTS[5] == {"A2": 0.577, "D3": 0.000, "D4": 2.114, "d2": 2.326}
    assert XBAR_R_CONSTANTS[10] == {"A2": 0.308, "D3": 0.223, "D4": 1.777, "d2": 3.078}
    # n = 2 is the moving-range case, so the I-MR pair must equal the table's row 2.
    assert XBAR_R_CONSTANTS[2]["d2"] == IMR_D2
    assert XBAR_R_CONSTANTS[2]["D4"] == IMR_D4
    # Table shape: D3 is zero (no lower R limit) only up to n = 6.
    assert [n for n, row in XBAR_R_CONSTANTS.items() if row["D3"] == 0.0] == [2, 3, 4, 5, 6]
    # A2 and D4 shrink monotonically with n; d2 grows.
    assert [row["A2"] for row in XBAR_R_CONSTANTS.values()] == sorted(
        (row["A2"] for row in XBAR_R_CONSTANTS.values()), reverse=True
    )
    assert [row["d2"] for row in XBAR_R_CONSTANTS.values()] == sorted(
        row["d2"] for row in XBAR_R_CONSTANTS.values()
    )


def test_xbar_s_constants_match_the_aiag_table():
    # RULE 2: AIAG X-bar/S constants keyed by subgroup size n = 2..12.
    assert sorted(XBAR_S_CONSTANTS) == list(range(2, 13))
    assert XBAR_S_CONSTANTS[2] == {"A3": 2.659, "B3": 0.000, "B4": 3.267, "c4": 0.7979}
    assert XBAR_S_CONSTANTS[5] == {"A3": 1.427, "B3": 0.000, "B4": 2.089, "c4": 0.9400}
    assert XBAR_S_CONSTANTS[12] == {"A3": 0.886, "B3": 0.354, "B4": 1.646, "c4": 0.9776}
    # c4 is the unbiasing constant: strictly increasing towards 1, never above it.
    c4_values = [row["c4"] for row in XBAR_S_CONSTANTS.values()]
    assert c4_values == sorted(c4_values)
    assert max(c4_values) < 1.0
    # B3 is zero (no lower S limit) only up to n = 5.
    assert [n for n, row in XBAR_S_CONSTANTS.items() if row["B3"] == 0.0] == [2, 3, 4, 5]


def test_subgroup_sizes_outside_the_aiag_tables_are_absent():
    """Failure case: the tables stop where AIAG's do — no silent extrapolation.

    Callers must fail loudly on an out-of-table subgroup size rather than receive a
    guessed constant.
    """
    with pytest.raises(KeyError):
        XBAR_R_CONSTANTS[11]
    with pytest.raises(KeyError):
        XBAR_S_CONSTANTS[13]


# ---------------------------------------------------------------------------
# 3. SHEWHART_CHART_TYPES is deliberately NOT derived from SPCChart (SME, #205).
# ---------------------------------------------------------------------------


def test_shewhart_chart_types_is_declared_independently_of_spcchart():
    """`SHEWHART_CHART_TYPES` must be a literal frozenset, never `get_args(SPCChart)`.

    It answers "charts where WE/Nelson run-rules are statistically valid", not
    "charts we can render". Deriving it would make run-rules fire on EWMA/CUSUM the
    day such a key joins `SPCChart` — the exact defect `detect_violations` prevents.
    The equality asserted in the *next* test is coincidence, and this test is what
    stops a future reader from "de-duplicating" it.
    """
    module = ast.parse(inspect.getsource(rule_detection))
    assignments = [
        node
        for node in module.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "SHEWHART_CHART_TYPES"
    ]
    assert len(assignments) == 1
    value = assignments[0].value
    assert value is not None
    # Only names allowed in the expression: the `frozenset` builtin itself. Any
    # reference to SPCChart / get_args / constants would show up here.
    referenced = {node.id for node in ast.walk(value) if isinstance(node, ast.Name)}
    assert referenced == {"frozenset"}
    literal_members = {
        node.value for node in ast.walk(value) if isinstance(node, ast.Constant)
    }
    assert literal_members == set(EXPECTED_CHART_KEYS)


def test_shewhart_chart_types_equals_the_chart_vocabulary_today():
    # Coincidence, not derivation — see the test above. Recorded so a divergence is a
    # deliberate, reviewed change rather than a silent one.
    assert SHEWHART_CHART_TYPES == frozenset(get_args(SPCChart))
    assert SHEWHART_CHART_TYPES is not get_args(SPCChart)


# ---------------------------------------------------------------------------
# 4. The spc_app shims re-export, they do not re-declare (the #205 contract).
# ---------------------------------------------------------------------------


def test_spc_engine_shims_are_the_same_objects_as_the_core():
    """Identity, not equality: a shadow copy in `spc_engine` would still be equal.

    This is the assertion that keeps the duplication #205 removed from creeping back.
    """
    assert shim_constants.IMR_E2 is IMR_E2
    assert shim_constants.IMR_D4 is IMR_D4
    assert shim_constants.IMR_D2 is IMR_D2
    assert shim_constants.XBAR_R_CONSTANTS is XBAR_R_CONSTANTS
    assert shim_constants.XBAR_S_CONSTANTS is XBAR_S_CONSTANTS
    assert shim_constants.SPCChart is SPCChart
    assert shim_rule_detection.detect_we_violations is detect_we_violations
    assert shim_rule_detection.SHEWHART_CHART_TYPES is SHEWHART_CHART_TYPES
    assert shim_utils.subgroup_rows is subgroup_rows
