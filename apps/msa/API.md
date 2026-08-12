# `msa-app` — stable API

The Measurement System Analysis engine: crossed Gage R&R by the AIAG Average-and-Range
method (default) or ANOVA. One published module, `msa_app.gage_rr_engine`; it is UI-free
and imports downward into `quality_core` only.

`msa_app` itself exports only `__version__` — import from the submodule
(`from msa_app.gage_rr_engine import compute_gage_rr`). `msa_app.schema`,
`msa_app.exporter` and `msa_app.pages` are application surface, not the published engine
contract.

The stable surface is the module's `__all__`. The fenced manifest below is the
machine-checkable copy; `tests/test_api_surface.py` asserts set equality both ways.

---

## 1. Stable symbols

### `msa_app.gage_rr_engine`

```
<!-- STABLE SYMBOLS: msa_app.gage_rr_engine -->
METHOD
METHOD_ANOVA
METHOD_NOTE
METHOD_NOTE_ANOVA
compute_gage_rr
<!-- END STABLE SYMBOLS -->
```

| Symbol | Kind | Purpose | Source |
|---|---|---|---|
| `METHOD` | constant | `"average_and_range"` — the default AIAG technique. | `apps/msa/msa_app/gage_rr_engine.py:78` |
| `METHOD_ANOVA` | constant | `"anova"` — the crossed two-factor ANOVA technique (#195). | `apps/msa/msa_app/gage_rr_engine.py:87` |
| `METHOD_NOTE` | constant | What Average-and-Range can and cannot see (no part × appraiser interaction). | `apps/msa/msa_app/gage_rr_engine.py:79` |
| `METHOD_NOTE_ANOVA` | constant | What the ANOVA technique estimates and tests. | `apps/msa/msa_app/gage_rr_engine.py:107` |
| `compute_gage_rr` | function | The whole AIAG computation: EV/AV/GRR/PV/TV, percentages, ndc, verdict. | `apps/msa/msa_app/gage_rr_engine.py:118` |

---

## 2. Signatures

```python
compute_gage_rr(data: pd.DataFrame | list[dict], tolerance: float | None = None, method: str = METHOD) -> dict[str, Any]
```

---

## 3. I/O types

**Input.** `data` is a long/tidy table — one row per measurement — as a `pd.DataFrame` or a
list of dicts, with the columns/keys `part`, `appraiser`, `trial`, `measurement`.
`tolerance` is the study-level `USL - LSL`; when `None`, only the study-variation
percentages are computed. `method` is `METHOD` or `METHOD_ANOVA`; any other value raises
`ValueError`.

**Output.** `compute_gage_rr` returns an **untyped `dict[str, Any]`** — there is no
`TypedDict` or dataclass for it today, and #261 deliberately does not add one (that would
be a behaviour-adjacent change). The key shape below is transcribed from the function's
docstring and is **documentation only**; it is not statically enforced.

| Key | Type | Meaning |
|---|---|---|
| `ev` | `float` | Repeatability / Equipment Variation |
| `av` | `float` | Reproducibility / Appraiser Variation |
| `grr` | `float` | `sqrt(EV² + AV²)`; `sqrt(EV² + AV² + INT²)` under `"anova"` |
| `pev_study` | `float` | %EV vs study variation (`inf` if TV == 0) |
| `pav_study` | `float` | %AV vs study variation (`inf` if TV == 0) |
| `pgrr_study` | `float` | %GRR vs study variation (`inf` if TV == 0) |
| `ppv_study` | `float` | %PV vs study variation (`inf` if TV == 0) |
| `pev_tolerance` | `float \| None` | %EV vs tolerance; `None` when no tolerance was supplied |
| `pav_tolerance` | `float \| None` | %AV vs tolerance; `None` when no tolerance was supplied |
| `pgrr_tolerance` | `float \| None` | %GRR vs tolerance; `None` when no tolerance was supplied |
| `ppv_tolerance` | `float \| None` | %PV vs tolerance; deliberately unclamped, may exceed 100% |
| `ndc` | `int` | Number of Distinct Categories |
| `verdict` | `str` | `"Accept"`, `"Marginal"`, or `"Reject"` |
| `tv` | `float` | Total Variation = `sqrt(GRR² + PV²)` |
| `pv` | `float` | Part Variation |
| `mean` | `float` | Overall mean of all measurements |
| `n_parts` | `int` | Unique parts |
| `n_appraisers` | `int` | Unique appraisers |
| `n_trials` | `int` | Replications per (part, appraiser) cell |
| `is_balanced` | `bool` | Every (part, appraiser) pair has `n_trials` measurements |
| `method` | `str` | `METHOD` or `METHOD_ANOVA` — the technique that actually ran |
| `method_note` | `str` | `METHOD_NOTE` / `METHOD_NOTE_ANOVA` |
| `interaction` | `float \| None` | σ of the part × appraiser interaction; `None` under Average-and-Range — branch on `is not None`, not truthiness |
| `interaction_f` | `float \| None` | Interaction F statistic (`MS_AxP / MS_e`); `None` under Average-and-Range |
| `interaction_significant` | `bool \| None` | Whether the interaction was **not** pooled at α = 0.05; `None` under Average-and-Range |

`ValueError` is raised for empty data, fewer than 2 parts/appraisers/replicates, a
zero/negative/NaN/inf tolerance, or an unsupported `method`.

No type from another package appears in this signature.

---

## 4. Stability

Zero behaviour change since v0.13.0; this file documents the existing contract, it does not
introduce one.

Going forward: removing a listed symbol, changing a listed signature, or changing the shape
of a listed type — including a key of the returned dict — is a **breaking** change. Adding a
new symbol (to `__all__` and to the manifest block above) is **non-breaking**.
