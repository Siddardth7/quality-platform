# SPC Manufacturing Quality Dashboard

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.50%2B-FF4B4B?logo=streamlit&logoColor=white)
![Tests](https://img.shields.io/badge/tests-83%20passing-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/Status-Live-brightgreen)

A multi-page Streamlit application for **Statistical Process Control (SPC)** built around aerospace and composites manufacturing scenarios. The app makes classical SPC behaviour visible and interactive: you can inspect five real process streams, compare Western Electric and Nelson rule sets side by side, quantify capability against AIAG targets, and watch special-cause patterns emerge in a real-time disturbance simulator.

**Live demo:** [manufacturing-spc-dashboard.streamlit.app](https://manufacturing-spc-dashboard-k8hyyj2fylnvjfrpcgqhyr.streamlit.app)
**Repository:** [github.com/Siddardth7/manufacturing-spc-dashboard](https://github.com/Siddardth7/manufacturing-spc-dashboard)

---

## Table of Contents

1. [What This App Does](#what-this-app-does)
2. [Quick Start](#quick-start)
3. [Project Architecture](#project-architecture)
4. [Module Reference](#module-reference)
5. [Demo Dataset](#demo-dataset)
6. [Control Charts Reference](#control-charts-reference)
7. [Rule Detection Reference](#rule-detection-reference)
8. [Process Capability Reference](#process-capability-reference)
9. [Running Tests](#running-tests)
10. [Deployment](#deployment)
11. [Extending the App](#extending-the-app)
12. [SPC Primer](#spc-primer)
13. [Standards](#standards)

---

## What This App Does

| Page | Purpose | Key Output |
|---|---|---|
| **Control Charts** | Variable and attribute charts for five manufacturing streams with rule overlays | Interactive Plotly chart — UCL/LCL/CL + violation markers |
| **Process Capability** | Cp, Cpk, Pp, Ppk with distribution histogram and normality feedback | Cpk gauge, capability table, Shapiro-Wilk result |
| **Live Simulation** | Real-time subgroup generation with injected disturbances | Animated chart, active disturbance status, violation count |

All three pages share the same `src/spc_engine/` math library. No external database is required — everything runs from a single committed CSV file that is auto-regenerated if missing.

---

## Quick Start

### Prerequisites

- Python 3.11 or later
- `pip` / `venv`

### Install and run

```bash
# 1. Clone the repo
git clone https://github.com/Siddardth7/manufacturing-spc-dashboard.git
cd manufacturing-spc-dashboard

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

Open the URL printed by Streamlit (default: `http://localhost:8501`).

### Run tests

```bash
pytest tests/ -v
```

Expected: 83 tests pass in under 3 seconds.

---

## Project Architecture

```
manufacturing-spc-dashboard/
│
├── app.py                          Landing page — navigation and standards overview
│
├── pages/
│   ├── 1_Control_Charts.py         Chart selector, rule overlay rendering, CSV upload
│   ├── 2_Process_Capability.py     Capability indices, histogram, normality test
│   └── 3_Live_Simulation.py        Real-time loop, disturbance injection buttons
│
├── src/
│   ├── spc_engine/
│   │   ├── control_charts.py       UCL/LCL/CL math for all five chart types
│   │   ├── rule_detection.py       Western Electric (1–4) + Nelson (5–8)
│   │   ├── capability.py           Cp/Cpk/Pp/Ppk + Shapiro-Wilk
│   │   ├── constants.py            AIAG SPC constants (A2 d2 D3 D4 c4 B3 B4 E2)
│   │   ├── data_generator.py       Deterministic demo CSV generator (seed=42)
│   │   └── utils.py                Shared subgroup_rows() groupby helper
│   ├── simulation/
│   │   └── engine.py               SimulationEngine — step, inject, reset
│   └── ui/
│       └── theme.py                CSS injection + Plotly layout constants
│
├── tests/
│   ├── test_control_charts.py      UCL/LCL/CL formula correctness
│   ├── test_rule_detection.py      All rule fire / no-fire cases
│   ├── test_capability.py          Cp/Cpk/Pp/Ppk + normality edge cases
│   ├── test_data_generator.py      Schema and value range checks
│   ├── test_utils.py               subgroup_rows helper
│   └── test_visualizer.py          Gauge figure guard for None cpk
│
├── data/
│   └── demo_composites_aerospace.csv   370-row committed demo dataset (auto-regenerates)
│
├── requirements.txt
└── .streamlit/config.toml
```

### Data flow

```
CSV on disk / uploaded file
        │
        ▼
  pd.read_csv()  ──── @st.cache_data ────▶  stream filter
                                                   │
                                                   ▼
                                      spc_engine/control_charts.py
                                      compute_xbar_r / compute_p / …
                                                   │
                                                   ▼
                                      spc_engine/rule_detection.py
                                      detect_we_violations / detect_nelson_violations
                                                   │
                                                   ▼
                                      src/visualizer.py
                                      build_control_chart / build_capability_histogram
                                                   │
                                                   ▼
                                          st.plotly_chart()
```

---

## Module Reference

### `src/spc_engine/control_charts.py`

All functions accept Python lists and return a `dict` of scalars and lists.

| Function | Inputs | Key outputs |
|---|---|---|
| `compute_xbar_r(subgroups)` | `list[list[float]]`, n = 2–10 | `xbarbar`, `rbar`, `sigma_hat`, `ucl_x`, `lcl_x`, `ucl_r`, `lcl_r` |
| `compute_xbar_s(subgroups)` | `list[list[float]]`, n = 2–12 | `xbarbar`, `sbar`, `sigma_hat`, `ucl_x`, `lcl_x`, `ucl_s`, `lcl_s` |
| `compute_imr(values)` | `list[float]`, len ≥ 2 | `xbar`, `mrbar`, `sigma_hat`, `ucl_x`, `lcl_x`, `ucl_mr`, `lcl_mr` |
| `compute_p(counts, sizes)` | two `list[float]` | `pbar`, `proportions`, `ucl[]`, `lcl[]` |
| `compute_u(counts, sizes)` | two `list[float]` | `ubar`, `u_values`, `ucl[]`, `lcl[]` |

All functions raise `ValueError` for invalid inputs (wrong dimensionality, unsupported subgroup size, mismatched arrays, non-positive sample sizes).

### `src/spc_engine/rule_detection.py`

```python
violations = detect_we_violations(points, cl=centerline, sigma=sigma_xbar)
violations = detect_nelson_violations(points, cl=centerline, sigma=sigma_xbar)
```

Each returns `list[{"index": int, "rule": str}]`.
`detect_nelson_violations` is a strict superset — it runs all four WE rules then adds Nelson 5–8.

**Which sigma to pass:**
- Xbar chart → `sigma_x̄ = sigma_hat / √n`
- I-MR chart → `sigma_hat` directly (n = 1)
- p chart → `sqrt(pbar * (1 - pbar) / avg_n)`
- u chart → `sqrt(ubar / avg_n)`

### `src/spc_engine/capability.py`

```python
result = compute_capability(values, lsl=9.5, usl=10.5, sigma_hat=0.1)
# Returns: cp, cpk, pp, ppk, mean, sigma_hat, sigma_overall
# Any of cp/cpk/pp/ppk is None when the required spec limit is absent.

normality = normality_test(values)
# Returns: w_stat, p_value, is_normal (bool, threshold p > 0.05)
# Requires at least 3 values.
```

### `src/simulation/engine.py`

```python
engine = SimulationEngine(process_stream="Composites", subgroup_size=5, rng_seed=42)
engine.step()                                      # → list[float], appended to engine.history
engine.inject_mean_shift(magnitude_sigma=1.5, duration=10)
engine.inject_spike(magnitude_sigma=4.0)
engine.inject_drift(max_sigma=2.0, duration=15)
engine.reset_disturbance()
engine.reset()                                     # clears history, re-seeds RNG
```

`engine.history` → `list[list[float]]` (all subgroups since last reset)
`engine.active_disturbance` → `DisturbanceState | None` with `.kind`, `.magnitude_sigma`, `.steps_remaining`

Available process streams: `"Composites"` (ply thickness, σ = 0.001 mm), `"Machining"` (hole diameter, σ = 0.005 mm).

---

## Demo Dataset

File: `data/demo_composites_aerospace.csv` (370 rows, deterministic seed = 42)

Auto-regenerated at startup if deleted. Source: `src/spc_engine/data_generator.py`.

### Schema

| Column | Type | Description |
|---|---|---|
| `stream` | str | Logical dataset identifier |
| `parameter` | str | Human-readable measurement label |
| `chart_type` | str | Recommended chart (`xbar_r`, `xbar_s`, `imr`, `p`, `u`) |
| `subgroup` | int | Subgroup / sample index (1-based) |
| `value` | float | Measurement value, defective count, or defect count |
| `sample_size` | float | Subgroup size n or opportunity size for attributes charts |
| `lsl` | float\|NaN | Lower spec limit (NaN for attribute streams) |
| `usl` | float\|NaN | Upper spec limit (NaN where not applicable) |

### Streams

| Stream | Parameter | Chart | n | Subgroups | LSL | USL | Special feature |
|---|---|---|---|---|---|---|---|
| `ply_thickness` | Ply Thickness (mm) | Xbar-R | 5 | 25 | 0.245 | 0.255 | Mean drift injected at subgroup 17 |
| `autoclave_temp` | Autoclave Cure Temperature (°C) | I-MR | 1 | 30 | 175.0 | 185.0 | Stable reference process |
| `hole_diameter` | Hole Diameter (mm) | Xbar-S | 12 | 20 | 9.985 | 10.015 | Tight tolerance, large subgroup |
| `reject_proportion` | Visual Inspection Reject Rate | p | variable 80–120 | 25 | — | — | Sinusoidal base rate |
| `surface_defects` | Surface Defects per Unit Area | u | variable 0.8–1.6 | 20 | — | 3.0 | Poisson-distributed |

---

## Control Charts Reference

### When to use which chart

| Scenario | Chart |
|---|---|
| Subgroup means n = 2–9, small samples, range is intuitive | Xbar-R |
| Subgroup means n ≥ 10, standard deviation more stable than range | Xbar-S |
| Individual observations — no natural subgrouping | I-MR |
| Fraction defective units (binomial count ÷ sample size) | p chart |
| Defects per unit, variable opportunity size (Poisson) | u chart |

### Sigma estimation (AIAG 4th Ed.)

| Chart | σ̂ formula | Constant source |
|---|---|---|
| Xbar-R | R̄ / d₂ | d₂ indexed by n, Table A |
| Xbar-S | s̄ / c₄ | c₄ indexed by n, Table A |
| I-MR | MR̄ / d₂ | d₂ = 1.128 (MR window = 2) |

For the Xbar rule-detection sigma, pass **σ_x̄ = σ̂ / √n**, not σ̂ itself.

---

## Rule Detection Reference

| Rule set | Rule | Definition | Window |
|---|---|---|---|
| Western Electric | 1 | 1 point beyond ±3σ | 1 |
| Western Electric | 2 | 2 of 3 consecutive > ±2σ, same side | 3 |
| Western Electric | 3 | 4 of 5 consecutive > ±1σ, same side | 5 |
| Western Electric | 4 | 8 consecutive on same side of CL | 8 |
| Nelson | 5 | 6 consecutive strictly monotone | 6 |
| Nelson | 6 | 14 consecutive alternating up/down | 14 |
| Nelson | 7 | 15 consecutive within ±1σ of CL | 15 |
| Nelson | 8 | 8 consecutive outside ±1σ on both sides | 8 |

Calling `detect_nelson_violations` always includes WE Rules 1–4 first.

---

## Process Capability Reference

| Index | Formula | Uses | Requires |
|---|---|---|---|
| Cp | (USL − LSL) / 6σ̂ | Potential capability, spread only | Both limits |
| Cpk | min((USL − μ)/3σ̂, (μ − LSL)/3σ̂) | Actual capability, centring + spread | At least one limit |
| Pp | (USL − LSL) / 6σ_overall | Long-term spread potential | Both limits |
| Ppk | min((USL − μ)/3σ_overall, (μ − LSL)/3σ_overall) | Long-term actual | At least one limit |

**σ̂** = within-subgroup estimate (Rbar/d2 or Sbar/c4).
**σ_overall** = sample standard deviation of all observations (`ddof=1`).

### Aerospace Cpk targets (AIAG reference)

| Cpk | Interpretation |
|---|---|
| < 1.00 | Not capable |
| 1.00 – 1.32 | Marginal — monitor and reduce variation |
| ≥ 1.33 | Capable — common aerospace minimum |

---

## Running Tests

```bash
# Full suite
pytest tests/ -v

# Single file
pytest tests/test_rule_detection.py -v

# With line coverage
pip install pytest-cov
pytest tests/ --cov=src --cov-report=term-missing
```

### Test inventory

| File | Tests | What it covers |
|---|---|---|
| `test_control_charts.py` | 23 | UCL/LCL/CL formulas, AIAG constant accuracy, clamp behaviour |
| `test_rule_detection.py` | 22 | Every rule fires and does-not-fire with minimal synthetic series |
| `test_capability.py` | 14 | Cp/Cpk/Pp/Ppk formulas, unilateral spec, both-None spec, Cpk < 0 |
| `test_data_generator.py` | 7 | Schema presence, stream membership, value ranges |
| `test_utils.py` | 3 | subgroup_rows sort order and shape |
| `test_visualizer.py` | 3 | build_cpk_gauge valid + None guard |

---

## Deployment

### Streamlit Cloud (recommended)

1. Push to GitHub (public or connected private repo).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Set **Main file path** to `app.py`.
4. Streamlit Cloud reads `requirements.txt` automatically. No secrets or environment variables required.
5. Add the deployed URL to this README.

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501"]
```

---

## Extending the App

### Add a new chart type

1. Implement `compute_<name>(...)` in `src/spc_engine/control_charts.py`. Return a dict following the existing convention.
2. Add the demo stream in `src/spc_engine/data_generator.py` (new `_<stream>()` function, concat into `generate_demo_dataset()`).
3. Add the entry to `CHART_OPTIONS` in `pages/1_Control_Charts.py`.
4. Add a `summarize_metrics` branch for the new key.
5. Write tests in `tests/test_control_charts.py`.

### Add a new process stream

1. Add a row-generator function in `data_generator.py`.
2. Regenerate the CSV:
   ```bash
   python3 -c "
   from src.spc_engine.data_generator import generate_demo_dataset
   generate_demo_dataset().to_csv('data/demo_composites_aerospace.csv', index=False)
   print('Done')
   "
   ```
3. Add the stream to `CHART_OPTIONS` and/or `STREAM_OPTIONS` as appropriate.

### Add a new simulation process

1. Add an entry to `PROCESS_CONFIGS` in `src/simulation/engine.py` with `target_mu`, `target_sigma`, `label`, `unit`.
2. The page 3 sidebar `st.selectbox` auto-discovers all entries from the dict — no other page change needed.

---

## SPC Primer

SPC (Statistical Process Control) uses control charts to distinguish **common-cause variation** (random noise inherent to the stable process) from **special-cause variation** (assignable, non-random events that can and should be investigated).

**Control limits** (UCL, LCL) are calculated from process data at ±3σ from the centreline. They are **not** specification limits. A point inside control limits can still be outside spec; a capable process inside spec can still show special-cause signals.

**The basic SPC cycle:**
1. Collect samples (subgroups) at defined intervals.
2. Plot on the appropriate chart type.
3. Apply rule tests — any violation is a signal to investigate.
4. Find and remove the assignable cause.
5. Recalculate limits with cleaned, stable data.

Capability analysis (Cp, Cpk) is **only meaningful on a stable process**. Computing Cpk on an out-of-control process produces a misleading number.

---

## Standards

- **AIAG SPC Reference Manual, 4th Edition (2005)** — chart constants (A₂, D₃, D₄, d₂, A₃, B₃, B₄, c₄, E₂), capability guidance
- **Western Electric Statistical Quality Control Handbook (1956)** — Rules 1–4
- **Nelson, L.S. (1984)** "The Shewhart Control Chart — Tests for Special Causes" — Rules 5–8 (*Journal of Quality Technology*, 16(4), 237–239)
- **AS9100 / aerospace supplier guidance** — Cpk ≥ 1.33 as common capability minimum reference
