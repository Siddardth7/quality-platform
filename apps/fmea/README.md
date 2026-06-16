# FMEA Risk Prioritization Tool

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.56-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Plotly](https://img.shields.io/badge/Plotly-6.6-3F4F75?logo=plotly&logoColor=white)](https://plotly.com)
[![Tests](https://img.shields.io/badge/Tests-105%20passing-brightgreen?logo=pytest)](https://github.com/Siddardth7/fmea-risk-analyzer)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/Siddardth7/fmea-risk-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/Siddardth7/fmea-risk-analyzer/actions/workflows/ci.yml)

**A portfolio-grade Python tool that automates Process FMEA risk analysis** — calculates RPN scores, applies AIAG FMEA-4 criticality flags, generates interactive Pareto and heatmap visualizations, and exports publication-ready PDF and Excel reports. Deployed as a live Streamlit web application.

> **Live Demo →** [fmea-risk-analyzer-mhwzcki9sdzfz5d8rbzsdn.streamlit.app](https://fmea-risk-analyzer-mhwzcki9sdzfz5d8rbzsdn.streamlit.app/)

**Engineering Reference:** AIAG FMEA-4 (4th Edition, 2008) + AIAG/VDA FMEA Handbook (5th Edition, 2019)  
**Author:** Siddardth | M.S. Aerospace Engineering, University of Illinois Urbana-Champaign

---

## Table of Contents

1. [What is FMEA? — The Engineering Problem](#1-what-is-fmea--the-engineering-problem)
2. [How RPN Works — The Math Behind Risk](#2-how-rpn-works--the-math-behind-risk)
3. [AIAG FMEA-4 Flagging Rules](#3-aiag-fmea-4-flagging-rules)
4. [Pareto 80/20 Applied to Risk](#4-pareto-8020-applied-to-risk)
5. [How This Application Works](#5-how-this-application-works)
6. [Features](#6-features)
7. [Screenshots](#7-screenshots)
8. [Quick Start](#8-quick-start)
9. [Project Structure](#9-project-structure)
10. [Input File Schema](#10-input-file-schema)
11. [Demo Dataset](#11-demo-dataset)
12. [Tech Stack](#12-tech-stack)
13. [Running Tests](#13-running-tests)
14. [Engineering References](#14-engineering-references)

---

## 1. What is FMEA? — The Engineering Problem

**Failure Mode and Effects Analysis (FMEA)** is a structured, bottom-up risk assessment methodology mandated across aerospace (AS9100), automotive (IATF 16949), and medical device (ISO 13485) manufacturing. It asks a deceptively simple question for every component or process step:

> *"How can this fail, what happens when it does, and how likely are we to catch it before the customer does?"*

In practice, an FMEA for a complex manufacturing process — composites layup, autoclave cure, precision machining — can easily contain 30–100+ failure modes across dozens of process steps. Engineering teams traditionally manage this in Excel spreadsheets, manually calculating risk scores and sorting rows. This is slow, error-prone, and produces no visualization.

**This tool automates the entire workflow:**

```
FMEA Spreadsheet (CSV/Excel)
        │
        ▼
   Validate Schema
        │
        ▼
  Calculate RPN Scores          ← Severity × Occurrence × Detection
        │
        ▼
  Apply AIAG Criticality Flags  ← High RPN, Severity ≥ 9, Action Priority H
        │
        ▼
  Rank & Tier Failure Modes     ← Red / Yellow / Green
        │
        ├──► Interactive Web Dashboard  (Streamlit)
        ├──► Pareto Chart               (which 20% of modes drive 80% of risk?)
        ├──► Severity × Occurrence Heatmap
        └──► PDF + Excel Export
```

---

## 2. How RPN Works — The Math Behind Risk

The **Risk Priority Number (RPN)** is the core metric of Process FMEA. It is calculated as:

```
RPN = Severity (S) × Occurrence (O) × Detection (D)
```

Each factor is scored on a **1–10 integer scale** per AIAG FMEA-4:

| Score | Severity (S) — Impact of the failure effect | Occurrence (O) — Likelihood of the cause | Detection (D) — Ability to catch before customer |
|:---:|---|---|---|
| **1** | No discernible effect on product or process | Failure is extremely unlikely (<1 in 1,500,000) | Current controls will almost certainly detect |
| **3** | Minor effect — slight customer annoyance | Relatively few failures (1 in 150,000) | High chance of detection |
| **5** | Moderate effect — customer dissatisfied, rework required | Occasional failures (1 in 400) | Controls may or may not detect |
| **7** | High effect — product inoperable, customer very dissatisfied | Repeated failures (1 in 80) | Controls are unlikely to detect |
| **9** | **Safety/regulatory impact — failure occurs with warning** | Failure almost inevitable (1 in 8) | Very remote chance of detection |
| **10** | **Safety/regulatory — failure occurs without warning** | Failure is certain | Absolutely no detection possible |

**RPN range:** 1 (lowest risk) → 1,000 (highest risk: S=10, O=10, D=10)

### The Limitation of RPN Alone

RPN has a well-documented mathematical weakness: **two failure modes with identical RPNs can represent radically different risk profiles**.

For example:
- `S=10, O=1, D=1` → RPN = **10** — *rare but catastrophic, undetectable*
- `S=2, O=5, D=1` → RPN = **10** — *common but minor, easily caught*

A naive RPN-only ranking would treat these identically. This is why AIAG introduced the **Severity ≥ 9 mandatory flag** and the **Action Priority system** in the 5th Edition — both implemented in this tool.

---

## 3. AIAG FMEA-4 Flagging Rules

This tool computes three boolean flag columns for every failure mode, each grounded in the AIAG standard:

### Flag 1 — `Flag_High_RPN` (RPN > 100)

The RPN > 100 threshold is the most widely cited corrective action cutoff in Tier-1 aerospace and automotive quality systems (Boeing D6-51991, GE Aviation supplier requirements). At RPN = 100 on a 1,000-point scale, you are at exactly 10% of maximum risk — the empirically established threshold below which monitoring is sufficient and above which structured corrective action planning is required.

### Flag 2 — `Flag_High_Severity` (Severity ≥ 9)

**Severity 9 and 10 failure modes require immediate corrective action regardless of Occurrence or Detection scores.** This is explicitly stated in both AIAG FMEA-4 (Section 3) and the AIAG/VDA 5th Edition. The engineering rationale: even a failure that happens once every million cycles, but causes a safety incident when it does, cannot be optimized away by good detection controls.

Real-world composite manufacturing example: Autoclave overpressure (S=10) and vacuum bag burst during cure (S=9) are assigned mandatory corrective action even if they occur once in ten years — because when they do occur, the consequences are catastrophic (explosion risk, complete part loss).

### Flag 3 — `Flag_Action_Priority_H` (RPN ≥ 200 OR Severity ≥ 9)

A fast **RPN-side heuristic** that approximates the Action Priority "High" tier — high-consequence or high-probability modes get immediate attention. It is *not* the Action Priority engine; for the standard's actual High/Medium/Low determination, the tool now ships the full AP table (below).

### Action Priority (AIAG-VDA 2019) — the full engine

The AIAG/VDA FMEA Handbook (2019) replaced RPN-based prioritization with **Action Priority (AP)**: a published lookup table that maps every S×O×D combination directly to **High / Medium / Low**, with **Severity dominant (emphasis order S → O → D)**. This closes RPN's core weakness — the `S=10, O=1, D=1` case above is **AP = High** even though its RPN is only 10.

This tool implements the **complete published table** (no approximation) in `fmea_app/ap_engine.py`. A sidebar toggle switches the prioritization basis **RPN ↔ AP**; both columns stay visible, and the choice flows into ranking, tiering, the critical-items view, and the Excel/PDF/CSV exports. The transcription is verified against an independent copy of the published table across all 1,000 S/O/D combinations plus a monotonicity invariant — see [`docs/FMEA_methodology_notes.md`](docs/FMEA_methodology_notes.md) §4.2 and [`docs/ASSUMPTIONS_LOG.md`](docs/ASSUMPTIONS_LOG.md) Rule 7.

### Risk Tier Color Assignment

| Tier | Condition | Engineering Meaning |
|:---:|---|---|
| 🔴 **Red** | RPN > 100 **OR** Severity ≥ 9 | Immediate corrective action plan required |
| 🟡 **Yellow** | RPN 50–100 AND Severity < 9 | Corrective action strongly recommended |
| 🟢 **Green** | RPN < 50 AND Severity < 9 | Monitor; act at engineer's discretion |

---

## 4. Pareto 80/20 Applied to Risk

The Pareto principle — that roughly 20% of causes drive 80% of effects — is one of the most powerful tools in manufacturing quality engineering. Applied to FMEA, it means:

> *A small number of failure modes account for the vast majority of total risk exposure. Fixing those first gives the highest return on corrective action investment.*

The Pareto chart in this tool:
1. **Sorts failure modes** from highest to lowest RPN
2. **Overlays a cumulative RPN % line** on a right-hand y-axis
3. **Marks the 80% threshold** with a dashed reference line
4. **Colors bars by Risk Tier** (Red/Yellow/Green) so risk concentration is immediately visible

In the composite panel demo dataset, the **top 6 failure modes (out of 30) account for approximately 29% of total RPN** — the chart's cumulative line makes it easy to identify where corrective action spending should be concentrated: autoclave cure temperature deviation, vacuum bag leak, and ply misalignment during layup.

**How to read it:** Any failure mode whose bar falls to the left of where the cumulative line crosses 80% should be your engineering team's primary corrective action focus.

---

## 5. How This Application Works

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        fmea-risk-analyzer                        │
│                                                                   │
│  ┌─────────────────┐    ┌────────────────────────────────────┐   │
│  │   DATA LAYER    │    │         STREAMLIT UI LAYER          │   │
│  │                 │    │                                     │   │
│  │  CSV / Excel    │───►│  File Upload (CSV/XLSX)             │   │
│  │  FMEA input     │    │  Demo Dataset fallback              │   │
│  │                 │    │  Sidebar Filters (RPN slider,       │   │
│  │  30-row demo    │    │    Severity ≥ 9 toggle)             │   │
│  │  dataset        │    │  Metric Badges (7 KPIs)             │   │
│  └─────────────────┘    │  Color-Coded Ranked Table           │   │
│                          │  Pareto Chart + Heatmap Tabs        │   │
│                          │  Critical Items Expander            │   │
│                          │  Excel + PDF Download Buttons       │   │
│                          └──────────────┬──────────────────────┘   │
│                                         │                          │
│              ┌──────────────────────────▼──────────────────────┐  │
│              │              PROCESSING LAYER                    │  │
│              │                                                  │  │
│              │  fmea_app/rpn_engine.py                               │  │
│              │   ├── validate_input(df)   — schema + range      │  │
│              │   ├── calculate_rpn(df)    — S × O × D          │  │
│              │   ├── flag_critical(df)    — AIAG rules          │  │
│              │   ├── rank_by_rpn(df)      — sort + tier         │  │
│              │   └── run_pipeline(df)     — convenience wrapper │  │
│              └──────────────┬───────────────────────────────────┘  │
│                             │                                       │
│           ┌─────────────────┼─────────────────────┐               │
│           ▼                 ▼                       ▼              │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐    │
│  │VISUALIZATION │  │   CLI LAYER      │  │  EXPORT LAYER    │    │
│  │              │  │                  │  │                  │    │
│  │plotly_charts │  │fmea_analyzer.py  │  │fmea_app/exporter.py   │    │
│  │  pareto      │  │  --input FILE    │  │  export_excel()  │    │
│  │  heatmap     │  │  --charts        │  │  export_pdf()    │    │
│  └──────────────┘  └──────────────────┘  └──────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow — Step by Step

**Step 1 — Input**
The user uploads a CSV or Excel file (or clicks "Use Demo Dataset"). The file is read into a pandas DataFrame.

**Step 2 — Validation** (`fmea_app/rpn_engine.py → validate_input`)
The engine checks: (a) all 11 required columns are present, (b) Severity/Occurrence/Detection are numeric with no nulls, (c) all S/O/D values are integers in [1, 10]. Any violation raises a `ValueError` with a descriptive message surfaced as `st.error()` in the UI.

**Step 3 — RPN Calculation** (`calculate_rpn`)
A single vectorized operation: `df["RPN"] = df["Severity"] * df["Occurrence"] * df["Detection"]`. Returns a copy of the DataFrame with the RPN column appended.

**Step 4 — Criticality Flagging** (`flag_critical`)
Three boolean flag columns are added using pandas boolean masks:
- `Flag_High_RPN = RPN > 100`
- `Flag_High_Severity = Severity >= 9`
- `Flag_Action_Priority_H = (RPN >= 200) | (Severity >= 9)`

**Step 5 — Ranking + Tier Assignment** (`rank_by_rpn`)
The DataFrame is sorted descending by RPN and a `Risk_Tier` column is assigned row-by-row: Red if `RPN > 100 OR Severity >= 9`, Yellow if `RPN 50–100 AND Severity < 9`, Green otherwise.

**Step 6 — Filtering** (sidebar controls)
`st.session_state` preserves filter state across rerenders. The RPN threshold slider (0–300) and Severity ≥ 9 toggle apply boolean masks to the ranked DataFrame, updating the table, charts, badges, and export output simultaneously.

**Step 7 — Visualization** (`fmea_app/plotly_charts.py`)
Plotly figures are generated once per filter-state change and cached in `st.session_state` to avoid regeneration on every button click. The Pareto chart uses dual y-axes (RPN bars left, cumulative % line right). The heatmap uses a custom colorscale mapped to tier ranks with cell-count annotations.

**Step 8 — Export** (`fmea_app/exporter.py`)
- **Excel**: `openpyxl` writes a 2-sheet workbook — Sheet 1 is the ranked table with `PatternFill` color-coding per Risk_Tier, Sheet 2 is a metadata summary. Returned as `io.BytesIO` bytes.
- **PDF**: `fpdf2` generates an A4 landscape report. Page 1 is the summary metrics + full ranked table with tier-colored rows. Pages 2–3 embed the Pareto and heatmap charts as PNG images rendered by `matplotlib`.

---

## 6. Features

| Feature | Detail |
|---|---|
| **File upload** | CSV and Excel (.xlsx) supported; schema validated on upload |
| **Demo dataset** | 30-row composite panel PFMEA loads in one click — no file needed |
| **RPN calculation** | Vectorized S × O × D; 100% accurate against AIAG FMEA-4 formula |
| **AIAG flags** | All 3 flag types: High RPN, Severity ≥ 9, Action Priority H |
| **Color-coded table** | Row-level Red/Yellow/Green styling via pandas Styler |
| **7 metric badges** | Total modes, Red/Yellow/Green counts, High RPN, Sev≥9, Action Priority H — all update with filters |
| **Pareto chart** | Interactive Plotly bar + cumulative % line; hover tooltips; bars colored by tier |
| **Risk heatmap** | 10×10 Severity × Occurrence matrix; cell count annotations; hover detail |
| **Live filters** | RPN threshold slider (0–300) + Severity ≥ 9 toggle; updates all panels in real time |
| **Critical items panel** | `st.expander` surfacing only Action Priority H rows |
| **Excel export** | 2-sheet openpyxl workbook with tier color fills + metadata sheet |
| **PDF export** | 3-page A4 landscape: summary table + Pareto PNG + Heatmap PNG |
| **CLI mode** | `fmea_analyzer.py --input FILE --charts` for terminal/pipeline use |
| **105 tests** | Full pytest suite covering RPN logic, visualizations, edge cases, export |

---

## 7. Screenshots

<!-- Screenshots coming soon -->

*Load the [live demo](https://fmea-risk-analyzer-mhwzcki9sdzfz5d8rbzsdn.streamlit.app/) and click **Use Demo Dataset** to see all panels in action.*

---

## 8. Quick Start

### Option A — Live Web App (no install)

Open [https://fmea-risk-analyzer-mhwzcki9sdzfz5d8rbzsdn.streamlit.app/](https://fmea-risk-analyzer-mhwzcki9sdzfz5d8rbzsdn.streamlit.app/) and click **Use Demo Dataset**.

### Option B — Run Locally

```bash
# 1. Clone the repository
git clone https://github.com/Siddardth7/fmea-risk-analyzer.git
cd fmea-risk-analyzer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the Streamlit app
streamlit run app.py
# Opens at http://localhost:8501
```

### Option C — CLI Mode

```bash
# Run analysis on the demo dataset and print ranked table to terminal
python fmea_analyzer.py --input data/composite_panel_fmea_demo.csv

# Also generate Pareto chart and heatmap as PNG files
python fmea_analyzer.py --input data/composite_panel_fmea_demo.csv --charts

# Run on your own FMEA file
python fmea_analyzer.py --input path/to/your_fmea.csv --charts --output-dir reports/
```

---

## 9. Project Structure

```
fmea-risk-analyzer/
│
├── app.py                              # Streamlit web application (entry point)
├── fmea_analyzer.py                    # CLI entry point
├── requirements.txt                    # Pinned dependencies
│
├── fmea_app/
│   ├── rpn_engine.py                   # Core FMEA engine: validate → RPN → flag → rank
│   ├── visualizer.py                   # Matplotlib charts for CLI output
│   ├── plotly_charts.py                # Interactive Plotly charts for Streamlit
│   └── exporter.py                     # Excel (openpyxl) + PDF (fpdf2) export
│
├── tests/
│   ├── test_rpn_engine.py              # RPN calculation + flagging logic
│   ├── test_visualizer.py              # matplotlib chart functions
│   ├── test_streamlit_edge_cases.py    # edge cases (empty, malformed, all-green)
│   └── test_exporter.py                # Excel workbook + PDF output
│
├── data/
│   ├── composite_panel_fmea_demo.csv   # 30-row aerospace composite panel PFMEA dataset
│   └── fmea_input_template.csv         # Blank template for creating your own FMEA
│
├── docs/
│   ├── FMEA_COMPLETE_GUIDE.md          # End-to-end knowledge & teaching guide (start here)
│   ├── FMEA_methodology_notes.md       # In-depth engineering methodology write-up
│   ├── ASSUMPTIONS_LOG.md              # Every threshold decision with AIAG source citations
│   ├── FMEA_input_schema.md            # Full column specification and validation rules
│   └── EXECUTION_ROADMAP.md            # 4-week build plan (29 days, 2 hrs/day)
│
├── assets/                             # Screenshots and demo GIF for README
└── .streamlit/
    └── config.toml                     # Streamlit Cloud theme configuration
```

---

## 10. Input File Schema

Your CSV or Excel file must contain exactly these 11 columns:

| Column | Type | Valid Range | Description |
|---|---|---|---|
| `ID` | int | Any unique int | Row identifier |
| `Process_Step` | str | — | Manufacturing process step name (e.g., "Autoclave Cure") |
| `Component` | str | — | Part, sub-assembly, or material being analyzed |
| `Function` | str | — | Intended function of the component in the process |
| `Failure_Mode` | str | — | Specific way the component or step can fail |
| `Effect` | str | — | Downstream consequence when the failure occurs |
| `Severity` | int | 1–10 | Severity of the effect on the customer/process (AIAG scale) |
| `Cause` | str | — | Root cause mechanism that leads to the failure mode |
| `Occurrence` | int | 1–10 | Likelihood of the cause occurring (AIAG scale) |
| `Current_Control` | str | — | Existing preventive or detective controls in place |
| `Detection` | int | 1–10 | Ability of current controls to detect before reaching customer |

**Calculated columns added automatically:** `RPN`, `Risk_Tier`, `Flag_High_RPN`, `Flag_High_Severity`, `Flag_Action_Priority_H`

A blank template is at `data/fmea_input_template.csv`.

---

## 11. Demo Dataset

`data/composite_panel_fmea_demo.csv` contains **30 failure modes** across **11 process steps** of a carbon fiber reinforced polymer (CFRP) composite panel manufacturing line — a realistic aerospace PFMEA scenario:

| Process Step | Example Failure Modes |
|---|---|
| **Prepreg Layup** | Ply misalignment (>±2°), wrong ply count, out-of-life prepreg used |
| **Bagging** | Bag puncture from sharp tool, sealant tape disbond, vacuum leak at fitting |
| **Autoclave Cure** | Temperature deviation from cure cycle, pressure drop mid-cure, cure abort |
| **Demold** | Part bonded to tool (release film omitted), edge delamination, impact during handling |
| **Post-Cure Inspection** | NDI (ultrasonic) miss of subsurface void, dimensional non-conformance |
| **Assembly** | Fastener overtorque causing bearing failure, adhesive bond deficiency |

Severity, Occurrence, and Detection scores are calibrated to reflect realistic aerospace supply chain conditions. Risk distribution: Red=19, Yellow=9, Green=2. High RPN (>100) = 14, Action Priority H = 8. The top 6 failure modes account for approximately 29% of total RPN.

---

## 12. Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Web UI | [Streamlit 1.56](https://streamlit.io) | Browser-based interactive dashboard |
| Charting | [Plotly 6.6](https://plotly.com/python/) | Interactive Pareto + heatmap charts |
| Data Processing | [pandas 3.0](https://pandas.pydata.org) + [numpy 2.4](https://numpy.org) | DataFrame operations, vectorized RPN |
| PDF Export | [fpdf2 2.8](https://py-pdf.github.io/fpdf2/) | Multi-page A4 landscape PDF report |
| Excel Export | [openpyxl 3.1](https://openpyxl.readthedocs.io) | Color-coded .xlsx workbook |
| CLI Charts | [matplotlib 3.10](https://matplotlib.org) | Static chart generation for terminal use and PDF embedding |
| Testing | [pytest 9.0](https://pytest.org) | 105 unit tests across 6 test modules (install via requirements-dev.txt) |

---

## 13. Running Tests

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
pytest --cov=fmea_app --cov-report=term-missing
```

```
tests/test_rpn_engine.py              passed
tests/test_streamlit_edge_cases.py    passed
tests/test_visualizer.py              passed
tests/test_exporter.py                passed
tests/test_app_integration.py         passed
tests/test_ui_modules.py              passed
------------------------------------------------
105 passed
```

Every threshold decision (RPN > 100, Severity ≥ 9, Action Priority H thresholds) has a corresponding test that verifies the correct row is flagged or not flagged. See `docs/ASSUMPTIONS_LOG.md` for the source citations behind each decision.

---

## 14. Engineering References

1. **AIAG FMEA-4** (4th Edition, 2008) — *Potential Failure Mode and Effects Analysis Reference Manual*. Automotive Industry Action Group. The primary reference for the RPN > 100 corrective action threshold, Severity ≥ 9 safety rule, and Risk Tier color assignments used in this tool.

2. **AIAG/VDA FMEA Handbook** (1st Edition, 2019) — Joint publication by AIAG and Verband der Automobilindustrie. Introduces the Action Priority (AP) system that supplements RPN-based prioritization. The `Flag_Action_Priority_H` flag in this tool is a simplified implementation of the AP "High" tier.

3. **ASQ** — *Failure Mode Effects Analysis (FMEA) Overview.* American Society for Quality. quality.asq.org

4. **Quality-One International** — *FMEA Reference Guide.* quality-one.com

5. `docs/ASSUMPTIONS_LOG.md` — Project-specific engineering decision log with source citations for every threshold value used in `fmea_app/rpn_engine.py`.

6. `docs/FMEA_methodology_notes.md` — Detailed methodology notes written alongside this project: RPN formula derivation, AIAG Action Priority logic, Pareto 80/20 application to FMEA.

7. `docs/FMEA_COMPLETE_GUIDE.md` — End-to-end knowledge and teaching guide: fundamentals, architecture, feature walkthrough, user guide, real-world applications, FAQ, and presentation talking points.
