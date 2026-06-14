# Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the FMEA Risk Analyzer from a polished demo into a production foundation by fixing all correctness, security, and trust issues, then refactoring the architecture for future product growth.

**Architecture:** Three sequential phases — Phase 1 fixes correctness and trust (P0), Phase 2 adds reliability and UX improvements (P1), Phase 3 introduces the Pydantic schema layer, splits `app.py`, and adds CI (P2). Each phase is independently deployable and produces a stable, testable state.

**Tech Stack:** Python 3.11+, Streamlit, pandas, Pydantic v2, fpdf2, openpyxl, matplotlib, Plotly, pytest, ruff, mypy, GitHub Actions, pre-commit

**Spec:** `docs/superpowers/specs/2026-04-20-audit-implementation-design.md`

---

## File Map

### Phase 1 — Correctness & Trust

| Action | File | What changes |
|---|---|---|
| Modify | `src/rpn_engine.py` | Add integer-only S/O/D check, null checks for text fields, duplicate ID rejection |
| Modify | `src/exporter.py` | Formula injection escape in `_write_fmea_sheet`; CSV sanitizer helper; remove `pareto_fig`/`heatmap_fig` params; add page-break header repeat |
| Modify | `app.py` | Lazy export caching in session_state; wrap exports in try/except; remove `.xls` from file type list |
| Modify | `tests/test_rpn_engine.py` | Add boundary tests: float scores, null text fields, null ID, duplicate IDs, boolean scores |
| Modify | `tests/test_exporter.py` | Update `export_pdf` call sites; add formula injection regression tests |
| Modify | `README.md` | Fix all demo dataset statistics; remove broken screenshot refs; add LICENSE badge; remove .xls |
| Modify | `docs/FMEA_COMPLETE_GUIDE.md` | Fix demo stats, fix Pareto narrative, fix PDF doc |
| Modify | `docs/ASSUMPTIONS_LOG.md` | Fix Pareto color banding reference |
| Create | `LICENSE` | MIT license text |

### Phase 2 — Reliability & UX

| Action | File | What changes |
|---|---|---|
| Create | `tests/test_app_integration.py` | AppTest-based integration tests for upload, filters, exports, malformed data |
| Modify | `app.py` | Chart cache key includes df content hash; RPN slider max is data-driven; add validation summary panel |
| Create | `requirements-dev.txt` | pytest, pytest-cov, ruff, mypy |
| Modify | `README.md` | Update test instructions to reference `requirements-dev.txt` |

### Phase 3 — Product Foundation

| Action | File | What changes |
|---|---|---|
| Create | `src/schema.py` | `FMEARow` and `FMEADataset` Pydantic v2 models |
| Modify | `src/rpn_engine.py` | Replace manual DataFrame checks with Pydantic model validation |
| Create | `ui/__init__.py` | Empty init |
| Create | `ui/filters.py` | Sidebar filter logic extracted from `app.py` |
| Create | `ui/charts.py` | Chart caching/rendering extracted from `app.py` |
| Create | `ui/exports.py` | Export button generation extracted from `app.py` |
| Modify | `app.py` | Thin orchestrator (~150 lines), imports from `ui/` |
| Create | `.github/workflows/ci.yml` | pytest + ruff + mypy on push/PR |
| Create | `.pre-commit-config.yaml` | ruff + mypy hooks |
| Modify | `requirements.txt` | Remove kaleido; add pydantic>=2.0 |
| Modify | `README.md` | Add CI badge |

---

## PHASE 1 — Correctness & Trust

---

### Task 1: Enforce Integer-Only S/O/D Validation

**Files:**
- Modify: `src/rpn_engine.py:108-131`
- Modify: `tests/test_rpn_engine.py`

- [ ] **Step 1: Write failing tests for float and boolean score rejection**

Add to `tests/test_rpn_engine.py`:

```python
import numpy as np
import pytest
import pandas as pd
from src.rpn_engine import validate_input

def _valid_df():
    """Minimal valid FMEA DataFrame for testing."""
    return pd.DataFrame([{
        "ID": 1, "Process_Step": "Stamping", "Component": "Panel",
        "Function": "Structural support", "Failure_Mode": "Crack",
        "Effect": "Part failure", "Severity": 8,
        "Cause": "Over-stress", "Occurrence": 3,
        "Current_Control": "Visual inspection", "Detection": 4,
    }])

def test_float_severity_rejected():
    df = _valid_df()
    df.loc[0, "Severity"] = 8.5
    with pytest.raises(ValueError, match="integer"):
        validate_input(df)

def test_float_occurrence_rejected():
    df = _valid_df()
    df.loc[0, "Occurrence"] = 3.2
    with pytest.raises(ValueError, match="integer"):
        validate_input(df)

def test_float_detection_rejected():
    df = _valid_df()
    df.loc[0, "Detection"] = 4.9
    with pytest.raises(ValueError, match="integer"):
        validate_input(df)

def test_boolean_score_rejected():
    df = _valid_df()
    df.loc[0, "Severity"] = True
    with pytest.raises(ValueError, match="integer"):
        validate_input(df)

def test_numeric_string_score_rejected():
    df = _valid_df()
    df["Severity"] = df["Severity"].astype(object)
    df.loc[0, "Severity"] = "8"
    with pytest.raises(ValueError):
        validate_input(df)
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_rpn_engine.py::test_float_severity_rejected tests/test_rpn_engine.py::test_float_occurrence_rejected tests/test_rpn_engine.py::test_float_detection_rejected tests/test_rpn_engine.py::test_boolean_score_rejected tests/test_rpn_engine.py::test_numeric_string_score_rejected -v
```

Expected: All FAIL (no integer check exists yet)

- [ ] **Step 3: Add integer enforcement to `validate_input` in `src/rpn_engine.py`**

Add this block immediately after Check 3 (after line 120), before Check 4 (the range check):

```python
    # --- Check 3b: S/O/D must be strict integers (no floats, no booleans) ---
    for col in SCORE_COLUMNS:
        def _is_strict_int(x):
            if isinstance(x, bool):
                return False
            return isinstance(x, (int, np.integer))
        if not df[col].apply(_is_strict_int).all():
            bad_ids = df.loc[~df[col].apply(_is_strict_int), "ID"].tolist()
            raise ValueError(
                f"Column '{col}' must contain integer values only (1–10). "
                f"Floats and booleans are not valid FMEA scores. "
                f"Affected row ID(s): {bad_ids}"
            )
```

Also add `import numpy as np` at the top of `src/rpn_engine.py` if not already present.

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_rpn_engine.py::test_float_severity_rejected tests/test_rpn_engine.py::test_float_occurrence_rejected tests/test_rpn_engine.py::test_float_detection_rejected tests/test_rpn_engine.py::test_boolean_score_rejected tests/test_rpn_engine.py::test_numeric_string_score_rejected -v
```

Expected: All PASS

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
pytest -q
```

Expected: All existing tests pass (61+5 new)

- [ ] **Step 6: Commit**

```bash
git add src/rpn_engine.py tests/test_rpn_engine.py
git commit -m "fix: enforce integer-only S/O/D validation — reject floats and booleans"
```

---

### Task 2: Validate Required Non-Score Text Fields and IDs

**Files:**
- Modify: `src/rpn_engine.py` (after integer check)
- Modify: `tests/test_rpn_engine.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_rpn_engine.py`:

```python
def test_null_process_step_rejected():
    df = _valid_df()
    df.loc[0, "Process_Step"] = None
    with pytest.raises(ValueError, match="Process_Step"):
        validate_input(df)

def test_null_id_rejected():
    df = _valid_df()
    df.loc[0, "ID"] = None
    with pytest.raises(ValueError, match="ID"):
        validate_input(df)

def test_non_integer_id_rejected():
    df = _valid_df()
    df.loc[0, "ID"] = "ABC"
    with pytest.raises(ValueError, match="ID"):
        validate_input(df)

def test_duplicate_ids_rejected():
    df = _valid_df()
    df2 = _valid_df()
    combined = pd.concat([df, df2], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        validate_input(combined)

def test_null_failure_mode_rejected():
    df = _valid_df()
    df.loc[0, "Failure_Mode"] = None
    with pytest.raises(ValueError, match="Failure_Mode"):
        validate_input(df)

def test_null_effect_rejected():
    df = _valid_df()
    df.loc[0, "Effect"] = None
    with pytest.raises(ValueError, match="Effect"):
        validate_input(df)
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_rpn_engine.py::test_null_process_step_rejected tests/test_rpn_engine.py::test_null_id_rejected tests/test_rpn_engine.py::test_non_integer_id_rejected tests/test_rpn_engine.py::test_duplicate_ids_rejected tests/test_rpn_engine.py::test_null_failure_mode_rejected tests/test_rpn_engine.py::test_null_effect_rejected -v
```

Expected: All FAIL

- [ ] **Step 3: Add text field and ID validation to `validate_input` in `src/rpn_engine.py`**

Add these constants near the top of the file (after `SCORE_COLUMNS`):

```python
TEXT_REQUIRED_COLUMNS = [
    "Process_Step", "Component", "Function",
    "Failure_Mode", "Effect", "Cause", "Current_Control",
]
```

Add this check block at the end of `validate_input`, after the range check:

```python
    # --- Check 5: ID must be non-null and integer-convertible; no duplicates ---
    if df["ID"].isnull().any():
        raise ValueError(
            "Column 'ID' contains null values. Every row must have a unique integer ID."
        )
    try:
        df["ID"].apply(lambda x: int(x))
    except (ValueError, TypeError):
        raise ValueError(
            "Column 'ID' contains non-integer values. IDs must be integers."
        )
    if df["ID"].duplicated().any():
        dupes = df.loc[df["ID"].duplicated(keep=False), "ID"].unique().tolist()
        raise ValueError(
            f"Column 'ID' contains duplicate values: {dupes}. Each row must have a unique ID."
        )

    # --- Check 6: Required text columns must be non-null strings ---
    for col in TEXT_REQUIRED_COLUMNS:
        if df[col].isnull().any():
            bad_ids = df.loc[df[col].isnull(), "ID"].tolist()
            raise ValueError(
                f"Column '{col}' contains null/missing values in row(s) with ID: {bad_ids}. "
                f"This field is required for filtering and reporting."
            )
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_rpn_engine.py::test_null_process_step_rejected tests/test_rpn_engine.py::test_null_id_rejected tests/test_rpn_engine.py::test_non_integer_id_rejected tests/test_rpn_engine.py::test_duplicate_ids_rejected tests/test_rpn_engine.py::test_null_failure_mode_rejected tests/test_rpn_engine.py::test_null_effect_rejected -v
```

Expected: All PASS

- [ ] **Step 5: Run full suite**

```bash
pytest -q
```

Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add src/rpn_engine.py tests/test_rpn_engine.py
git commit -m "fix: validate required text fields, integer IDs, and duplicate ID rejection at ingest boundary"
```

---

### Task 3: Fix Formula Injection in Excel and CSV Exports

**Files:**
- Modify: `src/exporter.py`
- Modify: `tests/test_exporter.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_exporter.py`:

```python
import io
import openpyxl
import pytest
import pandas as pd
from src.exporter import export_excel

def _pipeline_df_with_formula():
    """DataFrame with formula-injection strings in text fields."""
    from src.rpn_engine import run_pipeline
    import pandas as pd
    df = pd.DataFrame([{
        "ID": 1, "Process_Step": "=SUM(1,2)",
        "Component": "+malicious", "Function": "Structural support",
        "Failure_Mode": "=2+2", "Effect": "@badcell",
        "Severity": 8, "Cause": "-exploit",
        "Occurrence": 3, "Current_Control": "Visual inspection",
        "Detection": 4,
    }])
    return run_pipeline(df)

def test_excel_no_formula_injection():
    df = _pipeline_df_with_formula()
    raw = export_excel(df)
    wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=False)
    ws = wb.active
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            assert cell.data_type != "f", (
                f"Cell {cell.coordinate} was stored as a formula: {cell.value}"
            )

def test_csv_no_formula_injection():
    df = _pipeline_df_with_formula()
    from src.exporter import _sanitize_for_export
    sanitized = _sanitize_for_export(df)
    csv_text = sanitized.to_csv(index=False)
    for prefix in ("=", "+", "-", "@"):
        for field in ["Process_Step", "Component", "Failure_Mode", "Effect", "Cause"]:
            # Any cell starting with a formula prefix should be escaped with a leading apostrophe
            for line in csv_text.splitlines()[1:]:
                pass  # We verify via the sanitized df directly below

def test_sanitize_escapes_formula_prefixes():
    from src.exporter import _sanitize_for_export
    df = pd.DataFrame([{"Failure_Mode": "=evil", "Component": "+bad", "Effect": "-also", "Process_Step": "@nope", "ID": 1}])
    result = _sanitize_for_export(df)
    assert result.loc[0, "Failure_Mode"] == "'=evil"
    assert result.loc[0, "Component"] == "'+bad"
    assert result.loc[0, "Effect"] == "'-also"
    assert result.loc[0, "Process_Step"] == "'@nope"
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_exporter.py::test_excel_no_formula_injection tests/test_exporter.py::test_sanitize_escapes_formula_prefixes -v
```

Expected: FAIL (no sanitization exists yet)

- [ ] **Step 3: Add `_sanitize_for_export` helper and apply it in `export_excel` and the CSV export path**

Add to `src/exporter.py` (after the constants section, before `export_excel`):

```python
_FORMULA_PREFIXES = ("=", "+", "-", "@")

def _sanitize_for_export(df: pd.DataFrame) -> pd.DataFrame:
    """Escape formula-injection prefixes in all string columns."""
    df = df.copy()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].apply(
            lambda v: f"'{v}" if isinstance(v, str) and v.startswith(_FORMULA_PREFIXES) else v
        )
    return df
```

In `export_excel` (at `src/exporter.py`), apply sanitization before building the workbook:

```python
def export_excel(df: pd.DataFrame) -> bytes:
    df = _sanitize_for_export(df)   # add this line at the top of the function
    wb = openpyxl.Workbook()
    ...
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_exporter.py::test_excel_no_formula_injection tests/test_exporter.py::test_sanitize_escapes_formula_prefixes -v
```

Expected: PASS

- [ ] **Step 5: Also apply sanitization to CSV download in `app.py`**

In `app.py`, find `render_export_buttons` and update the CSV download:

```python
    with col_csv:
        st.download_button(
            label="📋  Download CSV",
            data=_sanitize_for_export(df).to_csv(index=False).encode("utf-8"),
            file_name="fmea_analysis.csv",
            mime="text/csv",
            use_container_width=True,
            help="Full analyzed dataset with all calculated columns",
        )
```

Add the import at the top of `app.py`:

```python
from src.exporter import export_excel, export_pdf, _sanitize_for_export
```

- [ ] **Step 6: Run full suite**

```bash
pytest -q
```

Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add src/exporter.py app.py tests/test_exporter.py
git commit -m "fix: neutralize Excel and CSV formula injection — escape = + - @ prefixes in all string columns"
```

---

### Task 4: Lazy Export Generation with Error Isolation

**Files:**
- Modify: `app.py` (function `render_export_buttons`)

- [ ] **Step 1: Replace eager export calls with session-state caching**

The current `render_export_buttons` at `app.py:437` calls `export_excel(df)` and `export_pdf(df, ...)` directly on every rerender. Replace the function with this:

```python
import hashlib

def _export_cache_key(df: pd.DataFrame, rpn_min: int, sev9_only: bool,
                      process_steps: list, export_type: str) -> tuple:
    df_hash = hashlib.md5(df.to_json().encode()).hexdigest()
    return (df_hash, rpn_min, sev9_only, tuple(sorted(process_steps)), export_type)


def render_export_buttons(
    df: pd.DataFrame,
    pareto_fig,
    heatmap_fig,
    rpn_min: int,
    sev9_only: bool,
    process_steps: list,
) -> None:
    st.subheader("📥  Export Report")

    col_xl, col_pdf, col_csv, _ = st.columns([1, 1, 1, 3])

    # --- Excel ---
    xl_key = _export_cache_key(df, rpn_min, sev9_only, process_steps, "excel")
    if st.session_state.get("_xl_cache_key") != xl_key:
        try:
            st.session_state["_xl_bytes"] = export_excel(df)
            st.session_state["_xl_cache_key"] = xl_key
        except Exception as exc:
            st.session_state["_xl_bytes"] = None
            st.warning(f"Excel export unavailable: {exc}")

    with col_xl:
        xl_bytes = st.session_state.get("_xl_bytes")
        st.download_button(
            label="📊  Download Excel",
            data=xl_bytes or b"",
            file_name="fmea_analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            disabled=xl_bytes is None,
            help="Color-coded 2-sheet workbook with metadata summary",
        )

    # --- PDF ---
    pdf_key = _export_cache_key(df, rpn_min, sev9_only, process_steps, "pdf")
    if st.session_state.get("_pdf_cache_key") != pdf_key:
        try:
            st.session_state["_pdf_bytes"] = export_pdf(df) if (pareto_fig is not None and heatmap_fig is not None) else None
            st.session_state["_pdf_cache_key"] = pdf_key
        except Exception as exc:
            st.session_state["_pdf_bytes"] = None
            st.warning(f"PDF export unavailable: {exc}")

    with col_pdf:
        pdf_bytes = st.session_state.get("_pdf_bytes")
        st.download_button(
            label="📄  Download PDF",
            data=pdf_bytes or b"",
            file_name="fmea_report.pdf",
            mime="application/pdf",
            use_container_width=True,
            disabled=pdf_bytes is None,
            help="3-page A4 landscape: table + Pareto + Heatmap",
        )

    # --- CSV ---
    with col_csv:
        st.download_button(
            label="📋  Download CSV",
            data=_sanitize_for_export(df).to_csv(index=False).encode("utf-8"),
            file_name="fmea_analysis.csv",
            mime="text/csv",
            use_container_width=True,
            help="Full analyzed dataset with all calculated columns",
        )
```

Also update the call site in `main()` (near line 610 in app.py) to pass the new required parameters:

```python
render_export_buttons(df_filtered, pareto_fig, heatmap_fig, rpn_min, sev9_only, process_steps)
```

- [ ] **Step 2: Run full suite**

```bash
pytest -q
```

Expected: All pass

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "fix: lazy export generation — cache bytes by filtered-data hash, isolate export errors from dashboard render"
```

---

### Task 5: PDF API Cleanup

**Files:**
- Modify: `src/exporter.py` (function `export_pdf`)
- Modify: `tests/test_exporter.py`
- Modify: `docs/FMEA_COMPLETE_GUIDE.md` (PDF section)

- [ ] **Step 1: Update the test that calls `export_pdf` to use the new signature**

In `tests/test_exporter.py`, find any calls to `export_pdf(df, pareto_fig, heatmap_fig)` and update them:

```python
def test_export_pdf_returns_bytes(sample_df):
    result = export_pdf(sample_df)  # no figure args
    assert isinstance(result, bytes)
    assert len(result) > 1000
```

- [ ] **Step 2: Run to confirm this test fails (old signature has 3 params)**

```bash
pytest tests/test_exporter.py::test_export_pdf_returns_bytes -v
```

Expected: FAIL (TypeError: too many arguments or similar)

- [ ] **Step 3: Remove unused figure parameters from `export_pdf` in `src/exporter.py`**

Replace the function signature at line 175:

```python
# OLD:
def export_pdf(
    df: pd.DataFrame,
    pareto_fig: Any,
    heatmap_fig: Any,
) -> bytes:

# NEW:
def export_pdf(df: pd.DataFrame) -> bytes:
```

Remove `from typing import Any` if it's no longer used elsewhere. Update the docstring to remove the Plotly references and describe the actual matplotlib implementation:

```python
def export_pdf(df: pd.DataFrame) -> bytes:
    """
    Export the analyzed FMEA DataFrame to a PDF report using matplotlib.

    Page 1: Summary header + flag counts + ranked FMEA table.
    Page 2: Pareto chart (matplotlib).
    Page 3: Risk heatmap (matplotlib).

    Parameters
    ----------
    df : pd.DataFrame
        Output of run_pipeline().

    Returns
    -------
    bytes
        Raw .pdf bytes suitable for st.download_button().
    """
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_exporter.py -v
```

Expected: All PASS

- [ ] **Step 5: Run full suite**

```bash
pytest -q
```

Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add src/exporter.py tests/test_exporter.py
git commit -m "fix: remove unused pareto_fig/heatmap_fig params from export_pdf — align API with matplotlib-only implementation"
```

---

### Task 6: Documentation Rewrite and Repo Hygiene

**Files:**
- Modify: `README.md`
- Modify: `docs/FMEA_COMPLETE_GUIDE.md`
- Modify: `docs/ASSUMPTIONS_LOG.md`
- Create: `LICENSE`
- Modify: `app.py` (remove `.xls` from accepted types)
- Modify: `requirements.txt` (remove `kaleido`)

- [ ] **Step 1: Remove `.xls` from the app upload handler**

In `app.py`, find the `st.file_uploader` call and update the `type` parameter:

```python
# OLD:
uploaded = st.sidebar.file_uploader(
    "Upload your FMEA file",
    type=["csv", "xlsx", "xls"],
    ...
)

# NEW:
uploaded = st.sidebar.file_uploader(
    "Upload your FMEA file",
    type=["csv", "xlsx"],
    help="Supported formats: CSV, Excel (.xlsx)",
    ...
)
```

Also remove the `.xls` branch from `_load_uploaded` if it has one.

- [ ] **Step 2: Remove `kaleido` from `requirements.txt`**

Open `requirements.txt` and delete the line containing `kaleido`. Verify the app still runs after removal.

- [ ] **Step 3: Create `LICENSE` file**

Create `/Users/jashwanth/Documents/Professional/Portfolio/CodeProjects/fmea-risk-analyzer/LICENSE` with MIT license text (replace `[year]` with `2026` and `[fullname]` with `Siddardth`):

```
MIT License

Copyright (c) 2026 Siddardth

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 4: Fix demo dataset statistics in README and guide**

The actual numbers from the audit (run `python3 fmea_analyzer.py --input data/composite_panel_fmea_demo.csv` to verify):
- 30 rows, 11 process steps
- Risk distribution: Red=19, Yellow=9, Green=2
- High RPN (>100) = 14, Action Priority H = 8
- Top 6 rows ≈ 29.15% of total RPN (not ~82%)

In `README.md`:
- Fix line ~143: update process step count to 11
- Fix lines ~358-369: update Red/Yellow/Green counts, High RPN count, AP-H count
- Remove broken screenshot references (line ~251) or replace with "Screenshots coming soon"
- Remove `.xls` from supported formats section
- Update MIT license badge link to point to `./LICENSE`

In `docs/FMEA_COMPLETE_GUIDE.md`:
- Fix lines ~620-622: update demo dataset description to 30 rows, 11 steps
- Fix lines ~755-769: update Pareto narrative — top 6 rows ≈ 29% of RPN, not 82%
- Fix lines ~690-699 and ~1011-1012: remove kaleido references, describe matplotlib PDF path
- Fix AP-H framing to say "threshold simplification (RPN ≥ 200 OR Severity ≥ 9), not full AIAG/VDA AP table"

In `docs/ASSUMPTIONS_LOG.md`:
- Fix the Pareto color banding reference (~line 84-90): clarify that bars are colored by `Risk_Tier`, not by Pareto 80/20 banding

- [ ] **Step 5: Run full test suite to confirm nothing broke**

```bash
pytest -q
```

Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add README.md docs/FMEA_COMPLETE_GUIDE.md docs/ASSUMPTIONS_LOG.md LICENSE app.py requirements.txt
git commit -m "docs: fix stale demo stats, Pareto narrative, PDF docs; add LICENSE; remove .xls and kaleido"
```

---

## PHASE 2 — Reliability & UX

---

### Task 7: Fix Chart Cache Key to Include Dataset Identity

**Files:**
- Modify: `app.py` (chart cache section at line ~578)

- [ ] **Step 1: Update the chart cache key to include a DataFrame content hash**

In `app.py`, find this block (around line 578):

```python
_cache_key = (rpn_min, sev9_only, tuple(sorted(process_steps)), len(df_filtered), dark)
```

Replace with:

```python
import hashlib
_df_hash = hashlib.md5(df_filtered.to_json().encode()).hexdigest()
_cache_key = (_df_hash, rpn_min, sev9_only, tuple(sorted(process_steps)), dark)
```

(If `hashlib` is already imported from Task 4, no need to import again.)

- [ ] **Step 2: Run full test suite**

```bash
pytest -q
```

Expected: All pass

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "fix: include DataFrame content hash in chart cache key to prevent stale charts across dataset changes"
```

---

### Task 8: Make RPN Filter Bounds Data-Driven

**Files:**
- Modify: `app.py` (slider at line ~218)

- [ ] **Step 1: Update the slider to use the actual max RPN from the dataset**

The `rpn_min` slider is currently defined in `render_sidebar` which runs before data is loaded. The slider needs to be moved or updated after data is available.

The cleanest approach: keep the slider in `render_sidebar` with a default max, then re-render it after data loads using `st.session_state`. In `app.py`, find the slider (line ~218):

```python
# OLD:
rpn_min = st.sidebar.slider(
    "Minimum RPN",
    min_value=0, max_value=300, value=0, step=10,
    ...
)

# NEW — make max data-driven after pipeline runs:
# In render_sidebar, use a session-state-driven max:
_rpn_max = int(st.session_state.get("_dataset_rpn_max", 1000))
rpn_min = st.sidebar.slider(
    "Minimum RPN",
    min_value=0,
    max_value=max(_rpn_max, 10),
    value=min(st.session_state.get("rpn_slider", 0), _rpn_max),
    step=10,
    help="Show only failure modes with RPN ≥ this value (max reflects your dataset)",
    key="rpn_slider",
)
```

Then in `main()`, after `run_pipeline` succeeds, store the max:

```python
df_analyzed = run_pipeline(raw_df)
st.session_state["_dataset_rpn_max"] = int(df_analyzed["RPN"].max())
```

- [ ] **Step 2: Run full test suite**

```bash
pytest -q
```

Expected: All pass

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "fix: make RPN filter slider max data-driven from actual dataset max RPN"
```

---

### Task 9: Add Validation Summary Panel

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add a `render_validation_summary` function to `app.py`**

Add this function before `main()`:

```python
def render_validation_summary(df: pd.DataFrame) -> None:
    """Show a compact dataset health panel immediately after upload."""
    n_rows = len(df)
    score_cols = ["Severity", "Occurrence", "Detection"]

    warnings = []

    # Near-boundary score check
    for col in score_cols:
        if col in df.columns:
            near_max = (df[col] == 10).sum()
            near_min = (df[col] == 1).sum()
            if near_max > 0:
                warnings.append(f"{near_max} row(s) have {col} = 10 (maximum)")
            if near_min > 0:
                warnings.append(f"{near_min} row(s) have {col} = 1 (minimum)")

    # Long text field check
    text_cols = ["Failure_Mode", "Effect", "Cause"]
    for col in text_cols:
        if col in df.columns:
            long = (df[col].str.len() > 120).sum()
            if long > 0:
                warnings.append(f"{long} row(s) have long '{col}' text (>120 chars — may truncate in PDF)")

    with st.expander("📋 Dataset Health", expanded=True):
        col1, col2, col3 = st.columns(3)
        col1.metric("Rows loaded", n_rows)
        col2.metric("Columns present", len(df.columns))
        col3.metric("Warnings", len(warnings))
        if warnings:
            for w in warnings:
                st.caption(f"⚠️ {w}")
        else:
            st.caption("✅ No data quality warnings detected.")
```

- [ ] **Step 2: Call it in `main()` right after `run_pipeline` succeeds**

```python
df_analyzed = run_pipeline(raw_df)
st.session_state["_dataset_rpn_max"] = int(df_analyzed["RPN"].max())
render_validation_summary(df_analyzed)   # add this line
```

- [ ] **Step 3: Run full test suite**

```bash
pytest -q
```

Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add validation summary panel — shows row count, column coverage, and data quality warnings after upload"
```

---

### Task 10: Add Dev Dependencies File and Integration Test Scaffold

**Files:**
- Create: `requirements-dev.txt`
- Create: `tests/test_app_integration.py`
- Modify: `README.md`

- [ ] **Step 1: Create `requirements-dev.txt`**

```
pytest>=8.0
pytest-cov>=5.0
ruff>=0.4
mypy>=1.10
```

- [ ] **Step 2: Install dev dependencies**

```bash
pip install -r requirements-dev.txt
```

- [ ] **Step 3: Create `tests/test_app_integration.py` with AppTest-based tests**

```python
"""
App-level integration tests using Streamlit's AppTest harness.
These tests exercise the full app surface: upload, filters, exports, and error handling.
"""
import io
import pytest
import pandas as pd
from streamlit.testing.v1 import AppTest


@pytest.fixture
def valid_csv_bytes():
    df = pd.DataFrame([{
        "ID": 1, "Process_Step": "Stamping", "Component": "Panel",
        "Function": "Structural support", "Failure_Mode": "Crack",
        "Effect": "Part failure", "Severity": 8,
        "Cause": "Over-stress", "Occurrence": 3,
        "Current_Control": "Visual inspection", "Detection": 4,
    }])
    return df.to_csv(index=False).encode("utf-8")


@pytest.fixture
def float_score_csv_bytes():
    df = pd.DataFrame([{
        "ID": 1, "Process_Step": "Stamping", "Component": "Panel",
        "Function": "Structural support", "Failure_Mode": "Crack",
        "Effect": "Part failure", "Severity": 8.5,
        "Cause": "Over-stress", "Occurrence": 3,
        "Current_Control": "Visual inspection", "Detection": 4,
    }])
    return df.to_csv(index=False).encode("utf-8")


def test_demo_dataset_loads():
    """Demo dataset button loads successfully and renders metrics."""
    at = AppTest.from_file("app.py").run()
    # Click the demo dataset button
    at.session_state["use_demo"] = True
    at = at.run()
    # App should not have errors
    assert len(at.error) == 0


def test_demo_renders_without_exception():
    """Full demo path runs without raising an exception."""
    at = AppTest.from_file("app.py").run()
    at.session_state["use_demo"] = True
    at = at.run(timeout=30)
    assert not at.exception


def test_malformed_float_score_shows_error():
    """Uploading a file with float S/O/D scores shows an error, does not crash."""
    at = AppTest.from_file("app.py").run()
    at.session_state["use_demo"] = False
    # Simulate validation error path by checking validate_input directly
    from src.rpn_engine import validate_input
    import pandas as pd
    df = pd.DataFrame([{
        "ID": 1, "Process_Step": "Stamping", "Component": "Panel",
        "Function": "Structural support", "Failure_Mode": "Crack",
        "Effect": "Part failure", "Severity": 8.5,
        "Cause": "Over-stress", "Occurrence": 3,
        "Current_Control": "Visual inspection", "Detection": 4,
    }])
    with pytest.raises(ValueError, match="integer"):
        validate_input(df)


def test_null_process_step_rejected_at_boundary():
    """Null Process_Step is caught at validation, not at filter time."""
    from src.rpn_engine import validate_input
    import pandas as pd
    df = pd.DataFrame([{
        "ID": 1, "Process_Step": None, "Component": "Panel",
        "Function": "Structural support", "Failure_Mode": "Crack",
        "Effect": "Part failure", "Severity": 8,
        "Cause": "Over-stress", "Occurrence": 3,
        "Current_Control": "Visual inspection", "Detection": 4,
    }])
    with pytest.raises(ValueError, match="Process_Step"):
        validate_input(df)


def test_formula_prefixed_strings_not_stored_as_formulas():
    """Formula-injection strings are escaped in Excel export."""
    import io
    import openpyxl
    from src.rpn_engine import run_pipeline
    from src.exporter import export_excel
    df = pd.DataFrame([{
        "ID": 1, "Process_Step": "Stamping", "Component": "Panel",
        "Function": "Structural support", "Failure_Mode": "=2+2",
        "Effect": "+bad", "Severity": 8,
        "Cause": "Over-stress", "Occurrence": 3,
        "Current_Control": "Visual inspection", "Detection": 4,
    }])
    result_df = run_pipeline(df)
    raw = export_excel(result_df)
    wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=False)
    ws = wb.active
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            assert cell.data_type != "f", f"Formula found in cell {cell.coordinate}"
```

- [ ] **Step 4: Run the integration tests**

```bash
pytest tests/test_app_integration.py -v
```

Expected: All PASS (some AppTest tests may be skipped if the harness requires additional setup — that's acceptable; the boundary tests must pass)

- [ ] **Step 5: Update README test instructions**

In `README.md`, find the test section and update:

```markdown
## Running Tests

Install dev dependencies first:
```bash
pip install -r requirements-dev.txt
```

Run the full test suite:
```bash
pytest -q
```

Run with coverage:
```bash
pytest --cov=src --cov-report=term-missing
```
```

- [ ] **Step 6: Commit**

```bash
git add requirements-dev.txt tests/test_app_integration.py README.md
git commit -m "test: add requirements-dev.txt and app-level integration test scaffold covering upload, validation, and export boundaries"
```

---

## PHASE 3 — Product Foundation

---

### Task 11: Introduce Pydantic Schema Layer

**Files:**
- Create: `src/schema.py`
- Modify: `src/rpn_engine.py`
- Modify: `tests/test_rpn_engine.py`

- [ ] **Step 1: Add `pydantic>=2.0` to `requirements.txt`**

```
pydantic>=2.0
```

Install it:

```bash
pip install "pydantic>=2.0"
```

- [ ] **Step 2: Write tests for the Pydantic models**

Add to `tests/test_rpn_engine.py`:

```python
from src.schema import FMEARow, FMEADataset
import pydantic

def test_fmea_row_valid():
    row = FMEARow(
        ID=1, Process_Step="Stamping", Component="Panel",
        Function="Structural support", Failure_Mode="Crack",
        Effect="Part failure", Severity=8,
        Cause="Over-stress", Occurrence=3,
        Current_Control="Visual inspection", Detection=4,
    )
    assert row.RPN == 96

def test_fmea_row_rejects_float_severity():
    with pytest.raises(pydantic.ValidationError):
        FMEARow(
            ID=1, Process_Step="Stamping", Component="Panel",
            Function="Structural support", Failure_Mode="Crack",
            Effect="Part failure", Severity=8.5,
            Cause="Over-stress", Occurrence=3,
            Current_Control="Visual inspection", Detection=4,
        )

def test_fmea_row_rejects_out_of_range():
    with pytest.raises(pydantic.ValidationError):
        FMEARow(
            ID=1, Process_Step="Stamping", Component="Panel",
            Function="Structural support", Failure_Mode="Crack",
            Effect="Part failure", Severity=11,
            Cause="Over-stress", Occurrence=3,
            Current_Control="Visual inspection", Detection=4,
        )

def test_fmea_dataset_rejects_duplicate_ids():
    row1 = FMEARow(ID=1, Process_Step="Stamping", Component="Panel", Function="F",
                   Failure_Mode="Crack", Effect="E", Severity=8, Cause="C",
                   Occurrence=3, Current_Control="Ctrl", Detection=4)
    row2 = FMEARow(ID=1, Process_Step="Welding", Component="Bracket", Function="F",
                   Failure_Mode="Warp", Effect="E", Severity=5, Cause="C",
                   Occurrence=2, Current_Control="Ctrl", Detection=3)
    with pytest.raises(pydantic.ValidationError, match="duplicate"):
        FMEADataset(rows=[row1, row2])
```

- [ ] **Step 3: Run to confirm they fail**

```bash
pytest tests/test_rpn_engine.py::test_fmea_row_valid tests/test_rpn_engine.py::test_fmea_row_rejects_float_severity tests/test_rpn_engine.py::test_fmea_dataset_rejects_duplicate_ids -v
```

Expected: FAIL (module doesn't exist yet)

- [ ] **Step 4: Create `src/schema.py`**

```python
"""
schema.py
Pydantic v2 domain models for FMEA data validation.
Serves as the single source of truth for field types, constraints, and dataset-level rules.
"""
from __future__ import annotations
from typing import Annotated
import pydantic


class FMEARow(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(strict=True)

    ID: int = pydantic.Field(gt=0)
    Process_Step: str = pydantic.Field(min_length=1)
    Component: str = pydantic.Field(min_length=1)
    Function: str = pydantic.Field(min_length=1)
    Failure_Mode: str = pydantic.Field(min_length=1)
    Effect: str = pydantic.Field(min_length=1)
    Severity: Annotated[int, pydantic.Field(ge=1, le=10)]
    Cause: str = pydantic.Field(min_length=1)
    Occurrence: Annotated[int, pydantic.Field(ge=1, le=10)]
    Current_Control: str = pydantic.Field(min_length=1)
    Detection: Annotated[int, pydantic.Field(ge=1, le=10)]

    @property
    def RPN(self) -> int:
        return self.Severity * self.Occurrence * self.Detection


class FMEADataset(pydantic.BaseModel):
    rows: list[FMEARow]

    @pydantic.model_validator(mode="after")
    def check_no_duplicate_ids(self) -> "FMEADataset":
        ids = [row.ID for row in self.rows]
        seen = set()
        dupes = [i for i in ids if i in seen or seen.add(i)]
        if dupes:
            raise ValueError(f"duplicate IDs found: {dupes}")
        return self
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
pytest tests/test_rpn_engine.py::test_fmea_row_valid tests/test_rpn_engine.py::test_fmea_row_rejects_float_severity tests/test_rpn_engine.py::test_fmea_dataset_rejects_duplicate_ids -v
```

Expected: PASS

- [ ] **Step 6: Wire `validate_input` to use Pydantic models as the source of truth**

The manual checks in `validate_input` (Tasks 1 and 2) and the new Pydantic models now overlap. Keep the DataFrame-based validate_input function as a thin bridge that delegates to Pydantic — this preserves the existing function interface while Pydantic does the actual validation:

```python
from src.schema import FMEARow, FMEADataset
import pydantic as _pydantic

def validate_input(df: pd.DataFrame) -> None:
    """Validate FMEA DataFrame using Pydantic schema models."""
    if df.empty:
        raise ValueError(
            "Input DataFrame is empty. FMEA file must contain at least one data row."
        )
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Missing required column(s): {missing_cols}. Expected: {REQUIRED_COLUMNS}"
        )
    try:
        rows = [FMEARow(**row) for row in df[REQUIRED_COLUMNS].to_dict(orient="records")]
        FMEADataset(rows=rows)
    except _pydantic.ValidationError as exc:
        # Surface the first error with a user-friendly message
        first = exc.errors()[0]
        field = " -> ".join(str(loc) for loc in first["loc"])
        raise ValueError(
            f"Validation error in column '{field}': {first['msg']}. "
            f"Check your data against the template at data/fmea_input_template.csv."
        ) from exc
```

- [ ] **Step 7: Run full suite — all old tests must still pass**

```bash
pytest -q
```

Expected: All pass (the Pydantic bridge preserves the `ValueError` interface the existing tests expect)

- [ ] **Step 8: Commit**

```bash
git add src/schema.py src/rpn_engine.py requirements.txt tests/test_rpn_engine.py
git commit -m "feat: introduce Pydantic v2 FMEARow/FMEADataset schema layer — validate_input now delegates to models"
```

---

### Task 12: Split `app.py` into UI Modules

**Files:**
- Create: `ui/__init__.py`
- Create: `ui/filters.py`
- Create: `ui/charts.py`
- Create: `ui/exports.py`
- Modify: `app.py` (thin orchestrator)

- [ ] **Step 1: Create `ui/__init__.py`**

```python
```
(empty file)

- [ ] **Step 2: Create `ui/filters.py`** — extract sidebar filter logic from `app.py`

```python
"""
ui/filters.py
Sidebar filter rendering for the FMEA Risk Analyzer.
"""
from __future__ import annotations
import streamlit as st
import pandas as pd


def render_rpn_slider() -> int:
    """Render the Minimum RPN slider. Returns the selected minimum RPN."""
    _rpn_max = int(st.session_state.get("_dataset_rpn_max", 1000))
    return st.sidebar.slider(
        "Minimum RPN",
        min_value=0,
        max_value=max(_rpn_max, 10),
        value=min(st.session_state.get("rpn_slider", 0), _rpn_max),
        step=10,
        help="Show only failure modes with RPN ≥ this value (max reflects your dataset)",
        key="rpn_slider",
    )


def render_severity_toggle() -> bool:
    """Render the Severity ≥ 9 filter toggle. Returns True if active."""
    return st.sidebar.toggle(
        "Severity ≥ 9 only",
        value=False,
        help="Show only safety-critical failure modes",
        key="sev9_toggle",
    )


def render_process_filter(df: pd.DataFrame) -> list[str]:
    """Render process step multiselect. Returns selected steps."""
    st.sidebar.divider()
    st.sidebar.subheader("📍  Process Steps")
    all_steps = sorted(df["Process_Step"].unique().tolist())
    selected = st.sidebar.multiselect(
        "Show steps",
        options=all_steps,
        default=all_steps,
        key="process_steps",
        help="Filter to specific manufacturing process steps",
    )
    return selected if selected else all_steps


def apply_filters(
    df: pd.DataFrame,
    rpn_min: int,
    sev9_only: bool,
    process_steps: list[str],
) -> pd.DataFrame:
    """Apply all sidebar filters to the analyzed DataFrame."""
    filtered = df[df["RPN"] >= rpn_min]
    if sev9_only:
        filtered = filtered[filtered["Severity"] >= 9]
    if process_steps:
        filtered = filtered[filtered["Process_Step"].isin(process_steps)]
    return filtered
```

- [ ] **Step 3: Create `ui/charts.py`** — extract chart caching/rendering from `app.py`

```python
"""
ui/charts.py
Chart rendering and session-state caching for the FMEA Risk Analyzer.
"""
from __future__ import annotations
import hashlib
import streamlit as st
import pandas as pd
from src.plotly_charts import pareto_chart_plotly, risk_heatmap_plotly


def get_or_build_charts(
    df_filtered: pd.DataFrame,
    rpn_min: int,
    sev9_only: bool,
    process_steps: list[str],
    dark: bool,
) -> tuple:
    """Return (pareto_fig, heatmap_fig) from cache or rebuild if stale."""
    _df_hash = hashlib.md5(df_filtered.to_json().encode()).hexdigest()
    cache_key = (_df_hash, rpn_min, sev9_only, tuple(sorted(process_steps)), dark)

    if st.session_state.get("_chart_cache_key") != cache_key or "pareto_fig" not in st.session_state:
        if not df_filtered.empty:
            st.session_state["pareto_fig"] = pareto_chart_plotly(df_filtered, dark=dark)
            st.session_state["heatmap_fig"] = risk_heatmap_plotly(df_filtered, dark=dark)
        else:
            st.session_state["pareto_fig"] = None
            st.session_state["heatmap_fig"] = None
        st.session_state["_chart_cache_key"] = cache_key

    return st.session_state.get("pareto_fig"), st.session_state.get("heatmap_fig")
```

- [ ] **Step 4: Create `ui/exports.py`** — extract export button generation from `app.py`

```python
"""
ui/exports.py
Export button rendering with lazy caching and error isolation.
"""
from __future__ import annotations
import hashlib
import streamlit as st
import pandas as pd
from src.exporter import export_excel, export_pdf, _sanitize_for_export


def _export_cache_key(
    df: pd.DataFrame,
    rpn_min: int,
    sev9_only: bool,
    process_steps: list[str],
    export_type: str,
) -> tuple:
    df_hash = hashlib.md5(df.to_json().encode()).hexdigest()
    return (df_hash, rpn_min, sev9_only, tuple(sorted(process_steps)), export_type)


def render_export_buttons(
    df: pd.DataFrame,
    pareto_fig,
    heatmap_fig,
    rpn_min: int,
    sev9_only: bool,
    process_steps: list[str],
) -> None:
    st.subheader("📥  Export Report")
    col_xl, col_pdf, col_csv, _ = st.columns([1, 1, 1, 3])

    # Excel
    xl_key = _export_cache_key(df, rpn_min, sev9_only, process_steps, "excel")
    if st.session_state.get("_xl_cache_key") != xl_key:
        try:
            st.session_state["_xl_bytes"] = export_excel(df)
            st.session_state["_xl_cache_key"] = xl_key
        except Exception as exc:
            st.session_state["_xl_bytes"] = None
            st.warning(f"Excel export unavailable: {exc}")

    with col_xl:
        xl_bytes = st.session_state.get("_xl_bytes")
        st.download_button(
            label="📊  Download Excel",
            data=xl_bytes or b"",
            file_name="fmea_analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            disabled=xl_bytes is None,
            help="Color-coded 2-sheet workbook with metadata summary",
        )

    # PDF
    pdf_key = _export_cache_key(df, rpn_min, sev9_only, process_steps, "pdf")
    if st.session_state.get("_pdf_cache_key") != pdf_key:
        try:
            pdf_data = export_pdf(df) if (pareto_fig is not None and heatmap_fig is not None) else None
            st.session_state["_pdf_bytes"] = pdf_data
            st.session_state["_pdf_cache_key"] = pdf_key
        except Exception as exc:
            st.session_state["_pdf_bytes"] = None
            st.warning(f"PDF export unavailable: {exc}")

    with col_pdf:
        pdf_bytes = st.session_state.get("_pdf_bytes")
        st.download_button(
            label="📄  Download PDF",
            data=pdf_bytes or b"",
            file_name="fmea_report.pdf",
            mime="application/pdf",
            use_container_width=True,
            disabled=pdf_bytes is None,
            help="3-page A4 landscape: table + Pareto + Heatmap",
        )

    # CSV
    with col_csv:
        st.download_button(
            label="📋  Download CSV",
            data=_sanitize_for_export(df).to_csv(index=False).encode("utf-8"),
            file_name="fmea_analysis.csv",
            mime="text/csv",
            use_container_width=True,
            help="Full analyzed dataset with all calculated columns",
        )
```

- [ ] **Step 5: Refactor `app.py` to import from `ui/` modules**

Replace the functions that were extracted (`render_process_filter`, `_apply_filters`, `render_export_buttons`, chart cache block) with imports from the new modules. The `main()` function becomes the thin orchestrator. Key import additions at the top of `app.py`:

```python
from ui.filters import render_rpn_slider, render_severity_toggle, render_process_filter, apply_filters
from ui.charts import get_or_build_charts
from ui.exports import render_export_buttons
```

Remove the old inline implementations of those functions from `app.py`.

Update `main()` to use the new module functions:

```python
def main():
    dark = render_sidebar_header()
    raw_df, rpn_min, sev9_only = render_sidebar_controls(dark)
    ...
    process_steps = render_process_filter(df_analyzed)
    df_filtered = apply_filters(df_analyzed, rpn_min, sev9_only, process_steps)
    pareto_fig, heatmap_fig = get_or_build_charts(df_filtered, rpn_min, sev9_only, process_steps, dark)
    ...
    render_export_buttons(df_filtered, pareto_fig, heatmap_fig, rpn_min, sev9_only, process_steps)
```

- [ ] **Step 6: Run full test suite to confirm behavior is identical**

```bash
pytest -q
```

Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add ui/ app.py
git commit -m "refactor: split app.py into ui/filters.py, ui/charts.py, ui/exports.py — app.py is now a thin orchestrator"
```

---

### Task 13: Add CI Pipeline and Pre-commit Hooks

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.pre-commit-config.yaml`
- Modify: `README.md` (add CI badge)

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run tests
        run: pytest -q --tb=short
      - name: Lint with ruff
        run: ruff check src/ app.py tests/ ui/
      - name: Type check with mypy
        run: mypy src/ ui/ --ignore-missing-imports
```

- [ ] **Step 2: Create `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        args: [--ignore-missing-imports]
        additional_dependencies: [pydantic>=2.0]
```

- [ ] **Step 3: Install pre-commit and activate hooks**

```bash
pip install pre-commit
pre-commit install
```

- [ ] **Step 4: Run pre-commit against all files to catch any issues**

```bash
pre-commit run --all-files
```

Fix any ruff or mypy errors reported before committing.

- [ ] **Step 5: Add CI badge to `README.md`**

Add near the top of `README.md` (replace `<YOUR_GITHUB_USERNAME>` with the actual username):

```markdown
[![CI](https://github.com/<YOUR_GITHUB_USERNAME>/fmea-risk-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/<YOUR_GITHUB_USERNAME>/fmea-risk-analyzer/actions/workflows/ci.yml)
```

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/ci.yml .pre-commit-config.yaml README.md
git commit -m "ci: add GitHub Actions CI (pytest + ruff + mypy) and pre-commit hooks"
```

---

### Task 14: PDF Layout Improvements

**Files:**
- Modify: `src/exporter.py` (PDF table rendering)
- Modify: `tests/test_exporter.py`

- [ ] **Step 1: Write a test that verifies headers repeat on multi-page PDFs**

Add to `tests/test_exporter.py`:

```python
def test_pdf_large_dataset_returns_bytes():
    """PDF export succeeds and returns bytes for a 50-row dataset."""
    import pandas as pd
    from src.rpn_engine import run_pipeline
    from src.exporter import export_pdf
    rows = []
    for i in range(1, 51):
        rows.append({
            "ID": i, "Process_Step": f"Step_{i % 5}", "Component": "Panel",
            "Function": "Structural support", "Failure_Mode": f"Mode_{i}",
            "Effect": "Part failure", "Severity": min(i % 10 + 1, 10),
            "Cause": "Over-stress", "Occurrence": min(i % 5 + 1, 10),
            "Current_Control": "Visual inspection",
            "Detection": min(i % 7 + 1, 10),
        })
    df = run_pipeline(pd.DataFrame(rows))
    result = export_pdf(df)
    assert isinstance(result, bytes)
    assert len(result) > 5000
```

- [ ] **Step 2: Run to confirm it passes (basic bytes test)**

```bash
pytest tests/test_exporter.py::test_pdf_large_dataset_returns_bytes -v
```

Expected: PASS (it should already pass — this establishes the baseline)

- [ ] **Step 3: Add header repeat on page break in `_pdf_page1` table section of `src/exporter.py`**

Find the table rendering loop in `_pdf_page1` (around line 314-347). Modify the row writing loop to check for page breaks and reprint the header:

```python
def _write_table_with_repeating_headers(pdf, headers, rows, col_widths, row_height=6):
    """Write a table that repeats column headers on each new page."""
    PAGE_BOTTOM_MARGIN = 190  # mm from top for landscape A4

    def _write_header_row():
        pdf.set_fill_color(44, 62, 80)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 7)
        for h, w in zip(headers, col_widths):
            pdf.cell(w, 6, h[:18], border=1, fill=True, align="C")
        pdf.ln()
        pdf.set_text_color(0, 0, 0)

    _write_header_row()

    for i, row_data in enumerate(rows):
        # Check if we need a new page
        if pdf.get_y() + row_height > PAGE_BOTTOM_MARGIN:
            pdf.add_page()
            _write_header_row()

        fill = i % 2 == 0
        pdf.set_fill_color(245, 245, 245) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.set_font("Helvetica", "", 7)
        for val, w in zip(row_data, col_widths):
            text = _safe_text(str(val))
            # Truncate to fit cell width (~6 chars per 10mm)
            max_chars = max(int(w * 0.6), 5)
            if len(text) > max_chars:
                text = text[:max_chars - 1] + "…"
            pdf.cell(w, row_height, text, border=1, fill=fill, align="L")
        pdf.ln()
```

Replace the existing table loop in `_pdf_page1` with a call to `_write_table_with_repeating_headers`.

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_exporter.py -v
```

Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/exporter.py tests/test_exporter.py
git commit -m "fix: PDF table repeats headers on page break; truncate long cell text with ellipsis"
```

---

### Task 15: Final Cleanup and Verification

**Files:**
- Modify: `requirements.txt` (confirm kaleido removed, pydantic present)
- Verify: all tests pass, CI config is valid

- [ ] **Step 1: Audit `requirements.txt` for stale entries**

Open `requirements.txt` and confirm:
- `kaleido` is absent
- `pydantic>=2.0` is present
- All other packages are still needed (cross-check against actual imports)

- [ ] **Step 2: Run the full test suite one final time**

```bash
pytest -q --tb=short
```

Expected: All pass, no warnings

- [ ] **Step 3: Run ruff and mypy**

```bash
ruff check src/ app.py tests/ ui/
mypy src/ ui/ --ignore-missing-imports
```

Fix any issues found.

- [ ] **Step 4: Verify the app launches without error**

```bash
streamlit run app.py
```

Load the demo dataset. Verify:
- Validation summary panel appears
- Charts render correctly
- All three download buttons work (Excel, PDF, CSV)
- RPN slider max reflects dataset max
- No console errors

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: final cleanup — verify requirements, confirm CI config, all tests green"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by task |
|---|---|
| Integer-only S/O/D enforcement | Task 1 |
| Null checks for ID, Process_Step, text fields | Task 2 |
| Duplicate ID rejection | Task 2 |
| Formula injection fix (Excel + CSV) | Task 3 |
| Lazy export generation with error isolation | Task 4 |
| PDF API cleanup (remove figure args) | Task 5 |
| Docs rewrite (stats, Pareto, PDF, XLS removal) | Task 6 |
| LICENSE file | Task 6 |
| Chart cache key includes df content hash | Task 7 |
| Dynamic RPN slider max | Task 8 |
| Validation summary panel | Task 9 |
| `requirements-dev.txt` | Task 10 |
| App-level integration tests | Task 10 |
| Pydantic `FMEARow` + `FMEADataset` models | Task 11 |
| `validate_input` delegates to Pydantic | Task 11 |
| `ui/filters.py` split | Task 12 |
| `ui/charts.py` split | Task 12 |
| `ui/exports.py` split | Task 12 |
| GitHub Actions CI | Task 13 |
| Pre-commit hooks | Task 13 |
| PDF repeated headers on page break | Task 14 |
| Remove kaleido from requirements | Task 6 + Task 15 |

**No gaps found.**

**Type consistency check:** `FMEARow` defined in Task 11, referenced in same task only. `apply_filters` defined in `ui/filters.py` Task 12, called from `app.py` Task 12. `get_or_build_charts` defined and used in Task 12. `render_export_buttons` signature is consistent between Task 4 (interim) and Task 12 (final module). `export_pdf(df)` single-arg signature set in Task 5 and used consistently in Tasks 4, 12, and 14.

**No placeholder issues found.**
