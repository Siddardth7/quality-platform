"""Seed this example's `spc/results/*.json` from the real SECOM dataset — one time only.

**This script is not part of the loop.** `run_project_loop` (and the four arrows it
sequences) *reads* `spc/results/<characteristic>.json`; no arrow writes one, because
running a control chart against live process data and persisting it is not any M3 arrow's
contract (see `docs/PROJECT_FILE_CONTRACT.md` and the `run_project_loop` docstring). The
result files this script produces are therefore committed to the repository as a
**precondition** of the demo — the equivalent of "a prior SPC charting session already
happened" — and this script exists only to prove they were derived, not invented.

What it does: loads `apps/secom/data/secom.data` through `secom_app.ingest.load_secom`,
runs the chosen sensor column through the existing `secom_app.charts` I-MR engine (which
is itself a thin adapter over `quality_core.spc` — no chart math lives here or there), and
adapts the result field-for-field into `quality_core.project.SPCResultArtifact`.

Only the SPC leg of this example is real SECOM data. The FMEA, Control Plan and Gage R&R
inputs are hand-authored illustrative fixtures — see this example's `README.md`.

Run from the workspace root:

    uv run python examples/secom-quality-loop/scripts/seed_spc_results.py
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import secom_app
from quality_core.project import (
    SCHEMA_VERSION,
    ChartMetric,
    ControlChartPayload,
    ControlChartViolation,
    SPCResultArtifact,
    discover_project,
    spc_result_path,
    write_artifact,
)
from secom_app.charts import SignalControlChart, control_chart_for_signal
from secom_app.ingest import load_secom

#: Which SECOM sensor column stands behind which hand-authored characteristic.
#: `sensor_220` was chosen empirically (see README "Why signal 220"): `select_signals()`
#: keeps it, and its I-MR chart trips three distinct Western Electric rules over the
#: dataset, so the loop has a genuine out-of-control condition to feed back.
SIGNAL_BY_CHARACTERISTIC = {"Etch chamber — Chamber parameter drift": "sensor_220"}

#: Western Electric run rules, matching `SPCResultArtifact.control_chart.rule_set`
#: elsewhere in the project-file contract.
RULE_SET = "Western Electric"

EXAMPLE_ROOT = Path(__file__).resolve().parents[1]
SECOM_DATA = EXAMPLE_ROOT.parents[1] / "apps" / "secom" / "data" / "secom.data"


def _payload(chart: SignalControlChart) -> ControlChartPayload:
    """Adapt one `SignalControlChart` into the project-file control-chart payload.

    Field-for-field only: every number comes from the engine result untouched.
    """
    imr = chart.imr
    return ControlChartPayload(
        chart_label="I-MR (Individuals)",
        stream=chart.signal,
        rule_set=RULE_SET,
        points=list(imr["values"]),
        cl=imr["xbar"],
        ucl=imr["ucl_x"],
        lcl=imr["lcl_x"],
        violations=[
            ControlChartViolation(index=int(v["index"]), rule=str(v["rule"]))
            for v in chart.violations
        ],
        metrics=[
            ChartMetric(label="SECOM signal", value=chart.signal),
            ChartMetric(label="Points charted", value=str(chart.n_used)),
            ChartMetric(label="Sigma (from moving range)", value=f"{imr['sigma_hat']:.6g}"),
            ChartMetric(label="Lag-1 autocorrelation", value=f"{chart.lag1_autocorr:.4f}"),
            ChartMetric(label="Autocorrelation flagged", value=str(chart.autocorr_flag)),
        ],
        secondary_points=None,
    )


def main() -> None:
    dataset = load_secom(SECOM_DATA)
    paths = discover_project(EXAMPLE_ROOT)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for characteristic, signal in SIGNAL_BY_CHARACTERISTIC.items():
        chart = control_chart_for_signal(dataset.features, signal, ruleset="we")
        artifact = SPCResultArtifact(
            schema_version=SCHEMA_VERSION,
            generated_at=stamp,
            generated_by=f"secom_app=={secom_app.__version__} (seed_spc_results.py)",
            kind="control_chart",
            characteristic=characteristic,
            control_chart=_payload(chart),
        )
        path = spc_result_path(paths, characteristic)
        write_artifact(path, artifact)
        print(f"{signal} -> {path} ({len(chart.violations)} violation(s))")


if __name__ == "__main__":
    main()
