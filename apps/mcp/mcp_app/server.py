"""The quality-platform MCP server: FastMCP app, stdio transport, meta + FMEA + SPC tools.

This module is the M1-1 foundation (#260); M1-3 (#262) added the FMEA tools and M1-4 (#263)
the SPC group — variables/attributes/time-weighted control charts, Phase I limit freezing and
Phase II application, the Western Electric / Nelson run-rule detectors, the capability study
(Cp/Cpk/Pp/Ppk + CIs) and the stability gate. Every later domain tool (MSA, Control Plan,
SECOM) lands on this same ``app`` object in this same module — the CI coverage gate targets
``mcp_app.server`` only, so a separate tools module would silently stop being covered.

The SPC tools wrap ``quality_core.spc`` directly, not ``spc_app``: audit A12 (#205) promoted
every SPC primitive into the shared core, so nothing here crosses an app boundary and no SPC
math is reimplemented — each tool is a thin typed wrapper over one engine function.

``mcp_app`` is the one intentional exception to the workspace's "apps never import each
other" rule (SME sign-off, #262): it is the aggregator whose job is wrapping domain-app
engines. Peer apps still never import peers — see ``tests/test_import_boundary.py``.

Tool namespace convention (fixed now so later tools don't re-litigate it, #260 decision 2):
meta tools that describe the server process itself stay flat and unprefixed (``health``,
``version``); every future engine tool gets a ``<domain>_`` prefix (e.g.
``fmea_action_priority``, ``spc_capability``, ``msa_gage_rr``) so this server's tool list
stays legible when a host also has other MCP servers connected.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, TypeVar, cast

import pandas as pd
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import ValidationError
from quality_core.schema import RelationalFMEA
from quality_core.scoring import action_priority, rpn
from quality_core.spc import (
    CAPABILITY_ALPHA,
    CUSUM_DEFAULT_H,
    CUSUM_DEFAULT_K,
    EWMA_DEFAULT_L,
    EWMA_DEFAULT_LAMBDA,
    ChartType,
    ExcludedPoint,
    FrozenLimits,
    assess_stability,
    compute_c,
    compute_capability_study,
    compute_cusum,
    compute_ewma,
    compute_imr,
    compute_p,
    compute_u,
    compute_xbar_r,
    compute_xbar_s,
    detect_nelson_violations,
    detect_we_violations,
    freeze_imr,
    freeze_xbar_r,
    freeze_xbar_s,
    normality_test,
)

from fmea_app.rating_scales import (
    load_default_scales,
    load_legacy_fmea4_scales,
    load_scales_from_json,
)
from fmea_app.rpn_engine import run_pipeline, run_pipeline_relational
from mcp_app import __version__

app = FastMCP("quality-platform")

_T = TypeVar("_T")


def _call(fn: Callable[..., _T], /, *args: Any, **kwargs: Any) -> _T:
    """Run an engine function, converting its input errors into a ``ToolError``.

    The FMEA engines raise plain ``ValueError`` for bad input (``validate_input``, ``rpn``,
    ``action_priority``, the scale loaders); ``RelationalFMEA.model_validate`` raises
    pydantic's ``ValidationError``. Both are "the caller sent bad data", so both become
    FastMCP's own structured error type — a client never sees a traceback, and never
    depends on ``mask_error_details`` staying off. (``ValidationError`` subclasses
    ``ValueError`` in pydantic v2, so it is caught either way; naming it is defensive and
    self-documenting.)
    """
    try:
        return fn(*args, **kwargs)
    except (ValueError, ValidationError) as exc:
        raise ToolError(str(exc)) from exc


def _scored_records(scored: pd.DataFrame) -> list[dict[str, Any]]:
    """Add the per-row AIAG-VDA Action Priority to a scored pipeline frame, as records.

    ``run_pipeline`` produces RPN, the criticality flags and ``Risk_Tier`` but no ``AP``
    column, so AP comes from the scalar ``quality_core.scoring.action_priority``. Records
    orientation keeps the payload JSON-friendly — no DataFrame goes over the wire.

    Shared by ``fmea_run`` and ``fmea_run_relational``: the relational pipeline flattens to
    the same frame shape, so the post-processing is byte-identical for both.
    """
    scored["AP"] = [
        _call(action_priority, s, o, d)
        for s, o, d in zip(
            scored["Severity"], scored["Occurrence"], scored["Detection"], strict=True
        )
    ]
    # pandas types record keys as Hashable; every FMEA column name is a str, and the same
    # cast is how rpn_engine.py bridges this (lines 150, 457).
    return cast("list[dict[str, Any]]", scored.to_dict(orient="records"))


@app.tool
def health() -> dict[str, str]:
    """Liveness probe: proves the request loop is up end-to-end."""
    return {"status": "ok"}


@app.tool
def version() -> dict[str, str]:
    """Report the running quality-platform MCP server build."""
    return {"version": __version__}


@app.tool
def fmea_score(severity: int, occurrence: int, detection: int) -> dict[str, int | str]:
    """Score one Severity/Occurrence/Detection triple: RPN + AIAG-VDA Action Priority.

    Pure lookup — the agent never computes RPN/AP itself. Both are scale-independent: the
    2019 AP table is baked into the engine, so the rating scale chosen for *describing*
    S/O/D never changes these numbers. Raises a structured tool error (not a stack trace)
    if any rating is outside the AIAG 1-10 scale.
    """
    return {
        "rpn": _call(rpn, severity, occurrence, detection),
        "action_priority": _call(action_priority, severity, occurrence, detection),
    }


@app.tool
def fmea_run(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run the full FMEA pipeline (validate -> RPN -> AP -> flags -> rank) over rows.

    Each row needs the 11 required FMEA columns (ID, Process_Step, Component, Function,
    Failure_Mode, Effect, Severity, Cause, Occurrence, Current_Control, Detection). Returns
    rows ranked by RPN descending, each with RPN, AP, the three criticality flags and
    Risk_Tier. Raises a structured tool error on invalid input — never a stack trace.
    """
    scored = _call(run_pipeline, pd.DataFrame(rows))
    return _scored_records(scored)


@app.tool
def fmea_run_relational(model: dict[str, Any]) -> list[dict[str, Any]]:
    """Run the full FMEA pipeline over a relational model supplied as a JSON object.

    ``model`` is a RelationalFMEA (Function -> FailureMode -> Effect/Cause/Control, tied
    together by links). It is flattened losslessly and then run through the same
    validate -> RPN -> AP -> flags -> rank pipeline as ``fmea_run``, so the output shape
    matches — plus the action-tracking columns when any link carries an action. Raises a
    structured tool error if the model fails its own validation (duplicate IDs, unknown
    link references) or the flattened rows fail input validation.
    """
    parsed = _call(RelationalFMEA.model_validate, model)
    scored = _call(run_pipeline_relational, parsed)
    return _scored_records(scored)


@app.tool
def fmea_list_scales() -> list[dict[str, str]]:
    """List the built-in FMEA rating-scale options an agent can select.

    Rating scales are reference text only: they document what a score *means*, and never
    change the RPN/AP that ``fmea_score``/``fmea_run`` return. Names come from the bundled
    scale files themselves rather than being restated here, so the menu can't drift from
    what ``fmea_get_scale`` actually returns.
    """
    return [
        {"id": "2019", "name": load_default_scales().name},
        {"id": "fmea4", "name": load_legacy_fmea4_scales().name},
    ]


@app.tool
def fmea_get_scale(scale_id: str = "2019", custom_json: str | None = None) -> dict[str, Any]:
    """Return one S/O/D rating scale's full severity/occurrence/detection text.

    scale_id: "2019" (AIAG & VDA 2019 PFMEA default), "fmea4" (AIAG FMEA-4 legacy), or
    "custom" (requires custom_json: raw JSON text with severity/occurrence/detection keys,
    each mapping ratings 1-10 to a description). Raises a structured tool error for an
    unknown scale_id, a missing custom_json when scale_id="custom", or a custom scale that
    fails validation.
    """
    if scale_id == "2019":
        scale = load_default_scales()
    elif scale_id == "fmea4":
        scale = load_legacy_fmea4_scales()
    elif scale_id == "custom":
        if custom_json is None:
            raise ToolError("scale_id='custom' requires custom_json.")
        scale = _call(load_scales_from_json, custom_json)
    else:
        raise ToolError(f"Unknown scale_id {scale_id!r}. Use '2019', 'fmea4', or 'custom'.")
    return scale.model_dump()


# ---------------------------------------------------------------------------
# SPC — control charts (quality_core.spc.control_charts)
#
# Every chart tool takes the engine's own native input shape (wide subgroups for
# X-bar charts, flat individuals for I-MR/EWMA/CUSUM, parallel count/size lists for
# the attribute charts) rather than a new JSON envelope, and returns the engine's
# result mapping verbatim as a plain dict. Bad input raises a structured tool error.
# ---------------------------------------------------------------------------


@app.tool
def spc_xbar_r(subgroups: list[list[float]]) -> dict[str, Any]:
    """X-bar & R chart (Phase I): limits computed from the supplied data itself.

    ``subgroups`` is one inner list per subgroup, all the same length, with a subgroup
    size of 2-10 (the AIAG tabulated A2/D3/D4 range). Returns subgroup means, ranges,
    the centre lines and both charts' limits, plus sigma_hat estimated as Rbar/d2.
    Raises a structured tool error for ragged/empty input or an untabulated subgroup
    size. To apply an existing frozen baseline instead, use ``spc_apply_xbar_r``.
    """
    return dict(_call(compute_xbar_r, subgroups))


@app.tool
def spc_xbar_s(subgroups: list[list[float]]) -> dict[str, Any]:
    """X-bar & S chart (Phase I): limits computed from the supplied data itself.

    Same wide-subgroup input as ``spc_xbar_r``, but the tabulated A3/B3/B4 range is
    2-12 and sigma_hat is Sbar/c4 — preferred over X-bar & R for larger subgroups.
    Raises a structured tool error for ragged/empty input or an untabulated subgroup
    size. Phase II lives in ``spc_apply_xbar_s``.
    """
    return dict(_call(compute_xbar_s, subgroups))


@app.tool
def spc_imr(values: list[float]) -> dict[str, Any]:
    """Individuals & Moving Range chart (Phase I) over a flat series of measurements.

    Use when the subgroup is one unit (n=1). Needs at least two values; returns the
    individuals and MR series with both charts' limits and sigma_hat = MRbar/d2.
    Phase II lives in ``spc_apply_imr``.
    """
    return dict(_call(compute_imr, values))


@app.tool
def spc_p(defective_counts: list[float], sample_sizes: list[float]) -> dict[str, Any]:
    """p-chart: proportion defective, variable sample size (limits vary per point).

    ``defective_counts`` and ``sample_sizes`` are parallel lists of equal length; every
    sample size must be finite and positive (a NaN size once produced NaN limits with no
    error at all — #200). Raises a structured tool error otherwise.
    """
    return dict(_call(compute_p, defective_counts, sample_sizes))


@app.tool
def spc_c(defect_counts: list[float]) -> dict[str, Any]:
    """c-chart: count of defects per inspection unit, constant sample size.

    One count per inspection unit; limits are cbar +/- 3*sqrt(cbar), with the lower
    limit clamped at zero. Raises a structured tool error on empty input.
    """
    return dict(_call(compute_c, defect_counts))


@app.tool
def spc_u(defect_counts: list[float], sample_sizes: list[float]) -> dict[str, Any]:
    """u-chart: defects per unit with a variable sample size (limits vary per point).

    Same parallel-list contract and sample-size validation as ``spc_p``; use it rather
    than the c-chart whenever the inspected area of opportunity is not constant.
    """
    return dict(_call(compute_u, defect_counts, sample_sizes))


@app.tool
def spc_ewma(
    values: list[float],
    mu0: float,
    sigma: float,
    lam: float = EWMA_DEFAULT_LAMBDA,
    L: float = EWMA_DEFAULT_L,
) -> dict[str, Any]:
    """EWMA chart: exponentially weighted moving average, for small sustained shifts.

    ``mu0`` and ``sigma`` are the independent Phase I estimates — never derived from the
    series being charted (ASSUMPTIONS_LOG RULE 12). ``lam``/``L`` default to the cited
    NIST/Lucas & Saccucci pairing carried in ``quality_core.spc.constants``; a mismatched
    pair is still computed but comes back with ``pairing_adequate=False`` and a
    ``pairing_note`` naming the recommended L — the tool does not swallow that warning.
    Raises a structured tool error for empty values, sigma<=0, lam outside (0,1] or L<=0.
    """
    return dict(_call(compute_ewma, values, mu0, sigma, lam, L))


@app.tool
def spc_cusum(
    values: list[float],
    mu0: float,
    sigma: float,
    k: float = CUSUM_DEFAULT_K,
    h: float = CUSUM_DEFAULT_H,
    fir: bool = False,
) -> dict[str, Any]:
    """Tabular CUSUM chart: cumulative sums, for detecting small sustained shifts fast.

    ``mu0``/``sigma`` are Phase I estimates as for ``spc_ewma``. ``k`` (reference value)
    and ``h`` (decision interval) default to the cited NIST values in
    ``quality_core.spc.constants``; ``fir=True`` applies the Lucas & Crosier head start
    (h/2) to both arms. Raises a structured tool error for empty values, sigma<=0, k<=0
    or h<=0.
    """
    return dict(_call(compute_cusum, values, mu0, sigma, k, h, fir))


# ---------------------------------------------------------------------------
# SPC — Phase I freezing and Phase II application (quality_core.spc.phase)
#
# Two tool families rather than a `frozen=` flag on the chart tools (SME decision,
# #263): ``spc_freeze_*`` establishes a baseline, ``spc_apply_*`` charts new data
# against it. The freeze output is a plain dict that goes straight back in as the
# ``frozen`` argument — that round trip is the whole point of the pair.
# ---------------------------------------------------------------------------


@app.tool
def spc_freeze_xbar_r(
    baseline: list[list[float]],
    excluded: list[dict[str, Any]] | None = None,
    phase_i_range: tuple[str, str] | None = None,
) -> dict[str, Any]:
    """Freeze X-bar & R limits from a Phase I baseline, for later Phase II monitoring.

    ``excluded`` drops baseline subgroups with an assignable cause: a list of
    ``{"index": int, "cause": str}`` objects. The cause is mandatory — an out-of-range,
    duplicated or uncaused index is a structured tool error, because dropping a point
    without a documented reason is not a defensible baseline. ``phase_i_range`` is an
    optional (start, end) label pair recorded on the result. The returned object carries
    the limits, sigma_hat and its method, the exclusions, and ``baseline_adequate`` /
    ``baseline_note`` flagging a baseline below the AIAG minimum subgroup count.
    """
    return dict(
        _call(
            freeze_xbar_r,
            baseline,
            excluded=cast("list[ExcludedPoint]", excluded or []),
            phase_i_range=phase_i_range,
        )
    )


@app.tool
def spc_freeze_xbar_s(
    baseline: list[list[float]],
    excluded: list[dict[str, Any]] | None = None,
    phase_i_range: tuple[str, str] | None = None,
) -> dict[str, Any]:
    """Freeze X-bar & S limits from a Phase I baseline (sigma_hat = Sbar/c4).

    Identical contract to ``spc_freeze_xbar_r`` — see it for ``excluded`` /
    ``phase_i_range`` — but the baseline subgroup size must be in the X-bar & S
    tabulated range of 2-12.
    """
    return dict(
        _call(
            freeze_xbar_s,
            baseline,
            excluded=cast("list[ExcludedPoint]", excluded or []),
            phase_i_range=phase_i_range,
        )
    )


@app.tool
def spc_freeze_imr(
    baseline: list[float],
    excluded: list[dict[str, Any]] | None = None,
    phase_i_range: tuple[str, str] | None = None,
) -> dict[str, Any]:
    """Freeze I-MR limits from a flat Phase I baseline of individual measurements.

    Same ``excluded`` / ``phase_i_range`` contract as ``spc_freeze_xbar_r``, except that
    an excluded index drops one individual value rather than a whole subgroup, and the
    adequacy floor is the AIAG minimum number of individuals.
    """
    return dict(
        _call(
            freeze_imr,
            baseline,
            excluded=cast("list[ExcludedPoint]", excluded or []),
            phase_i_range=phase_i_range,
        )
    )


@app.tool
def spc_apply_xbar_r(subgroups: list[list[float]], frozen: dict[str, Any]) -> dict[str, Any]:
    """Phase II X-bar & R: chart new subgroups against frozen baseline limits.

    ``frozen`` is a ``spc_freeze_xbar_r`` result passed straight back in. The limits are
    taken from it verbatim — nothing is recomputed from the new data, which is what makes
    a Phase II signal meaningful. Raises a structured tool error if the frozen baseline is
    for a different chart type or a different subgroup size than the new data.
    """
    return dict(_call(compute_xbar_r, subgroups, cast("FrozenLimits", frozen)))


@app.tool
def spc_apply_xbar_s(subgroups: list[list[float]], frozen: dict[str, Any]) -> dict[str, Any]:
    """Phase II X-bar & S: chart new subgroups against frozen baseline limits.

    ``frozen`` is a ``spc_freeze_xbar_s`` result; same chart-type/subgroup-size guard as
    ``spc_apply_xbar_r``.
    """
    return dict(_call(compute_xbar_s, subgroups, cast("FrozenLimits", frozen)))


@app.tool
def spc_apply_imr(values: list[float], frozen: dict[str, Any]) -> dict[str, Any]:
    """Phase II I-MR: chart new individuals against frozen baseline limits.

    ``frozen`` is a ``spc_freeze_imr`` result; same chart-type guard as
    ``spc_apply_xbar_r`` (I-MR is always n=1).
    """
    return dict(_call(compute_imr, values, cast("FrozenLimits", frozen)))


# ---------------------------------------------------------------------------
# SPC — run-rule detection (quality_core.spc.rule_detection)
# ---------------------------------------------------------------------------


@app.tool
def spc_detect_we_violations(
    points: list[float], cl: float, sigma: float
) -> list[dict[str, int | str]]:
    """Western Electric run rules over plotted points, given their centre line and sigma.

    ``cl``/``sigma`` come from a chart tool's result — and for X-bar charts ``sigma`` is
    the sigma of the *plotted points* (sigma_hat/sqrt(n)), not sigma_hat itself. Returns
    one ``{"index", "rule"}`` object per signal, empty when in control. Raises a
    structured tool error for sigma<=0.
    """
    return _call(detect_we_violations, points, cl, sigma)


@app.tool
def spc_detect_nelson_violations(
    points: list[float], cl: float, sigma: float
) -> list[dict[str, int | str]]:
    """Nelson run rules over plotted points — the WE zone tests plus trend, alternation,
    stratification and mixture rules.

    Same ``points``/``cl``/``sigma`` contract and same ``{"index", "rule"}`` output as
    ``spc_detect_we_violations``; raises a structured tool error for sigma<=0.
    """
    return _call(detect_nelson_violations, points, cl, sigma)


# ---------------------------------------------------------------------------
# SPC — capability (quality_core.spc.capability)
# ---------------------------------------------------------------------------


@app.tool
def spc_capability(
    data: list[float] | list[list[float]],
    lsl: float | None,
    usl: float | None,
    alpha: float = CAPABILITY_ALPHA,
    allow_yeojohnson: bool = True,
    force_method: Literal["auto", "normal", "boxcox", "percentile"] = "auto",
    violations: list[dict[str, int | str]] | None = None,
) -> dict[str, Any]:
    """Capability study: Cp/Cpk/Pp/Ppk with confidence intervals and method selection.

    ``data`` is flat individuals or wide subgroups (subgroups give a within-subgroup
    sigma). At least one of ``lsl``/``usl`` is needed for an index; with neither, the
    indices come back as null and nothing raises. ``force_method`` overrides the default
    Shapiro-Wilk-driven selection between the normal-theory, Box-Cox/Yeo-Johnson transform
    and ISO 22514-2 fitted-percentile paths (``allow_yeojohnson=False`` forces a shifted
    Box-Cox for non-positive data instead).

    Two result subtleties, both deliberate — read them before rendering anything:

    - CIs are attached only to the estimator they were derived for (#193). On the normal
      path ``cp_ci``/``cpk_ci`` are always null and ``pp_ci``/``ppk_ci``/``ppk_lower``
      carry the chi-square/Bissell intervals (``ci_estimator="sample_sd_ddof1"``,
      ``ci_df=n-1``); on the percentile path Pp/Ppk and their CIs are null and
      ``cp_ci``/``cpk_ci`` are deterministic bootstrap intervals (``ci_df=null``). Every
      field is returned verbatim, nulls included: "no CI for this estimator" and "CI not
      computed" are different facts and a client needs ``ci_estimator``/``ci_df`` to tell
      them apart.
    - ``violations`` is the caller's own control-chart signal list (from
      ``spc_detect_we_violations`` / ``spc_detect_nelson_violations`` / the ``signals`` of
      ``spc_assess_stability``) and drives a tri-state stability gate: omit it and
      ``stable`` is null — "not assessed", never a fabricated in-control claim; pass ``[]``
      to state the chart was assessed and is in control. No stability check is run inside
      this tool; the caller supplies the chart context, exactly as the engine expects.

    Raises a structured tool error for alpha outside (0,1), data that is neither 1-D nor
    2-D, fewer than three observations, or constant data.
    """
    return dict(
        _call(
            compute_capability_study,
            data,
            lsl,
            usl,
            alpha=alpha,
            allow_yeojohnson=allow_yeojohnson,
            force_method=force_method,
            violations=violations,
        )
    )


@app.tool
def spc_normality_test(data: list[float]) -> dict[str, Any]:
    """Shapiro-Wilk normality test: returns the W statistic, p-value and is_normal.

    ``is_normal`` is p > 0.05 — the same gate ``spc_capability``'s "auto" method selection
    uses. Needs at least three values; raises a structured tool error otherwise.
    """
    return _call(normality_test, data)


# ---------------------------------------------------------------------------
# SPC — stability gate (quality_core.spc.stability)
# ---------------------------------------------------------------------------


@app.tool
def spc_assess_stability(
    values: list[float],
    subgroups: list[str | int],
    chart_type: ChartType = "I-MR",
    rule_set: str = "Western Electric",
) -> dict[str, Any]:
    """Assess whether a stream is in statistical control, for the capability gate.

    Long format, unlike the chart tools: ``values`` and ``subgroups`` are parallel lists,
    one row per measurement, which is what preserves measurement order within a subgroup
    on the I-MR path. ``chart_type`` is "I-MR", "Xbar-R" or "Xbar-S" and is caller-supplied
    on purpose — inferring it from the data understates sigma and flips verdicts (#191).
    ``rule_set`` is "Western Electric" (default) or "Nelson".

    Returns ``sigma_hat`` and the ``signals`` list; an empty list means in control. Feed
    ``signals`` into ``spc_capability``'s ``violations`` to gate the indices. Raises a
    structured tool error for ragged subgroups or a subgroup size outside the chart's
    tabulated range.
    """
    frame = pd.DataFrame({"value": values, "subgroup": subgroups})
    sigma_hat, signals = _call(assess_stability, frame, chart_type, rule_set=rule_set)
    return {"sigma_hat": sigma_hat, "signals": signals}


def main() -> None:
    """Console-script entry point (``quality-mcp``).

    stdio is FastMCP's default transport — what Claude Desktop / Cursor / Claude Code
    launch (#260 scope: stdio only, HTTP is M1-8).
    """
    app.run()


# pragma: no cover — the module-as-script path can't be exercised from a test without
# starting the blocking stdio loop; `main()` itself is covered directly.
if __name__ == "__main__":  # pragma: no cover
    main()
