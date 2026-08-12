# `secom-app` — stable API

The SECOM semiconductor case-study engine: honest ingest of the vendored SECOM dataset,
signal selection, yield/DPPM, control charts, capability, an observational effect screen,
and a structural Gage R&R applicability check. Engine-only (#206) — there is no UI and no
entry script, and `apps/secom/tests/test_import_boundary.py` enforces that nothing here
imports another app at runtime.

Seven published modules, each with its own `__all__`. Import from the submodule
(`from secom_app.ingest import load_secom`); `secom_app` itself exports only `__version__`.
The fenced manifests below are the machine-checkable copy of those `__all__`s;
`tests/test_api_surface.py` asserts set equality both ways.

Standards note: `secom_app.selection` and `secom_app.doe_screening` implement heuristics for
which **no published standard exists**, and say so in their module docstrings. Treat their
thresholds as declared platform choices, not AIAG requirements.

---

## 1. Stable symbols

### `secom_app.ingest`

```
<!-- STABLE SYMBOLS: secom_app.ingest -->
SecomDataset
load_secom
secom_missingness
IngestError
PASS
FAIL
SECOM_DATA_PATH
SECOM_LABELS_PATH
<!-- END STABLE SYMBOLS -->
```

| Symbol | Kind | Purpose | Source |
|---|---|---|---|
| `SecomDataset` | class | A loaded, row-aligned SECOM study (features + labels). | `apps/secom/secom_app/ingest.py:52` |
| `load_secom` | function | Read the vendored raw files into an aligned, NaN-preserving dataset. | `apps/secom/secom_app/ingest.py:65` |
| `secom_missingness` | function | Per-signal missingness, one row per signal. | `apps/secom/secom_app/ingest.py:113` |
| `IngestError` | class | Re-exported from `quality_core.io`, so a caller catches one exception type. | `packages/quality-core/src/quality_core/io/validate.py:87` |
| `PASS` | constant | Label value `-1` (a passing wafer). | `apps/secom/secom_app/ingest.py:46` |
| `FAIL` | constant | Label value `1` (a failing wafer). | `apps/secom/secom_app/ingest.py:46` |
| `SECOM_DATA_PATH` | constant | Path to the vendored `secom.data`. | `apps/secom/secom_app/ingest.py:42` |
| `SECOM_LABELS_PATH` | constant | Path to the vendored `secom_labels.data`. | `apps/secom/secom_app/ingest.py:43` |

### `secom_app.selection`

```
<!-- STABLE SYMBOLS: secom_app.selection -->
SelectionCriteria
select_signals
MIN_NON_MISSING
NZV_FREQ_RATIO
NZV_PERCENT_UNIQUE
<!-- END STABLE SYMBOLS -->
```

| Symbol | Kind | Purpose | Source |
|---|---|---|---|
| `SelectionCriteria` | class | The three selection thresholds, overridable per call. | `apps/secom/secom_app/selection.py:50` |
| `select_signals` | function | First-pass screen for SPC/capability-amenable signals; returns an audit frame. | `apps/secom/secom_app/selection.py:77` |
| `MIN_NON_MISSING` | constant | Minimum non-missing observations for a usable signal. | `apps/secom/secom_app/selection.py:42` |
| `NZV_FREQ_RATIO` | constant | Near-zero-variance frequency-ratio threshold. | `apps/secom/secom_app/selection.py:46` |
| `NZV_PERCENT_UNIQUE` | constant | Near-zero-variance percent-unique threshold. | `apps/secom/secom_app/selection.py:47` |

### `secom_app.yield_dppm`

```
<!-- STABLE SYMBOLS: secom_app.yield_dppm -->
YieldSummary
yield_summary
failing_signal_pareto
<!-- END STABLE SYMBOLS -->
```

| Symbol | Kind | Purpose | Source |
|---|---|---|---|
| `YieldSummary` | class | Counts, yield fraction/percent, and DPPM for a study. | `apps/secom/secom_app/yield_dppm.py:59` |
| `yield_summary` | function | Pass/fail counts → yield + DPPM (defective **units** PPM, not DPMO). | `apps/secom/secom_app/yield_dppm.py:69` |
| `failing_signal_pareto` | function | Association Pareto (**not** root cause) over kept signals on failed wafers. | `apps/secom/secom_app/yield_dppm.py:103` |

### `secom_app.charts`

```
<!-- STABLE SYMBOLS: secom_app.charts -->
SignalControlChart
control_chart_for_signal
control_charts_for_selection
Ruleset
<!-- END STABLE SYMBOLS -->
```

| Symbol | Kind | Purpose | Source |
|---|---|---|---|
| `SignalControlChart` | class | One signal's I-MR result, violations, and lag-1 autocorrelation flag. | `apps/secom/secom_app/charts.py:70` |
| `control_chart_for_signal` | function | Run one sensor column through the shared I-MR engine (individuals). | `apps/secom/secom_app/charts.py:131` |
| `control_charts_for_selection` | function | Chart every `status == "keep"` signal from a selection audit. | `apps/secom/secom_app/charts.py:185` |
| `Ruleset` | constant (Literal alias) | `Literal["we", "nelson"]` — which rule set to detect against. | `apps/secom/secom_app/charts.py:60` |

### `secom_app.capability`

```
<!-- STABLE SYMBOLS: secom_app.capability -->
SignalCapability
capability_for_signal
<!-- END STABLE SYMBOLS -->
```

| Symbol | Kind | Purpose | Source |
|---|---|---|---|
| `SignalCapability` | class | One signal's capability payload plus its chart and stability verdict. | `apps/secom/secom_app/capability.py:47` |
| `capability_for_signal` | function | Cp/Cpk/Pp/Ppk for one sensor column against caller-supplied limits. | `apps/secom/secom_app/capability.py:58` |

### `secom_app.doe_screening`

```
<!-- STABLE SYMBOLS: secom_app.doe_screening -->
ScreeningResult
screen_signals
ALPHA
MIN_GROUP_N
SCREEN_COLUMNS
<!-- END STABLE SYMBOLS -->
```

| Symbol | Kind | Purpose | Source |
|---|---|---|---|
| `ScreeningResult` | class | Alpha, method, candidate/significant counts, and the screen table. | `apps/secom/secom_app/doe_screening.py:80` |
| `screen_signals` | function | Observational univariate effect screen of pass/fail on candidate signals. | `apps/secom/secom_app/doe_screening.py:99` |
| `ALPHA` | constant | Default significance level (0.05). | `apps/secom/secom_app/doe_screening.py:72` |
| `MIN_GROUP_N` | constant | Minimum per-group n for a signal to be screenable. | `apps/secom/secom_app/doe_screening.py:75` |
| `SCREEN_COLUMNS` | constant | Column order of `ScreeningResult.table`. | `apps/secom/secom_app/doe_screening.py:59` |

### `secom_app.msa`

```
<!-- STABLE SYMBOLS: secom_app.msa -->
GAGE_RR_DIMENSIONS
MsaApplicability
gage_rr_applicability
assert_gage_rr_applicable
<!-- END STABLE SYMBOLS -->
```

| Symbol | Kind | Purpose | Source |
|---|---|---|---|
| `GAGE_RR_DIMENSIONS` | constant | `("part", "appraiser", "trial")` — the crossed-study dimensions SECOM lacks. | `apps/secom/secom_app/msa.py:33` |
| `MsaApplicability` | class | Structural applicability verdict for a would-be Gage R&R frame. | `apps/secom/secom_app/msa.py:51` |
| `gage_rr_applicability` | function | Structural AIAG-MSA applicability check for a frame. | `apps/secom/secom_app/msa.py:60` |
| `assert_gage_rr_applicable` | function | Raise `ValueError` with the AIAG-anchored reason when a frame cannot support Gage R&R. | `apps/secom/secom_app/msa.py:74` |

---

## 2. Signatures

```python
# secom_app.ingest
load_secom(data_path: str | Path = SECOM_DATA_PATH, labels_path: str | Path = SECOM_LABELS_PATH) -> SecomDataset
secom_missingness(features: pd.DataFrame) -> pd.DataFrame

# secom_app.selection
select_signals(features: pd.DataFrame, criteria: SelectionCriteria = SelectionCriteria()) -> pd.DataFrame

# secom_app.yield_dppm
yield_summary(labels: pd.Series) -> YieldSummary
failing_signal_pareto(dataset: SecomDataset, audit: pd.DataFrame, ruleset: Ruleset = "nelson") -> pd.DataFrame

# secom_app.charts
control_chart_for_signal(features: pd.DataFrame, signal: str, ruleset: Ruleset = "nelson") -> SignalControlChart
control_charts_for_selection(features: pd.DataFrame, audit: pd.DataFrame, ruleset: Ruleset = "nelson") -> dict[str, SignalControlChart]

# secom_app.capability
capability_for_signal(features: pd.DataFrame, signal: str, lsl: float | None, usl: float | None, ruleset: Ruleset = "nelson") -> SignalCapability

# secom_app.doe_screening
screen_signals(dataset: SecomDataset, audit: pd.DataFrame, alpha: float = ALPHA) -> ScreeningResult

# secom_app.msa
gage_rr_applicability(features: pd.DataFrame) -> MsaApplicability
assert_gage_rr_applicable(features: pd.DataFrame) -> None
```

---

## 3. I/O types

**Owned by this package** (all frozen dataclasses unless noted):

| Type | Fields | Source |
|---|---|---|
| `SecomDataset` | `features: pd.DataFrame` (NaN preserved), `labels: pd.Series` (values in `{PASS, FAIL}`), `timestamps: pd.Series` — all index-aligned | `apps/secom/secom_app/ingest.py:52` |
| `SelectionCriteria` | `min_non_missing: int = MIN_NON_MISSING`, `nzv_freq_ratio: float = NZV_FREQ_RATIO`, `nzv_percent_unique: float = NZV_PERCENT_UNIQUE` | `apps/secom/secom_app/selection.py:50` |
| `YieldSummary` | `n_total`, `n_pass`, `n_fail`, `yield_fraction`, `yield_pct`, `dppm` | `apps/secom/secom_app/yield_dppm.py:59` |
| `SignalControlChart` | `signal`, `n_used`, `imr: ImrResult`, `violations: list[dict[str, int \| str]]`, `lag1_autocorr`, `autocorr_flag` | `apps/secom/secom_app/charts.py:70` |
| `SignalCapability` | `signal`, `chart: SignalControlChart`, `capability: dict[str, Any]`, `lsl`, `usl`, `stable`, `stability_warning` | `apps/secom/secom_app/capability.py:47` |
| `ScreeningResult` | `alpha`, `method`, `n_candidates`, `n_significant`, `table: pd.DataFrame` (columns = `SCREEN_COLUMNS`) | `apps/secom/secom_app/doe_screening.py:80` |
| `MsaApplicability` | `applicable: bool`, `missing_dimensions: tuple[str, ...]`, `reason: str` | `apps/secom/secom_app/msa.py:51` |
| `Ruleset` | `Literal["we", "nelson"]` | `apps/secom/secom_app/charts.py:60` |

**Owned elsewhere — see that package's `API.md`, not restated here:**

| Type | Owner | Reference |
|---|---|---|
| `ImrResult` (inside `SignalControlChart`) and the capability payload produced by `compute_capability_study` | `quality_core.spc` | `packages/quality-core/API.md` |
| `IngestError` (re-exported by `secom_app.ingest`) | `quality_core.io` | `packages/quality-core/API.md` |

The selection audit and the Pareto are plain `pd.DataFrame`s; `select_signals` documents its
audit columns in its own docstring.

---

## 4. Stability

Zero behaviour change since v0.13.0; this file documents the existing contract, it does not
introduce one.

Going forward: removing a listed symbol, changing a listed signature, or changing the shape
of a listed type is a **breaking** change. Adding a new symbol (to `__all__` and to the
matching manifest block above) is **non-breaking**.
