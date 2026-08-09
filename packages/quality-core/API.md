# `quality-core` — stable API

The shared, UI-free core. Three published module surfaces: `quality_core.scoring`
(scalar risk scoring), `quality_core.spc` (control charts, capability, rules, phase),
`quality_core.io` (validated ingest + export primitives).

Import from the submodule, not the top level — `from quality_core.spc import compute_xbar_r`,
`from quality_core.io import load_table`, `from quality_core.scoring import rpn`. The
top-level `quality_core` package deliberately exports only `__version__`.

Each module's stable surface is its `__all__`. The fenced manifests below are the
machine-checkable copy of those lists; `tests/test_api_surface.py` asserts set equality in
both directions, so a symbol added or removed without a doc update fails CI.

---

## 1. Stable symbols

### `quality_core.scoring`

```
<!-- STABLE SYMBOLS: quality_core.scoring -->
rpn
action_priority
HIGH
MEDIUM
LOW
BASIS_RPN
BASIS_AP
<!-- END STABLE SYMBOLS -->
```

| Symbol | Kind | Purpose | Source |
|---|---|---|---|
| `rpn` | function | Risk Priority Number = Severity × Occurrence × Detection. | `packages/quality-core/src/quality_core/scoring.py:164` |
| `action_priority` | function | AIAG/VDA 2019 Action Priority lookup for one S/O/D combination. | `packages/quality-core/src/quality_core/scoring.py:179` |
| `HIGH` | constant | `action_priority` return value `"High"`. | `packages/quality-core/src/quality_core/scoring.py:39` |
| `MEDIUM` | constant | `action_priority` return value `"Medium"`. | `packages/quality-core/src/quality_core/scoring.py:40` |
| `LOW` | constant | `action_priority` return value `"Low"`. | `packages/quality-core/src/quality_core/scoring.py:41` |
| `BASIS_RPN` | constant | Prioritization-basis token `"RPN"`. | `packages/quality-core/src/quality_core/scoring.py:47` |
| `BASIS_AP` | constant | Prioritization-basis token `"AP"`. | `packages/quality-core/src/quality_core/scoring.py:48` |

`AP_ORDER` and `_AP_GRID` are internal lookup structures and are **not** part of the
stable surface.

### `quality_core.spc`

```
<!-- STABLE SYMBOLS: quality_core.spc -->
CapabilityStudy
compute_capability
compute_capability_study
normality_test
BOOTSTRAP_RESAMPLES
BOOTSTRAP_SEED
BOXCOX_LAMBDA_CANDIDATES
CAPABILITY_ALPHA
CUSUM_DEFAULT_H
CUSUM_DEFAULT_K
CUSUM_FIR_FRACTION
EWMA_DEFAULT_L
EWMA_DEFAULT_LAMBDA
EWMA_L_BY_LAMBDA
IMR_D2
IMR_D4
IMR_E2
MIN_BASELINE_INDIVIDUALS
MIN_BASELINE_SUBGROUPS
NONNORMAL_LOWER_PCTL
NONNORMAL_UPPER_PCTL
PERCENTILE_FIT_CANDIDATES
SPCChart
XBAR_R_CONSTANTS
XBAR_S_CONSTANTS
NELSON_LABELS
SHEWHART_CHART_TYPES
WE_LABELS
detect_nelson_violations
detect_violations
detect_we_violations
subgroup_rows
CResult
CUSUMResult
EWMAResult
ImrLimits
ImrResult
PResult
UResult
XbarRResult
XbarSResult
compute_c
compute_cusum
compute_ewma
compute_imr
compute_p
compute_u
compute_xbar_r
compute_xbar_s
imr_limits
ExcludedPoint
FrozenLimits
freeze_imr
freeze_xbar_r
freeze_xbar_s
NOT_ASSESSED_NOTE
ChartType
assess_stability
stability_fields
<!-- END STABLE SYMBOLS -->
```

| Symbol | Kind | Purpose | Source |
|---|---|---|---|
| `CapabilityStudy` | class (TypedDict) | Return shape of `compute_capability_study`. | `packages/quality-core/src/quality_core/spc/capability.py:46` |
| `compute_capability` | function | Cp/Cpk/Pp/Ppk (+ CIs) from data and a supplied within-sigma. | `packages/quality-core/src/quality_core/spc/capability.py:78` |
| `compute_capability_study` | function | Full capability study: normality, method selection, indices, stability fields. | `packages/quality-core/src/quality_core/spc/capability.py:144` |
| `normality_test` | function | Shapiro-Wilk normality verdict for a sample. | `packages/quality-core/src/quality_core/spc/capability.py:131` |
| `BOOTSTRAP_RESAMPLES` | constant | Bootstrap resample count for non-normal CIs. | `packages/quality-core/src/quality_core/spc/constants.py:77` |
| `BOOTSTRAP_SEED` | constant | Fixed seed making bootstrap CIs reproducible. | `packages/quality-core/src/quality_core/spc/constants.py:76` |
| `BOXCOX_LAMBDA_CANDIDATES` | constant | Box-Cox lambda grid. | `packages/quality-core/src/quality_core/spc/constants.py:70` |
| `CAPABILITY_ALPHA` | constant | Default confidence level alpha for capability CIs. | `packages/quality-core/src/quality_core/spc/constants.py:69` |
| `CUSUM_DEFAULT_H` | constant | Default CUSUM decision interval H. | `packages/quality-core/src/quality_core/spc/constants.py:65` |
| `CUSUM_DEFAULT_K` | constant | Default CUSUM reference value k. | `packages/quality-core/src/quality_core/spc/constants.py:64` |
| `CUSUM_FIR_FRACTION` | constant | Fast-initial-response head start fraction. | `packages/quality-core/src/quality_core/spc/constants.py:66` |
| `EWMA_DEFAULT_L` | constant | Default EWMA control-limit width L. | `packages/quality-core/src/quality_core/spc/constants.py:51` |
| `EWMA_DEFAULT_LAMBDA` | constant | Default EWMA smoothing constant. | `packages/quality-core/src/quality_core/spc/constants.py:50` |
| `EWMA_L_BY_LAMBDA` | constant | Published L values keyed by lambda. | `packages/quality-core/src/quality_core/spc/constants.py:55` |
| `IMR_D2` | constant | AIAG d2 for n = 2 (moving range). | `packages/quality-core/src/quality_core/spc/constants.py:43` |
| `IMR_D4` | constant | AIAG D4 for the moving-range chart. | `packages/quality-core/src/quality_core/spc/constants.py:42` |
| `IMR_E2` | constant | AIAG E2 for the individuals chart. | `packages/quality-core/src/quality_core/spc/constants.py:41` |
| `MIN_BASELINE_INDIVIDUALS` | constant | Minimum individuals for a Phase I baseline. | `packages/quality-core/src/quality_core/spc/constants.py:47` |
| `MIN_BASELINE_SUBGROUPS` | constant | Minimum subgroups for a Phase I baseline. | `packages/quality-core/src/quality_core/spc/constants.py:46` |
| `NONNORMAL_LOWER_PCTL` | constant | Lower percentile for the non-normal capability method. | `packages/quality-core/src/quality_core/spc/constants.py:71` |
| `NONNORMAL_UPPER_PCTL` | constant | Upper percentile for the non-normal capability method. | `packages/quality-core/src/quality_core/spc/constants.py:72` |
| `PERCENTILE_FIT_CANDIDATES` | constant | Distribution families tried by the percentile method. | `packages/quality-core/src/quality_core/spc/constants.py:74` |
| `SPCChart` | constant (Literal alias) | The platform-wide chart vocabulary. | `packages/quality-core/src/quality_core/spc/constants.py:83` |
| `XBAR_R_CONSTANTS` | constant | AIAG A2/D3/D4/d2 by subgroup size. | `packages/quality-core/src/quality_core/spc/constants.py:13` |
| `XBAR_S_CONSTANTS` | constant | AIAG A3/B3/B4/c4 by subgroup size (n ≤ 12). | `packages/quality-core/src/quality_core/spc/constants.py:26` |
| `NELSON_LABELS` | constant | Rule-key → Nelson rule label. | `packages/quality-core/src/quality_core/spc/rule_detection.py:35` |
| `SHEWHART_CHART_TYPES` | constant | Chart types the rule sets apply to. | `packages/quality-core/src/quality_core/spc/rule_detection.py:24` |
| `WE_LABELS` | constant | Rule-key → Western Electric rule label. | `packages/quality-core/src/quality_core/spc/rule_detection.py:29` |
| `detect_nelson_violations` | function | Nelson rule violations for a point series. | `packages/quality-core/src/quality_core/spc/rule_detection.py:73` |
| `detect_violations` | function | Run WE/Nelson rules for Shewhart chart types only. | `packages/quality-core/src/quality_core/spc/rule_detection.py:43` |
| `detect_we_violations` | function | Western Electric rule violations for a point series. | `packages/quality-core/src/quality_core/spc/rule_detection.py:65` |
| `subgroup_rows` | function | Group a tidy frame into per-subgroup value lists. | `packages/quality-core/src/quality_core/spc/utils.py:12` |
| `CResult` | class (TypedDict) | `compute_c` return shape. | `packages/quality-core/src/quality_core/spc/control_charts.py:89` |
| `CUSUMResult` | class (TypedDict) | `compute_cusum` return shape. | `packages/quality-core/src/quality_core/spc/control_charts.py:119` |
| `EWMAResult` | class (TypedDict) | `compute_ewma` return shape. | `packages/quality-core/src/quality_core/spc/control_charts.py:105` |
| `ImrLimits` | class (TypedDict) | `imr_limits` return shape. | `packages/quality-core/src/quality_core/spc/control_charts.py:72` |
| `ImrResult` | class (TypedDict) | `compute_imr` return shape. | `packages/quality-core/src/quality_core/spc/control_charts.py:60` |
| `PResult` | class (TypedDict) | `compute_p` return shape. | `packages/quality-core/src/quality_core/spc/control_charts.py:80` |
| `UResult` | class (TypedDict) | `compute_u` return shape. | `packages/quality-core/src/quality_core/spc/control_charts.py:96` |
| `XbarRResult` | class (TypedDict) | `compute_xbar_r` return shape. | `packages/quality-core/src/quality_core/spc/control_charts.py:36` |
| `XbarSResult` | class (TypedDict) | `compute_xbar_s` return shape. | `packages/quality-core/src/quality_core/spc/control_charts.py:48` |
| `compute_c` | function | c chart (defect counts, constant sample). | `packages/quality-core/src/quality_core/spc/control_charts.py:302` |
| `compute_cusum` | function | Tabular CUSUM chart. | `packages/quality-core/src/quality_core/spc/control_charts.py:379` |
| `compute_ewma` | function | EWMA chart. | `packages/quality-core/src/quality_core/spc/control_charts.py:340` |
| `compute_imr` | function | Individuals + moving-range chart. | `packages/quality-core/src/quality_core/spc/control_charts.py:243` |
| `compute_p` | function | p chart (defective proportion, variable sample). | `packages/quality-core/src/quality_core/spc/control_charts.py:280` |
| `compute_u` | function | u chart (defects per unit, variable sample). | `packages/quality-core/src/quality_core/spc/control_charts.py:318` |
| `compute_xbar_r` | function | X-bar/R chart. | `packages/quality-core/src/quality_core/spc/control_charts.py:134` |
| `compute_xbar_s` | function | X-bar/S chart. | `packages/quality-core/src/quality_core/spc/control_charts.py:179` |
| `imr_limits` | function | I-MR limits + within-sigma from a centre line and MR-bar. | `packages/quality-core/src/quality_core/spc/control_charts.py:222` |
| `ExcludedPoint` | class (TypedDict) | One baseline point excluded when freezing limits. | `packages/quality-core/src/quality_core/spc/phase.py:30` |
| `FrozenLimits` | class (TypedDict) | Phase I limits frozen for Phase II monitoring. | `packages/quality-core/src/quality_core/spc/phase.py:35` |
| `freeze_imr` | function | Freeze I-MR limits from a baseline. | `packages/quality-core/src/quality_core/spc/phase.py:121` |
| `freeze_xbar_r` | function | Freeze X-bar/R limits from a baseline. | `packages/quality-core/src/quality_core/spc/phase.py:55` |
| `freeze_xbar_s` | function | Freeze X-bar/S limits from a baseline. | `packages/quality-core/src/quality_core/spc/phase.py:88` |
| `NOT_ASSESSED_NOTE` | constant | Note used when stability was not assessed. | `packages/quality-core/src/quality_core/spc/stability.py:32` |
| `ChartType` | constant (Literal alias) | Chart types `assess_stability` accepts. | `packages/quality-core/src/quality_core/spc/stability.py:30` |
| `assess_stability` | function | Within-subgroup sigma-hat + rule violations for a frame. | `packages/quality-core/src/quality_core/spc/stability.py:40` |
| `stability_fields` | function | Tri-state `(stable, stability_note)` for a capability study. | `packages/quality-core/src/quality_core/spc/stability.py:95` |

### `quality_core.io`

```
<!-- STABLE SYMBOLS: quality_core.io -->
FORMULA_PREFIXES
now
generated_line
fmt
fmt_opt
sanitize_cell
sanitize_for_export
export_csv
safe_text
write_table_sheet
write_keyvalue_sheet
render_table
add_image_page
pdf_title
pdf_subheader
pdf_summary_cells
IngestError
TableSchema
DEFAULT_MAX_UPLOAD_BYTES
DEFAULT_MAX_ROWS
DEFAULT_MAX_COLUMNS
read_table
read_table_from_path
validate_table
load_table
load_table_from_path
<!-- END STABLE SYMBOLS -->
```

| Symbol | Kind | Purpose | Source |
|---|---|---|---|
| `FORMULA_PREFIXES` | constant | Characters escaped to prevent spreadsheet formula injection. | `packages/quality-core/src/quality_core/io/export.py:64` |
| `now` | function | Current timestamp as `YYYY-MM-DD HH:MM:SS`. | `packages/quality-core/src/quality_core/io/export.py:35` |
| `generated_line` | function | "Generated: … / detail" caption line for PDF sub-headers. | `packages/quality-core/src/quality_core/io/export.py:40` |
| `fmt` | function | Format a float to a fixed decimal string. | `packages/quality-core/src/quality_core/io/export.py:45` |
| `fmt_opt` | function | Format an optional float, `"N/A"` when `None`. | `packages/quality-core/src/quality_core/io/export.py:50` |
| `sanitize_cell` | function | Escape one formula-injection-risky value. | `packages/quality-core/src/quality_core/io/export.py:103` |
| `sanitize_for_export` | function | Escape risky string cells and column labels in a copy of a frame. | `packages/quality-core/src/quality_core/io/export.py:116` |
| `export_csv` | function | DataFrame → UTF-8 CSV bytes with injection escaping. | `packages/quality-core/src/quality_core/io/export.py:133` |
| `safe_text` | function | Latin-1-safe text for fpdf2 core fonts. | `packages/quality-core/src/quality_core/io/export.py:258` |
| `write_table_sheet` | function | Write a styled table into an openpyxl worksheet. | `packages/quality-core/src/quality_core/io/export.py:147` |
| `write_keyvalue_sheet` | function | Write a two-column metadata sheet. | `packages/quality-core/src/quality_core/io/export.py:208` |
| `render_table` | function | Render a bordered table into a PDF. | `packages/quality-core/src/quality_core/io/export.py:266` |
| `add_image_page` | function | Add a landscape PDF page with a title bar and embedded PNG. | `packages/quality-core/src/quality_core/io/export.py:312` |
| `pdf_title` | function | Full-width coloured PDF title bar. | `packages/quality-core/src/quality_core/io/export.py:339` |
| `pdf_subheader` | function | Centred grey PDF caption line. | `packages/quality-core/src/quality_core/io/export.py:355` |
| `pdf_summary_cells` | function | One row of labelled PDF metric cells. | `packages/quality-core/src/quality_core/io/export.py:363` |
| `IngestError` | class | User-facing ingest failure, message safe to display as-is. | `packages/quality-core/src/quality_core/io/validate.py:87` |
| `TableSchema` | class | A per-tool ingest contract: how to validate one uploaded table. | `packages/quality-core/src/quality_core/io/validate.py:96` |
| `DEFAULT_MAX_UPLOAD_BYTES` | constant | Upload byte ceiling (20 MiB). | `packages/quality-core/src/quality_core/io/validate.py:62` |
| `DEFAULT_MAX_ROWS` | constant | Row ceiling for an ingested table. | `packages/quality-core/src/quality_core/io/validate.py:68` |
| `DEFAULT_MAX_COLUMNS` | constant | Column ceiling for an ingested table. | `packages/quality-core/src/quality_core/io/validate.py:72` |
| `read_table` | function | Read a `.csv`/`.xlsx` upload into a DataFrame (friendly errors only). | `packages/quality-core/src/quality_core/io/validate.py:202` |
| `read_table_from_path` | function | Read a `.csv`/`.xlsx` file from a trusted path. | `packages/quality-core/src/quality_core/io/validate.py:295` |
| `validate_table` | function | Validate a frame against a `TableSchema`; return the validated columns. | `packages/quality-core/src/quality_core/io/validate.py:390` |
| `load_table` | function | `read_table` + `validate_table` in one call. | `packages/quality-core/src/quality_core/io/validate.py:458` |
| `load_table_from_path` | function | `read_table_from_path` + `validate_table` in one call. | `packages/quality-core/src/quality_core/io/validate.py:483` |

---

## 2. Signatures

### `quality_core.scoring`

```python
rpn(severity: int, occurrence: int, detection: int) -> int
action_priority(severity: int, occurrence: int, detection: int) -> str
```

### `quality_core.spc`

```python
compute_capability(data: np.ndarray | list[float], lsl: float | None, usl: float | None, sigma_hat: float, *, alpha: float = 0.05) -> dict[str, Any]
compute_capability_study(data: np.ndarray | list[float] | list[list[float]], lsl: float | None, usl: float | None, *, alpha: float = 0.05, allow_yeojohnson: bool = True, force_method: Literal["auto", "normal", "boxcox", "percentile"] = "auto", violations: Sequence[Mapping[str, int | str]] | None = None) -> CapabilityStudy
normality_test(data: np.ndarray | list[float]) -> dict[str, Any]
detect_nelson_violations(points: list[float], cl: float, sigma: float) -> list[dict[str, int | str]]
detect_violations(chart_type: str, points: list[float], cl: float, sigma: float, rule_set: str) -> list[dict[str, int | str]]
detect_we_violations(points: list[float], cl: float, sigma: float) -> list[dict[str, int | str]]
subgroup_rows(frame: pd.DataFrame) -> list[list[float]]
compute_c(defect_counts: list[float]) -> CResult
compute_cusum(values: list[float], mu0: float, sigma: float, k: float = 0.5, h: float = 5.0, fir: bool = False) -> CUSUMResult
compute_ewma(values: list[float], mu0: float, sigma: float, lam: float = 0.2, L: float = 2.86) -> EWMAResult
compute_imr(values: list[float], frozen: FrozenLimits | None = None) -> ImrResult
compute_p(defective_counts: list[float], sample_sizes: list[float]) -> PResult
compute_u(defect_counts: list[float], sample_sizes: list[float]) -> UResult
compute_xbar_r(subgroups: list[list[float]], frozen: FrozenLimits | None = None) -> XbarRResult
compute_xbar_s(subgroups: list[list[float]], frozen: FrozenLimits | None = None) -> XbarSResult
imr_limits(xbar: float, mrbar: float) -> ImrLimits
freeze_imr(baseline: list[float], *, excluded: Sequence[ExcludedPoint] = (), phase_i_range: tuple[str, str] | None = None, frozen_at: str | None = None) -> FrozenLimits
freeze_xbar_r(baseline: list[list[float]], *, excluded: Sequence[ExcludedPoint] = (), phase_i_range: tuple[str, str] | None = None, frozen_at: str | None = None) -> FrozenLimits
freeze_xbar_s(baseline: list[list[float]], *, excluded: Sequence[ExcludedPoint] = (), phase_i_range: tuple[str, str] | None = None, frozen_at: str | None = None) -> FrozenLimits
assess_stability(frame: pd.DataFrame, chart_type: ChartType = "I-MR", *, rule_set: str = "Western Electric") -> tuple[float, list[dict[str, int | str]]]
stability_fields(violations: Sequence[Mapping[str, int | str]] | None) -> tuple[bool | None, str | None]
```

### `quality_core.io`

```python
now() -> str
generated_line(detail: str) -> str
fmt(value: float, precision: int = 4) -> str
fmt_opt(value: float | None, precision: int = 4) -> str
sanitize_cell(value: Any) -> Any
sanitize_for_export(df: pd.DataFrame) -> pd.DataFrame
export_csv(df: pd.DataFrame) -> bytes
safe_text(s: object) -> str
write_table_sheet(ws: Any, df: pd.DataFrame, *, title: str, columns: Sequence[str], col_widths: Mapping[str, float], row_fill_hex: Callable[[pd.Series], str | None] | None = None, header_fill_hex: str = "2C3E50", default_width: float = 14, header_height: float = 22, freeze: str | None = "A2") -> None
write_keyvalue_sheet(ws: Any, rows: Sequence[tuple[str, object]], *, title: str | None = None, key_width: float = 22, value_width: float = 48) -> None
render_table(pdf: Any, df: pd.DataFrame, *, columns: Sequence[tuple[str, float]], row_values: Callable[[pd.Series], Sequence[str]], row_rgb: Callable[[pd.Series], tuple[int, int, int]], header_fill_rgb: tuple[int, int, int] = (44, 62, 80), header_font_size: float = 8, row_font_size: float = 7, row_height: float = 6) -> None
add_image_page(pdf: Any, png_path: str, title: str, *, header_fill_rgb: tuple[int, int, int] = (44, 62, 80), image_width: float = 277) -> None
pdf_title(pdf: Any, title: str, *, fill_rgb: tuple[int, int, int] = (44, 62, 80), font_size: float = 16, height: float = 10) -> None
pdf_subheader(pdf: Any, text: str, *, font_size: float = 9) -> None
pdf_summary_cells(pdf: Any, cells: Sequence[tuple[str, str]], *, fill_rgb: tuple[int, int, int] = (240, 243, 246), label_rgb: tuple[int, int, int] = (44, 62, 80)) -> None
read_table(source: Source, *, filename: str | None = None, max_bytes: int | None = DEFAULT_MAX_UPLOAD_BYTES, max_rows: int | None = DEFAULT_MAX_ROWS, max_columns: int | None = DEFAULT_MAX_COLUMNS) -> pd.DataFrame
read_table_from_path(path: PathSource, *, max_bytes: int | None = DEFAULT_MAX_UPLOAD_BYTES, max_rows: int | None = DEFAULT_MAX_ROWS, max_columns: int | None = DEFAULT_MAX_COLUMNS) -> pd.DataFrame
validate_table(df: pd.DataFrame, schema: TableSchema) -> pd.DataFrame
load_table(source: Source, schema: TableSchema, *, filename: str | None = None, max_bytes: int | None = DEFAULT_MAX_UPLOAD_BYTES, max_rows: int | None = DEFAULT_MAX_ROWS, max_columns: int | None = DEFAULT_MAX_COLUMNS) -> pd.DataFrame
load_table_from_path(path: PathSource, schema: TableSchema, *, max_bytes: int | None = DEFAULT_MAX_UPLOAD_BYTES, max_rows: int | None = DEFAULT_MAX_ROWS, max_columns: int | None = DEFAULT_MAX_COLUMNS) -> pd.DataFrame
```

---

## 3. I/O types

All types below are **owned by `quality-core`** and defined here.

| Type | Kind | Owner | Used by |
|---|---|---|---|
| `CapabilityStudy` | `TypedDict` (`spc/capability.py:46`) | `quality-core` | return of `compute_capability_study` |
| `XbarRResult`, `XbarSResult`, `ImrResult`, `ImrLimits`, `PResult`, `CResult`, `UResult`, `EWMAResult`, `CUSUMResult` | `TypedDict` (`spc/control_charts.py`) | `quality-core` | returns of the `compute_*` chart functions and `imr_limits` |
| `FrozenLimits`, `ExcludedPoint` | `TypedDict` (`spc/phase.py`) | `quality-core` | returns/arguments of `freeze_*`, `compute_xbar_r/s`, `compute_imr` |
| `SPCChart` | `Literal["Xbar-R", "Xbar-S", "I-MR", "p", "c", "u"]` (`spc/constants.py:83`) | `quality-core` | the platform-wide chart vocabulary; re-exported by `controlplan_app.schema` |
| `ChartType` | `Literal["Xbar-R", "Xbar-S", "I-MR"]` (`spc/stability.py:30`) | `quality-core` | argument of `assess_stability` |
| `TableSchema` | dataclass (`io/validate.py:96`) | `quality-core` | argument of `validate_table` / `load_table*` |
| `IngestError` | exception (`io/validate.py:87`) | `quality-core` | raised by every ingest entry point |

`Source` / `PathSource` in the signatures above are internal type aliases for the accepted
upload/path inputs (`str | bytes | os.PathLike | BinaryIO`-shaped); they are not exported
names and callers pass ordinary paths or file objects.

Violation records are plain `list[dict[str, int | str]]`; there is no dedicated type.

`quality_core.schema` (`RelationalFMEA`, `FailureMode`, `Function`, `Cause`, `Effect`,
`Control`, `FailureLink`, `FMEARow`, `FMEADataset`) is a separate already-published surface
with its own `__all__`; it is not part of the three manifests above and is unchanged by #261.

---

## 4. Stability

Zero behaviour change since v0.13.0; this file documents the existing contract, it does not
introduce one.

Going forward: removing a listed symbol, changing a listed signature, or changing the shape
of a listed type is a **breaking** change. Adding a new symbol (to `__all__` and to the
matching manifest block above) is **non-breaking**.
