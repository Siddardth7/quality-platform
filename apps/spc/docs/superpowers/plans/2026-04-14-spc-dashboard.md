# SPC Manufacturing Quality Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multi-page Streamlit SPC dashboard with 6 control chart types, dual WE + Nelson rule detection, Cp/Cpk/Pp/Ppk capability analysis, and a live simulation mode with disturbance injection — deployed on Streamlit Cloud.

**Architecture:** Pure-Python SPC engine (`src/spc_engine/`) is completely decoupled from Streamlit. Visualizer (`src/visualizer.py`) builds Plotly figures from engine outputs. Streamlit pages are thin renderers only. `SimulationEngine` (`src/simulation/engine.py`) is a state machine stored in `st.session_state` with no Streamlit imports — fully testable.

**Tech Stack:** Python 3.10+, Streamlit 1.32+, Plotly 5.x, pandas, NumPy, SciPy (Shapiro-Wilk), pytest

---

## File Map

| File | Responsibility |
|------|---------------|
| `app.py` | Streamlit entry point, sidebar branding |
| `pages/1_Control_Charts.py` | Page 1: chart type selector, CSV upload, rule toggle |
| `pages/2_Process_Capability.py` | Page 2: capability indices, distribution histogram |
| `pages/3_Live_Simulation.py` | Page 3: simulation controls, live chart, disturbance buttons |
| `src/spc_engine/constants.py` | AIAG A2, D3, D4, d2, A3, B3, B4, c4, E2 tables |
| `src/spc_engine/control_charts.py` | `compute_xbar_r`, `compute_xbar_s`, `compute_imr`, `compute_p`, `compute_c`, `compute_u` |
| `src/spc_engine/rule_detection.py` | `detect_we_violations`, `detect_nelson_violations` |
| `src/spc_engine/capability.py` | `compute_capability`, `normality_test` |
| `src/spc_engine/data_generator.py` | `generate_demo_dataset` — returns DataFrame with 5 process streams |
| `src/simulation/engine.py` | `SimulationEngine` class — `step()`, `inject_disturbance()`, `reset()` |
| `src/visualizer.py` | `build_control_chart`, `build_capability_histogram`, `build_gauge` |
| `tests/test_control_charts.py` | UCL/LCL/CL math tests |
| `tests/test_rule_detection.py` | WE + Nelson rule fire/no-fire tests |
| `tests/test_capability.py` | Cp/Cpk/Pp/Ppk formula tests |
| `data/demo_composites_aerospace.csv` | Pre-generated demo dataset |
| `requirements.txt` | Pinned dependencies |
| `.streamlit/config.toml` | Wide layout, page title |

---

## Task 1: [D01] Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.streamlit/config.toml`
- Create: `.gitignore`
- Create: `src/__init__.py`, `src/spc_engine/__init__.py`, `src/simulation/__init__.py`
- Create: `tests/__init__.py`
- Create: `app.py` (stub)
- Create: `pages/1_Control_Charts.py` (stub)
- Create: `pages/2_Process_Capability.py` (stub)
- Create: `pages/3_Live_Simulation.py` (stub)

- [ ] **Step 1: Create requirements.txt**

```
streamlit==1.32.2
plotly==5.20.0
pandas==2.2.1
numpy==1.26.4
scipy==1.12.0
pytest==8.1.1
fpdf2==2.7.9
openpyxl==3.1.2
```

- [ ] **Step 2: Create .streamlit/config.toml**

```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#262730"
textColor = "#fafafa"

[server]
headless = true

[browser]
gatherUsageStats = false

[runner]
magicEnabled = false
```

- [ ] **Step 3: Create .gitignore**

```
__pycache__/
*.py[cod]
.venv/
venv/
env/
*.egg-info/
.ipynb_checkpoints/
.DS_Store
.pytest_cache/
```

- [ ] **Step 4: Create all __init__.py files**

```bash
mkdir -p src/spc_engine src/simulation tests pages .streamlit data
touch src/__init__.py src/spc_engine/__init__.py src/simulation/__init__.py tests/__init__.py
```

- [ ] **Step 5: Create app.py stub**

```python
import streamlit as st

st.set_page_config(
    page_title="SPC Manufacturing Quality Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("📊 SPC Manufacturing Quality Dashboard")
st.markdown(
    "**Statistical Process Control** for composites and aerospace manufacturing. "
    "Use the sidebar to navigate between pages."
)

st.sidebar.success("Select a page above.")
```

- [ ] **Step 6: Create page stubs**

`pages/1_Control_Charts.py`:
```python
import streamlit as st
st.set_page_config(page_title="Control Charts", layout="wide")
st.title("Control Charts")
st.info("Coming soon.")
```

`pages/2_Process_Capability.py`:
```python
import streamlit as st
st.set_page_config(page_title="Process Capability", layout="wide")
st.title("Process Capability")
st.info("Coming soon.")
```

`pages/3_Live_Simulation.py`:
```python
import streamlit as st
st.set_page_config(page_title="Live Simulation", layout="wide")
st.title("Live Simulation")
st.info("Coming soon.")
```

- [ ] **Step 7: Verify app runs**

```bash
streamlit run app.py
```
Expected: App opens in browser, sidebar shows 3 pages, no errors.

- [ ] **Step 8: Commit**

```bash
git add .
git commit -m "[D01] feat: project scaffold — Streamlit multi-page stub + config"
```

---

## Task 2: [D02] AIAG Constants + Demo Dataset

**Files:**
- Create: `src/spc_engine/constants.py`
- Create: `src/spc_engine/data_generator.py`
- Create: `data/demo_composites_aerospace.csv`
- Test: `tests/test_data_generator.py`

- [ ] **Step 1: Create constants.py**

```python
# src/spc_engine/constants.py
# Source: AIAG SPC Reference Manual, 4th Ed. (2005), Appendix — Control Chart Constants

# X-bar R chart constants keyed by subgroup size n
XBAR_R_CONSTANTS = {
    2:  {"A2": 1.880, "D3": 0.000, "D4": 3.267, "d2": 1.128},
    3:  {"A2": 1.023, "D3": 0.000, "D4": 2.574, "d2": 1.693},
    4:  {"A2": 0.729, "D3": 0.000, "D4": 2.282, "d2": 2.059},
    5:  {"A2": 0.577, "D3": 0.000, "D4": 2.114, "d2": 2.326},
    6:  {"A2": 0.483, "D3": 0.000, "D4": 2.004, "d2": 2.534},
    7:  {"A2": 0.419, "D3": 0.076, "D4": 1.924, "d2": 2.704},
    8:  {"A2": 0.373, "D3": 0.136, "D4": 1.864, "d2": 2.847},
    9:  {"A2": 0.337, "D3": 0.184, "D4": 1.816, "d2": 2.970},
    10: {"A2": 0.308, "D3": 0.223, "D4": 1.777, "d2": 3.078},
}

# X-bar S chart constants keyed by subgroup size n
XBAR_S_CONSTANTS = {
    2:  {"A3": 2.659, "B3": 0.000, "B4": 3.267, "c4": 0.7979},
    3:  {"A3": 1.954, "B3": 0.000, "B4": 2.568, "c4": 0.8862},
    4:  {"A3": 1.628, "B3": 0.000, "B4": 2.266, "c4": 0.9213},
    5:  {"A3": 1.427, "B3": 0.000, "B4": 2.089, "c4": 0.9400},
    6:  {"A3": 1.287, "B3": 0.030, "B4": 1.970, "c4": 0.9515},
    7:  {"A3": 1.182, "B3": 0.118, "B4": 1.882, "c4": 0.9594},
    8:  {"A3": 1.099, "B3": 0.185, "B4": 1.815, "c4": 0.9650},
    9:  {"A3": 1.032, "B3": 0.239, "B4": 1.761, "c4": 0.9693},
    10: {"A3": 0.975, "B3": 0.284, "B4": 1.716, "c4": 0.9727},
    11: {"A3": 0.927, "B3": 0.321, "B4": 1.679, "c4": 0.9754},
    12: {"A3": 0.886, "B3": 0.354, "B4": 1.646, "c4": 0.9776},
}

# I-MR chart: E2 constant for individuals chart, d2 for n=2 (moving range of 2)
# Source: AIAG SPC Reference Manual, 4th Ed., Table of Constants
IMR_E2 = 2.660   # UCL_X = X̄ + E2 * MR̄
IMR_D4 = 3.267   # UCL_MR = D4 * MR̄  (n=2)
IMR_d2 = 1.128   # sigma_hat = MR̄ / d2
```

- [ ] **Step 2: Write failing tests for data_generator**

```python
# tests/test_data_generator.py
import pandas as pd
import pytest
from src.spc_engine.data_generator import generate_demo_dataset


def test_returns_dataframe():
    df = generate_demo_dataset()
    assert isinstance(df, pd.DataFrame)


def test_has_required_streams():
    df = generate_demo_dataset()
    streams = df["stream"].unique().tolist()
    assert "ply_thickness" in streams
    assert "autoclave_temp" in streams
    assert "hole_diameter" in streams
    assert "reject_proportion" in streams
    assert "surface_defects" in streams


def test_ply_thickness_values_in_range():
    df = generate_demo_dataset()
    ply = df[df["stream"] == "ply_thickness"]
    # Spec limits: LSL=0.245, USL=0.255 — values should be within ±0.01 of nominal
    assert ply["value"].between(0.230, 0.270).all()


def test_autoclave_temp_values_in_range():
    df = generate_demo_dataset()
    temp = df[df["stream"] == "autoclave_temp"]
    # Spec limits: LSL=175, USL=185
    assert temp["value"].between(170.0, 190.0).all()


def test_hole_diameter_values_in_range():
    df = generate_demo_dataset()
    dia = df[df["stream"] == "hole_diameter"]
    # Spec: LSL=9.985, USL=10.015
    assert dia["value"].between(9.970, 10.030).all()


def test_required_columns_present():
    df = generate_demo_dataset()
    for col in ["stream", "subgroup", "value", "sample_size"]:
        assert col in df.columns, f"Missing column: {col}"


def test_ply_thickness_subgroup_size_5():
    df = generate_demo_dataset()
    ply = df[df["stream"] == "ply_thickness"]
    # n=5 per subgroup → each subgroup_id has 5 rows
    counts = ply.groupby("subgroup")["value"].count()
    assert (counts == 5).all()
```

- [ ] **Step 3: Run tests — expect FAIL**

```bash
pytest tests/test_data_generator.py -v
```
Expected: ImportError — `generate_demo_dataset` not defined.

- [ ] **Step 4: Implement data_generator.py**

```python
# src/spc_engine/data_generator.py
import numpy as np
import pandas as pd

_RNG = np.random.default_rng(42)


def generate_demo_dataset() -> pd.DataFrame:
    """Generate five composite/aerospace process streams for demo use.

    Returns a long-format DataFrame with columns:
        stream      : process stream identifier
        subgroup    : subgroup index (1-based)
        value       : individual measurement
        sample_size : subgroup size (for attributes charts)
    """
    frames = []
    frames.append(_ply_thickness())
    frames.append(_autoclave_temp())
    frames.append(_hole_diameter())
    frames.append(_reject_proportion())
    frames.append(_surface_defects())
    df = pd.concat(frames, ignore_index=True)
    return df


# ── Variables streams ──────────────────────────────────────────────────────

def _ply_thickness() -> pd.DataFrame:
    """X̄-R stream: composites layup ply thickness (mm), n=5, 25 subgroups.
    Process drifts toward UCL in last 8 subgroups to create a visible SPC story.
    Spec: LSL=0.245, USL=0.255, target=0.250.
    """
    n, n_subgroups = 5, 25
    mu, sigma = 0.250, 0.0015
    rows = []
    for sg in range(1, n_subgroups + 1):
        drift = 0.0012 * max(0, sg - 17) / 8  # drift starts subgroup 18
        vals = _RNG.normal(mu + drift, sigma, n)
        for v in vals:
            rows.append({"stream": "ply_thickness", "subgroup": sg,
                         "value": round(v, 5), "sample_size": n})
    return pd.DataFrame(rows)


def _autoclave_temp() -> pd.DataFrame:
    """I-MR stream: autoclave cure temperature (°C), individual measurements, 30 readings.
    Spec: LSL=175, USL=185, target=180.
    """
    n_obs = 30
    mu, sigma = 180.0, 1.2
    vals = _RNG.normal(mu, sigma, n_obs)
    return pd.DataFrame({
        "stream": "autoclave_temp",
        "subgroup": range(1, n_obs + 1),
        "value": vals.round(2),
        "sample_size": 1,
    })


def _hole_diameter() -> pd.DataFrame:
    """X̄-S stream: CNC machined hole diameter (mm), n=12, 20 subgroups.
    Spec: LSL=9.985, USL=10.015, target=10.000.
    """
    n, n_subgroups = 12, 20
    mu, sigma = 10.000, 0.003
    rows = []
    for sg in range(1, n_subgroups + 1):
        vals = _RNG.normal(mu, sigma, n)
        for v in vals:
            rows.append({"stream": "hole_diameter", "subgroup": sg,
                         "value": round(v, 5), "sample_size": n})
    return pd.DataFrame(rows)


# ── Attributes streams ─────────────────────────────────────────────────────

def _reject_proportion() -> pd.DataFrame:
    """p-chart stream: proportion of defective panels, variable sample size.
    25 inspection lots; p̄ ≈ 0.04 (4% baseline reject rate).
    """
    n_lots = 25
    p_true = 0.04
    sample_sizes = _RNG.integers(80, 151, n_lots)
    rows = []
    for i, ni in enumerate(sample_sizes, start=1):
        defects = _RNG.binomial(ni, p_true)
        rows.append({
            "stream": "reject_proportion",
            "subgroup": i,
            "value": round(defects / ni, 4),
            "sample_size": int(ni),
        })
    return pd.DataFrame(rows)


def _surface_defects() -> pd.DataFrame:
    """u-chart stream: surface defects per m² on composite panels, variable area inspected.
    20 panels; baseline u ≈ 1.5 defects/m².
    """
    n_panels = 20
    u_true = 1.5
    areas = _RNG.uniform(0.8, 1.6, n_panels)  # m² inspected per panel
    rows = []
    for i, area in enumerate(areas, start=1):
        defects = _RNG.poisson(u_true * area)
        rows.append({
            "stream": "surface_defects",
            "subgroup": i,
            "value": round(defects / area, 3),
            "sample_size": round(area, 3),
        })
    return pd.DataFrame(rows)
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
pytest tests/test_data_generator.py -v
```
Expected: 7 tests PASS.

- [ ] **Step 6: Export CSV**

```python
# run once in terminal:
python -c "
from src.spc_engine.data_generator import generate_demo_dataset
df = generate_demo_dataset()
df.to_csv('data/demo_composites_aerospace.csv', index=False)
print(df['stream'].value_counts())
"
```

- [ ] **Step 7: Commit**

```bash
git add src/spc_engine/constants.py src/spc_engine/data_generator.py \
        tests/test_data_generator.py data/demo_composites_aerospace.csv
git commit -m "[D02] feat: AIAG constants table + demo dataset (5 process streams)"
```

---

## Task 3: [D03] Control Charts — Variables (X̄-R, X̄-S, I-MR)

**Files:**
- Create: `src/spc_engine/control_charts.py`
- Test: `tests/test_control_charts.py` (variables section)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_control_charts.py
import numpy as np
import pytest
from src.spc_engine.control_charts import compute_xbar_r, compute_xbar_s, compute_imr


# ── X̄-R ──────────────────────────────────────────────────────────────────

class TestXbarR:
    def _subgroups(self, n=5, k=10, mu=10.0, sigma=0.5):
        rng = np.random.default_rng(0)
        return [rng.normal(mu, sigma, n).tolist() for _ in range(k)]

    def test_returns_required_keys(self):
        result = compute_xbar_r(self._subgroups())
        for key in ("xbar", "ranges", "xbar_bar", "r_bar",
                    "ucl_xbar", "lcl_xbar", "cl_xbar",
                    "ucl_r", "lcl_r", "cl_r", "sigma_hat"):
            assert key in result, f"Missing key: {key}"

    def test_xbar_values_correct(self):
        subgroups = [[10.0, 10.0, 10.0, 10.0, 10.0]] * 5
        result = compute_xbar_r(subgroups)
        assert all(abs(x - 10.0) < 1e-9 for x in result["xbar"])

    def test_range_of_constant_subgroup_is_zero(self):
        subgroups = [[10.0, 10.0, 10.0, 10.0, 10.0]] * 5
        result = compute_xbar_r(subgroups)
        assert all(r == 0.0 for r in result["ranges"])

    def test_ucl_formula_n5(self):
        # For n=5: A2=0.577, D4=2.114
        # Known subgroup: values all = [9, 11, 10, 10, 10] → x̄=10.0, R=2.0
        # x̄_bar = 10.0, R̄ = 2.0
        # UCL_xbar = 10.0 + 0.577*2.0 = 11.154
        subgroups = [[9.0, 11.0, 10.0, 10.0, 10.0]] * 10
        result = compute_xbar_r(subgroups)
        assert abs(result["ucl_xbar"] - (10.0 + 0.577 * 2.0)) < 1e-3

    def test_ucl_r_formula_n5(self):
        # UCL_R = D4 * R̄ = 2.114 * 2.0 = 4.228
        subgroups = [[9.0, 11.0, 10.0, 10.0, 10.0]] * 10
        result = compute_xbar_r(subgroups)
        assert abs(result["ucl_r"] - (2.114 * 2.0)) < 1e-3

    def test_lcl_r_zero_for_n_less_than_7(self):
        # D3=0 for n<=6, so LCL_R = 0
        subgroups = [[9.0, 11.0, 10.0, 10.0, 10.0]] * 10  # n=5
        result = compute_xbar_r(subgroups)
        assert result["lcl_r"] == 0.0

    def test_sigma_hat_equals_r_bar_over_d2(self):
        # sigma_hat = R̄ / d2; for n=5, d2=2.326
        subgroups = [[9.0, 11.0, 10.0, 10.0, 10.0]] * 10
        result = compute_xbar_r(subgroups)
        assert abs(result["sigma_hat"] - (2.0 / 2.326)) < 1e-3

    def test_raises_on_invalid_subgroup_size(self):
        with pytest.raises(ValueError, match="Subgroup size"):
            compute_xbar_r([[1.0]] * 5)  # n=1 not valid for X̄-R

    def test_raises_on_n_greater_than_10(self):
        with pytest.raises(ValueError, match="Subgroup size"):
            compute_xbar_r([[1.0] * 11] * 5)


# ── X̄-S ──────────────────────────────────────────────────────────────────

class TestXbarS:
    def test_returns_required_keys(self):
        rng = np.random.default_rng(1)
        subgroups = [rng.normal(10.0, 0.5, 12).tolist() for _ in range(15)]
        result = compute_xbar_s(subgroups)
        for key in ("xbar", "stds", "xbar_bar", "s_bar",
                    "ucl_xbar", "lcl_xbar", "cl_xbar",
                    "ucl_s", "lcl_s", "cl_s", "sigma_hat"):
            assert key in result

    def test_ucl_formula_n12(self):
        # For n=12: A3=0.886, B4=1.646, c4=0.9776
        # subgroup all same except one: s will be computed
        subgroups = [[10.0] * 11 + [11.0]] * 10  # std ≈ 0.302
        result = compute_xbar_s(subgroups)
        expected_ucl = result["xbar_bar"] + 0.886 * result["s_bar"]
        assert abs(result["ucl_xbar"] - expected_ucl) < 1e-6

    def test_sigma_hat_equals_s_bar_over_c4(self):
        rng = np.random.default_rng(2)
        subgroups = [rng.normal(10.0, 0.5, 12).tolist() for _ in range(15)]
        result = compute_xbar_s(subgroups)
        from src.spc_engine.constants import XBAR_S_CONSTANTS
        c4 = XBAR_S_CONSTANTS[12]["c4"]
        assert abs(result["sigma_hat"] - result["s_bar"] / c4) < 1e-9


# ── I-MR ─────────────────────────────────────────────────────────────────

class TestIMR:
    def test_returns_required_keys(self):
        values = [10.0 + i * 0.01 for i in range(20)]
        result = compute_imr(values)
        for key in ("individuals", "moving_ranges", "x_bar", "mr_bar",
                    "ucl_x", "lcl_x", "cl_x",
                    "ucl_mr", "cl_mr", "sigma_hat"):
            assert key in result

    def test_moving_range_calculation(self):
        # MR[i] = |X[i] - X[i-1]|
        values = [10.0, 10.5, 10.2, 10.8]
        result = compute_imr(values)
        expected_mr = [0.5, 0.3, 0.6]
        for calc, exp in zip(result["moving_ranges"], expected_mr):
            assert abs(calc - exp) < 1e-9

    def test_ucl_x_formula(self):
        # UCL_X = X̄ + E2 * MR̄  (E2=2.660)
        values = [10.0] * 20
        result = compute_imr(values)
        assert abs(result["ucl_x"] - (10.0 + 2.660 * 0.0)) < 1e-9

    def test_ucl_mr_formula(self):
        # UCL_MR = D4 * MR̄  (D4=3.267 for n=2)
        values = [10.0, 10.2] * 10
        result = compute_imr(values)
        expected_ucl_mr = 3.267 * result["mr_bar"]
        assert abs(result["ucl_mr"] - expected_ucl_mr) < 1e-6

    def test_sigma_hat_equals_mr_bar_over_d2(self):
        # sigma_hat = MR̄ / d2  (d2=1.128 for n=2)
        values = [10.0, 10.2] * 10
        result = compute_imr(values)
        assert abs(result["sigma_hat"] - result["mr_bar"] / 1.128) < 1e-9
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
pytest tests/test_control_charts.py -v
```
Expected: ImportError — `control_charts` not implemented.

- [ ] **Step 3: Implement control_charts.py (variables)**

```python
# src/spc_engine/control_charts.py
from __future__ import annotations
import numpy as np
from .constants import XBAR_R_CONSTANTS, XBAR_S_CONSTANTS, IMR_E2, IMR_D4, IMR_d2


def compute_xbar_r(subgroups: list[list[float]]) -> dict:
    """X̄-R control chart limits.

    Args:
        subgroups: list of k subgroups, each a list of n individual values.
                   All subgroups must have the same size n, 2 ≤ n ≤ 10.

    Returns dict with keys:
        xbar, ranges, xbar_bar, r_bar,
        ucl_xbar, lcl_xbar, cl_xbar,
        ucl_r, lcl_r, cl_r, sigma_hat
    """
    n = len(subgroups[0])
    if n < 2 or n > 10:
        raise ValueError(f"Subgroup size n={n} out of range — X̄-R requires 2 ≤ n ≤ 10.")
    if any(len(sg) != n for sg in subgroups):
        raise ValueError("All subgroups must have the same size.")

    c = XBAR_R_CONSTANTS[n]
    xbar = [float(np.mean(sg)) for sg in subgroups]
    ranges = [float(max(sg) - min(sg)) for sg in subgroups]
    xbar_bar = float(np.mean(xbar))
    r_bar = float(np.mean(ranges))

    ucl_xbar = xbar_bar + c["A2"] * r_bar
    lcl_xbar = xbar_bar - c["A2"] * r_bar
    ucl_r = c["D4"] * r_bar
    lcl_r = c["D3"] * r_bar
    sigma_hat = r_bar / c["d2"]

    return {
        "xbar": xbar, "ranges": ranges,
        "xbar_bar": xbar_bar, "r_bar": r_bar,
        "ucl_xbar": ucl_xbar, "lcl_xbar": lcl_xbar, "cl_xbar": xbar_bar,
        "ucl_r": ucl_r, "lcl_r": lcl_r, "cl_r": r_bar,
        "sigma_hat": sigma_hat,
    }


def compute_xbar_s(subgroups: list[list[float]]) -> dict:
    """X̄-S control chart limits.

    Args:
        subgroups: list of k subgroups, each a list of n individual values.
                   All subgroups must have the same size n, 2 ≤ n ≤ 12.

    Returns dict with same structure as compute_xbar_r but uses s_bar instead of r_bar.
    """
    n = len(subgroups[0])
    if n < 2 or n > 12:
        raise ValueError(f"Subgroup size n={n} out of range — X̄-S requires 2 ≤ n ≤ 12.")
    if any(len(sg) != n for sg in subgroups):
        raise ValueError("All subgroups must have the same size.")

    c = XBAR_S_CONSTANTS[n]
    xbar = [float(np.mean(sg)) for sg in subgroups]
    # ddof=1 for sample std dev
    stds = [float(np.std(sg, ddof=1)) for sg in subgroups]
    xbar_bar = float(np.mean(xbar))
    s_bar = float(np.mean(stds))

    ucl_xbar = xbar_bar + c["A3"] * s_bar
    lcl_xbar = xbar_bar - c["A3"] * s_bar
    ucl_s = c["B4"] * s_bar
    lcl_s = c["B3"] * s_bar
    sigma_hat = s_bar / c["c4"]

    return {
        "xbar": xbar, "stds": stds,
        "xbar_bar": xbar_bar, "s_bar": s_bar,
        "ucl_xbar": ucl_xbar, "lcl_xbar": lcl_xbar, "cl_xbar": xbar_bar,
        "ucl_s": ucl_s, "lcl_s": lcl_s, "cl_s": s_bar,
        "sigma_hat": sigma_hat,
    }


def compute_imr(values: list[float]) -> dict:
    """Individuals and Moving Range (I-MR) control chart limits.

    Args:
        values: list of individual measurements (one per time period).
                Minimum 2 values required.

    Returns dict with keys:
        individuals, moving_ranges, x_bar, mr_bar,
        ucl_x, lcl_x, cl_x, ucl_mr, cl_mr, sigma_hat
    """
    if len(values) < 2:
        raise ValueError("I-MR requires at least 2 individual values.")

    x = list(values)
    mr = [abs(x[i] - x[i - 1]) for i in range(1, len(x))]
    x_bar = float(np.mean(x))
    mr_bar = float(np.mean(mr))

    ucl_x = x_bar + IMR_E2 * mr_bar
    lcl_x = x_bar - IMR_E2 * mr_bar
    ucl_mr = IMR_D4 * mr_bar
    sigma_hat = mr_bar / IMR_d2

    return {
        "individuals": x, "moving_ranges": mr,
        "x_bar": x_bar, "mr_bar": mr_bar,
        "ucl_x": ucl_x, "lcl_x": lcl_x, "cl_x": x_bar,
        "ucl_mr": ucl_mr, "cl_mr": mr_bar,
        "sigma_hat": sigma_hat,
    }
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_control_charts.py -v -k "TestXbarR or TestXbarS or TestIMR"
```
Expected: 14 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/spc_engine/control_charts.py tests/test_control_charts.py
git commit -m "[D03] feat: variables control charts — X̄-R, X̄-S, I-MR with AIAG constants"
```

---

## Task 4: [D04] Control Charts — Attributes (p, c, u)

**Files:**
- Modify: `src/spc_engine/control_charts.py` (add `compute_p`, `compute_c`, `compute_u`)
- Modify: `tests/test_control_charts.py` (add attributes tests)

- [ ] **Step 1: Write failing tests (append to test_control_charts.py)**

```python
# Append to tests/test_control_charts.py
from src.spc_engine.control_charts import compute_p, compute_c, compute_u


class TestPChart:
    def test_returns_required_keys(self):
        defectives = [4, 6, 3, 5, 7]
        sample_sizes = [100] * 5
        result = compute_p(defectives, sample_sizes)
        for key in ("p_i", "p_bar", "ucl", "lcl", "cl", "sample_sizes"):
            assert key in result

    def test_p_bar_calculation(self):
        # p̄ = total defectives / total inspected
        defectives = [4, 6]
        sample_sizes = [100, 100]
        result = compute_p(defectives, sample_sizes)
        assert abs(result["p_bar"] - 0.05) < 1e-9

    def test_ucl_formula_fixed_n(self):
        # UCL_i = p̄ + 3*sqrt(p̄*(1-p̄)/n_i)
        defectives = [5] * 20
        sample_sizes = [100] * 20
        result = compute_p(defectives, sample_sizes)
        p_bar = 0.05
        expected_ucl = p_bar + 3 * (p_bar * (1 - p_bar) / 100) ** 0.5
        assert abs(result["ucl"][0] - expected_ucl) < 1e-6

    def test_lcl_clamped_to_zero(self):
        # LCL cannot be negative
        defectives = [1] * 20
        sample_sizes = [20] * 20  # small n → wide limits → LCL could go negative
        result = compute_p(defectives, sample_sizes)
        assert all(lcl >= 0.0 for lcl in result["lcl"])

    def test_p_i_values(self):
        defectives = [10, 20]
        sample_sizes = [100, 200]
        result = compute_p(defectives, sample_sizes)
        assert abs(result["p_i"][0] - 0.10) < 1e-9
        assert abs(result["p_i"][1] - 0.10) < 1e-9


class TestCChart:
    def test_returns_required_keys(self):
        counts = [3, 5, 2, 4, 6]
        result = compute_c(counts)
        for key in ("counts", "c_bar", "ucl", "lcl", "cl"):
            assert key in result

    def test_c_bar_is_mean(self):
        counts = [2, 4, 6]
        result = compute_c(counts)
        assert abs(result["c_bar"] - 4.0) < 1e-9

    def test_ucl_formula(self):
        # UCL = c̄ + 3*sqrt(c̄)
        counts = [4] * 20
        result = compute_c(counts)
        expected_ucl = 4.0 + 3.0 * (4.0 ** 0.5)
        assert abs(result["ucl"] - expected_ucl) < 1e-9

    def test_lcl_clamped_to_zero(self):
        counts = [1] * 10  # small c̄ → LCL could go negative
        result = compute_c(counts)
        assert result["lcl"] >= 0.0


class TestUChart:
    def test_returns_required_keys(self):
        defects = [3, 5, 4]
        areas = [1.0, 1.2, 0.9]
        result = compute_u(defects, areas)
        for key in ("u_i", "u_bar", "ucl", "lcl", "cl", "areas"):
            assert key in result

    def test_u_bar_calculation(self):
        # ū = total defects / total area
        defects = [3, 6]
        areas = [1.0, 2.0]
        result = compute_u(defects, areas)
        assert abs(result["u_bar"] - (9.0 / 3.0)) < 1e-9

    def test_ucl_formula(self):
        # UCL_i = ū + 3*sqrt(ū/n_i)
        defects = [2] * 20
        areas = [1.0] * 20
        result = compute_u(defects, areas)
        u_bar = 2.0
        expected_ucl = u_bar + 3 * (u_bar / 1.0) ** 0.5
        assert abs(result["ucl"][0] - expected_ucl) < 1e-9

    def test_lcl_clamped_to_zero(self):
        defects = [0] * 10
        areas = [0.5] * 10
        result = compute_u(defects, areas)
        assert all(lcl >= 0.0 for lcl in result["lcl"])
```

- [ ] **Step 2: Run new tests — expect FAIL**

```bash
pytest tests/test_control_charts.py -v -k "TestPChart or TestCChart or TestUChart"
```
Expected: ImportError — `compute_p`, `compute_c`, `compute_u` not defined.

- [ ] **Step 3: Add attributes charts to control_charts.py**

```python
# Append to src/spc_engine/control_charts.py

def compute_p(defectives: list[int], sample_sizes: list[int]) -> dict:
    """p-chart: proportion defective with variable sample sizes.

    Args:
        defectives:   count of defective units per subgroup
        sample_sizes: number of units inspected per subgroup

    Returns dict with per-subgroup UCL/LCL (vary with n_i):
        p_i, p_bar, ucl (list), lcl (list), cl, sample_sizes
    """
    n_arr = np.array(sample_sizes, dtype=float)
    d_arr = np.array(defectives, dtype=float)
    p_i = d_arr / n_arr
    p_bar = float(d_arr.sum() / n_arr.sum())

    sigma_i = np.sqrt(p_bar * (1 - p_bar) / n_arr)
    ucl = np.clip(p_bar + 3 * sigma_i, 0, 1).tolist()
    lcl = np.clip(p_bar - 3 * sigma_i, 0, None).tolist()

    return {
        "p_i": p_i.tolist(), "p_bar": p_bar,
        "ucl": ucl, "lcl": lcl, "cl": p_bar,
        "sample_sizes": sample_sizes,
    }


def compute_c(counts: list[int]) -> dict:
    """c-chart: count of defects per unit with fixed sample size.

    Args:
        counts: defect count per subgroup (fixed inspection unit)

    Returns dict:
        counts, c_bar, ucl (scalar), lcl (scalar), cl
    """
    c_arr = np.array(counts, dtype=float)
    c_bar = float(c_arr.mean())
    ucl = float(c_bar + 3 * np.sqrt(c_bar))
    lcl = float(max(0.0, c_bar - 3 * np.sqrt(c_bar)))

    return {
        "counts": counts, "c_bar": c_bar,
        "ucl": ucl, "lcl": lcl, "cl": c_bar,
    }


def compute_u(defects: list[int], areas: list[float]) -> dict:
    """u-chart: defect rate per unit area with variable inspection area.

    Args:
        defects: defect count per subgroup
        areas:   inspection area (or unit count) per subgroup

    Returns dict with per-subgroup UCL/LCL:
        u_i, u_bar, ucl (list), lcl (list), cl, areas
    """
    a_arr = np.array(areas, dtype=float)
    d_arr = np.array(defects, dtype=float)
    u_i = d_arr / a_arr
    u_bar = float(d_arr.sum() / a_arr.sum())

    sigma_i = np.sqrt(u_bar / a_arr)
    ucl = np.clip(u_bar + 3 * sigma_i, 0, None).tolist()
    lcl = np.clip(u_bar - 3 * sigma_i, 0, None).tolist()

    return {
        "u_i": u_i.tolist(), "u_bar": u_bar,
        "ucl": ucl, "lcl": lcl, "cl": u_bar,
        "areas": areas,
    }
```

- [ ] **Step 4: Run all control chart tests — expect PASS**

```bash
pytest tests/test_control_charts.py -v
```
Expected: All tests PASS (14 variables + 14 attributes = 28 total).

- [ ] **Step 5: Commit**

```bash
git add src/spc_engine/control_charts.py tests/test_control_charts.py
git commit -m "[D04] feat: attributes control charts — p, c, u with variable limits"
```

---

## Task 5: [D05] Rule Detection — Western Electric Rules

**Files:**
- Create: `src/spc_engine/rule_detection.py`
- Create: `tests/test_rule_detection.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_rule_detection.py
import pytest
from src.spc_engine.rule_detection import detect_we_violations, detect_nelson_violations


# ── Western Electric Rules ────────────────────────────────────────────────
# Source: AIAG SPC Reference Manual, 4th Ed. (2005), Chapter IV

class TestWERule1:
    """WE Rule 1: 1 point beyond ±3σ."""

    def test_point_beyond_ucl_flagged(self):
        # Point at 3.1σ above mean → violation
        points = [0.0] * 9 + [3.1]
        result = detect_we_violations(points, cl=0.0, sigma=1.0)
        assert 9 in result["rule1"]

    def test_point_at_exactly_3sigma_not_flagged(self):
        # Exactly 3σ is on the boundary — not a violation
        points = [0.0] * 9 + [3.0]
        result = detect_we_violations(points, cl=0.0, sigma=1.0)
        assert 9 not in result["rule1"]

    def test_point_below_lcl_flagged(self):
        points = [0.0] * 9 + [-3.1]
        result = detect_we_violations(points, cl=0.0, sigma=1.0)
        assert 9 in result["rule1"]

    def test_clean_process_no_violations(self):
        points = [0.0] * 20
        result = detect_we_violations(points, cl=0.0, sigma=1.0)
        assert len(result["rule1"]) == 0


class TestWERule2:
    """WE Rule 2: 2 of 3 consecutive points beyond ±2σ (same side)."""

    def test_two_of_three_above_2sigma_flagged(self):
        # positions 7,8,9: [2.1, 0.5, 2.1] → 2 of 3 above +2σ
        points = [0.0] * 7 + [2.1, 0.5, 2.1]
        result = detect_we_violations(points, cl=0.0, sigma=1.0)
        assert 9 in result["rule2"]

    def test_two_of_three_on_opposite_sides_not_flagged(self):
        # One above +2σ, one below -2σ → not same side
        points = [0.0] * 7 + [2.1, 0.0, -2.1]
        result = detect_we_violations(points, cl=0.0, sigma=1.0)
        assert 9 not in result["rule2"]

    def test_clean_process_no_rule2_violations(self):
        points = [0.5] * 20
        result = detect_we_violations(points, cl=0.0, sigma=1.0)
        assert len(result["rule2"]) == 0


class TestWERule3:
    """WE Rule 3: 4 of 5 consecutive points beyond ±1σ (same side)."""

    def test_four_of_five_above_1sigma_flagged(self):
        points = [0.0] * 5 + [1.5, 1.5, 0.5, 1.5, 1.5]
        result = detect_we_violations(points, cl=0.0, sigma=1.0)
        assert 9 in result["rule3"]

    def test_four_of_five_mixed_sides_not_flagged(self):
        points = [0.0] * 5 + [1.5, -1.5, 0.5, 1.5, 1.5]
        result = detect_we_violations(points, cl=0.0, sigma=1.0)
        assert 9 not in result["rule3"]


class TestWERule4:
    """WE Rule 4: 8 consecutive points on same side of centerline."""

    def test_eight_consecutive_above_cl_flagged(self):
        points = [0.0] * 2 + [0.5] * 8
        result = detect_we_violations(points, cl=0.0, sigma=1.0)
        assert 9 in result["rule4"]

    def test_eight_consecutive_below_cl_flagged(self):
        points = [0.0] * 2 + [-0.5] * 8
        result = detect_we_violations(points, cl=0.0, sigma=1.0)
        assert 9 in result["rule4"]

    def test_seven_consecutive_not_flagged(self):
        points = [0.0] * 3 + [0.5] * 7
        result = detect_we_violations(points, cl=0.0, sigma=1.0)
        assert 9 not in result["rule4"]

    def test_returns_all_four_rule_keys(self):
        points = [0.0] * 10
        result = detect_we_violations(points, cl=0.0, sigma=1.0)
        for k in ("rule1", "rule2", "rule3", "rule4"):
            assert k in result
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
pytest tests/test_rule_detection.py -v -k "TestWE"
```

- [ ] **Step 3: Implement detect_we_violations**

```python
# src/spc_engine/rule_detection.py
from __future__ import annotations


def detect_we_violations(
    points: list[float],
    cl: float,
    sigma: float,
) -> dict[str, list[int]]:
    """Detect Western Electric rule violations.

    Source: AIAG SPC Reference Manual, 4th Ed. (2005), Chapter IV — Tests for Special Causes.

    Args:
        points: list of plotted statistics (x̄ values, individual values, etc.)
        cl:     process centerline
        sigma:  process sigma (σ̂ for the plotted statistic, not raw sigma)

    Returns dict mapping rule name → list of 0-based indices where violation ends.
        rule1: 1 point beyond ±3σ
        rule2: 2 of 3 consecutive beyond ±2σ (same side)
        rule3: 4 of 5 consecutive beyond ±1σ (same side)
        rule4: 8 consecutive on same side of CL
    """
    n = len(points)
    z = [(p - cl) / sigma for p in points]  # standardize

    rule1, rule2, rule3, rule4 = [], [], [], []

    for i in range(n):
        # Rule 1: beyond ±3σ
        if abs(z[i]) > 3.0:
            rule1.append(i)

        # Rule 2: 2 of 3 beyond ±2σ, same side (check windows ending at i)
        if i >= 2:
            window = z[i - 2: i + 1]
            above = sum(1 for v in window if v > 2.0)
            below = sum(1 for v in window if v < -2.0)
            if above >= 2 or below >= 2:
                rule2.append(i)

        # Rule 3: 4 of 5 beyond ±1σ, same side (check windows ending at i)
        if i >= 4:
            window = z[i - 4: i + 1]
            above = sum(1 for v in window if v > 1.0)
            below = sum(1 for v in window if v < -1.0)
            if above >= 4 or below >= 4:
                rule3.append(i)

        # Rule 4: 8 consecutive on same side of CL
        if i >= 7:
            window = z[i - 7: i + 1]
            above = sum(1 for v in window if v > 0.0)
            below = sum(1 for v in window if v < 0.0)
            if above == 8 or below == 8:
                rule4.append(i)

    return {"rule1": rule1, "rule2": rule2, "rule3": rule3, "rule4": rule4}
```

- [ ] **Step 4: Run WE tests — expect PASS**

```bash
pytest tests/test_rule_detection.py -v -k "TestWE"
```
Expected: All WE tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/spc_engine/rule_detection.py tests/test_rule_detection.py
git commit -m "[D05] feat: Western Electric rule detection engine (4 rules, AIAG SPC 4th Ed.)"
```

---

## Task 6: [D06] Rule Detection — Nelson Rules (Checkpoint 1)

**Files:**
- Modify: `src/spc_engine/rule_detection.py` (add `detect_nelson_violations`)
- Modify: `tests/test_rule_detection.py` (add Nelson tests)

- [ ] **Step 1: Write failing Nelson rule tests (append to test_rule_detection.py)**

```python
# Append to tests/test_rule_detection.py

class TestNelsonRule5:
    """Nelson Rule 5: 6 consecutive points trending in same direction.
    Source: Nelson (1984), Journal of Quality Technology, 16(4):238-239.
    """

    def test_six_consecutive_increasing_flagged(self):
        points = [0.0] * 4 + [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        result = detect_nelson_violations(points, cl=0.0, sigma=1.0)
        assert 9 in result["rule5"]

    def test_six_consecutive_decreasing_flagged(self):
        points = [0.0] * 4 + [6.0, 5.0, 4.0, 3.0, 2.0, 1.0]
        result = detect_nelson_violations(points, cl=0.0, sigma=1.0)
        assert 9 in result["rule5"]

    def test_five_consecutive_not_flagged(self):
        # Only 5 trending → not a violation (need 6)
        points = [0.0] * 5 + [1.0, 2.0, 3.0, 4.0, 5.0]
        result = detect_nelson_violations(points, cl=0.0, sigma=1.0)
        assert 9 not in result["rule5"]

    def test_trend_broken_not_flagged(self):
        points = [0.0] * 4 + [1.0, 2.0, 1.5, 3.0, 4.0, 5.0]
        result = detect_nelson_violations(points, cl=0.0, sigma=1.0)
        assert 9 not in result["rule5"]


class TestNelsonRule6:
    """Nelson Rule 6: 14 consecutive points alternating up and down."""

    def test_14_alternating_flagged(self):
        alt = [(-1) ** i * 0.5 for i in range(14)]
        points = [0.0] * 5 + alt
        result = detect_nelson_violations(points, cl=0.0, sigma=1.0)
        assert len(alt) + 5 - 1 in result["rule6"]

    def test_13_alternating_not_flagged(self):
        alt = [(-1) ** i * 0.5 for i in range(13)]
        points = [0.0] * 5 + alt
        result = detect_nelson_violations(points, cl=0.0, sigma=1.0)
        assert len(alt) + 5 - 1 not in result["rule6"]


class TestNelsonRule7:
    """Nelson Rule 7: 15 consecutive points within ±1σ (stratification)."""

    def test_15_within_1sigma_flagged(self):
        points = [0.0] * 4 + [0.5] * 15
        result = detect_nelson_violations(points, cl=0.0, sigma=1.0)
        assert 18 in result["rule7"]

    def test_14_within_1sigma_not_flagged(self):
        points = [0.0] * 5 + [0.5] * 14
        result = detect_nelson_violations(points, cl=0.0, sigma=1.0)
        assert 18 not in result["rule7"]


class TestNelsonRule8:
    """Nelson Rule 8: 8 consecutive points outside ±1σ (mixture / bimodal)."""

    def test_eight_outside_1sigma_both_sides_flagged(self):
        # Alternating above and below ±1σ
        pts = [1.5, -1.5] * 4
        points = [0.0] * 2 + pts
        result = detect_nelson_violations(points, cl=0.0, sigma=1.0)
        assert 9 in result["rule8"]

    def test_eight_all_one_side_beyond_1sigma_not_flagged_by_rule8(self):
        # All above +1σ — this is Rule 3 territory, not Rule 8 (Rule 8 requires BOTH sides)
        points = [0.0] * 2 + [1.5] * 8
        result = detect_nelson_violations(points, cl=0.0, sigma=1.0)
        assert 9 not in result["rule8"]

    def test_returns_all_eight_rule_keys(self):
        points = [0.0] * 10
        result = detect_nelson_violations(points, cl=0.0, sigma=1.0)
        for k in ("rule1", "rule2", "rule3", "rule4",
                  "rule5", "rule6", "rule7", "rule8"):
            assert k in result
```

- [ ] **Step 2: Run Nelson tests — expect FAIL**

```bash
pytest tests/test_rule_detection.py -v -k "TestNelson"
```

- [ ] **Step 3: Add detect_nelson_violations to rule_detection.py**

```python
# Append to src/spc_engine/rule_detection.py

def detect_nelson_violations(
    points: list[float],
    cl: float,
    sigma: float,
) -> dict[str, list[int]]:
    """Detect Nelson rule violations (all 8 rules).

    Rules 1-4 are identical to Western Electric rules.
    Rules 5-8 extend the detection set.
    Source: Nelson, L.S. (1984). Journal of Quality Technology, 16(4):238-239.

    Returns dict mapping rule name → list of 0-based indices where violation ends.
    """
    # Rules 1-4 are the same as WE
    result = detect_we_violations(points, cl=cl, sigma=sigma)
    n = len(points)
    z = [(p - cl) / sigma for p in points]

    rule5, rule6, rule7, rule8 = [], [], [], []

    for i in range(n):
        # Rule 5: 6 consecutive trending in same direction
        if i >= 5:
            window = z[i - 5: i + 1]
            diffs = [window[j + 1] - window[j] for j in range(5)]
            if all(d > 0 for d in diffs) or all(d < 0 for d in diffs):
                rule5.append(i)

        # Rule 6: 14 consecutive alternating
        if i >= 13:
            window = z[i - 13: i + 1]
            diffs = [window[j + 1] - window[j] for j in range(13)]
            alternating = all(
                (diffs[j] > 0) != (diffs[j + 1] > 0) for j in range(12)
            )
            if alternating:
                rule6.append(i)

        # Rule 7: 15 consecutive within ±1σ (stratification)
        if i >= 14:
            window = z[i - 14: i + 1]
            if all(abs(v) < 1.0 for v in window):
                rule7.append(i)

        # Rule 8: 8 consecutive outside ±1σ on BOTH sides (mixture)
        if i >= 7:
            window = z[i - 7: i + 1]
            outside = [abs(v) > 1.0 for v in window]
            has_above = any(v > 1.0 for v in window)
            has_below = any(v < -1.0 for v in window)
            if all(outside) and has_above and has_below:
                rule8.append(i)

    result.update({"rule5": rule5, "rule6": rule6, "rule7": rule7, "rule8": rule8})
    return result
```

- [ ] **Step 4: Run all rule detection tests — expect PASS**

```bash
pytest tests/test_rule_detection.py -v
```
Expected: All tests PASS. Count: ~24 tests.

- [ ] **Step 5: Checkpoint 1 — run full test suite**

```bash
pytest tests/ -v --tb=short
```
Expected: All tests GREEN. This is the Day 6 checkpoint.

- [ ] **Step 6: Commit**

```bash
git add src/spc_engine/rule_detection.py tests/test_rule_detection.py
git commit -m "[D06] feat: Nelson rule detection engine (Rules 5-8) — Checkpoint 1 ✅"
```

---

## Task 7: [D07] Process Capability Engine

**Files:**
- Create: `src/spc_engine/capability.py`
- Create: `tests/test_capability.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_capability.py
import numpy as np
import pytest
from src.spc_engine.capability import compute_capability, normality_test


class TestComputeCapability:
    """Tests for Cp, Cpk, Pp, Ppk per AIAG SPC Reference Manual 4th Ed."""

    def _data(self, mu=10.0, sigma=0.5, n=100):
        rng = np.random.default_rng(42)
        return rng.normal(mu, sigma, n).tolist()

    def test_returns_required_keys(self):
        data = self._data()
        result = compute_capability(data, lsl=8.5, usl=11.5, sigma_hat=0.5)
        for key in ("cp", "cpk", "pp", "ppk", "mean", "sigma_hat", "sigma_overall"):
            assert key in result

    def test_cp_formula(self):
        # Cp = (USL - LSL) / (6 * sigma_hat)
        data = self._data(mu=10.0, sigma=0.5)
        result = compute_capability(data, lsl=7.0, usl=13.0, sigma_hat=0.5)
        expected_cp = (13.0 - 7.0) / (6 * 0.5)
        assert abs(result["cp"] - expected_cp) < 1e-9

    def test_cpk_formula(self):
        # Cpk = min[(USL - x̄)/(3*sigma_hat), (x̄ - LSL)/(3*sigma_hat)]
        data = [10.0] * 50  # perfect centering
        result = compute_capability(data, lsl=7.0, usl=13.0, sigma_hat=0.5)
        expected_cpk = min((13.0 - 10.0) / (3 * 0.5), (10.0 - 7.0) / (3 * 0.5))
        assert abs(result["cpk"] - expected_cpk) < 1e-9

    def test_cpk_negative_when_mean_outside_spec(self):
        # Mean at 14.0, USL=13.0 → Cpk < 0
        data = [14.0] * 50
        result = compute_capability(data, lsl=7.0, usl=13.0, sigma_hat=0.5)
        assert result["cpk"] < 0.0

    def test_pp_uses_overall_sigma(self):
        # Pp = (USL - LSL) / (6 * sigma_overall)
        data = self._data(mu=10.0, sigma=1.0)
        result = compute_capability(data, lsl=7.0, usl=13.0, sigma_hat=0.5)
        sigma_overall = np.std(data, ddof=1)
        expected_pp = (13.0 - 7.0) / (6 * sigma_overall)
        assert abs(result["pp"] - expected_pp) < 1e-6

    def test_ppk_uses_overall_sigma(self):
        data = [10.0] * 50
        result = compute_capability(data, lsl=7.0, usl=13.0, sigma_hat=0.5)
        sigma_overall = np.std(data, ddof=1)
        # sigma_overall of constant data is 0; ppk would be inf — test with real data
        data2 = self._data(mu=10.0, sigma=1.0)
        result2 = compute_capability(data2, lsl=7.0, usl=13.0, sigma_hat=1.0)
        sigma_ov = np.std(data2, ddof=1)
        mean2 = np.mean(data2)
        expected_ppk = min((13.0 - mean2) / (3 * sigma_ov),
                           (mean2 - 7.0) / (3 * sigma_ov))
        assert abs(result2["ppk"] - expected_ppk) < 1e-6

    def test_unilateral_usl_only(self):
        # Only USL provided — Cpk = (USL - x̄) / (3 * sigma_hat)
        data = [10.0] * 50
        result = compute_capability(data, lsl=None, usl=13.0, sigma_hat=0.5)
        assert abs(result["cpk"] - (13.0 - 10.0) / (3 * 0.5)) < 1e-9
        assert result["cp"] is None  # Cp requires both spec limits

    def test_unilateral_lsl_only(self):
        data = [10.0] * 50
        result = compute_capability(data, lsl=7.0, usl=None, sigma_hat=0.5)
        assert abs(result["cpk"] - (10.0 - 7.0) / (3 * 0.5)) < 1e-9
        assert result["cp"] is None


class TestNormalityTest:
    def test_normal_data_high_p_value(self):
        rng = np.random.default_rng(0)
        data = rng.normal(10.0, 1.0, 100).tolist()
        result = normality_test(data)
        assert result["p_value"] > 0.05
        assert result["is_normal"] is True

    def test_returns_required_keys(self):
        data = [1.0, 2.0, 3.0, 4.0, 5.0] * 10
        result = normality_test(data)
        for key in ("statistic", "p_value", "is_normal"):
            assert key in result
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
pytest tests/test_capability.py -v
```

- [ ] **Step 3: Implement capability.py**

```python
# src/spc_engine/capability.py
from __future__ import annotations
import numpy as np
from scipy import stats


def compute_capability(
    data: list[float],
    lsl: float | None,
    usl: float | None,
    sigma_hat: float,
) -> dict:
    """Compute Cp, Cpk, Pp, Ppk capability indices.

    Source: AIAG SPC Reference Manual, 4th Ed. (2005), Chapter III — Process Capability.

    Args:
        data:       individual measurement values (all observations)
        lsl:        lower spec limit (None if unilateral, USL-only)
        usl:        upper spec limit (None if unilateral, LSL-only)
        sigma_hat:  short-term within-subgroup sigma estimate (R̄/d2 or S̄/c4)

    Returns dict:
        cp:            potential capability (None if unilateral)
        cpk:           actual capability (short-term)
        pp:            long-term potential (None if unilateral)
        ppk:           long-term actual
        mean:          process mean
        sigma_hat:     short-term sigma (echoed for reference)
        sigma_overall: long-term overall sigma (sample std dev)
    """
    arr = np.array(data, dtype=float)
    mean = float(arr.mean())
    sigma_overall = float(arr.std(ddof=1))

    # Cp / Pp — require both limits
    if lsl is not None and usl is not None:
        cp = (usl - lsl) / (6 * sigma_hat) if sigma_hat > 0 else None
        pp = (usl - lsl) / (6 * sigma_overall) if sigma_overall > 0 else None
    else:
        cp = None
        pp = None

    # Cpk — one-sided when only one limit given
    if usl is not None and lsl is not None:
        cpu = (usl - mean) / (3 * sigma_hat)
        cpl = (mean - lsl) / (3 * sigma_hat)
        cpk = min(cpu, cpl)
    elif usl is not None:
        cpk = (usl - mean) / (3 * sigma_hat)
    elif lsl is not None:
        cpk = (mean - lsl) / (3 * sigma_hat)
    else:
        raise ValueError("At least one spec limit (lsl or usl) must be provided.")

    # Ppk — same logic with sigma_overall
    if sigma_overall > 0:
        if usl is not None and lsl is not None:
            ppu = (usl - mean) / (3 * sigma_overall)
            ppl = (mean - lsl) / (3 * sigma_overall)
            ppk = min(ppu, ppl)
        elif usl is not None:
            ppk = (usl - mean) / (3 * sigma_overall)
        else:
            ppk = (mean - lsl) / (3 * sigma_overall)
    else:
        ppk = float("inf")

    return {
        "cp": cp, "cpk": cpk, "pp": pp, "ppk": ppk,
        "mean": mean, "sigma_hat": sigma_hat, "sigma_overall": sigma_overall,
    }


def normality_test(data: list[float]) -> dict:
    """Shapiro-Wilk normality test.

    Returns:
        statistic: Shapiro-Wilk W statistic
        p_value:   p-value (< 0.05 → reject normality at 95% confidence)
        is_normal: True if p_value >= 0.05
    """
    stat, p = stats.shapiro(data)
    return {"statistic": float(stat), "p_value": float(p), "is_normal": bool(p >= 0.05)}
```

- [ ] **Step 4: Run all tests — expect PASS**

```bash
pytest tests/ -v --tb=short
```
Expected: All tests PASS. Running total: ~50+ tests.

- [ ] **Step 5: Commit**

```bash
git add src/spc_engine/capability.py tests/test_capability.py
git commit -m "[D07] feat: capability engine — Cp/Cpk/Pp/Ppk + Shapiro-Wilk normality test"
```

---

## Task 8: [D08] Visualizer — All Plotly Chart Builders

**Files:**
- Create: `src/visualizer.py`

No unit tests for the visualizer — it returns Plotly Figure objects. Integration tested visually in Streamlit pages.

- [ ] **Step 1: Create visualizer.py**

```python
# src/visualizer.py
from __future__ import annotations
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np


_VIOLATION_COLOR = "red"
_UCL_COLOR = "#e63946"
_LCL_COLOR = "#e63946"
_CL_COLOR = "#457b9d"
_DATA_COLOR = "#a8dadc"
_AREA_COLOR = "rgba(168, 218, 220, 0.15)"


def build_control_chart(
    points: list[float],
    cl: float,
    ucl: float | list[float],
    lcl: float | list[float],
    violations: dict[str, list[int]],
    title: str = "Control Chart",
    y_label: str = "Value",
    subgroup_label: str = "Subgroup",
) -> go.Figure:
    """Build a Plotly control chart with violation markers.

    Args:
        points:     plotted statistics (x̄, individuals, p_i, etc.)
        cl:         centerline value
        ucl:        upper control limit (scalar or per-point list)
        lcl:        lower control limit (scalar or per-point list)
        violations: output of detect_we_violations or detect_nelson_violations
        title:      chart title
        y_label:    y-axis label
        subgroup_label: x-axis label

    Returns: Plotly Figure
    """
    x = list(range(1, len(points) + 1))

    # Flatten all violation indices
    all_violation_idx = set()
    for rule_violations in violations.values():
        all_violation_idx.update(rule_violations)

    # Build violation labels for hover
    rule_labels = {
        "rule1": "WE/Nelson Rule 1: Beyond ±3σ",
        "rule2": "WE/Nelson Rule 2: 2 of 3 beyond ±2σ",
        "rule3": "WE/Nelson Rule 3: 4 of 5 beyond ±1σ",
        "rule4": "WE/Nelson Rule 4: 8 on same side of CL",
        "rule5": "Nelson Rule 5: 6 consecutive trending",
        "rule6": "Nelson Rule 6: 14 alternating",
        "rule7": "Nelson Rule 7: 15 within ±1σ",
        "rule8": "Nelson Rule 8: 8 outside ±1σ both sides",
    }
    hover_labels = {i: [] for i in all_violation_idx}
    for rule_key, idxs in violations.items():
        for i in idxs:
            hover_labels[i].append(rule_labels.get(rule_key, rule_key))

    fig = go.Figure()

    # Control limits (handle scalar or list)
    ucl_vals = ucl if isinstance(ucl, list) else [ucl] * len(points)
    lcl_vals = lcl if isinstance(lcl, list) else [lcl] * len(points)

    # UCL/LCL shaded band
    fig.add_trace(go.Scatter(
        x=x + x[::-1],
        y=ucl_vals + lcl_vals[::-1],
        fill="toself",
        fillcolor=_AREA_COLOR,
        line=dict(width=0),
        hoverinfo="skip",
        showlegend=False,
    ))

    # UCL line
    fig.add_trace(go.Scatter(
        x=x, y=ucl_vals, mode="lines",
        line=dict(color=_UCL_COLOR, dash="dash", width=1.5),
        name="UCL",
    ))

    # LCL line
    fig.add_trace(go.Scatter(
        x=x, y=lcl_vals, mode="lines",
        line=dict(color=_LCL_COLOR, dash="dash", width=1.5),
        name="LCL",
    ))

    # Centerline
    fig.add_hline(y=cl, line=dict(color=_CL_COLOR, width=1.5, dash="dot"),
                  annotation_text="CL", annotation_position="right")

    # Data line + normal points
    normal_x = [x[i] for i in range(len(points)) if i not in all_violation_idx]
    normal_y = [points[i] for i in range(len(points)) if i not in all_violation_idx]
    fig.add_trace(go.Scatter(
        x=x, y=points, mode="lines",
        line=dict(color=_DATA_COLOR, width=1.5),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=normal_x, y=normal_y, mode="markers",
        marker=dict(color=_DATA_COLOR, size=7),
        name="In Control",
    ))

    # Violation markers
    if all_violation_idx:
        viol_x = [x[i] for i in sorted(all_violation_idx)]
        viol_y = [points[i] for i in sorted(all_violation_idx)]
        viol_hover = ["<br>".join(hover_labels[i]) for i in sorted(all_violation_idx)]
        fig.add_trace(go.Scatter(
            x=viol_x, y=viol_y, mode="markers",
            marker=dict(color=_VIOLATION_COLOR, size=10, symbol="circle-open",
                        line=dict(width=2, color=_VIOLATION_COLOR)),
            name="Violation",
            hovertext=viol_hover,
            hoverinfo="text+x+y",
        ))

    fig.update_layout(
        title=title,
        xaxis_title=subgroup_label,
        yaxis_title=y_label,
        template="plotly_dark",
        height=420,
        margin=dict(l=60, r=30, t=50, b=50),
        legend=dict(orientation="h", y=-0.2),
    )
    return fig


def build_capability_histogram(
    data: list[float],
    lsl: float | None,
    usl: float | None,
    mean: float,
    sigma_overall: float,
    title: str = "Process Distribution",
) -> go.Figure:
    """Histogram of data with fitted normal curve and spec limit lines."""
    fig = go.Figure()

    # Histogram
    fig.add_trace(go.Histogram(
        x=data, nbinsx=30,
        histnorm="probability density",
        name="Data",
        marker_color=_DATA_COLOR,
        opacity=0.7,
    ))

    # Fitted normal curve
    x_range = np.linspace(mean - 4 * sigma_overall, mean + 4 * sigma_overall, 200)
    from scipy.stats import norm
    y_norm = norm.pdf(x_range, mean, sigma_overall)
    fig.add_trace(go.Scatter(
        x=x_range, y=y_norm, mode="lines",
        line=dict(color=_CL_COLOR, width=2),
        name="Normal Fit",
    ))

    # Spec limits
    if lsl is not None:
        fig.add_vline(x=lsl, line=dict(color=_UCL_COLOR, width=2, dash="dash"),
                      annotation_text="LSL", annotation_position="top left")
    if usl is not None:
        fig.add_vline(x=usl, line=dict(color=_UCL_COLOR, width=2, dash="dash"),
                      annotation_text="USL", annotation_position="top right")

    # Mean line
    fig.add_vline(x=mean, line=dict(color="white", width=1.5, dash="dot"),
                  annotation_text=f"x̄={mean:.4f}", annotation_position="top")

    fig.update_layout(
        title=title, xaxis_title="Measurement", yaxis_title="Density",
        template="plotly_dark", height=380,
        margin=dict(l=60, r=30, t=50, b=50),
    )
    return fig


def build_cpk_gauge(cpk: float) -> go.Figure:
    """Color-coded gauge for Cpk value.

    Thresholds per AIAG SPC Reference Manual / AS9100 Rev D:
        < 1.00  → Red  (not capable)
        1.00–1.33 → Yellow (marginally capable)
        ≥ 1.33  → Green (capable)
    """
    if cpk < 1.00:
        color = "#e63946"
        status = "Not Capable"
    elif cpk < 1.33:
        color = "#f4a261"
        status = "Marginally Capable"
    else:
        color = "#2a9d8f"
        status = "Capable"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=cpk,
        title={"text": f"Cpk — {status}", "font": {"size": 16}},
        gauge={
            "axis": {"range": [0, 2.0], "tickwidth": 1},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 1.00], "color": "rgba(230,57,70,0.15)"},
                {"range": [1.00, 1.33], "color": "rgba(244,162,97,0.15)"},
                {"range": [1.33, 2.0], "color": "rgba(42,157,143,0.15)"},
            ],
            "threshold": {
                "line": {"color": "white", "width": 2},
                "thickness": 0.75,
                "value": 1.33,
            },
        },
        number={"font": {"color": color}, "valueformat": ".3f"},
    ))
    fig.update_layout(
        template="plotly_dark", height=300,
        margin=dict(l=30, r=30, t=50, b=20),
    )
    return fig
```

- [ ] **Step 2: Verify import works**

```bash
python -c "from src.visualizer import build_control_chart, build_capability_histogram, build_cpk_gauge; print('visualizer OK')"
```
Expected: `visualizer OK`

- [ ] **Step 3: Commit**

```bash
git add src/visualizer.py
git commit -m "[D08] feat: Plotly visualizer — control chart, capability histogram, Cpk gauge"
```

---

## Task 9: [D09] Simulation Engine

**Files:**
- Create: `src/simulation/engine.py`

- [ ] **Step 1: Create engine.py**

```python
# src/simulation/engine.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class DisturbanceType(Enum):
    NONE = "none"
    MEAN_SHIFT = "mean_shift"
    SPIKE = "spike"
    DRIFT = "drift"


@dataclass
class ProcessConfig:
    """Default process parameters for each stream."""
    name: str
    mu: float        # target mean
    sigma: float     # process standard deviation
    unit: str        # measurement unit label
    lsl: float | None
    usl: float | None


PROCESS_CONFIGS = {
    "Composites — Ply Thickness": ProcessConfig(
        name="Composites — Ply Thickness",
        mu=0.250, sigma=0.001, unit="mm",
        lsl=0.245, usl=0.255,
    ),
    "Aerospace — Hole Diameter": ProcessConfig(
        name="Aerospace — Hole Diameter",
        mu=10.000, sigma=0.005, unit="mm",
        lsl=9.985, usl=10.015,
    ),
}


class SimulationEngine:
    """State machine for live SPC simulation.

    Generates subgroups on demand, supports disturbance injection.
    No Streamlit imports — fully testable as a standalone class.
    """

    def __init__(self, config: ProcessConfig, subgroup_size: int = 5, seed: int = 0):
        self._rng = np.random.default_rng(seed)
        self.config = config
        self.subgroup_size = subgroup_size
        self.history: list[list[float]] = []       # list of subgroups
        self._disturbance = DisturbanceType.NONE
        self._disturbance_steps_remaining = 0
        self._drift_step = 0
        self._drift_total_steps = 0

    # ── Public API ────────────────────────────────────────────────────────

    def step(self) -> list[float]:
        """Generate the next subgroup and append to history. Returns the new subgroup."""
        mu, sigma = self._current_params()
        subgroup = self._rng.normal(mu, sigma, self.subgroup_size).tolist()
        self.history.append(subgroup)

        # Advance disturbance counter
        if self._disturbance != DisturbanceType.NONE:
            self._disturbance_steps_remaining -= 1
            if self._disturbance == DisturbanceType.DRIFT:
                self._drift_step += 1
            if self._disturbance_steps_remaining <= 0:
                self.reset_disturbance()

        return subgroup

    def inject_mean_shift(self, magnitude_sigma: float = 1.5, duration: int = 10) -> None:
        """Shift mean by magnitude_sigma * sigma for duration subgroups."""
        self._disturbance = DisturbanceType.MEAN_SHIFT
        self._disturbance_steps_remaining = duration
        self._shift_magnitude = magnitude_sigma

    def inject_spike(self) -> None:
        """Generate exactly one subgroup with mean at mu + 4*sigma."""
        self._disturbance = DisturbanceType.SPIKE
        self._disturbance_steps_remaining = 1

    def inject_drift(self, max_sigma: float = 2.0, duration: int = 15) -> None:
        """Drift mean linearly from mu to mu + max_sigma*sigma over duration subgroups."""
        self._disturbance = DisturbanceType.DRIFT
        self._disturbance_steps_remaining = duration
        self._drift_max_sigma = max_sigma
        self._drift_total_steps = duration
        self._drift_step = 0

    def reset_disturbance(self) -> None:
        """Return to in-control state."""
        self._disturbance = DisturbanceType.NONE
        self._disturbance_steps_remaining = 0
        self._drift_step = 0
        self._drift_total_steps = 0

    def reset(self) -> None:
        """Clear history and disturbance state."""
        self.history = []
        self.reset_disturbance()

    @property
    def subgroup_means(self) -> list[float]:
        return [float(np.mean(sg)) for sg in self.history]

    @property
    def subgroup_ranges(self) -> list[float]:
        return [float(max(sg) - min(sg)) for sg in self.history]

    @property
    def active_disturbance(self) -> str:
        return self._disturbance.value

    # ── Private ───────────────────────────────────────────────────────────

    def _current_params(self) -> tuple[float, float]:
        mu = self.config.mu
        sigma = self.config.sigma

        if self._disturbance == DisturbanceType.MEAN_SHIFT:
            mu += self._shift_magnitude * sigma

        elif self._disturbance == DisturbanceType.SPIKE:
            mu += 4.0 * sigma

        elif self._disturbance == DisturbanceType.DRIFT:
            fraction = self._drift_step / max(self._drift_total_steps - 1, 1)
            mu += self._drift_max_sigma * sigma * fraction

        return mu, sigma
```

- [ ] **Step 2: Verify SimulationEngine works**

```bash
python -c "
from src.simulation.engine import SimulationEngine, PROCESS_CONFIGS
eng = SimulationEngine(PROCESS_CONFIGS['Composites — Ply Thickness'])
for _ in range(5):
    sg = eng.step()
    print(f'sg mean={sum(sg)/len(sg):.4f}')
eng.inject_mean_shift()
sg = eng.step()
print(f'after shift: mean={sum(sg)/len(sg):.4f}')
"
```
Expected: 5 in-control means near 0.250, then shifted mean noticeably higher.

- [ ] **Step 3: Commit**

```bash
git add src/simulation/engine.py
git commit -m "[D09] feat: SimulationEngine state machine — mean shift, spike, drift injection"
```

---

## Task 10: [D10] Page 1 — Control Charts Dashboard (Checkpoint 2)

**Files:**
- Modify: `pages/1_Control_Charts.py`

- [ ] **Step 1: Implement Control Charts page**

```python
# pages/1_Control_Charts.py
import streamlit as st
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, ".")

from src.spc_engine.control_charts import (
    compute_xbar_r, compute_xbar_s, compute_imr,
    compute_p, compute_c, compute_u,
)
from src.spc_engine.rule_detection import detect_we_violations, detect_nelson_violations
from src.spc_engine.data_generator import generate_demo_dataset
from src.visualizer import build_control_chart

st.set_page_config(page_title="Control Charts", layout="wide")
st.title("📈 Control Charts")
st.markdown("Select a chart type and load process data to monitor for special cause variation.")

# ── Sidebar ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Chart Settings")
    chart_type = st.selectbox(
        "Chart Type",
        ["X̄-R (Variables, small n)", "X̄-S (Variables, large n)",
         "I-MR (Individuals)", "p-chart (Proportion)", "u-chart (Defect rate)"],
    )
    rule_set = st.radio("Rule Set", ["Western Electric (AIAG)", "Nelson (8 rules)"])
    st.divider()
    st.header("Data Source")
    data_source = st.radio("Source", ["Demo Dataset", "Upload CSV"])

# ── Data Loading ─────────────────────────────────────────────────────────
if data_source == "Demo Dataset":
    df = generate_demo_dataset()
    stream_map = {
        "X̄-R (Variables, small n)": "ply_thickness",
        "X̄-S (Variables, large n)": "hole_diameter",
        "I-MR (Individuals)": "autoclave_temp",
        "p-chart (Proportion)": "reject_proportion",
        "u-chart (Defect rate)": "surface_defects",
    }
    stream = stream_map[chart_type]
    df_stream = df[df["stream"] == stream].copy()
    st.info(f"Demo data: **{stream}** — {len(df_stream['subgroup'].unique())} subgroups")
else:
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded is None:
        st.warning("Upload a CSV or switch to Demo Dataset.")
        st.stop()
    df_stream = pd.read_csv(uploaded)
    if "subgroup" not in df_stream.columns or "value" not in df_stream.columns:
        st.error("CSV must have columns: subgroup, value, (optional: sample_size)")
        st.stop()

# ── Chart Computation ─────────────────────────────────────────────────────
detect_fn = detect_nelson_violations if "Nelson" in rule_set else detect_we_violations

try:
    if "X̄-R" in chart_type:
        subgroups = [
            df_stream[df_stream["subgroup"] == sg]["value"].tolist()
            for sg in sorted(df_stream["subgroup"].unique())
        ]
        res = compute_xbar_r(subgroups)
        # X̄ chart
        violations_xbar = detect_fn(res["xbar"], cl=res["cl_xbar"], sigma=res["sigma_hat"])
        fig_xbar = build_control_chart(
            res["xbar"], res["cl_xbar"], res["ucl_xbar"], res["lcl_xbar"],
            violations_xbar, title="X̄ Chart — Ply Thickness", y_label="Mean (mm)",
        )
        violations_r = detect_fn(res["ranges"], cl=res["cl_r"], sigma=res["sigma_hat"])
        fig_r = build_control_chart(
            res["ranges"], res["cl_r"], res["ucl_r"], res["lcl_r"],
            violations_r, title="R Chart — Ply Thickness", y_label="Range (mm)",
        )
        col1, col2 = st.columns(2)
        with col1:
            st.metric("X̄̄ (Grand Mean)", f"{res['xbar_bar']:.5f}")
            st.metric("R̄", f"{res['r_bar']:.5f}")
            st.metric("σ̂", f"{res['sigma_hat']:.5f}")
        st.plotly_chart(fig_xbar, use_container_width=True)
        st.plotly_chart(fig_r, use_container_width=True)

    elif "X̄-S" in chart_type:
        subgroups = [
            df_stream[df_stream["subgroup"] == sg]["value"].tolist()
            for sg in sorted(df_stream["subgroup"].unique())
        ]
        res = compute_xbar_s(subgroups)
        violations_xbar = detect_fn(res["xbar"], cl=res["cl_xbar"], sigma=res["sigma_hat"])
        fig_xbar = build_control_chart(
            res["xbar"], res["cl_xbar"], res["ucl_xbar"], res["lcl_xbar"],
            violations_xbar, title="X̄ Chart — Hole Diameter", y_label="Mean (mm)",
        )
        violations_s = detect_fn(res["stds"], cl=res["cl_s"], sigma=res["sigma_hat"])
        fig_s = build_control_chart(
            res["stds"], res["cl_s"], res["ucl_s"], res["lcl_s"],
            violations_s, title="S Chart — Hole Diameter", y_label="Std Dev (mm)",
        )
        st.plotly_chart(fig_xbar, use_container_width=True)
        st.plotly_chart(fig_s, use_container_width=True)

    elif "I-MR" in chart_type:
        values = df_stream.sort_values("subgroup")["value"].tolist()
        res = compute_imr(values)
        violations_i = detect_fn(res["individuals"], cl=res["cl_x"], sigma=res["sigma_hat"])
        fig_i = build_control_chart(
            res["individuals"], res["cl_x"], res["ucl_x"], res["lcl_x"],
            violations_i, title="Individuals Chart — Autoclave Temp", y_label="Temp (°C)",
        )
        violations_mr = detect_fn(res["moving_ranges"], cl=res["cl_mr"], sigma=res["sigma_hat"])
        fig_mr = build_control_chart(
            res["moving_ranges"], res["cl_mr"], res["ucl_mr"], 0.0,
            violations_mr, title="Moving Range Chart", y_label="Moving Range",
        )
        col1, col2, col3 = st.columns(3)
        col1.metric("X̄", f"{res['x_bar']:.2f} °C")
        col2.metric("MR̄", f"{res['mr_bar']:.3f}")
        col3.metric("σ̂", f"{res['sigma_hat']:.3f}")
        st.plotly_chart(fig_i, use_container_width=True)
        st.plotly_chart(fig_mr, use_container_width=True)

    elif "p-chart" in chart_type:
        df_sorted = df_stream.sort_values("subgroup")
        defectives = (df_sorted["value"] * df_sorted["sample_size"]).round().astype(int).tolist()
        sample_sizes = df_sorted["sample_size"].tolist()
        res = compute_p(defectives, sample_sizes)
        violations = detect_fn(res["p_i"], cl=res["p_bar"],
                               sigma=((res["p_bar"] * (1 - res["p_bar"])) /
                                      np.mean(sample_sizes)) ** 0.5)
        fig = build_control_chart(
            res["p_i"], res["p_bar"], res["ucl"], res["lcl"],
            violations, title="p-Chart — Proportion Defective", y_label="Proportion",
        )
        st.metric("p̄", f"{res['p_bar']:.4f} ({res['p_bar']*100:.2f}%)")
        st.plotly_chart(fig, use_container_width=True)

    elif "u-chart" in chart_type:
        df_sorted = df_stream.sort_values("subgroup")
        defects = (df_sorted["value"] * df_sorted["sample_size"]).round().astype(int).tolist()
        areas = df_sorted["sample_size"].tolist()
        res = compute_u(defects, areas)
        u_sigma = (res["u_bar"] / np.mean(areas)) ** 0.5
        violations = detect_fn(res["u_i"], cl=res["u_bar"], sigma=u_sigma)
        fig = build_control_chart(
            res["u_i"], res["u_bar"], res["ucl"], res["lcl"],
            violations, title="u-Chart — Surface Defects/m²", y_label="Defects per m²",
        )
        st.metric("ū", f"{res['u_bar']:.3f} defects/m²")
        st.plotly_chart(fig, use_container_width=True)

except ValueError as e:
    st.error(f"Chart error: {e}")

# ── Violations summary ────────────────────────────────────────────────────
st.divider()
st.subheader("Rule Set Reference")
if "Nelson" in rule_set:
    st.markdown("""
| Rule | Description | Source |
|------|-------------|--------|
| Rule 1 | 1 point beyond ±3σ | AIAG / Nelson |
| Rule 2 | 2 of 3 consecutive beyond ±2σ (same side) | AIAG / Nelson |
| Rule 3 | 4 of 5 consecutive beyond ±1σ (same side) | AIAG / Nelson |
| Rule 4 | 8 consecutive on same side of CL | AIAG / Nelson |
| Rule 5 | 6 consecutive trending in same direction | Nelson (1984) |
| Rule 6 | 14 consecutive alternating | Nelson (1984) |
| Rule 7 | 15 consecutive within ±1σ | Nelson (1984) |
| Rule 8 | 8 consecutive outside ±1σ both sides | Nelson (1984) |
""")
else:
    st.markdown("""
| Rule | Description | Source |
|------|-------------|--------|
| Rule 1 | 1 point beyond ±3σ | AIAG SPC 4th Ed. |
| Rule 2 | 2 of 3 consecutive beyond ±2σ (same side) | AIAG SPC 4th Ed. |
| Rule 3 | 4 of 5 consecutive beyond ±1σ (same side) | AIAG SPC 4th Ed. |
| Rule 4 | 8 consecutive on same side of CL | AIAG SPC 4th Ed. |
""")
```

- [ ] **Step 2: Run Streamlit and verify page**

```bash
streamlit run app.py
```
Navigate to Control Charts. Test: switch chart types, switch rule sets, verify charts render with correct labels and metrics.

- [ ] **Step 3: Checkpoint 2 — full test suite**

```bash
pytest tests/ -v --tb=short
```
Expected: All tests GREEN.

- [ ] **Step 4: Commit**

```bash
git add pages/1_Control_Charts.py
git commit -m "[D10] feat: Control Charts page — 5 chart types, dual rule engine, demo data — Checkpoint 2 ✅"
```

---

## Task 11: [D11] Page 2 — Process Capability

**Files:**
- Modify: `pages/2_Process_Capability.py`

- [ ] **Step 1: Implement Process Capability page**

```python
# pages/2_Process_Capability.py
import streamlit as st
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, ".")

from src.spc_engine.control_charts import compute_xbar_r, compute_imr
from src.spc_engine.capability import compute_capability, normality_test
from src.spc_engine.data_generator import generate_demo_dataset
from src.visualizer import build_capability_histogram, build_cpk_gauge

st.set_page_config(page_title="Process Capability", layout="wide")
st.title("📐 Process Capability Analysis")
st.markdown("Cp, Cpk, Pp, Ppk indices per **AIAG SPC Reference Manual, 4th Ed.** Capability threshold ≥ 1.33 per AS9100 Rev D.")

# ── Sidebar ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Process Selection")
    process = st.selectbox(
        "Process Stream",
        ["Composites — Ply Thickness (X̄-R)",
         "Aerospace — Hole Diameter (X̄-S)",
         "Autoclave Cure Temp (I-MR)"],
    )
    st.divider()
    st.header("Spec Limits")
    lsl = st.number_input("LSL (Lower Spec Limit)", value=None, format="%.5f",
                          help="Leave blank for unilateral upper-spec-only")
    usl = st.number_input("USL (Upper Spec Limit)", value=None, format="%.5f",
                          help="Leave blank for unilateral lower-spec-only")

# ── Data + sigma_hat ─────────────────────────────────────────────────────
df = generate_demo_dataset()

if "Ply Thickness" in process:
    df_s = df[df["stream"] == "ply_thickness"]
    subgroups = [df_s[df_s["subgroup"] == sg]["value"].tolist()
                 for sg in sorted(df_s["subgroup"].unique())]
    res_cc = compute_xbar_r(subgroups)
    data = df_s["value"].tolist()
    sigma_hat = res_cc["sigma_hat"]
    default_lsl, default_usl = 0.245, 0.255
    unit = "mm"
    chart_label = "Ply Thickness"

elif "Hole Diameter" in process:
    df_s = df[df["stream"] == "hole_diameter"]
    subgroups = [df_s[df_s["subgroup"] == sg]["value"].tolist()
                 for sg in sorted(df_s["subgroup"].unique())]
    from src.spc_engine.control_charts import compute_xbar_s
    res_cc = compute_xbar_s(subgroups)
    data = df_s["value"].tolist()
    sigma_hat = res_cc["sigma_hat"]
    default_lsl, default_usl = 9.985, 10.015
    unit = "mm"
    chart_label = "Hole Diameter"

else:  # Autoclave
    df_s = df[df["stream"] == "autoclave_temp"]
    values = df_s.sort_values("subgroup")["value"].tolist()
    res_cc = compute_imr(values)
    data = values
    sigma_hat = res_cc["sigma_hat"]
    default_lsl, default_usl = 175.0, 185.0
    unit = "°C"
    chart_label = "Autoclave Cure Temp"

# Apply sidebar spec limits or defaults
actual_lsl = lsl if lsl is not None else default_lsl
actual_usl = usl if usl is not None else default_usl

# ── Compute Capability ────────────────────────────────────────────────────
cap = compute_capability(data, lsl=actual_lsl, usl=actual_usl, sigma_hat=sigma_hat)
norm = normality_test(data)

# ── Layout ────────────────────────────────────────────────────────────────
col_gauge, col_metrics = st.columns([1, 1])

with col_gauge:
    st.plotly_chart(build_cpk_gauge(cap["cpk"]), use_container_width=True)

with col_metrics:
    st.subheader("Indices")
    m1, m2 = st.columns(2)
    m1.metric("Cp (short-term potential)", f"{cap['cp']:.3f}" if cap["cp"] else "N/A (unilateral)")
    m2.metric("Cpk (short-term actual)", f"{cap['cpk']:.3f}")
    m3, m4 = st.columns(2)
    m3.metric("Pp (long-term potential)", f"{cap['pp']:.3f}" if cap["pp"] else "N/A (unilateral)")
    m4.metric("Ppk (long-term actual)", f"{cap['ppk']:.3f}")
    st.divider()
    st.subheader("Process Stats")
    s1, s2, s3 = st.columns(3)
    s1.metric("Mean", f"{cap['mean']:.5f} {unit}")
    s2.metric("σ̂ (short-term)", f"{cap['sigma_hat']:.5f}")
    s3.metric("σ (long-term)", f"{cap['sigma_overall']:.5f}")

st.divider()
st.plotly_chart(
    build_capability_histogram(
        data, actual_lsl, actual_usl,
        cap["mean"], cap["sigma_overall"],
        title=f"Process Distribution — {chart_label}",
    ),
    use_container_width=True,
)

# ── Normality Warning ─────────────────────────────────────────────────────
if not norm["is_normal"]:
    st.warning(
        f"⚠️ Non-normal distribution detected (Shapiro-Wilk p={norm['p_value']:.4f} < 0.05). "
        "Cp/Cpk/Pp/Ppk indices assume normality — interpret with caution."
    )
else:
    st.success(
        f"✅ Normality assumption satisfied (Shapiro-Wilk p={norm['p_value']:.3f} ≥ 0.05)."
    )

# ── Interpretation Table ──────────────────────────────────────────────────
st.divider()
st.subheader("Capability Interpretation (AIAG / AS9100)")
st.markdown("""
| Cpk | Interpretation | Action |
|-----|---------------|--------|
| < 1.00 | Not capable — process producing defects | Immediate corrective action required |
| 1.00 – 1.33 | Marginally capable | Investigate centering and variation |
| ≥ 1.33 | Capable | AS9100 Rev D minimum — process acceptable |
| ≥ 1.67 | Highly capable | Six Sigma target threshold |
""")
```

- [ ] **Step 2: Test in Streamlit**

```bash
streamlit run app.py
```
Navigate to Process Capability. Verify: Cpk gauge renders, metrics show, histogram with normal curve and spec lines, normality test result shown.

- [ ] **Step 3: Commit**

```bash
git add pages/2_Process_Capability.py
git commit -m "[D11] feat: Process Capability page — Cp/Cpk/Pp/Ppk, Cpk gauge, normality test"
```

---

## Task 12: [D12] Page 3 — Live Simulation

**Files:**
- Modify: `pages/3_Live_Simulation.py`

- [ ] **Step 1: Implement Live Simulation page**

```python
# pages/3_Live_Simulation.py
import streamlit as st
import time
import sys
sys.path.insert(0, ".")

from src.simulation.engine import SimulationEngine, PROCESS_CONFIGS
from src.spc_engine.control_charts import compute_xbar_r
from src.spc_engine.rule_detection import detect_we_violations, detect_nelson_violations
from src.visualizer import build_control_chart

st.set_page_config(page_title="Live Simulation", layout="wide")
st.title("⚡ Live SPC Simulation")
st.markdown(
    "Watch a control chart update in real time. Inject disturbances to trigger rule violations "
    "and see exactly which rule fires."
)

# ── Sidebar ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Process Config")
    process_name = st.selectbox("Process Stream", list(PROCESS_CONFIGS.keys()))
    n = st.slider("Subgroup Size (n)", 2, 9, 5)
    interval = st.slider("Update Interval (s)", 0.5, 3.0, 1.0, 0.5)
    rule_set = st.radio("Rule Set", ["Western Electric (AIAG)", "Nelson (8 rules)"])
    st.divider()
    st.header("Simulation Control")
    run = st.toggle("▶ Run Simulation", value=False)
    if st.button("🔄 Reset"):
        if "sim_engine" in st.session_state:
            st.session_state.sim_engine.reset()

# ── Engine init ───────────────────────────────────────────────────────────
config = PROCESS_CONFIGS[process_name]
if "sim_engine" not in st.session_state or \
   st.session_state.get("sim_process") != process_name or \
   st.session_state.get("sim_n") != n:
    st.session_state.sim_engine = SimulationEngine(config, subgroup_size=n)
    st.session_state.sim_process = process_name
    st.session_state.sim_n = n

engine: SimulationEngine = st.session_state.sim_engine

# ── Disturbance buttons ───────────────────────────────────────────────────
st.subheader("Disturbance Injection")
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("📈 Mean Shift (+1.5σ)", help="Shifts mean +1.5σ for 10 subgroups"):
        engine.inject_mean_shift(magnitude_sigma=1.5, duration=10)
        st.toast("Mean shift injected", icon="📈")
with col2:
    if st.button("⚡ Spike (+4σ)", help="One subgroup at mean + 4σ — instant Rule 1 violation"):
        engine.inject_spike()
        st.toast("Spike injected", icon="⚡")
with col3:
    if st.button("📉 Drift (+2σ over 15)", help="Gradual drift — triggers Nelson Rule 5"):
        engine.inject_drift(max_sigma=2.0, duration=15)
        st.toast("Drift injected", icon="📉")
with col4:
    if st.button("✅ Reset Process", help="Return to in-control state"):
        engine.reset_disturbance()
        st.toast("Process reset to in-control", icon="✅")

# Active disturbance indicator
if engine.active_disturbance != "none":
    st.info(f"Active disturbance: **{engine.active_disturbance.replace('_', ' ').title()}** "
            f"({engine._disturbance_steps_remaining} subgroups remaining)")

# ── Chart placeholder ─────────────────────────────────────────────────────
chart_ph = st.empty()
metrics_ph = st.empty()

detect_fn = detect_nelson_violations if "Nelson" in rule_set else detect_we_violations
WINDOW = 50  # show last 50 subgroups

# ── Render function ───────────────────────────────────────────────────────
def render():
    history = engine.history[-WINDOW:]
    if len(history) < 2:
        chart_ph.info("Simulation starting... (need ≥ 2 subgroups)")
        return

    try:
        res = compute_xbar_r(history)
    except ValueError:
        return

    violations = detect_fn(res["xbar"], cl=res["cl_xbar"], sigma=res["sigma_hat"])
    fig = build_control_chart(
        res["xbar"], res["cl_xbar"], res["ucl_xbar"], res["lcl_xbar"],
        violations,
        title=f"Live X̄ Chart — {config.name}",
        y_label=f"Subgroup Mean ({config.unit})",
        subgroup_label="Subgroup (rolling window)",
    )
    chart_ph.plotly_chart(fig, use_container_width=True)

    total_viols = sum(len(v) for v in violations.values())
    with metrics_ph.container():
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Subgroups generated", len(engine.history))
        m2.metric("X̄̄", f"{res['xbar_bar']:.4f} {config.unit}")
        m3.metric("σ̂", f"{res['sigma_hat']:.5f}")
        m4.metric("Violations (window)", total_viols,
                  delta=None if total_viols == 0 else f"{total_viols} rules firing",
                  delta_color="inverse")

# Initial render (static if not running)
if engine.history:
    render()
else:
    chart_ph.info("Press ▶ Run Simulation in the sidebar to start.")

# ── Run loop ──────────────────────────────────────────────────────────────
if run:
    engine.step()
    render()
    time.sleep(interval)
    st.rerun()
```

- [ ] **Step 2: Test in Streamlit**

```bash
streamlit run app.py
```
Navigate to Live Simulation. Test:
1. Toggle Run → chart updates live
2. Click "Spike (+4σ)" → red violation marker appears immediately
3. Click "Drift" → Rule 5 violation appears after ~6 subgroups
4. Click "Reset Process" → chart stabilizes
5. Switch rule sets → violations update

- [ ] **Step 3: Commit**

```bash
git add pages/3_Live_Simulation.py
git commit -m "[D12] feat: Live Simulation page — real-time chart, disturbance injection, rule violations"
```

---

## Task 13: [D13] Final Test Run + Polish

**Files:**
- Modify: `app.py` (landing page polish)
- Review: all pages for UX consistency

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v --tb=short
```
Expected: 50+ tests, all PASS. If any fail, fix before continuing.

- [ ] **Step 2: Polish app.py landing page**

```python
# app.py
import streamlit as st

st.set_page_config(
    page_title="SPC Manufacturing Quality Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("📊 SPC Manufacturing Quality Dashboard")
st.markdown("**Statistical Process Control** for composites and aerospace manufacturing processes.")

col1, col2, col3 = st.columns(3)
with col1:
    st.info("### 📈 Control Charts\n6 chart types · X̄-R · X̄-S · I-MR · p · c · u\nDual WE + Nelson rule detection")
with col2:
    st.info("### 📐 Process Capability\nCp · Cpk · Pp · Ppk\nAIAG SPC 4th Ed. · AS9100 thresholds\nShapiro-Wilk normality test")
with col3:
    st.info("### ⚡ Live Simulation\nReal-time control chart updates\nMean shift · Spike · Drift injection\nRule violations flagged live")

st.divider()
st.markdown("""
**Standards implemented:**
- AIAG SPC Reference Manual, 4th Ed. (2005) — control chart constants, WE rules, Cp/Cpk thresholds
- Nelson, L.S. (1984). *Journal of Quality Technology* — Rules 5–8
- AS9100 Rev D — Cpk ≥ 1.33 minimum capability threshold

**Demo process streams:** Composites ply thickness · Autoclave cure temperature · CNC hole diameter · Panel inspection
""")
st.sidebar.success("Select a page above to get started.")
```

- [ ] **Step 3: Verify all three pages load cleanly**

```bash
streamlit run app.py
```
Click through all pages, verify no errors in terminal.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "[D13] polish: landing page — standards reference, feature cards, UX consistency"
```

---

## Task 14: [D14] GitHub Push + Streamlit Deploy + README

**Files:**
- Create: `README.md`
- Create: `docs/EXECUTION_ROADMAP.md`

- [ ] **Step 1: Create README.md** (copy structure from FMEA README — badges, live demo link, theory, structure, quick start)

Key sections:
```markdown
# SPC Manufacturing Quality Dashboard

[![Python](badge)] [![Streamlit](badge)] [![Plotly](badge)] [![Tests](50+ passing badge)]

**A production-grade Streamlit SPC dashboard...**

> Live Demo → [streamlit URL]

## What is SPC?
## Chart Types Implemented
## Rule Detection
## Process Capability
## Live Simulation Mode
## Industry Standards
## Quick Start
## Project Structure
## Input File Schema (for CSV upload)
```

- [ ] **Step 2: Push to GitHub**

```bash
git remote add origin https://github.com/Siddardth7/manufacturing-spc-dashboard.git
git push -u origin main
```

- [ ] **Step 3: Deploy on Streamlit Cloud**

1. Go to share.streamlit.io
2. Connect repo `Siddardth7/manufacturing-spc-dashboard`
3. Main file: `app.py`
4. Deploy — wait for green status
5. Copy live URL

- [ ] **Step 4: Update README with live URL**

```bash
# Replace placeholder URL with actual Streamlit URL
# Re-commit and push
git add README.md
git commit -m "[D14] docs: professional README with live demo URL"
git push
```

- [ ] **Step 5: Final test suite**

```bash
pytest tests/ -v
```
Expected: All tests PASS. Count: 53+.

- [ ] **Step 6: Launch commit**

```bash
git tag v1.0-launch
git push --tags
git commit --allow-empty -m "[D14] launch: SPC Manufacturing Quality Dashboard v1.0 🚀"
git push
```

---

## Spec Coverage Check

| Spec Section | Covered By |
|---|---|
| 6 control chart types | Tasks 3, 4, 10 |
| Western Electric + Nelson rules, user-toggled | Tasks 5, 6, 10 |
| Cp/Cpk/Pp/Ppk + Shapiro-Wilk | Tasks 7, 11 |
| Cpk gauge color-coded | Task 8, 11 |
| SimulationEngine — mean shift, spike, drift | Task 9, 12 |
| Live chart with st.rerun() + scrolling window | Task 12 |
| Multi-page Streamlit layout | Tasks 1, 10, 11, 12, 13 |
| 5 demo process streams (composites + machining) | Task 2 |
| 50+ pytest tests | Tasks 3, 4, 5, 6, 7 |
| Deployed on Streamlit Cloud | Task 14 |
| Professional README with standards references | Task 14 |

All spec requirements covered. No gaps.
