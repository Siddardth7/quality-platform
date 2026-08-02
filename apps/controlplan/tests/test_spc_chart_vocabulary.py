"""
tests/test_spc_chart_vocabulary.py
`controlplan_app.schema.SPCChart` is the promoted core Literal, re-exported — not a
second declaration (audit A12, #205, PR 1 of 3).

Lives in the Control Plan suite rather than the core suite because it asserts something
about `controlplan_app`. The core's tests must not import an app: #205 exists to make
imports point downward, and a core test reaching up would contradict the change it
verifies. Before this split the assertion sat in `packages/quality-core/tests/` and
needed a hard-coded `sys.path` insert to reach here.

For the same reason this file asserts only the leg it owns — core ↔ `controlplan_app`.
The core ↔ `spc_app` leg is asserted in `apps/spc/tests/test_spc_engine_shims.py`,
where `spc_app` is a first-party import rather than a sideways one. Two one-legged
tests in the right suites beat one three-legged test that has to import both apps.
"""

from __future__ import annotations

from typing import get_args

from controlplan_app import schema as controlplan_schema
from quality_core.spc.constants import SPCChart

EXPECTED_CHART_KEYS = ("Xbar-R", "Xbar-S", "I-MR", "p", "c", "u")


def test_controlplan_schema_reexports_the_core_literal():
    """The Control Plan app's `SPCChart` is the core one, and stays in `__all__`.

    Note the limit of the `is` check: `typing` caches `Literal[...]`, so an identical
    re-declaration elsewhere would also be this object and would pass. The value
    assertion is what catches a *diverging* re-declaration; `connector.py` imports the
    name from here, so `__all__` membership is the part that must not regress.
    """
    assert controlplan_schema.SPCChart is SPCChart
    assert set(get_args(controlplan_schema.SPCChart)) == set(get_args(SPCChart))
    assert "SPCChart" in controlplan_schema.__all__


def test_controlplan_vocabulary_is_the_documented_one():
    """Pins the value itself, so a divergence is visible here and not only upstream."""
    assert get_args(controlplan_schema.SPCChart) == EXPECTED_CHART_KEYS
