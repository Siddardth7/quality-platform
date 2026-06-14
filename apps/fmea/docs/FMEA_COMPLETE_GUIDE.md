# FMEA Risk Analyzer — Complete Knowledge & Teaching Guide

**Author:** Siddardth | M.S. Aerospace Engineering, UIUC  
**Live App:** [fmea-risk-analyzer on Streamlit Cloud](https://fmea-risk-analyzer-mhwzcki9sdzfz5d8rbzsdn.streamlit.app/)  
**Engineering Reference:** AIAG FMEA-4 (4th Edition, 2008) + AIAG/VDA FMEA Handbook (5th Edition, 2019)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Background & Fundamentals](#2-background--fundamentals)
3. [Problem Statement](#3-problem-statement)
4. [Solution Overview](#4-solution-overview)
5. [System Architecture](#5-system-architecture)
6. [Core Logic & Algorithms](#6-core-logic--algorithms)
7. [Codebase Breakdown](#7-codebase-breakdown)
8. [Feature Walkthrough](#8-feature-walkthrough)
9. [How to Use the Tool — User Guide](#9-how-to-use-the-tool--user-guide)
10. [Deployment & Setup](#10-deployment--setup)
11. [Real-World Applications](#11-real-world-applications)
12. [Limitations](#12-limitations)
13. [Improvements & Future Scope](#13-improvements--future-scope)
14. [Key Talking Points — For Presentation](#14-key-talking-points--for-presentation)
15. [FAQ Section](#15-faq-section)

---

## 1. Executive Summary

### What the Project Is

The **FMEA Risk Prioritization Tool** is a Python-based web application and command-line tool that automates the risk analysis workflow used in aerospace, automotive, and manufacturing engineering. It takes a structured list of potential failures in a manufacturing process, calculates risk scores using the industry-standard formula, applies criticality flags from global engineering standards, and delivers visual dashboards and exportable reports.

The application is deployed live on Streamlit Cloud and is usable by anyone with a web browser — no installation required.

### Why It Exists

Manufacturing engineers routinely conduct **Failure Mode and Effects Analysis (FMEA)** — a systematic process of asking "what can go wrong, how bad is it, and how likely is it?" for every step of a production process. Traditionally, this entire workflow is done manually in Excel spreadsheets: engineers enter scores by hand, calculate risk numbers with formulas, sort rows manually, and produce reports through copy-paste. This is:

- **Slow** — a single FMEA spreadsheet with 50 failure modes can take hours to analyze manually
- **Error-prone** — manual RPN calculations introduce arithmetic mistakes
- **Visually opaque** — spreadsheet rows give no immediate sense of where the highest risks are concentrated
- **Hard to share** — getting a formatted, color-coded report out of Excel requires significant effort

This tool replaces all of that with a web app that runs the entire pipeline in seconds.

### Key Value Proposition

| Without This Tool | With This Tool |
|---|---|
| Manual RPN calculation in Excel | Automated RPN pipeline — zero arithmetic errors |
| No visual risk distribution | Interactive Pareto chart + heatmap |
| Sorting rows by hand | Automatic risk-tier ranking (Red/Yellow/Green) |
| Copy-paste reports | One-click Excel + PDF export |
| Standards applied inconsistently | AIAG FMEA-4 flags enforced automatically |

### Who It Is For

- **Manufacturing engineers** conducting Process FMEA for aerospace, automotive, or medical device production
- **Quality engineers** performing root cause analysis and corrective action prioritization
- **Engineering managers** who need risk dashboards for program reviews
- **Students and researchers** learning FMEA methodology in an interactive environment

---

## 2. Background & Fundamentals

### What is FMEA?

**Failure Mode and Effects Analysis (FMEA)** is a structured, bottom-up methodology for identifying and prioritizing risks before they cause problems. It originated at NASA in the 1960s for the Apollo program and has since become mandatory across most high-stakes manufacturing sectors.

The core idea is simple: for every step in a process or every component in a design, ask three questions:

1. **How can this fail?** (the Failure Mode)
2. **What happens when it does?** (the Effect)
3. **How likely are we to catch it before it reaches the customer?** (Detection)

Then score each of those three dimensions on a 1–10 scale and multiply them together to get a single risk number — the **Risk Priority Number (RPN)**.

### Two Types of FMEA

| Type | Focus | When Used |
|---|---|---|
| **Design FMEA (DFMEA)** | Product design — will the product function as intended? | During product development |
| **Process FMEA (PFMEA)** | Manufacturing process — can the process produce conforming parts? | During production planning |

This tool is built for **Process FMEA** — analyzing manufacturing steps, not product design.

### Why FMEA is Important

FMEA is not just good engineering practice — it is a regulatory requirement in many industries:

- **Aerospace:** AS9100 (Quality Management Systems), FAA production approvals
- **Automotive:** IATF 16949, required by every major OEM (Ford, GM, BMW, Toyota)
- **Medical Devices:** ISO 13485, FDA Design Controls
- **Defense:** MIL-STD-1629A

When a supplier submits a production plan to Boeing or Airbus, a completed Process FMEA is part of the required documentation package. There is no shipping product without it.

### Traditional vs. Automated FMEA

```
TRADITIONAL (Excel-based)              AUTOMATED (This Tool)
─────────────────────────────          ─────────────────────────────────────
1. Engineer opens spreadsheet          1. Engineer uploads CSV/Excel file
2. Manually enters S, O, D scores      2. Tool validates schema automatically
3. Types formula =S*O*D in each row    3. RPN calculated in milliseconds
4. Sorts rows by RPN manually          4. Ranked table generated instantly
5. Highlights cells by hand            5. Red/Yellow/Green applied automatically
6. Creates charts in Excel (slow)      6. Interactive Pareto + heatmap ready
7. Copies data to Word for report      7. Click "Download PDF" — done
8. Emails spreadsheet around           8. Share the live web link
─────────────────────────────          ─────────────────────────────────────
Time: 2-4 hours                        Time: 30 seconds
```

### Key Concepts

#### Severity (S)
Rates **how bad the consequence is** when the failure occurs. Scored 1–10:
- **1–2:** No meaningful effect on product or process
- **5–6:** Customer is dissatisfied; rework or scrap required
- **9:** Safety or regulatory impact — failure happens with warning
- **10:** Safety or regulatory — failure happens *without* warning

The critical rule: **Severity ≥ 9 always requires corrective action, regardless of how rare the failure is.** A catastrophic failure that happens once every ten years still demands action.

#### Occurrence (O)
Rates **how likely the failure cause is to occur**. Scored 1–10:
- **1:** Extremely rare — less than 1 in 1,500,000 cycles
- **5:** Occasional — roughly 1 in 400 cycles
- **9–10:** Almost certain — failure happens regularly

#### Detection (D)
Rates **how well existing controls can detect the failure before it reaches the customer**. Scored 1–10:

> **Important:** Detection is scored *inversely* to what you might expect. A **low Detection score means you're good at catching failures**; a **high Detection score means failures slip through undetected.**

- **1:** Controls will almost certainly detect the failure
- **5:** Controls may or may not detect it
- **10:** No detection possible — failure goes directly to the customer

#### Risk Priority Number (RPN)

```
RPN = Severity × Occurrence × Detection

Minimum possible: 1 × 1 × 1 = 1
Maximum possible: 10 × 10 × 10 = 1,000
```

---

## 3. Problem Statement

### What Problem This Tool Solves

A manufacturing engineer running Process FMEA on a 30-step composite panel layup process might have 60–100 failure modes to analyze. The workflow typically looks like this:

1. Open an Excel template that was built years ago by someone who has since left
2. Fill in failure modes, effects, and causes for each process step
3. Assign S, O, D scores and let the spreadsheet formula calculate RPN
4. Sort by RPN, then manually identify which ones require action
5. Screenshot or copy-paste data into a PowerPoint for a program review
6. Email the file around and manually reconcile feedback from three engineers

Every step has failure points. The formula might be broken in one row. Sorting is forgotten after someone adds a new row. The "Red/Yellow/Green" color scheme is applied inconsistently or not at all. The 30-page Excel file becomes unmanageable.

### Limitations of Manual FMEA

**Arithmetic errors:** RPN = S × O × D is simple, but multiplying 80 rows manually with Excel formulas that can be accidentally deleted or overwritten is a real problem.

**Missing safety flags:** AIAG FMEA-4 requires that failures with Severity ≥ 9 be flagged regardless of their RPN. Excel spreadsheets don't enforce this unless someone builds a specific rule — and even then it can be bypassed.

**No Pareto visibility:** The 80/20 rule is critical to FMEA — a small subset of failure modes typically drives most of the total risk. But a flat spreadsheet gives no visual insight into this distribution.

**No standardized export:** Getting a clean, formatted report out of Excel requires significant formatting work. Every report looks different.

**Single-user bottleneck:** The FMEA lives in one person's Excel file. Everyone else has to wait for updates.

### Why This Tool Was Needed

The tool was built to demonstrate that the entire FMEA workflow — from raw data to ranked risk table to visual dashboard to formatted report — can be fully automated in Python, deployed as a free web application, and made accessible to any engineer in seconds. It is also a portfolio demonstration of applied engineering knowledge combined with structured, test-driven software development.

---

## 4. Solution Overview

### How the Tool Solves the Problem

The FMEA Risk Prioritization Tool replaces the entire manual workflow with a four-step automated pipeline:

```
INPUT                    PIPELINE                        OUTPUT
─────                    ────────                        ──────
CSV / Excel  ──────►  Validate Schema                   Web Dashboard
FMEA File    ──────►  Calculate RPN (S × O × D)    ──►  Color-coded Table
             ──────►  Apply AIAG Flags              ──►  Pareto Chart
             ──────►  Rank & Tier                   ──►  Heatmap
                                                    ──►  PDF Report
                                                    ──►  Excel Report
```

### Core Features and Capabilities

| Feature | What It Does |
|---|---|
| **File upload** | Accepts CSV or Excel FMEA files; validates schema before processing |
| **Demo dataset** | 30-row aerospace composite panel FMEA; loads in one click |
| **RPN calculation** | Vectorized S × O × D using pandas — mathematically guaranteed correct |
| **AIAG flags** | Enforces three AIAG FMEA-4 rules automatically (see Section 6) |
| **Risk-tier ranking** | Sorts failure modes by RPN; assigns Red/Yellow/Green tier to every row |
| **Pareto chart** | Interactive bar chart with cumulative % line and 80% threshold marker |
| **Heatmap** | 10×10 Severity × Occurrence matrix showing risk concentration |
| **Live filters** | RPN threshold slider and Severity ≥ 9 toggle; all panels update together |
| **Critical panel** | Expander showing only Action Priority H failure modes |
| **Excel export** | Color-coded 2-sheet workbook with metadata summary |
| **PDF export** | 3-page A4 landscape report with table, Pareto, and heatmap |
| **CLI mode** | Terminal command for batch use or pipeline integration |
| **78 tests** | Full pytest suite ensuring every calculation is correct |

### What Makes This Tool Different

1. **Standards-grounded:** Every threshold (RPN > 100, Severity ≥ 9, Action Priority H) is sourced from AIAG FMEA-4 and documented in `docs/ASSUMPTIONS_LOG.md` with citations. Note: `Flag_Action_Priority_H` uses a threshold simplification (`RPN >= 200 OR Severity >= 9`), not the full 2019 AIAG/VDA Action Priority lookup table.

2. **Portfolio implementation with production practices:** 78 unit tests, validated against the AIAG standard, clean architecture with separated concerns (engine / visualization / export / UI).

3. **Immediately deployable:** Runs as a web app at a public URL. No installation. No license. No login.

4. **Dual interface:** Both a web app (Streamlit) and a CLI (`fmea_analyzer.py`) for engineers who prefer terminal workflows.

---

## 5. System Architecture

### Full Architecture Breakdown

```
┌─────────────────────────────────────────────────────────────────────┐
│                       fmea-risk-analyzer                             │
│                                                                       │
│  ┌──────────────────┐         ┌────────────────────────────────────┐ │
│  │   DATA LAYER     │         │         UI LAYER (app.py)           │ │
│  │                  │         │                                     │ │
│  │  CSV / XLSX      │────────►│  • File upload (sidebar)            │ │
│  │  FMEA input      │         │  • Demo dataset button              │ │
│  │                  │         │  • RPN slider filter                │ │
│  │  30-row demo     │         │  • Severity ≥ 9 toggle              │ │
│  │  dataset         │         │  • 7 metric badges                  │ │
│  └──────────────────┘         │  • Color-coded ranked table         │ │
│                                │  • Pareto chart tab                 │ │
│                                │  • Risk heatmap tab                 │ │
│                                │  • Critical items expander          │ │
│                                │  • Excel + PDF download buttons     │ │
│                                └──────────────┬──────────────────────┘ │
│                                               │                        │
│                     ┌─────────────────────────▼────────────────────┐  │
│                     │       PROCESSING LAYER (src/rpn_engine.py)    │  │
│                     │                                               │  │
│                     │  validate_input(df)  — schema + range check   │  │
│                     │  calculate_rpn(df)   — S × O × D              │  │
│                     │  flag_critical(df)   — AIAG rules 1/2/3       │  │
│                     │  rank_by_rpn(df)     — sort + tier            │  │
│                     │  run_pipeline(df)    — convenience wrapper     │  │
│                     └────────┬───────────────┬──────────────────────┘  │
│                              │               │                          │
│           ┌──────────────────┼───────────────┼─────────────────────┐   │
│           ▼                  ▼               ▼                       │   │
│  ┌──────────────────┐  ┌──────────────┐  ┌──────────────────────┐  │   │
│  │ VISUALIZATION    │  │  CLI LAYER   │  │   EXPORT LAYER       │  │   │
│  │                  │  │              │  │                      │  │   │
│  │ plotly_charts.py │  │fmea_analyzer │  │ src/exporter.py      │  │   │
│  │  pareto_plotly() │  │  .py         │  │   export_excel()     │  │   │
│  │  heatmap_plotly()│  │  --input     │  │   export_pdf()       │  │   │
│  │                  │  │  --charts    │  │                      │  │   │
│  │ visualizer.py    │  │              │  │ openpyxl workbook    │  │   │
│  │  pareto_chart()  │  │  ANSI color  │  │ fpdf2 PDF            │  │   │
│  │  risk_heatmap()  │  │  table       │  │ matplotlib PNG       │  │   │
│  └──────────────────┘  └──────────────┘  └──────────────────────┘  │   │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow — Step by Step

The following describes exactly what happens when a user uploads a file and clicks "Run":

```
Step 1: INPUT
  User uploads CSV or clicks "Use Demo Dataset"
  → pandas reads file into DataFrame (df_raw)
  → 30 rows × 11 columns

Step 2: VALIDATION (validate_input)
  Check 1: DataFrame is not empty (≥ 1 row)
  Check 2: All 11 required columns present
  Check 3: Severity, Occurrence, Detection have no null values
  Check 4: All S/O/D values are integers in range [1, 10]
  → If any check fails: ValueError raised, shown as st.error() in UI
  → If all pass: continue

Step 3: RPN CALCULATION (calculate_rpn)
  df["RPN"] = df["Severity"] * df["Occurrence"] * df["Detection"]
  → One vectorized operation — 30 rows calculated simultaneously
  → Returns copy of DataFrame with RPN column added

Step 4: FLAG APPLICATION (flag_critical)
  df["Flag_High_RPN"]          = df["RPN"] > 100
  df["Flag_High_Severity"]     = df["Severity"] >= 9
  df["Flag_Action_Priority_H"] = (df["RPN"] >= 200) | (df["Severity"] >= 9)
  → Three boolean columns added

Step 5: RANKING + TIER ASSIGNMENT (rank_by_rpn)
  Sort DataFrame descending by RPN
  For each row:
    if RPN > 100 OR Severity >= 9:  Risk_Tier = "Red"
    elif RPN >= 50:                  Risk_Tier = "Yellow"
    else:                            Risk_Tier = "Green"
  → Returns sorted DataFrame with Risk_Tier column

Step 6: FILTER (sidebar controls)
  Apply user-selected minimum RPN threshold
  Apply user-selected Severity ≥ 9 toggle
  → Filtered view for table, charts, badges, export

Step 7: VISUALIZATION (plotly_charts.py)
  pareto_chart_plotly(df_filtered) → Plotly Figure
    - Bars sorted by RPN, colored by Risk_Tier
    - Cumulative % line overlaid on second y-axis
    - 80% reference line
  risk_heatmap_plotly(df_filtered) → Plotly Figure
    - 10×10 grid: x=Occurrence, y=Severity
    - Cell color = highest Risk_Tier in that cell
    - Cell number = count of failure modes

Step 8: EXPORT (exporter.py)
  Excel: openpyxl builds 2-sheet workbook
    Sheet 1 "FMEA Analysis": ranked table with color fills
    Sheet 2 "Metadata": timestamp, counts, AIAG reference
  PDF: fpdf2 builds 3-page A4 landscape
    Page 1: Summary metrics + full table
    Page 2: Pareto chart (rendered from matplotlib)
    Page 3: Risk heatmap (rendered from matplotlib)
```

### Integrations and External Services

| Service | Role |
|---|---|
| **Streamlit Cloud** | Free hosting platform; deploys automatically from GitHub |
| **GitHub** | Source control; Streamlit Cloud connects directly |
| No database | No user data is stored; all processing happens in-memory per session |
| No external APIs | Fully self-contained; runs without internet after install |

---

## 6. Core Logic & Algorithms

### How Risk is Calculated — The RPN Formula

The Risk Priority Number formula is:

```
RPN = Severity × Occurrence × Detection
```

This is a trilinear product that produces a single number from 1 to 1,000. In the code (`src/rpn_engine.py:166`):

```python
df["RPN"] = df["Severity"] * df["Occurrence"] * df["Detection"]
```

This is a **vectorized pandas operation** — it operates on the entire column at once rather than looping row by row. This ensures mathematical accuracy and handles any size dataset efficiently.

### The Three AIAG Flagging Rules

Beyond the RPN score, the tool applies three mandatory flags from the AIAG standard. These are documented in `docs/ASSUMPTIONS_LOG.md` with source citations.

#### Rule 1 — High RPN Flag (RPN > 100)

```python
df["Flag_High_RPN"] = df["RPN"] > 100
```

**Why 100?** On a 1,000-point scale, 100 represents exactly 10% of maximum risk. This threshold appears in Boeing D6-51991, GE Aviation supplier quality requirements, and is the most widely cited corrective action threshold in AIAG FMEA-4. Below 100: monitoring is sufficient. Above 100: a structured corrective action plan is required.

#### Rule 2 — High Severity Flag (Severity ≥ 9)

```python
df["Flag_High_Severity"] = df["Severity"] >= 9
```

**Why this is special:** This flag fires regardless of Occurrence or Detection scores. The rationale: even a failure that occurs once every million cycles, but causes a safety incident when it does, cannot be "fixed" by good detection controls. AIAG FMEA-4 states explicitly: **Severity 9 and 10 failure modes require corrective action independent of RPN.**

This catches failures that RPN-only systems miss. Example:
- A failure with S=9, O=1, D=1 → RPN = 9 (would be ignored by a naive threshold)
- But this is a safety-critical failure mode — it gets flagged by Rule 2 regardless

#### Rule 3 — Action Priority H (RPN ≥ 200 OR Severity ≥ 9)

```python
df["Flag_Action_Priority_H"] = (df["RPN"] >= 200) | (df["Severity"] >= 9)
```

This is a simplified implementation of the AIAG FMEA 5th Edition (2019) Action Priority system. The full 5th Edition uses a 3-dimensional S×O×D lookup table; this tool uses a conservative threshold-based approximation. The 200 threshold was chosen as a conservative proxy for the "High" tier — it captures the intent without requiring the company-specific customization that the full AP table requires.

### Risk Tier Assignment Algorithm

After flagging, each failure mode is assigned a visual tier (Rule 4 in the ASSUMPTIONS_LOG):

```python
def _assign_tier(row):
    if row["RPN"] > 100 or row["Severity"] >= 9:
        return "Red"       # Immediate corrective action required
    elif row["RPN"] >= 50:
        return "Yellow"    # Corrective action strongly recommended
    else:
        return "Green"     # Monitor; act at engineer's discretion
```

| Tier | Condition | Meaning |
|---|---|---|
| 🔴 Red | RPN > 100 **OR** Severity ≥ 9 | Stop. Plan corrective action now. |
| 🟡 Yellow | RPN 50–100 AND Severity < 9 | Review. Corrective action recommended. |
| 🟢 Green | RPN < 50 AND Severity < 9 | OK. Monitor; revisit at next FMEA cycle. |

### Pareto Chart Logic — The 80/20 Principle

The Pareto chart identifies the "vital few" failure modes that drive most of the total risk:

```python
cumulative_pct = np.cumsum(rpns) / rpns.sum() * 100
```

Steps:
1. Sort failure modes from highest to lowest RPN
2. Compute running sum of RPNs
3. Divide by total RPN sum to get percentage
4. Overlay this as a line on the second y-axis
5. Draw a dashed horizontal reference line at 80%

**How to interpret:** Any failure mode whose bar falls to the left of where the cumulative line crosses 80% is in your "vital few" — these should be your team's primary corrective action focus. In the demo dataset, the top 6 of 30 failure modes account for approximately 29% of total RPN; the 80% threshold is crossed further along the distribution.

### Risk Heatmap Logic

The heatmap plots Severity (y-axis) vs. Occurrence (x-axis) on a 10×10 grid:

```python
grid_count[severity - 1][occurrence - 1] += 1      # count per cell
grid_tier_rank[s, o] = max(current, new_tier_rank)  # highest tier wins
```

Each cell shows:
- **Count:** how many failure modes fall in that Severity × Occurrence combination
- **Color:** Red/Yellow/Green based on the highest Risk_Tier of all failure modes in that cell

The heatmap reveals **risk concentration patterns** — for example, clustering in the upper-right (high Severity, high Occurrence) corner is a warning sign for the process.

### Edge Cases Handled

| Edge Case | How It's Handled |
|---|---|
| Empty CSV | Rejected with `ValueError: Input DataFrame is empty` |
| Missing column | Lists all missing columns in error message |
| Null S/O/D value | Reports which row IDs contain null values |
| S/O/D out of range | Reports which row IDs contain values outside [1, 10] |
| Non-numeric S/O/D | Reports actual dtype found |
| All failure modes filtered out | Charts show "No data" message; PDF export disabled |
| Unsupported file format | Rejects with descriptive error; accepts .csv and .xlsx only |

---

## 7. Codebase Breakdown

### Folder Structure

```
fmea-risk-analyzer/
│
├── app.py                           # Streamlit web app — entry point
├── fmea_analyzer.py                 # CLI tool — entry point
├── requirements.txt                 # Pinned Python dependencies
│
├── src/                             # Business logic (importable modules)
│   ├── __init__.py
│   ├── rpn_engine.py                # CORE: validate → calculate → flag → rank
│   ├── visualizer.py                # Matplotlib charts for CLI (static PNG)
│   ├── plotly_charts.py             # Plotly charts for Streamlit (interactive)
│   └── exporter.py                  # Excel (openpyxl) + PDF (fpdf2) export
│
├── tests/                           # pytest test suite (78 tests)
│   ├── test_rpn_engine.py           # RPN math, flagging, ranking
│   ├── test_visualizer.py           # chart function coverage
│   ├── test_streamlit_edge_cases.py # edge cases (empty, malformed)
│   └── test_exporter.py             # Excel/PDF output validation
│
├── data/
│   ├── composite_panel_fmea_demo.csv  # 30-row aerospace FMEA demo
│   └── fmea_input_template.csv        # Blank template for users
│
├── docs/
│   ├── ASSUMPTIONS_LOG.md           # Engineering decisions with AIAG citations
│   ├── FMEA_input_schema.md         # Column specification and validation rules
│   ├── EXECUTION_ROADMAP.md         # 4-week build plan
│   └── FMEA_COMPLETE_GUIDE.md       # This document
│
├── assets/                          # Screenshots for README
└── .streamlit/
    └── config.toml                  # Streamlit Cloud theme settings
```

### Key Files and Their Roles

#### `src/rpn_engine.py` — The Heart of the Tool

This is the most important file. It contains four public functions that form a sequential pipeline:

| Function | Input | Output | What It Does |
|---|---|---|---|
| `validate_input(df)` | raw DataFrame | None / ValueError | Schema + range validation |
| `calculate_rpn(df)` | validated df | df + RPN column | S × O × D calculation |
| `flag_critical(df)` | df with RPN | df + 3 flag columns | AIAG rules 1, 2, 3 |
| `rank_by_rpn(df)` | flagged df | sorted df + tier | Sort + Red/Yellow/Green |
| `run_pipeline(df)` | raw DataFrame | fully analyzed df | Runs all four in sequence |

Both `app.py` and `fmea_analyzer.py` call `run_pipeline()` — the engine is fully reusable.

#### `app.py` — The Streamlit Web Application

The UI layer. Follows a clear modular structure:

| Function | What It Renders |
|---|---|
| `render_header()` | Title and description |
| `render_sidebar()` | File upload, demo button, filters |
| `render_metric_badges()` | 7 KPI metrics in a column layout |
| `render_table()` | Color-coded pandas Styler table |
| `render_charts()` | Tabbed Pareto/heatmap panel |
| `render_critical_panel()` | Expandable critical items list |
| `render_export_buttons()` | Excel and PDF download buttons |
| `render_landing()` | Empty state with schema reference |
| `main()` | Orchestrates all components |

Chart objects are cached in `st.session_state` so they don't regenerate on every sidebar interaction.

#### `fmea_analyzer.py` — The CLI Tool

For engineers who prefer terminal output or want to integrate FMEA analysis into a pipeline:

```bash
python fmea_analyzer.py --input data/composite_panel_fmea_demo.csv
python fmea_analyzer.py --input my_fmea.csv --charts --output-dir reports/
```

Produces ANSI-colored terminal output with Red/Yellow/Green tier color codes, plus optional PNG chart files.

#### `src/plotly_charts.py` — Interactive Charts

Two functions:
- `pareto_chart_plotly(df)` → Plotly Figure with dual y-axes (RPN bars + cumulative % line)
- `risk_heatmap_plotly(df)` → Plotly Figure with 10×10 heatmap grid

Both return `plotly.graph_objects.Figure` objects passed directly to `st.plotly_chart()`.

#### `src/visualizer.py` — Static Charts (CLI)

Same two charts (Pareto + heatmap) built with matplotlib for static PNG output. Used by the CLI tool's `--charts` flag. Uses `matplotlib.use("Agg")` for non-interactive rendering safe for server environments.

#### `src/exporter.py` — Export Engine

Two functions:
- `export_excel(df)` → bytes — openpyxl workbook with PatternFill color coding
- `export_pdf(df)` → bytes — fpdf2 PDF with matplotlib-rendered charts

Both return raw `bytes` objects plugged directly into Streamlit's `st.download_button()`.

### How Components Interact

```
User uploads file
      │
      ▼
app.py calls _load_uploaded(file)
      │
      ▼
rpn_engine.validate_input(df)    ← raises ValueError if invalid
      │
      ▼
rpn_engine.run_pipeline(df)      ← returns fully analyzed DataFrame
      │
      ├──► _apply_filters(df, rpn_min, sev9_only)
      │           │
      │           ├──► plotly_charts.pareto_chart_plotly(df_filtered)
      │           ├──► plotly_charts.risk_heatmap_plotly(df_filtered)
      │           ├──► _style_table(df_filtered)
      │           ├──► render_metric_badges(df_filtered)
      │           └──► render_critical_panel(df_filtered)
      │
      └──► On download button click:
               ├──► exporter.export_excel(df_filtered)
               └──► exporter.export_pdf(df_filtered)
```

---

## 8. Feature Walkthrough

### Feature 1 — File Upload

**Location:** Left sidebar, "Data Source" section  
**How it works:** Streamlit's `file_uploader` widget accepts `.csv` and `.xlsx`. The file is read into a pandas DataFrame using `pd.read_csv()` or `pd.read_excel()`. Schema validation fires immediately.

**What users see:** A drag-and-drop area. After uploading, the filename appears as a caption.

**Error states:** If the file has missing columns or invalid scores, a red error banner appears at the top of the main panel with a specific error message identifying the problem row.

### Feature 2 — Demo Dataset

**Location:** "Use Demo Dataset" button in sidebar  
**What it loads:** `data/composite_panel_fmea_demo.csv` — 30 failure modes from a carbon fiber composite panel manufacturing process across 11 process steps.

**Why it's useful:** Lets anyone explore the tool without having an FMEA file ready. Produces a realistic risk distribution (Red=19, Yellow=9, Green=2) useful for exploring all tool features.

### Feature 3 — 7 Metric Badges

A row of 7 metric cards at the top of the main panel:

| Badge | What It Shows |
|---|---|
| Total Modes | Count of failure modes (after filter) |
| 🔴 Red | Count with Risk_Tier = Red |
| 🟡 Yellow | Count with Risk_Tier = Yellow |
| 🟢 Green | Count with Risk_Tier = Green |
| High RPN (>100) | Count with Flag_High_RPN = True |
| Severity ≥ 9 | Count with Flag_High_Severity = True |
| Action Priority H | Count with Flag_Action_Priority_H = True |

All seven update instantly when the sidebar filters change.

### Feature 4 — Color-Coded Ranked Table

The main data table sorted by RPN descending. Each row is background-colored by Risk_Tier:

- 🔴 Red rows: light red background (`#fde8e8`)
- 🟡 Yellow rows: light yellow background (`#fef9e7`)
- 🟢 Green rows: light green background (`#eafaf1`)

Columns displayed: Failure_Mode, Process_Step, Component, Severity, Occurrence, Detection, RPN, Risk_Tier, Flag_High_RPN, Flag_High_Severity, Flag_Action_Priority_H

### Feature 5 — Pareto Chart

**Tab:** "Pareto Chart" in the visualization panel  
**What it shows:** Failure modes sorted from highest to lowest RPN as colored bars, with a cumulative RPN percentage line on a second y-axis and an 80% dashed reference line.

**How to use it:** Find where the cumulative line crosses 80%. Every failure mode to the *left* of that point is in your "vital few" — these drive 80% of your total risk. Focus corrective action resources here.

**Interactive features:** Hover over any bar to see the failure mode name, exact RPN, and risk tier. Click legend items to toggle tier visibility.

### Feature 6 — Risk Heatmap

**Tab:** "Risk Heatmap" in the visualization panel  
**What it shows:** A 10×10 grid where x-axis = Occurrence (1–10) and y-axis = Severity (1–10). Each occupied cell shows the count of failure modes with that S×O combination, colored by the worst Risk_Tier present.

**How to use it:** High concentrations in the upper-right corner (high Severity, high Occurrence) indicate systemic process problems. The bottom-left corner (low Severity, low Occurrence) is the safe zone.

### Feature 7 — Live Filters

**RPN Threshold Slider (0–300):** Shows only failure modes with RPN ≥ the selected value. Useful for focusing on high-risk items only.

**Severity ≥ 9 Toggle:** Shows only safety-critical failure modes. Use this before program reviews where safety is the primary discussion topic.

Both filters update the table, charts, metric badges, critical panel, and export content simultaneously.

### Feature 8 — Critical Items Panel

**Location:** Expandable section below the main table  
**Label:** "⚠️ Critical Failure Modes — Action Priority H (N items)"  
**What it shows:** A compact table of only the failure modes with `Flag_Action_Priority_H = True` — these are the ones requiring immediate corrective action per AIAG FMEA-4.

Auto-expands when critical items exist.

### Feature 9 — Excel Export

**Button:** "📊 Download Excel"  
**Output:** `fmea_analysis.xlsx` with two sheets:

- **Sheet 1 "FMEA Analysis":** Full ranked table with tier-colored rows, frozen header row
- **Sheet 2 "Metadata":** Timestamp, AIAG reference, row counts by tier, flag counts

### Feature 10 — PDF Export

**Button:** "📄 Download PDF"  
**Output:** `fmea_report.pdf` — A4 landscape, 3 pages:

- **Page 1:** Header bar, summary metrics row, full ranked table with color coding
- **Page 2:** Pareto chart (static image, matplotlib)
- **Page 3:** Risk heatmap (static image, matplotlib)

PDF is disabled if the filtered table is empty (no data to export).

### Feature 11 — CLI Mode

For terminal users or pipeline integration:

```bash
# Ranked table in terminal with ANSI color coding
python fmea_analyzer.py --input data/composite_panel_fmea_demo.csv

# Ranked table + Pareto PNG + Heatmap PNG saved to disk
python fmea_analyzer.py --input my_fmea.csv --charts --output-dir reports/
```

Terminal output shows the same summary metrics and ranked table as the web app, with Red/Yellow/Green rendered as ANSI color codes.

---

## 9. How to Use the Tool — User Guide

### Step-by-Step Usage: Web App

**Step 1: Open the tool**  
Go to: [https://fmea-risk-analyzer-mhwzcki9sdzfz5d8rbzsdn.streamlit.app/](https://fmea-risk-analyzer-mhwzcki9sdzfz5d8rbzsdn.streamlit.app/)

**Step 2: Load data**  
Choose one of:
- Click "Use Demo Dataset" to load the 30-row composite panel FMEA instantly
- Upload your own CSV/Excel file using the file uploader

**Step 3: Review the metric badges**  
The seven metric cards at the top give you an immediate summary: how many failure modes are Red (urgent), how many are Safety-critical (Severity ≥ 9), and how many require immediate action.

**Step 4: Read the ranked table**  
The table shows all failure modes sorted from highest to lowest RPN. Red rows need attention now. Scan from top to bottom — your first priority should be the Red rows in the Action Priority H category.

**Step 5: Open the Pareto chart**  
Click the "Pareto Chart" tab. Find where the cumulative line crosses 80%. These are your vital few. Share this chart in engineering reviews to justify corrective action investment.

**Step 6: Check the Heatmap**  
Click the "Risk Heatmap" tab. Look for clustering in high-Severity, high-Occurrence cells. This reveals patterns that raw RPN numbers don't show directly.

**Step 7: Use filters (optional)**  
If you want to focus the analysis:
- Drag the RPN slider to 100 to see only high-risk items
- Toggle "Severity ≥ 9 only" to see only safety-critical failures

**Step 8: Export**  
Click "Download Excel" for a formatted workbook to share with your team. Click "Download PDF" for a ready-to-present report.

### Complete Example: Composite Panel Aerospace FMEA

**Context:** You are the quality engineer for a composite panel manufacturing line producing CFRP parts for an aircraft interior. The process has 11 steps and 30 identified failure modes.

**Input:** Load the demo dataset (`data/composite_panel_fmea_demo.csv`).

**Results (demo dataset):**
- Total failure modes: 30
- Red (immediate action): 19
- Yellow (action recommended): 9
- Green (monitor): 2
- High RPN (>100): 14
- Severity ≥ 9: 8
- Action Priority H: 8

**Top 3 failure modes by RPN:**
1. **Scanner calibration drift — missed defect** (NDI step) — RPN 360, S=10, O=2, D=3 → 🔴 Red
2. **NDI finding not dispositioned** (NDI step) — RPN 162, S=9, O=2, D=3 → 🔴 Red  
3. **Temperature overshoot during cure** (Autoclave Cure) — RPN 160, S=8, O=2, D=4 → 🔴 Red

**Corrective action focus:** The Pareto chart ranks failure modes from highest to lowest RPN. In this dataset, the top 6 failure modes (20% of total) account for approximately 29% of total RPN. Use the cumulative % line on the chart to identify where to concentrate corrective action resources.

### Best Practices for Users

1. **Calibrate scores carefully.** RPN is only as accurate as the S/O/D scores entered. Use the AIAG FMEA-4 scale tables (in Section 2 of this guide) as reference when assigning scores.

2. **Don't ignore low-RPN safety failures.** A failure mode with S=9 but O=1 and D=1 gives RPN=9 — but the Severity ≥ 9 flag ensures it's surfaced. Trust the flags, not just the RPN number.

3. **Use the Pareto to prioritize corrective actions.** Don't try to fix everything at once. The Pareto chart tells you where to spend engineering time first for maximum risk reduction.

4. **Re-run FMEA after corrective actions.** Once a corrective action reduces the Occurrence or improves Detection, re-enter updated scores and re-run the analysis to verify the risk tier has moved from Red to Yellow or Green.

5. **Use the CSV template for new FMEAs.** `data/fmea_input_template.csv` has the correct column headers pre-populated. Start there to avoid schema errors.

### Common Mistakes to Avoid

| Mistake | Consequence | Correct Approach |
|---|---|---|
| Leaving S/O/D cells blank | Validation error on upload | All S, O, D fields are required — use a score of 1 if truly negligible |
| Entering S/O/D as text (e.g., "high") | Validation error | Use integer 1–10 only |
| Confusing Detection scale direction | Underestimating detection risk | Low D = good detection; High D = poor detection |
| Ignoring Severity ≥ 9 flags because RPN is low | Missing safety-critical items | Always act on all Severity ≥ 9 failures regardless of RPN |
| Using RPN ranking alone | Missing low-frequency catastrophic failures | Also check Flag_High_Severity and Flag_Action_Priority_H columns |

---

## 10. Deployment & Setup

### How the Project is Deployed

The application is deployed on **Streamlit Community Cloud** (free tier):

1. Code lives in a public GitHub repository at `github.com/Siddardth7/fmea-risk-analyzer`
2. Streamlit Cloud connects directly to the GitHub repository
3. When code is pushed to `main`, Streamlit Cloud automatically redeploys within minutes
4. The app runs at the public URL — no server management required

**Configuration file:** `.streamlit/config.toml` sets the visual theme (dark/light mode, primary colors). This is read by Streamlit Cloud on startup.

**Dependencies:** `requirements.txt` lists all pinned package versions:
```
streamlit==1.56.*
plotly==6.6.*
pandas==3.0.*
numpy==2.4.*
openpyxl==3.1.*
fpdf2==2.8.*
matplotlib==3.10.*
```

### Running Locally

```bash
# 1. Clone the repository
git clone https://github.com/Siddardth7/fmea-risk-analyzer.git
cd fmea-risk-analyzer

# 2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate       # Mac/Linux
# or: venv\Scripts\activate    # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the Streamlit app
streamlit run app.py
# Opens automatically at http://localhost:8501

# 5. Or run the CLI tool
python fmea_analyzer.py --input data/composite_panel_fmea_demo.csv
```

### Running Tests

```bash
# Run the full test suite
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_rpn_engine.py -v

# Run with coverage report
python -m pytest tests/ --cov=src
```

Expected output: **78 tests passing**.

---

## 11. Real-World Applications

### Manufacturing and Aerospace

The demo dataset is modeled on a real aerospace scenario: manufacturing CFRP (Carbon Fiber Reinforced Polymer) composite panels. This type of FMEA would be conducted by a Tier-2 aerospace supplier producing structural panels for Boeing or Airbus programs. The AS9100 quality standard requires PFMEA documentation before first article approval.

**Process steps in the demo:**
- **Prepreg Layup:** Manual fiber placement; risk of ply misalignment, wrong ply count, out-of-life material
- **Vacuum Bagging:** Bag integrity; risk of leaks, sealant failure, breather cloth blockage
- **Autoclave Cure:** Temperature/pressure control; risk of cure cycle deviation, thermocouple failure
- **Demolding:** Part extraction; risk of tool adhesion, edge delamination
- **Non-Destructive Inspection (NDI):** Ultrasonic scanning; risk of calibration drift, missed defects
- **Assembly:** Fastening and bonding; risk of overtorque, adhesive failures

### Automotive Manufacturing

IATF 16949 (the automotive quality standard) mandates PFMEA for all manufacturing processes supplying parts to automotive OEMs. The same tool and workflow apply directly — just swap the process steps and failure modes. Common automotive scenarios:

- **Stamping process FMEA:** Failure modes like die misalignment, material thickness variation, burring
- **Welding FMEA:** Fusion defects, porosity, dimensional distortion
- **Paint shop FMEA:** Adhesion failures, contamination, color mismatch

### Medical Device Manufacturing

ISO 13485 and FDA Design Controls require risk analysis for medical device manufacturing. FMEA is the primary tool. The same S/O/D framework applies, though severity scores reflect patient harm rather than customer dissatisfaction.

### Quality Engineering and Continuous Improvement

Beyond manufacturing, FMEA logic applies to any process where failures have consequences:

- **Software development:** Failure mode = bug type; Effect = user impact; Detection = testing coverage
- **Supply chain:** Failure mode = supplier delivery failure; Effect = production line stop
- **Healthcare:** Failure mode = medication dispensing error; Effect = patient harm

---

## 12. Limitations

### What the Tool Does Not Handle Well

**1. The Full AIAG 5th Edition Action Priority Table**  
The official AP system uses a 3-dimensional S×O×D lookup table with company-specific customization. This tool uses a simplified threshold-based approximation (RPN ≥ 200 OR Severity ≥ 9). For organizations that have implemented the full AP table, the tool's `Flag_Action_Priority_H` output may not exactly match their classification.

**2. Multi-User Collaboration**  
There is no database or user accounts. Each browser session is independent. If two engineers are working on the same FMEA simultaneously, they cannot see each other's changes. The tool is designed for one engineer to upload, analyze, and export — not for real-time collaborative editing.

**3. FMEA History and Versioning**  
The tool does not store historical FMEA analyses. Each session starts fresh. Engineers who want to track how RPN scores change over time (before/after corrective actions) must manage their own file versions externally.

**4. Design FMEA (DFMEA)**  
The tool is built specifically for Process FMEA. Design FMEA has different column requirements and some different scoring criteria. The current schema and validation are PFMEA-specific.

**5. Large Datasets**  
The tool has been tested with up to ~100 rows. Very large FMEAs (500+ failure modes) may encounter Streamlit display performance limitations, particularly with the styled table rendering.

**6. Score Calibration Guidance**  
The tool validates that scores are in [1–10] range but cannot verify that the scores are *appropriate*. A team that consistently over- or under-rates Occurrence will produce inaccurate RPN rankings regardless of how well the tool works.

---

## 13. Improvements & Future Scope

### Near-Term Feature Ideas

**Database persistence:** Store FMEA analyses in a lightweight database (SQLite or PostgreSQL on Supabase) so users can retrieve previous analyses and track changes over time.

**Before/After comparison:** Allow uploading two FMEA versions and generate a diff showing which failure modes changed tier (Red → Yellow, etc.) after corrective actions were implemented.

**Full AIAG 5th Edition AP table:** Implement the complete 3D S×O×D lookup matrix rather than the simplified threshold approximation, making the `Flag_Action_Priority_H` output exactly compliant with the 2019 standard.

**Design FMEA (DFMEA) support:** Extend the schema and validation logic to handle Design FMEA column structures.

**Corrective action tracking:** Add a notes column where engineers can record planned corrective actions and target completion dates, then track progress.

### Enterprise/Production-Grade Features

**Authentication and access control:** User login (OAuth/SSO) so teams can maintain private FMEAs with role-based access (view-only vs. edit).

**API layer:** A REST API (`/analyze`, `/export-pdf`, `/export-excel`) so the FMEA engine can be called programmatically from other tools (PLM systems, ERP integrations, CI/CD pipelines for software FMEAs).

**Real-time collaboration:** WebSocket-based multi-user sessions where multiple engineers see the same FMEA simultaneously with live updates.

**Audit trail:** Log every change to S/O/D scores with timestamp and user, satisfying AS9100 and IATF 16949 record-keeping requirements.

**Custom scoring scales:** Allow companies to upload their own S/O/D scale definitions rather than using the standard AIAG scales.

### Scalability Considerations

The current architecture (Streamlit + pandas in-memory) scales well for single-user sessions with up to ~500 rows. For enterprise use with thousands of users and large datasets:

- Move from Streamlit to FastAPI backend + React frontend
- Replace in-memory pandas with database-backed data layer
- Add Redis caching for chart generation
- Deploy on Kubernetes rather than Streamlit Cloud

---

## 14. Key Talking Points — For Presentation

### 1-Minute Pitch

"I built a web application that automates the Failure Mode and Effects Analysis workflow used across aerospace, automotive, and manufacturing. Engineers currently do this manually in Excel — calculating risk scores, sorting rows, applying industry standards by hand. My tool does all of that automatically: you upload a CSV, and in seconds you get a ranked risk table, an interactive Pareto chart showing where 80% of your risk is concentrated, and a PDF report ready to present. It's deployed live and built to the AIAG FMEA-4 standard."

### 3-Minute Explanation

"FMEA is a risk analysis technique required by aerospace (AS9100), automotive (IATF 16949), and medical device standards. For every step in a manufacturing process, engineers rate three things on a 1–10 scale: how severe is the failure, how often does it occur, and how well can you detect it before it reaches the customer. Multiply those three numbers and you get the Risk Priority Number — your risk score.

The problem is that this entire workflow is done manually in Excel spreadsheets, which is slow, error-prone, and produces no useful visualization. My tool automates it completely.

The core engine in `rpn_engine.py` validates your data, calculates RPNs, and applies three mandatory flags from the AIAG standard — including a safety rule that flags dangerous failures even if their RPN looks low. Then it sorts everything by risk tier: Red means act now, Yellow means review, Green means monitor.

The web app adds interactive Pareto and heatmap visualizations, live filters, and one-click PDF and Excel export. It's deployed on Streamlit Cloud — anyone can use it right now at the link in the README."

### 5-Minute Deep Dive

Use the 3-minute explanation, then add:

"Let me show you something interesting about the math. Two failure modes can have the same RPN but represent completely different risks. S=10, O=1, D=1 gives RPN=10 — a catastrophic failure that almost never happens and is easy to detect. But S=2, O=5, D=1 also gives RPN=10 — a minor failure that happens often and is easy to catch. A naive RPN-only system treats these identically. That's why the AIAG standard added the Severity ≥ 9 mandatory flag — and why my tool enforces it.

On the architecture side: I separated the processing logic from the UI completely. The `rpn_engine.py` module knows nothing about Streamlit — it just takes DataFrames in and returns DataFrames out. That's why I could add a CLI interface with only 200 lines of additional code, and why I can write 61 pytest tests against the engine logic without touching the UI.

The export system shows the same principle: `exporter.py` takes the analyzed DataFrame and Plotly figures, builds openpyxl workbooks and fpdf2 PDFs in memory, and returns raw bytes — which Streamlit's download button can serve directly to the browser.

The whole project was built in 4 weeks, 2 hours a day, with a documented roadmap tracking every feature as a GitHub issue. That structure — planning upfront, building incrementally, testing each layer — is something I'd apply to any engineering project."

---

## 15. FAQ Section

### General Questions

**Q: What industries use FMEA?**  
A: FMEA is mandatory in automotive (IATF 16949), aerospace (AS9100), medical devices (ISO 13485), and defense (MIL-STD-1629A). It is also widely used in semiconductor manufacturing, oil and gas, and nuclear power — anywhere the consequences of failure are significant.

**Q: What does AIAG stand for?**  
A: Automotive Industry Action Group — the organization that publishes the FMEA reference manual standard. The FMEA-4 (4th Edition, 2008) is the most widely referenced version; the 5th Edition (2019, published jointly with VDA, the German automotive association) introduced the Action Priority system.

**Q: Is this a real industry tool or a demo?**  
A: It implements real AIAG FMEA-4 standards and the calculations are mathematically correct. A quality engineer could legitimately use this to analyze a real FMEA dataset. It lacks some enterprise features (user accounts, audit trails, collaboration) that a production enterprise tool would have.

### Technical Questions

**Q: Why did you use Streamlit instead of Flask or Django?**  
A: Streamlit is purpose-built for data applications and eliminates the need to write frontend HTML/CSS/JavaScript. For a data-centric tool like this, Streamlit lets you go from Python analysis code to deployed web app with minimal overhead. Flask/Django would add significant frontend development effort without adding value to the core analytical functionality.

**Q: Why pandas instead of a database?**  
A: FMEA datasets are small by nature — typically 30–200 rows. Pandas handles this in-memory with zero infrastructure overhead, no SQL queries to write or optimize, and simple DataFrame operations that are easy to test. For a single-user web app analyzing engineering spreadsheets, pandas is the right tool.

**Q: Why did you separate visualizer.py and plotly_charts.py?**  
A: `visualizer.py` uses matplotlib for the CLI tool — matplotlib produces static PNG files, which is what the `--charts` flag needs. `plotly_charts.py` uses Plotly for the Streamlit app — Plotly produces interactive HTML-based charts with hover tooltips that Streamlit can render natively. The two serve different output formats and can't share implementations.

**Q: How does the PDF export work?**  
A: The `fpdf2` library generates the PDF structure (text, tables, layout). For the chart pages, matplotlib renders the Pareto chart and risk heatmap to PNG images, written to temporary files, embedded as images in the PDF, then the temp files are deleted. The final PDF is returned as bytes streamed directly to the browser.

**Q: What happens if a user uploads a malformed file?**  
A: `validate_input()` catches four categories of errors before any calculation runs: empty files, missing columns, null values in S/O/D, and out-of-range values. Each raises a `ValueError` with a specific message that identifies the problem (e.g., "Column 'Severity' contains null values in rows with ID: [3, 7, 12]"). The Streamlit UI displays this as a red error banner.

### Methodology Questions

**Q: Why is the Detection scale counterintuitive?**  
A: The AIAG scale uses 1 = "will almost certainly be detected" and 10 = "absolutely no detection possible." So a high Detection score is bad, not good. This is intentional — higher numbers always mean higher risk contribution, which keeps the formula intuitive: higher S, O, or D always increases RPN.

**Q: Why 80% as the Pareto threshold?**  
A: The 80/20 rule (Pareto Principle) — approximately 80% of effects come from 20% of causes — was applied to quality engineering by Joseph Juran in the 1950s and is now standard practice in Six Sigma and lean manufacturing. The 80% cumulative RPN threshold is the most widely cited cutoff for FMEA prioritization.

**Q: Can an RPN of 1,000 ever be acceptable?**  
A: No. RPN = 1,000 requires S=10, O=10, D=10: a catastrophic failure that is certain to occur and completely undetectable. Any failure mode at this level represents a fundamental process or design failure and would require immediate halt and redesign, not just corrective action planning.

**Q: Why does the tool use RPN ≥ 200 for Action Priority H instead of the full AIAG table?**  
A: The full AIAG FMEA 5th Edition Action Priority table has ~1,000 cells and requires company-specific customization. For a portfolio tool, implementing a conservative threshold (RPN ≥ 200) that approximates the "High" tier intent is documented in `docs/ASSUMPTIONS_LOG.md` as an accepted engineering tradeoff. It is conservative — it may flag some items as "H" that the full table would classify "M," which is safer than the reverse.

**Q: Is RPN the best way to measure risk?**  
A: It is the most widely used metric, but it has known limitations. The main one: multiplication of three different scales produces ambiguous results (two completely different failure profiles can produce the same RPN). This is why AIAG introduced the Action Priority system in 2019 as a supplement. This tool addresses the main RPN weakness by adding the mandatory Severity ≥ 9 flag, which catches high-consequence failures that low Occurrence and Detection scores would otherwise hide.

---

*Document generated: April 2026*  
*Engineering reference: AIAG FMEA-4 (4th Edition) + AIAG/VDA FMEA Handbook (5th Edition, 2019)*
