"""Shared SPC primitives for Quality Platform apps.

`constants` holds the AIAG SPC chart constants (4th Ed. control chart factors,
Phase-I baseline minimums, EWMA/CUSUM defaults, non-normal capability settings)
plus `SPCChart` — the platform's one chart vocabulary. `rule_detection` holds the
Western Electric / Nelson run-rule detectors and the Shewhart chart set they are
valid on. `utils` holds `subgroup_rows`.

Promoted out of `spc_app.spc_engine` (audit A12, #205) so SECOM, the Control Plan
app and the future API import *downward* into `quality_core` instead of sideways
into another app. `spc_app.spc_engine.*` now re-exports these, so existing SPC
callers are unchanged — mirroring how `fmea_app.ap_engine` re-exports
`quality_core.scoring`.

Every constant, threshold and citation comment moved verbatim: nothing here is a
new or re-derived standards rule (see `apps/spc/docs/ASSUMPTIONS_LOG.md`).
"""

from quality_core.spc.constants import (
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    BOXCOX_LAMBDA_CANDIDATES,
    CAPABILITY_ALPHA,
    CUSUM_DEFAULT_H,
    CUSUM_DEFAULT_K,
    CUSUM_FIR_FRACTION,
    EWMA_DEFAULT_L,
    EWMA_DEFAULT_LAMBDA,
    EWMA_L_BY_LAMBDA,
    IMR_D2,
    IMR_D4,
    IMR_E2,
    MIN_BASELINE_INDIVIDUALS,
    MIN_BASELINE_SUBGROUPS,
    NONNORMAL_LOWER_PCTL,
    NONNORMAL_UPPER_PCTL,
    PERCENTILE_FIT_CANDIDATES,
    XBAR_R_CONSTANTS,
    XBAR_S_CONSTANTS,
    SPCChart,
)
from quality_core.spc.rule_detection import (
    NELSON_LABELS,
    SHEWHART_CHART_TYPES,
    WE_LABELS,
    detect_nelson_violations,
    detect_violations,
    detect_we_violations,
)
from quality_core.spc.utils import subgroup_rows

__all__ = [
    "BOOTSTRAP_RESAMPLES",
    "BOOTSTRAP_SEED",
    "BOXCOX_LAMBDA_CANDIDATES",
    "CAPABILITY_ALPHA",
    "CUSUM_DEFAULT_H",
    "CUSUM_DEFAULT_K",
    "CUSUM_FIR_FRACTION",
    "EWMA_DEFAULT_L",
    "EWMA_DEFAULT_LAMBDA",
    "EWMA_L_BY_LAMBDA",
    "IMR_D2",
    "IMR_D4",
    "IMR_E2",
    "MIN_BASELINE_INDIVIDUALS",
    "MIN_BASELINE_SUBGROUPS",
    "NONNORMAL_LOWER_PCTL",
    "NONNORMAL_UPPER_PCTL",
    "PERCENTILE_FIT_CANDIDATES",
    "SPCChart",
    "XBAR_R_CONSTANTS",
    "XBAR_S_CONSTANTS",
    "NELSON_LABELS",
    "SHEWHART_CHART_TYPES",
    "WE_LABELS",
    "detect_nelson_violations",
    "detect_violations",
    "detect_we_violations",
    "subgroup_rows",
]
