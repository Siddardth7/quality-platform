"""Stability gate for capability studies (docs/ASSUMPTIONS_LOG.md RULE 7).

Capability indices presuppose a process in statistical control, so this module
assembles a stream's control chart, runs Western Electric rule detection on it,
and turns the resulting signal list into the `stable` / `stability_note` fields
carried on `CapabilityStudy`.

The engine deliberately does NOT infer the chart type from the data (#191 D3):
I-MR on flattened subgrouped data understates sigma and flips verdicts, and a
2-D auto-derivation raises for subgroup sizes outside 2..10. Chart context is
caller-supplied; a caller with no chart gets `stable=None` ("not assessed"),
never a fabricated `True`.

Promoted out of `spc_app.spc_engine` by audit A12 (#205, PR 2 of 3);
`spc_app.spc_engine.stability` now re-exports it, so existing SPC callers are
unchanged. Moved verbatim apart from import paths — including the `kind="stable"`
justification below (#191).
"""

from __future__ import annotations

from typing import Literal, Mapping, Sequence

import pandas as pd

from quality_core.spc.control_charts import compute_imr, compute_xbar_r, compute_xbar_s
from quality_core.spc.rule_detection import detect_violations
from quality_core.spc.utils import subgroup_rows

ChartType = Literal["Xbar-R", "Xbar-S", "I-MR"]

NOT_ASSESSED_NOTE = (
    "Stability not assessed — no control-chart context was supplied. Capability "
    "indices (Cp/Cpk/Pp/Ppk) presuppose a process in statistical control "
    "(AIAG SPC 4th Ed. Ch. IV; NIST/SEMATECH e-Handbook 6.1.6); treat these "
    "values as indicative only until stability is established."
)


def assess_stability(
    frame: pd.DataFrame,
    chart_type: ChartType = "I-MR",
    *,
    rule_set: str = "Western Electric",
) -> tuple[float, list[dict[str, int | str]]]:
    """Compute within-subgroup sigma_hat and detect Western Electric
    out-of-control signals on the stream's control chart.

    Capability indices are only meaningful on a stable process, so the
    Capability page uses the signal list to gate (warn on) Cpk reporting.
    Returns (sigma_hat, signals); an empty list means in statistical control.

    `frame` must carry `value` and `subgroup` columns. Propagates ValueError /
    KeyError from `subgroup_rows` and `compute_xbar_r` (ragged subgroups,
    subgroup size outside 2..10) — callers wrap it.
    """
    if chart_type == "Xbar-R":
        subgroups = subgroup_rows(frame)
        xr = compute_xbar_r(subgroups)
        points: list[float] = xr["subgroup_means"]
        cl: float = xr["xbarbar"]
        sigma_hat: float = xr["sigma_hat"]
        # The plotted points are subgroup means, so their spread is sigma/sqrt(n).
        sigma_points: float = sigma_hat / (len(subgroups[0]) ** 0.5)
    elif chart_type == "Xbar-S":
        subgroups = subgroup_rows(frame)
        xs = compute_xbar_s(subgroups)
        points = xs["subgroup_means"]
        cl = xs["xbarbar"]
        sigma_hat = xs["sigma_hat"]
        sigma_points = sigma_hat / (len(subgroups[0]) ** 0.5)
    else:
        # kind="stable" is load-bearing, not a style choice. A stream charted as
        # I-MR may still carry several rows per subgroup (ply_misalignment has 5),
        # so sorting by "subgroup" alone is full of ties. pandas' default
        # quicksort is UNSTABLE, so it reorders tied rows differently on different
        # platforms — which permutes the individuals series, changes every moving
        # range, and moves sigma_hat enough to flip the verdict (macOS gave 20
        # signals on ply_misalignment, Linux CI gave 19). A stable sort preserves
        # the frame's own row order within a subgroup, which is the real
        # measurement order and the only defensible reading of the data.
        im = compute_imr(frame.sort_values("subgroup", kind="stable")["value"].tolist())
        points = im["values"]
        cl = im["xbar"]
        sigma_hat = im["sigma_hat"]
        sigma_points = sigma_hat

    # Routed through the gated chokepoint (rule_detection.detect_violations) rather
    # than calling detect_we_violations directly — same behaviour for a Shewhart
    # chart_type (WE runs, sigma<=0 -> []), but every caller now shares one gate.
    signals = detect_violations(chart_type, points, cl=cl, sigma=sigma_points, rule_set=rule_set)
    return sigma_hat, signals


def stability_fields(
    violations: Sequence[Mapping[str, int | str]] | None,
) -> tuple[bool | None, str | None]:
    """(stable, stability_note) for a capability study — tri-state (#191 D2).

    `None` means the caller supplied no control-chart context, so stability was
    never assessed; an EMPTY sequence means it was assessed and the process is
    in control. The `is None` test below is load-bearing: a truthiness test
    would silently downgrade an in-control assessment to "not assessed".
    """
    if violations is None:
        return None, NOT_ASSESSED_NOTE
    if not violations:
        return True, None
    return False, (
        f"Process is not in statistical control — {len(violations)} out-of-control "
        "signal(s) detected on the control chart. Capability indices (Cp/Cpk/Pp/Ppk) "
        "are not a valid capability claim until the process is stabilized; treat "
        "these values as indicative only."
    )
