"""
tests/test_spc_engine_shims.py
`spc_app.spc_engine.*` re-exports the promoted core primitives — it does not re-declare
them (audit A12, #205).

These live in the SPC app suite, not the core suite, on purpose: they assert something
about `spc_app`, and the core's tests must not import an app. #205 exists to make
imports point downward, so a core test reaching up into `spc_app` would contradict the
change it is verifying.
"""

from __future__ import annotations

from typing import get_args

from quality_core.spc.capability import (
    CapabilityStudy,
    compute_capability,
    compute_capability_study,
    normality_test,
)
from quality_core.spc.constants import (
    IMR_D2,
    IMR_D4,
    IMR_E2,
    XBAR_R_CONSTANTS,
    XBAR_S_CONSTANTS,
    SPCChart,
)
from quality_core.spc.control_charts import (
    ImrResult,
    compute_cusum,
    compute_ewma,
    compute_imr,
    compute_xbar_r,
    imr_limits,
)
from quality_core.spc.phase import FrozenLimits, freeze_imr
from quality_core.spc.rule_detection import SHEWHART_CHART_TYPES, detect_we_violations
from quality_core.spc.stability import assess_stability, stability_fields
from quality_core.spc.utils import subgroup_rows

from spc_app import control_plan_config
from spc_app.spc_engine import capability as shim_capability
from spc_app.spc_engine import constants as shim_constants
from spc_app.spc_engine import control_charts as shim_control_charts
from spc_app.spc_engine import phase as shim_phase
from spc_app.spc_engine import rule_detection as shim_rule_detection
from spc_app.spc_engine import stability as shim_stability
from spc_app.spc_engine import utils as shim_utils


def test_spc_engine_shims_are_the_same_objects_as_the_core():
    """Identity, not equality: a shadow copy in `spc_engine` would still be equal.

    This is the assertion that keeps the duplication #205 removed from creeping back.
    A re-declared constant with the correct value passes an `==` check and fails here.
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


def test_chart_phase_and_stability_shims_are_the_same_objects_as_the_core():
    """The PR-2 shims (#205): `is`, never `==` — a wrapper `def` would pass equality.

    Importing the three shim modules here is also what guarantees they are executed
    during the SPC coverage gate.
    """
    assert shim_control_charts.compute_imr is compute_imr
    assert shim_control_charts.compute_xbar_r is compute_xbar_r
    assert shim_control_charts.compute_ewma is compute_ewma
    assert shim_control_charts.compute_cusum is compute_cusum
    assert shim_control_charts.imr_limits is imr_limits
    assert shim_control_charts.ImrResult is ImrResult
    assert shim_phase.freeze_imr is freeze_imr
    assert shim_phase.FrozenLimits is FrozenLimits
    assert shim_stability.assess_stability is assess_stability
    assert shim_stability.stability_fields is stability_fields


def test_capability_shim_is_the_same_object_as_the_core():
    """The PR-3 shim (#205): `is`, never `==` — a re-declared engine would pass equality.

    Importing the shim module here is also what executes it during the SPC coverage
    gate, so a shim added and left unimported fails loudly.
    """
    assert shim_capability.compute_capability is compute_capability
    assert shim_capability.compute_capability_study is compute_capability_study
    assert shim_capability.normality_test is normality_test
    assert shim_capability.CapabilityStudy is CapabilityStudy


def test_control_plan_config_derives_its_keys_instead_of_retyping_them():
    """`_VALID_CHART_KEYS` must BE `get_args(SPCChart)`, not merely equal it.

    `typing.get_args` on a Literal returns the alias's cached `__args__` tuple — the
    same object on every call — so an `is` check passes only while the derivation is
    live. Re-hardcoding the tuple in `control_plan_config` produces an equal but
    distinct object and fails here, which value equality alone would not catch.
    """
    assert control_plan_config._VALID_CHART_KEYS is get_args(SPCChart)
    assert control_plan_config._VALID_CHART_KEYS == ("Xbar-R", "Xbar-S", "I-MR", "p", "c", "u")
