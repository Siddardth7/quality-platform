"""The quality-platform MCP server: FastMCP app, stdio transport, meta + FMEA + SPC tools.

This module is the M1-1 foundation (#260); M1-3 (#262) added the FMEA tools and M1-4 (#263)
the SPC group — variables/attributes/time-weighted control charts, Phase I limit freezing and
Phase II application, the Western Electric / Nelson run-rule detectors, the capability study
(Cp/Cpk/Pp/Ppk + CIs) and the stability gate. M1-7 (#266) added the export tools: CSV/Excel/
PDF artifacts from the FMEA, SPC and MSA report builders plus the two FMEA chart PNGs, every
one of them a thin wrapper over an existing exporter so the formula-injection sanitizer in
``quality_core.io.export`` is never bypassed. Every later domain tool (MSA, Control Plan,
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

import io
from collections.abc import Callable
from typing import Any, Literal, TypeVar, cast

import pandas as pd
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import File, Image
from matplotlib import pyplot as plt
from msa_app.exporter import GageStudyReport
from msa_app.exporter import export_csv as msa_export_study_csv_bytes
from msa_app.exporter import export_excel as msa_export_excel_bytes
from msa_app.exporter import export_pdf as msa_export_pdf_bytes
from msa_app.exporter import export_results_csv as msa_export_results_csv_bytes
from pydantic import ValidationError
from quality_core.io.export import export_csv as core_export_csv
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

from fmea_app.exporter import export_excel as fmea_export_excel_bytes
from fmea_app.exporter import export_pdf as fmea_export_pdf_bytes
from fmea_app.rating_scales import (
    load_default_scales,
    load_legacy_fmea4_scales,
    load_scales_from_json,
)
from fmea_app.rpn_engine import run_pipeline, run_pipeline_relational
from fmea_app.visualizer import pareto_chart, risk_heatmap
from mcp_app import __version__
from spc_app.exporter import (
    CapabilityReport,
    ControlChartReport,
    build_capability_report_excel,
    build_capability_report_pdf,
    build_control_chart_report_excel,
    build_control_chart_report_pdf,
)

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


# ---------------------------------------------------------------------------
# Export / report tools (M1-7, #266)
#
# Return convention (spec Q1, SME sign-off): every artifact tool returns a
# ``fastmcp.utilities.types.File`` — or ``Image`` for a PNG — and nothing else. FastMCP's
# own tool-result converter turns those into MCP ``EmbeddedResource``/``ImageContent``
# (base64 inside), so there is no hand-rolled base64 envelope here, no resource
# registration, no served-transport requirement and no project-directory contract. When a
# future project/session-directory surface (M3) wants written paths instead, only the
# return statements change — no exporter and no sanitizer is involved in that swap.
#
# Every tool is a thin wrapper over an already-shipped, already-100%-covered report
# builder: ``quality_core.io.export`` for plain CSV, ``fmea_app``/``spc_app``/``msa_app``'s
# ``exporter`` modules for the styled artifacts. Formula-injection escaping therefore comes
# from ``quality_core.io.export.sanitize_for_export`` inside those builders and is never
# reimplemented — and never bypassed with a direct ``DataFrame.to_csv()`` call. No new
# report layout is introduced: the frozen ``ControlChartReport``/``CapabilityReport``/
# ``GageStudyReport`` dataclasses are assembled inline from tool parameters.
#
# Error policy (spec "Interfaces"): bad-input ``ValueError``/``ValidationError`` becomes a
# structured ``ToolError`` through ``_call``, as everywhere else in this module; a missing
# *mapping* key in a caller-supplied result dict (e.g. ``results["cp"]``) raises ``KeyError``
# and is deliberately left uncaught, matching how ``spc_capability`` already lets a
# malformed ``violations`` shape fail loudly rather than be silently swallowed. Each tool
# below says so where it applies.
# ---------------------------------------------------------------------------


def _figure_png(fig: plt.Figure) -> Image:
    """Render a matplotlib figure to a PNG ``Image``, closing the figure.

    ``dpi=150``/``bbox_inches="tight"`` mirror the settings ``fmea_app.visualizer`` already
    uses for its own on-disk PNGs, so a chart returned here is byte-comparable with the one
    embedded in the FMEA PDF. Closing is mandatory: the visualizer only closes the figure on
    its ``output_path`` branch, and a leaked figure is a slow memory leak in a long-running
    server process.
    """
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return Image(data=buf.getvalue(), format="png")


@app.tool
def export_csv(table: list[dict[str, Any]]) -> File:
    """Export any tabular result (FMEA rows, SPC points, ...) to formula-safe CSV.

    ``table`` is a list of row dicts — e.g. ``fmea_run``'s output straight back in. Every
    string cell whose first non-whitespace character is ``=``, ``+``, ``-`` or ``@`` (or a
    leading Tab/CR) is escaped with a leading apostrophe so no spreadsheet evaluates it as a
    formula, while numeric literals such as ``"-3.0000"`` are left alone; that is
    ``quality_core.io.export.sanitize_for_export``'s contract, applied here rather than
    restated. Raises a structured tool error for an empty ``table``.
    """
    if not table:
        raise ToolError("table must have at least one row.")
    return File(data=core_export_csv(pd.DataFrame(table)), format="csv", name="export")


@app.tool
def fmea_export_excel(rows: list[dict[str, Any]]) -> File:
    """FMEA scored rows -> styled .xlsx: ranked sheet colour-coded by Risk_Tier + metadata.

    ``rows`` is ``fmea_run`` / ``fmea_run_relational``'s own output. Columns the export
    layout doesn't know about are dropped and missing ones degrade gracefully, so a partial
    frame still exports. Raises a structured tool error for empty ``rows``.
    """
    if not rows:
        raise ToolError("rows must have at least one row.")
    return File(
        data=fmea_export_excel_bytes(pd.DataFrame(rows)), format="xlsx", name="fmea_report"
    )


@app.tool
def fmea_export_pdf(rows: list[dict[str, Any]]) -> File:
    """FMEA scored rows -> 3-page A4 PDF (summary, ranked table, action page).

    Same ``rows`` contract and same empty-input tool error as ``fmea_export_excel``.
    """
    if not rows:
        raise ToolError("rows must have at least one row.")
    return File(data=fmea_export_pdf_bytes(pd.DataFrame(rows)), format="pdf", name="fmea_report")


@app.tool
def fmea_chart_pareto_png(rows: list[dict[str, Any]]) -> Image:
    """Pareto chart PNG: failure modes ranked by RPN, coloured by Risk_Tier, 80% line.

    ``rows`` needs Failure_Mode, RPN and Risk_Tier — ``fmea_run``'s output has all three.
    The visualizer's existing Top-N + "Others" aggregation and figure-width cap apply
    unchanged, which is why nothing here calls matplotlib against the frame directly. A
    missing required column raises the visualizer's own ``KeyError`` naming it (see the
    error-policy note above); empty ``rows`` is a structured tool error.
    """
    if not rows:
        raise ToolError("rows must have at least one row.")
    return _figure_png(pareto_chart(pd.DataFrame(rows)))


@app.tool
def fmea_chart_heatmap_png(rows: list[dict[str, Any]]) -> Image:
    """Severity x Occurrence risk heatmap PNG (10x10, cells coloured by dominant Risk_Tier).

    ``rows`` needs Severity, Occurrence and Risk_Tier; same missing-column and empty-input
    behaviour as ``fmea_chart_pareto_png``.
    """
    if not rows:
        raise ToolError("rows must have at least one row.")
    return _figure_png(risk_heatmap(pd.DataFrame(rows)))


def _control_chart_report(
    chart_label: str,
    stream: str,
    rule_set: str,
    points: list[float],
    cl: float,
    ucl: float | list[float],
    lcl: float | list[float],
    violations: list[dict[str, Any]],
    metrics: list[tuple[str, str]],
    secondary_label: str | None,
    secondary_points: list[float] | None,
) -> ControlChartReport:
    """Assemble the frozen ``ControlChartReport`` the SPC report builders take.

    The optional second series only becomes a report field when both its label and its
    values are supplied — half a pair is treated as "not supplied", matching the exporter's
    ``None`` default that keeps every existing report byte-identical.
    """
    secondary = (
        (secondary_label, secondary_points)
        if secondary_label is not None and secondary_points is not None
        else None
    )
    return ControlChartReport(
        chart_label=chart_label,
        stream=stream,
        rule_set=rule_set,
        points=points,
        cl=cl,
        ucl=ucl,
        lcl=lcl,
        violations=violations,
        metrics=metrics,
        secondary_points=secondary,
    )


@app.tool
def spc_export_control_chart_excel(
    chart_label: str,
    stream: str,
    rule_set: str,
    points: list[float],
    cl: float,
    ucl: float | list[float],
    lcl: float | list[float],
    violations: list[dict[str, Any]],
    metrics: list[tuple[str, str]],
    secondary_label: str | None = None,
    secondary_points: list[float] | None = None,
) -> File:
    """Control-chart report -> .xlsx: a per-point sheet with signals highlighted + summary.

    ``points``/``cl``/``ucl``/``lcl`` are a chart tool's own result fields passed back in
    (e.g. ``spc_xbar_r``'s xbar_values/cl/ucl/lcl), ``violations`` is a detector tool's
    ``{"index", "rule"}`` list, and ``metrics`` is the (label, value) pairs to print in the
    summary. ``ucl``/``lcl`` accept a per-point list for the p- and u-charts. Nothing is
    recomputed here — the caller owns the chart, this tool only renders it.
    ``secondary_label`` + ``secondary_points`` render an optional second series (e.g.
    CUSUM's lower arm) and are used only when both are given.
    """
    report = _control_chart_report(
        chart_label,
        stream,
        rule_set,
        points,
        cl,
        ucl,
        lcl,
        violations,
        metrics,
        secondary_label,
        secondary_points,
    )
    return File(
        data=build_control_chart_report_excel(report), format="xlsx", name="control_chart_report"
    )


@app.tool
def spc_export_control_chart_pdf(
    chart_label: str,
    stream: str,
    rule_set: str,
    points: list[float],
    cl: float,
    ucl: float | list[float],
    lcl: float | list[float],
    violations: list[dict[str, Any]],
    metrics: list[tuple[str, str]],
    secondary_label: str | None = None,
    secondary_points: list[float] | None = None,
) -> File:
    """Control-chart report -> PDF; identical parameters to
    ``spc_export_control_chart_excel``."""
    report = _control_chart_report(
        chart_label,
        stream,
        rule_set,
        points,
        cl,
        ucl,
        lcl,
        violations,
        metrics,
        secondary_label,
        secondary_points,
    )
    return File(
        data=build_control_chart_report_pdf(report), format="pdf", name="control_chart_report"
    )


@app.tool
def spc_export_capability_excel(
    stream_label: str,
    values: list[float],
    capability: dict[str, Any],
    lsl: float | None,
    usl: float | None,
    normality: dict[str, Any],
    oos_signal_count: int,
) -> File:
    """Capability report -> .xlsx (indices + CIs, normality, spec limits, the raw values).

    ``capability`` is ``spc_capability``'s result dict verbatim and ``normality`` is
    ``spc_normality_test``'s; ``lsl``/``usl`` may each independently be null, as in
    ``spc_capability``. ``oos_signal_count`` is the number of control-chart signals that
    gated this study — ``0`` states "assessed, in control" and is a real, reachable value,
    not a stand-in for "not assessed". A key the layout needs but the supplied
    ``capability``/``normality`` dict lacks raises ``KeyError`` (see the error-policy note
    above) rather than silently rendering a blank field.
    """
    report = CapabilityReport(
        stream_label=stream_label,
        values=values,
        capability=capability,
        lsl=lsl,
        usl=usl,
        normality=normality,
        oos_signal_count=oos_signal_count,
    )
    return File(
        data=build_capability_report_excel(report), format="xlsx", name="capability_report"
    )


@app.tool
def spc_export_capability_pdf(
    stream_label: str,
    values: list[float],
    capability: dict[str, Any],
    lsl: float | None,
    usl: float | None,
    normality: dict[str, Any],
    oos_signal_count: int,
) -> File:
    """Capability report -> PDF; identical parameters to ``spc_export_capability_excel``."""
    report = CapabilityReport(
        stream_label=stream_label,
        values=values,
        capability=capability,
        lsl=lsl,
        usl=usl,
        normality=normality,
        oos_signal_count=oos_signal_count,
    )
    return File(data=build_capability_report_pdf(report), format="pdf", name="capability_report")


@app.tool
def msa_export_excel(
    study: list[dict[str, Any]],
    results: dict[str, Any],
    usl: float | None = None,
    lsl: float | None = None,
) -> File:
    """Gage R&R study + results -> .xlsx (results/metadata summary sheet + study sheet).

    ``study`` is the validated study rows (part/appraiser/trial/measurement) and ``results``
    is ``compute_gage_rr``'s result dict verbatim; ``usl``/``lsl`` add the tolerance-basis
    rows and may each be null. Study cells are formula-injection escaped by the exporter.
    Empty ``study`` is a structured tool error; a ``results`` dict missing a metric the
    report prints raises ``KeyError`` (see the error-policy note above).
    """
    if not study:
        raise ToolError("study must have at least one row.")
    report = GageStudyReport(study=pd.DataFrame(study), results=results, usl=usl, lsl=lsl)
    return File(data=msa_export_excel_bytes(report), format="xlsx", name="gage_rr_report")


@app.tool
def msa_export_pdf(
    study: list[dict[str, Any]],
    results: dict[str, Any],
    usl: float | None = None,
    lsl: float | None = None,
) -> File:
    """Gage R&R report -> PDF (%GRR/ndc/verdict strip + metric detail table).

    Identical parameters and identical error behaviour to ``msa_export_excel``.
    """
    if not study:
        raise ToolError("study must have at least one row.")
    report = GageStudyReport(study=pd.DataFrame(study), results=results, usl=usl, lsl=lsl)
    return File(data=msa_export_pdf_bytes(report), format="pdf", name="gage_rr_report")


@app.tool
def msa_export_study_csv(study: list[dict[str, Any]]) -> File:
    """Gage R&R study rows -> round-trippable, formula-injection-safe CSV.

    ``study`` needs the four study columns (part/appraiser/trial/measurement); a missing one
    raises ``KeyError``. Empty ``study`` is a structured tool error.
    """
    if not study:
        raise ToolError("study must have at least one row.")
    report = GageStudyReport(study=pd.DataFrame(study), results={}, usl=None, lsl=None)
    return File(data=msa_export_study_csv_bytes(report), format="csv", name="gage_rr_study")


@app.tool
def msa_export_results_csv(results: dict[str, Any]) -> File:
    """Flat one-row Gage R&R results table -> CSV (EV/AV/GRR/PV/TV, the %-bases, ndc,
    verdict).

    ``results`` is ``compute_gage_rr``'s result dict verbatim; a missing metric key raises
    ``KeyError`` (see the error-policy note above). The values are engine-computed numbers
    and fixed verdict strings rather than user input, so — matching the SPC exporter's own
    convention — this sheet is not routed through the injection sanitizer.
    """
    report = GageStudyReport(study=pd.DataFrame(), results=results, usl=None, lsl=None)
    return File(data=msa_export_results_csv_bytes(report), format="csv", name="gage_rr_results")


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
