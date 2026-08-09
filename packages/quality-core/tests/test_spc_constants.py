"""Tests for `quality_core.spc.constants` — the promoted AIAG constant tables and
`SPCChart`, the platform's single chart vocabulary (audit A12, #205 PR 1).

Why this file exists: `constants.py` is pure module-level assignment, so it reaches
100% line+branch coverage the moment ANY test imports `quality_core.spc` — the
`--cov=quality_core.spc` gate can therefore not tell "tested" from "imported".
These assertions are the actual test of its content (spec §4.4).

Two properties are pinned here:

1. **Constant tables intact.** Both AIAG tables are asserted *whole*, not spot-checked
   — review of this PR mutated `XBAR_R_CONSTANTS[7]["D3"]` and 410 tests stayed green
   because the sampled rows missed it. Scope limit: `ASSUMPTIONS_LOG` RULES 1-3 cite
   the AIAG SPC Ref. Manual 4th Ed. but do not reproduce the tables, so this detects
   drift from the reviewed set rather than re-deriving from the handbook.
2. **`SHEWHART_CHART_TYPES` is NOT derived from `SPCChart`** (SME decision, #205):
   deriving it would silently validate WE/Nelson run-rules on EWMA/CUSUM.

The single-source assertions live with the code they assert about, NOT here: this
suite must not import an app — #205 exists to make imports point downward, so a core
test reaching up would contradict the change it verifies. See
`apps/spc/tests/test_spc_engine_shims.py` and
`apps/controlplan/tests/test_spc_chart_vocabulary.py`.
"""

from __future__ import annotations

import ast
import inspect
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
from quality_core.spc.rule_detection import SHEWHART_CHART_TYPES

#: The chart vocabulary as it stands today. Written out longhand on purpose: this is
#: the value every other copy in the platform is checked against.
EXPECTED_CHART_KEYS = ("Xbar-R", "Xbar-S", "I-MR", "p", "c", "u")


# ---------------------------------------------------------------------------
# 1. SPCChart is the single source of the chart vocabulary.
# ---------------------------------------------------------------------------


def test_spcchart_members_are_the_documented_vocabulary():
    assert get_args(SPCChart) == EXPECTED_CHART_KEYS


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
    """Every cell, not a spot-check.

    Review of #205 PR 1 mutated `XBAR_R_CONSTANTS[7]["D3"]` to 0.999 and all 356 core
    tests plus all 54 `test_control_charts.py` tests stayed green — the sampled rows
    (2, 5, 10) simply did not include it. This file exists to be the check on these
    tables, so it pins them whole against ASSUMPTIONS_LOG RULE 1. A wrong cell is a
    wrong control limit on every chart built at that subgroup size.
    """
    assert XBAR_R_CONSTANTS == {
        2: {"A2": 1.880, "D3": 0.000, "D4": 3.267, "d2": 1.128},
        3: {"A2": 1.023, "D3": 0.000, "D4": 2.574, "d2": 1.693},
        4: {"A2": 0.729, "D3": 0.000, "D4": 2.282, "d2": 2.059},
        5: {"A2": 0.577, "D3": 0.000, "D4": 2.114, "d2": 2.326},
        6: {"A2": 0.483, "D3": 0.000, "D4": 2.004, "d2": 2.534},
        7: {"A2": 0.419, "D3": 0.076, "D4": 1.924, "d2": 2.704},
        8: {"A2": 0.373, "D3": 0.136, "D4": 1.864, "d2": 2.847},
        9: {"A2": 0.337, "D3": 0.184, "D4": 1.816, "d2": 2.970},
        10: {"A2": 0.308, "D3": 0.223, "D4": 1.777, "d2": 3.078},
    }
    # RULE 1: AIAG constants keyed by subgroup size n = 2..10.
    assert sorted(XBAR_R_CONSTANTS) == list(range(2, 11))
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
    """Every cell, for the same reason as the X-bar/R table above.

    Scope limit, stated plainly: `ASSUMPTIONS_LOG` RULE 2 cites the AIAG SPC Reference
    Manual 4th Ed. as the source but does not reproduce the table, so this pin cannot
    independently re-derive the values — it detects *drift* from the reviewed set, it
    does not re-validate them against the handbook. Re-validation against the manual is
    a separate exercise; changing a cell here should require citing the page.
    """
    assert XBAR_S_CONSTANTS == {
        2: {"A3": 2.659, "B3": 0.000, "B4": 3.267, "c4": 0.7979},
        3: {"A3": 1.954, "B3": 0.000, "B4": 2.568, "c4": 0.8862},
        4: {"A3": 1.628, "B3": 0.000, "B4": 2.266, "c4": 0.9213},
        5: {"A3": 1.427, "B3": 0.000, "B4": 2.089, "c4": 0.9400},
        6: {"A3": 1.287, "B3": 0.030, "B4": 1.970, "c4": 0.9515},
        7: {"A3": 1.182, "B3": 0.118, "B4": 1.882, "c4": 0.9594},
        8: {"A3": 1.099, "B3": 0.185, "B4": 1.815, "c4": 0.9650},
        9: {"A3": 1.032, "B3": 0.239, "B4": 1.761, "c4": 0.9693},
        10: {"A3": 0.975, "B3": 0.284, "B4": 1.716, "c4": 0.9727},
        11: {"A3": 0.927, "B3": 0.321, "B4": 1.679, "c4": 0.9754},
        12: {"A3": 0.886, "B3": 0.354, "B4": 1.646, "c4": 0.9776},
    }
    # RULE 2: AIAG X-bar/S constants keyed by subgroup size n = 2..12.
    assert sorted(XBAR_S_CONSTANTS) == list(range(2, 13))
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


