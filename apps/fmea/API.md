# `fmea-app` — stable API

The FMEA engine surface: the pure-pandas RPN pipeline (`fmea_app.rpn_engine`) and the
data-driven S/O/D rating scales (`fmea_app.rating_scales`). Both are UI-free and import
downward into `quality_core` only.

`fmea_app` itself exports only `__version__` — import from the submodule
(`from fmea_app.rpn_engine import run_pipeline`). Everything else in the package
(`app.py`, `pages/`, `ui/`, `exporter`, `plotly_charts`, `visualizer`) is application
surface, not the published engine contract.

Each module's stable surface is its `__all__`. The fenced manifests below are the
machine-checkable copy; `tests/test_api_surface.py` asserts set equality both ways.

---

## 1. Stable symbols

### `fmea_app.rpn_engine`

```
<!-- STABLE SYMBOLS: fmea_app.rpn_engine -->
validate_input
calculate_rpn
flag_critical
rank_by_rpn
run_pipeline
relational_to_dataframe
run_pipeline_relational
dataframe_to_relational
<!-- END STABLE SYMBOLS -->
```

| Symbol | Kind | Purpose | Source |
|---|---|---|---|
| `validate_input` | function | Schema/type/range check; raises `ValueError` on failure. | `apps/fmea/fmea_app/rpn_engine.py:95` |
| `calculate_rpn` | function | Add the `RPN` column (S × O × D). | `apps/fmea/fmea_app/rpn_engine.py:179` |
| `flag_critical` | function | Apply the AIAG FMEA-4 criticality flags. | `apps/fmea/fmea_app/rpn_engine.py:215` |
| `rank_by_rpn` | function | Sort by RPN descending and assign `Risk_Tier`. | `apps/fmea/fmea_app/rpn_engine.py:279` |
| `run_pipeline` | function | validate → calculate → flag → rank, in one call. | `apps/fmea/fmea_app/rpn_engine.py:336` |
| `relational_to_dataframe` | function | Flatten a `RelationalFMEA` to the flat engine frame. | `apps/fmea/fmea_app/rpn_engine.py:416` |
| `run_pipeline_relational` | function | `run_pipeline` over a `RelationalFMEA`. | `apps/fmea/fmea_app/rpn_engine.py:437` |
| `dataframe_to_relational` | function | Build a `RelationalFMEA` from a flat frame. | `apps/fmea/fmea_app/rpn_engine.py:447` |

`validate_input` is listed deliberately, beyond the seven pipeline functions: a caller that
uses `calculate_rpn`/`flag_critical`/`rank_by_rpn` directly rather than through
`run_pipeline` needs it to get the same validation `run_pipeline` applies for free.

The module's threshold constants (`RPN_HIGH_THRESHOLD`, `SEVERITY_HIGH_THRESHOLD`,
`RPN_ACTION_PRIORITY_H_THRESHOLD`, `RPN_RED_THRESHOLD`, `RPN_YELLOW_MIN`,
`REQUIRED_COLUMNS`, `SCORE_COLUMNS`) are documented in `docs/ASSUMPTIONS_LOG.md` and are
**not** part of the stable surface — they are the engine's own citation-backed settings,
not a consumer knob.

### `fmea_app.rating_scales`

```
<!-- STABLE SYMBOLS: fmea_app.rating_scales -->
RatingScaleSet
load_default_scales
load_legacy_fmea4_scales
load_scales_from_mapping
load_scales_from_json
FACTORS
DEFAULT_SCALES_PATH
LEGACY_FMEA4_SCALES_PATH
<!-- END STABLE SYMBOLS -->
```

| Symbol | Kind | Purpose | Source |
|---|---|---|---|
| `RatingScaleSet` | class | Validated container for the three 1–10 S/O/D scales. | `apps/fmea/fmea_app/rating_scales.py:70` |
| `load_default_scales` | function | Load the bundled AIAG & VDA 2019 PFMEA default scale. | `apps/fmea/fmea_app/rating_scales.py:123` |
| `load_legacy_fmea4_scales` | function | Load the bundled AIAG FMEA-4 legacy scale. | `apps/fmea/fmea_app/rating_scales.py:129` |
| `load_scales_from_mapping` | function | Validate an already-parsed mapping (custom scale). | `apps/fmea/fmea_app/rating_scales.py:161` |
| `load_scales_from_json` | function | Parse + validate raw JSON text/bytes (custom scale upload). | `apps/fmea/fmea_app/rating_scales.py:169` |
| `FACTORS` | constant | `("severity", "occurrence", "detection")`, in display order. | `apps/fmea/fmea_app/rating_scales.py:65` |
| `DEFAULT_SCALES_PATH` | constant | Path to the bundled 2019 PFMEA scale JSON. | `apps/fmea/fmea_app/rating_scales.py:59` |
| `LEGACY_FMEA4_SCALES_PATH` | constant | Path to the bundled FMEA-4 legacy scale JSON. | `apps/fmea/fmea_app/rating_scales.py:62` |

---

## 2. Signatures

### `fmea_app.rpn_engine`

```python
validate_input(df: pd.DataFrame) -> None
calculate_rpn(df: pd.DataFrame) -> pd.DataFrame
flag_critical(df: pd.DataFrame) -> pd.DataFrame
rank_by_rpn(df: pd.DataFrame) -> pd.DataFrame
run_pipeline(df: pd.DataFrame) -> pd.DataFrame
relational_to_dataframe(model: RelationalFMEA) -> pd.DataFrame
run_pipeline_relational(model: RelationalFMEA) -> pd.DataFrame
dataframe_to_relational(df: pd.DataFrame) -> RelationalFMEA
```

### `fmea_app.rating_scales`

```python
load_default_scales() -> RatingScaleSet
load_legacy_fmea4_scales() -> RatingScaleSet
load_scales_from_mapping(obj: dict[str, Any]) -> RatingScaleSet
load_scales_from_json(text: str | bytes, *, max_bytes: int = DEFAULT_MAX_UPLOAD_BYTES) -> RatingScaleSet
```

`RatingScaleSet` also exposes `to_frame(factor: str) -> pd.DataFrame`, which returns a
rating-10→1 display frame for one factor.

---

## 3. I/O types

**Owned by this package:**

| Type | Kind | Source | Used by |
|---|---|---|---|
| `RatingScaleSet` | Pydantic v2 model — `name`, `source`, and `severity`/`occurrence`/`detection` each a complete `dict[int, str]` for ratings 1–10 | `apps/fmea/fmea_app/rating_scales.py:70` | return of every `load_*` scale function |

**Owned elsewhere — see that package's `API.md`, not restated here:**

| Type | Owner | Reference |
|---|---|---|
| `RelationalFMEA`, `FailureMode`, `Function`, `Cause`, `Effect`, `Control`, `FailureLink` | `quality_core.schema` | `packages/quality-core/API.md` |
| `DEFAULT_MAX_UPLOAD_BYTES` (the `load_scales_from_json` byte ceiling) | `quality_core.io` | `packages/quality-core/API.md` |
| `pd.DataFrame` | pandas | — |

The flat engine frame is a plain `pd.DataFrame` with the 11 required FMEA columns; the
column contract is specified in `docs/FMEA_input_schema.md` and enforced by
`fmea_app.schema.FMEARow` / `FMEADataset`.

---

## 4. Stability

Zero behaviour change since v0.13.0; this file documents the existing contract, it does not
introduce one.

Going forward: removing a listed symbol, changing a listed signature, or changing the shape
of a listed type is a **breaking** change. Adding a new symbol (to `__all__` and to the
matching manifest block above) is **non-breaking**.
