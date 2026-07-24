"""
secom_app/capability.py
SECOM signal -> existing SPC capability engine (W09-3, #67).

Wires a SECOM sensor column into the platform's already-tested
`compute_capability` (`apps/spc/spc_app/spc_engine/capability.py`, reused
read-only — see `apps/secom/CLAUDE.md` sys.path shim in `conftest.py`). This
module does NOT reimplement Cp/Cpk/Pp/Ppk math; it only adapts the W09-2
control chart result into the shape the engine expects, and couples the
result to the W09-2 stability gate.

SME resolutions (`.pipeline/spec.md`, locked 2026-07-23), each labelled:

- **OQ-A (SME-set, no-fabrication option):** SECOM ships no USL/LSL. Limits
  are caller-supplied per signal — `capability_for_signal()` takes `lsl`/`usl`
  as explicit arguments (either may be `None` for a one-sided characteristic).
  This module never derives, defaults, or fabricates a limit. A later UI/
  limits-source issue is responsible for supplying them.
- **OQ-B (SME-set, compute + flag):** on an unstable process (non-empty
  `chart.violations`), the indices are still computed but returned with
  `stable=False` and a populated `stability_warning` — mirrors
  `apps/spc/spc_app/pages/process_capability.py:156`. Indices are never
  hard-suppressed (returned `None`) for instability.

**Batch helper deferred:** a `capability_for_selection` needs a per-signal
`{signal: (lsl, usl)}` limits map, which only exists once a limits source is
decided; not built here (ponytail — add when a UI/limits source lands).

#65/#66 RED LINE update: SECOM still ships no USL/LSL. This module lifts the
"never call `compute_capability`" red line *only* via caller-supplied limits
(OQ-A) — it still never fabricates a limit. `charts.py` remains untouched and
pure control-chart.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from secom_app.charts import Ruleset, SignalControlChart, control_chart_for_signal
from spc_app.spc_engine.capability import compute_capability

__all__ = ["SignalCapability", "capability_for_signal"]


@dataclass(frozen=True)
class SignalCapability:
    signal: str
    chart: SignalControlChart  # reused W09-2 result — carries .violations, .imr, autocorr
    capability: dict[str, Any]  # compute_capability output: cp/cpk/pp/ppk/mean/sigma_hat/sigma_overall
    lsl: float | None
    usl: float | None
    stable: bool  # False iff chart.violations is non-empty
    stability_warning: str | None  # populated iff not stable; None when stable


def capability_for_signal(
    features: pd.DataFrame,
    signal: str,
    lsl: float | None,
    usl: float | None,
    ruleset: Ruleset = "nelson",
) -> SignalCapability:
    """Cp/Cpk/Pp/Ppk for one SECOM sensor column against caller-supplied limits.

    Raises ValueError if both `lsl` and `usl` are None (no capability without
    a limit), if both are given with `lsl >= usl`, or via
    `control_chart_for_signal`/`compute_capability` for signal/data errors
    (unknown signal, <2 present values, constant series)."""
    if lsl is None and usl is None:
        raise ValueError("At least one of lsl/usl must be given to compute capability.")
    if lsl is not None and usl is not None and lsl >= usl:
        raise ValueError(f"lsl ({lsl}) must be less than usl ({usl}).")

    chart = control_chart_for_signal(features, signal, ruleset=ruleset)
    capability = compute_capability(
        chart.imr["values"],
        lsl=lsl,
        usl=usl,
        sigma_hat=chart.imr["sigma_hat"],
    )

    stable = not chart.violations
    stability_warning = (
        None
        if stable
        else (
            f"Process is not in statistical control — {len(chart.violations)} "
            f"{ruleset} signal(s) detected on the control chart. Capability indices "
            "(Cp/Cpk/Pp/Ppk) are not a valid capability claim until the process is "
            "stabilized; treat these values as indicative only."
        )
    )

    return SignalCapability(
        signal=signal,
        chart=chart,
        capability=capability,
        lsl=lsl,
        usl=usl,
        stable=stable,
        stability_warning=stability_warning,
    )
