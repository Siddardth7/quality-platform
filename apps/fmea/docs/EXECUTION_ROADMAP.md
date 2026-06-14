# FMEA Risk Prioritization Tool — Full Execution Roadmap
### Program Manager + Engineering Lead Blueprint
**Project:** `fmea-risk-analyzer`
**Start Date:** March 26, 2026
**Launch Date:** April 23, 2026
**Owner:** Siddardth | M.S. Aerospace Engineering, UIUC
**Constraint:** 2 hours/day, remote

---

## TABLE OF CONTENTS

1. [Project Definition](#1-project-definition)
2. [System Architecture](#2-system-architecture)
3. [Work Breakdown Structure (WBS)](#3-work-breakdown-structure-wbs)
4. [Master Timeline](#4-master-timeline)
5. [Weekly Execution Plan](#5-weekly-execution-plan)
6. [Daily Execution Plan](#6-daily-execution-plan-2-hoursday)
7. [Task Tracking System](#7-task-tracking-system)
8. [Tools & Stack](#8-tools--stack)
9. [Deliverable Structure](#9-deliverable-structure-github)
10. [Quality Control System](#10-quality-control-system)
11. [Risks & Failure Points](#11-risks--failure-points)
12. [Final Launch Plan](#12-final-launch-plan)
13. [Execution Rules](#13-execution-rules)

---

## 1. PROJECT DEFINITION

### Technical Objective
Build a Python-based FMEA Risk Prioritization Tool that ingests an FMEA spreadsheet (CSV/Excel), automatically calculates RPN scores, flags critical failure modes per AIAG FMEA-4 rules, generates Pareto and heatmap visualizations, and produces an exportable report — delivered as a live Streamlit web application.

### Scope

**INCLUDED:**
- CSV/Excel FMEA file ingestion
- RPN calculation engine (Severity × Occurrence × Detection)
- AIAG FMEA-4 flagging logic (RPN > threshold, Severity ≥ 9, Action Priority)
- Pareto chart — top failure modes by RPN contribution
- Severity × Occurrence risk heatmap
- Color-coded risk ranking table (Red / Yellow / Green)
- PDF report export
- Excel report export
- Streamlit web UI (local + cloud deployed)
- Realistic composite manufacturing demo dataset (30+ failure modes)
- GitHub repository with full documentation

**EXCLUDED:**
- DFMEA (Design FMEA) — this tool targets PFMEA only
- Database / user accounts / login system
- Real-time data streaming or live manufacturing integration
- Multi-user collaboration features
- FMEA version control / change tracking
- Any paid API or paid deployment service

### Final Deliverables (What "Done" Looks Like)
1. `fmea_analyzer.py` — core CLI script, runs standalone
2. `app.py` — Streamlit web application
3. `src/rpn_engine.py` — RPN calculator + AIAG flagging module
4. `src/charts.py` — Pareto + heatmap visualization module
5. `src/exporter.py` — PDF + Excel report export module
6. `data/composite_panel_fmea_demo.csv` — demo dataset, 30+ rows
7. `docs/FMEA_methodology_notes.md` — written engineering context
8. `README.md` — recruiter-ready, with screenshots + demo GIF
9. Live Streamlit Cloud deployment URL
10. GitHub repository: `fmea-risk-analyzer` (public)

### Success Metrics
| Metric | Target |
|--------|--------|
| Demo dataset size | ≥ 30 failure modes across ≥ 5 process steps |
| RPN calculation accuracy | 100% match against manual verification (spot-check 10 rows) |
| AIAG flagging coverage | All 3 flag types implemented (RPN threshold, Severity ≥ 9, Action Priority) |
| Streamlit app load time | < 5 seconds on demo dataset |
| PDF report generation | Completes in < 10 seconds |
| GitHub stars/visibility | Public repo, README has screenshot + live demo link |
| LinkedIn engagement | Post within 48 hrs of launch |

---

## 2. SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                    fmea-risk-analyzer                        │
│                                                              │
│  ┌──────────────┐    ┌────────────────────────────────────┐  │
│  │  DATA LAYER  │    │        STREAMLIT UI LAYER           │  │
│  │              │    │                                    │  │
│  │ CSV / Excel  │───▶│  File Upload Widget                │  │
│  │ FMEA input   │    │  Ranked Table (color-coded)        │  │
│  │              │    │  Chart panels (Pareto + Heatmap)   │  │
│  │ Demo dataset │    │  Export buttons (PDF / Excel)      │  │
│  └──────────────┘    └────────────────┬───────────────────┘  │
│         │                             │                      │
│         ▼                             ▼                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              PROCESSING / LOGIC LAYER                │    │
│  │                                                      │    │
│  │  rpn_engine.py                                       │    │
│  │   ├── validate_input(df)          — schema check     │    │
│  │   ├── calculate_rpn(df)           — S × O × D       │    │
│  │   ├── flag_critical(df)           — AIAG rules       │    │
│  │   └── rank_by_rpn(df)            — sorted output    │    │
│  └─────────────────────────────────────────────────────┘    │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │          ENGINEERING ANALYSIS LAYER                  │    │
│  │                                                      │    │
│  │  charts.py                                           │    │
│  │   ├── pareto_chart(df)           — top RPN modes    │    │
│  │   └── risk_heatmap(df)           — S × O matrix     │    │
│  └─────────────────────────────────────────────────────┘    │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              OUTPUT / EXPORT LAYER                   │    │
│  │                                                      │    │
│  │  exporter.py                                         │    │
│  │   ├── export_pdf(df, charts)     — reportlab PDF    │    │
│  │   └── export_excel(df)           — openpyxl report  │    │
│  └─────────────────────────────────────────────────────┘    │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              DOCUMENTATION LAYER                     │    │
│  │                                                      │    │
│  │  README.md          — recruiter-facing entry point  │    │
│  │  FMEA_methodology_notes.md — engineering context    │    │
│  │  ASSUMPTIONS_LOG.md — engineering judgment trail    │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Layer Connections
- **Data Layer → Logic Layer:** pandas `read_csv()` / `read_excel()` feeds a validated DataFrame into `rpn_engine.py`
- **Logic Layer → Analysis Layer:** Processed + ranked DataFrame feeds chart generators in `charts.py`
- **Logic Layer → Export Layer:** `exporter.py` receives the ranked DataFrame + chart figures
- **All Layers → UI Layer:** `app.py` orchestrates all modules; Streamlit renders output in browser
- **Documentation Layer:** Standalone — written in Markdown, committed alongside code

---

## 3. WORK BREAKDOWN STRUCTURE (WBS)

```
PROJECT: fmea-risk-analyzer
│
├── PHASE 1: Foundation (Week 1)
│   ├── MODULE 1.1: Research & Schema Design
│   │   ├── TASK 1.1.1: Extract AIAG FMEA-4 flagging rules (RPN threshold, Severity ≥ 9, Action Priority)
│   │   ├── TASK 1.1.2: Define FMEA CSV input schema (column names, data types, valid ranges)
│   │   └── TASK 1.1.3: Document assumptions for RPN thresholds in ASSUMPTIONS_LOG.md
│   │
│   ├── MODULE 1.2: Demo Dataset Creation
│   │   ├── TASK 1.2.1: Draft 15 failure modes for composite panel layup process (5 process steps)
│   │   ├── TASK 1.2.2: Assign realistic S/O/D scores based on domain knowledge
│   │   └── TASK 1.2.3: Validate dataset manually (calculate RPN by hand for 5 rows)
│   │
│   └── MODULE 1.3: RPN Engine
│       ├── TASK 1.3.1: Create repo structure + requirements.txt + .gitignore
│       ├── TASK 1.3.2: Implement `validate_input(df)` — check required columns + data types
│       ├── TASK 1.3.3: Implement `calculate_rpn(df)` — RPN = S × O × D column
│       ├── TASK 1.3.4: Implement `flag_critical(df)` — AIAG rule flags as boolean columns
│       ├── TASK 1.3.5: Implement `rank_by_rpn(df)` — sort + assign color tier
│       └── TASK 1.3.6: Write unit tests for RPN engine (test_rpn_engine.py)
│
├── PHASE 2: Visualization (Week 2)
│   ├── MODULE 2.1: Pareto Chart
│   │   ├── TASK 2.1.1: Implement `pareto_chart(df)` using Plotly — bar + cumulative % line
│   │   ├── TASK 2.1.2: Add color bands (Red ≥ 80% cumulative, Yellow 80–95%, Green < 95%)
│   │   └── TASK 2.1.3: Test with demo dataset, verify top-N logic
│   │
│   ├── MODULE 2.2: Risk Heatmap
│   │   ├── TASK 2.2.1: Implement `risk_heatmap(df)` — Severity (y) × Occurrence (x) matrix
│   │   ├── TASK 2.2.2: Color cells by RPN zone (red/amber/green per AIAG color logic)
│   │   └── TASK 2.2.3: Annotate cells with failure mode count per zone
│   │
│   ├── MODULE 2.3: Dataset Expansion
│   │   ├── TASK 2.3.1: Expand demo dataset from 15 → 30 rows (add bagging, autoclave, inspection steps)
│   │   └── TASK 2.3.2: Verify expanded dataset produces meaningful Pareto (no flat distribution)
│   │
│   └── MODULE 2.4: Integration
│       ├── TASK 2.4.1: Wire charts.py to accept ranked DataFrame from rpn_engine.py
│       └── TASK 2.4.2: Run end-to-end CLI test: CSV in → ranked table + charts out
│
├── PHASE 3: Streamlit Application (Week 3)
│   ├── MODULE 3.1: App Skeleton
│   │   ├── TASK 3.1.1: Create app.py with Streamlit layout (sidebar + main panel)
│   │   ├── TASK 3.1.2: Add file upload widget (CSV/Excel, with fallback to demo dataset)
│   │   └── TASK 3.1.3: Display raw uploaded table in app
│   │
│   ├── MODULE 3.2: Analysis Display
│   │   ├── TASK 3.2.1: Pipe uploaded file → rpn_engine → display ranked color-coded table
│   │   ├── TASK 3.2.2: Embed Pareto chart in main panel
│   │   ├── TASK 3.2.3: Embed risk heatmap in main panel
│   │   └── TASK 3.2.4: Add sidebar filters (min RPN slider, Severity threshold toggle)
│   │
│   ├── MODULE 3.3: Critical Flags Panel
│   │   ├── TASK 3.3.1: Add "Critical Items" section — filtered table showing flagged rows only
│   │   └── TASK 3.3.2: Add flag badges/icons for each AIAG rule triggered
│   │
│   └── MODULE 3.4: End-to-End Testing
│       ├── TASK 3.4.1: Test with demo dataset (full flow: upload → analysis → charts)
│       ├── TASK 3.4.2: Test with edge case: all Severity = 1 (no critical flags)
│       └── TASK 3.4.3: Test with edge case: malformed CSV (missing columns)
│
└── PHASE 4: Export + Deploy + Launch (Week 4)
    ├── MODULE 4.1: Report Export
    │   ├── TASK 4.1.1: Implement `export_pdf()` — cover page, ranked table, Pareto chart, critical items list
    │   ├── TASK 4.1.2: Implement `export_excel()` — color-formatted ranked table + metadata sheet
    │   └── TASK 4.1.3: Wire both exports to Streamlit download buttons
    │
    ├── MODULE 4.2: Documentation
    │   ├── TASK 4.2.1: Write README.md (full structure defined in Section 9)
    │   ├── TASK 4.2.2: Write docs/FMEA_methodology_notes.md (AIAG FMEA-4 summary, RPN logic, Action Priority)
    │   └── TASK 4.2.3: Finalize ASSUMPTIONS_LOG.md with all threshold decisions
    │
    ├── MODULE 4.3: Deployment
    │   ├── TASK 4.3.1: Push final code to GitHub (public repo)
    │   ├── TASK 4.3.2: Create requirements.txt and test clean install in fresh venv
    │   ├── TASK 4.3.3: Deploy to Streamlit Community Cloud (connect GitHub repo)
    │   └── TASK 4.3.4: Verify live deployment works with demo dataset
    │
    └── MODULE 4.4: Launch Assets
        ├── TASK 4.4.1: Capture 3 screenshots (ranked table, Pareto, heatmap)
        ├── TASK 4.4.2: Record 15-second screen recording GIF (use LICEcap or Kap)
        ├── TASK 4.4.3: Update README with live demo URL + screenshots + GIF
        └── TASK 4.4.4: Draft LinkedIn post text (template in Section 12)
```

---

## 4. MASTER TIMELINE

**Total Duration:** 4 weeks (29 days)
**Start:** March 26, 2026 (Thursday)
**Launch:** April 23, 2026 (Thursday)

```
WEEK 1  Mar 26 – Apr 1   ▓▓▓▓▓▓▓  FOUNDATION: Research + Schema + RPN Engine
WEEK 2  Apr 2  – Apr 8   ▓▓▓▓▓▓▓  VISUALIZATION: Charts + Dataset Expansion
WEEK 3  Apr 9  – Apr 15  ▓▓▓▓▓▓▓  STREAMLIT APP: UI Build + Integration
WEEK 4  Apr 16 – Apr 22  ▓▓▓▓▓▓▓  EXPORT + DEPLOY + DOCUMENTATION
LAUNCH  Apr 23            ★        GITHUB PUBLIC + STREAMLIT LIVE + LINKEDIN POST
```

### Hard Deadlines

| Deadline | Date | What Must Be Done |
|----------|------|-------------------|
| **Checkpoint 1** | April 1, 2026 | RPN engine complete, demo dataset (15 rows), unit tests passing |
| **Checkpoint 2** | April 8, 2026 | Pareto + heatmap rendering correctly, demo dataset expanded to 30 rows |
| **Checkpoint 3** | April 15, 2026 | Full Streamlit app running locally, all charts embedded, edge cases tested |
| **Checkpoint 4** | April 22, 2026 | Exports working, README complete, Streamlit Cloud deployed |
| **LAUNCH** | **April 23, 2026** | GitHub public, live URL confirmed, LinkedIn post published |

> **Policy:** If a checkpoint is missed, cut scope — not the deadline. Remove a feature before delaying launch.

---

## 5. WEEKLY EXECUTION PLAN

### WEEK 1 — March 26–April 1
**Objective:** Have a working Python script that reads a composite panel FMEA CSV and outputs a ranked, flagged table.

**Deliverables to Complete:**
- AIAG FMEA-4 rules document (5 rules extracted, written in ASSUMPTIONS_LOG.md)
- FMEA CSV schema defined and validated
- Demo dataset v1 (15 rows, composite panel layup process)
- `src/rpn_engine.py` — all 4 functions implemented
- `tests/test_rpn_engine.py` — basic unit tests passing
- GitHub repo initialized, first commit pushed

**Key Risks:**
- Over-researching AIAG FMEA-4 instead of building. **Mitigation:** Cap research to Day 1 only — 2 hours max.
- RPN schema mismatch (column names inconsistent). **Mitigation:** Define schema on Day 2 before writing any code.

**Expected Output:** Running `python fmea_analyzer.py --input data/demo.csv` prints a ranked FMEA table to terminal.

---

### WEEK 2 — April 2–8
**Objective:** Visualization module complete. Pareto chart and risk heatmap render from the ranked DataFrame.

**Deliverables to Complete:**
- `src/charts.py` — `pareto_chart()` and `risk_heatmap()` implemented
- Demo dataset expanded to 30 rows
- End-to-end CLI test passes: CSV in → ranked table + 2 charts rendered
- Charts validated visually (Pareto shows 80/20 pattern, heatmap has expected red zones)

**Key Risks:**
- Plotly chart formatting takes longer than expected. **Mitigation:** Use default Plotly theme first, style later in Week 4.
- Dataset with 30 rows requires domain thought (not just copy-paste). **Mitigation:** Allocate Thursday for this specifically.

**Expected Output:** Running `python fmea_analyzer.py --input data/demo.csv --charts` opens Pareto + heatmap in browser.

---

### WEEK 3 — April 9–15
**Objective:** Streamlit app running locally with full functionality — upload, analyze, display, filter.

**Deliverables to Complete:**
- `app.py` — complete Streamlit application
- File upload → RPN analysis → ranked table displayed
- Pareto and heatmap embedded in app
- Sidebar filters working (RPN threshold, Severity flag toggle)
- Critical Items panel displaying flagged rows
- 3 edge case tests passing (normal input, no flags, malformed CSV)

**Key Risks:**
- Streamlit layout complexity (chart sizing, column layout). **Mitigation:** Use `st.columns()` simple 2-column layout, no custom CSS.
- Edge case handling adds scope creep. **Mitigation:** Only handle the 3 defined test cases — no others.

**Expected Output:** `streamlit run app.py` opens in browser, full demo dataset analysis displays correctly.

---

### WEEK 4 — April 16–22
**Objective:** Everything deployed, documented, and ready for public visibility.

**Deliverables to Complete:**
- `src/exporter.py` — PDF and Excel export working
- Download buttons wired in Streamlit app
- `README.md` — complete with screenshots, GIF, live URL, resume bullet
- `docs/FMEA_methodology_notes.md` — written
- `ASSUMPTIONS_LOG.md` — finalized
- Streamlit Community Cloud deployment live
- 3 screenshots + 1 demo GIF captured
- LinkedIn post drafted

**Key Risks:**
- reportlab PDF export is finicky (layout, image embedding). **Mitigation:** Use simple tabular layout, skip complex formatting.
- Streamlit Cloud deployment fails (dependency issue). **Mitigation:** Test `requirements.txt` clean install on Day 5 before deploying.

**Expected Output:** `https://[yourapp].streamlit.app` is live and publicly accessible.

---

## 6. DAILY EXECUTION PLAN (2 Hours/Day)

> **Format:** Day | Date | Task | Definition of Done

---

### WEEK 1: Foundation

| Day | Date | Task | Done When |
|-----|------|------|-----------|
| Thu | Mar 26 | Read AIAG FMEA-4 Action Priority rules online (free summaries). Extract: (1) RPN threshold for action required, (2) Severity ≥ 9 auto-flag rule, (3) Action Priority H/M/L logic. Write all 3 rules + sources into `docs/ASSUMPTIONS_LOG.md`. Initialize GitHub repo, push skeleton. | ASSUMPTIONS_LOG.md committed with ≥ 3 rules documented |
| Fri | Mar 27 | Define FMEA CSV input schema. Columns: `ID`, `Process_Step`, `Component`, `Function`, `Failure_Mode`, `Effect`, `Severity`, `Cause`, `Occurrence`, `Current_Control`, `Detection`, `RPN` (calculated), `Action_Priority` (calculated). Write schema to `docs/FMEA_input_schema.md`. | Schema doc committed, no ambiguous column types |
| Sat | Mar 28 | Build demo dataset v1. 15 rows across 5 composite panel process steps: Ply Cutting, Layup, Bagging, Autoclave Cure, Demold. Assign realistic S/O/D values (e.g., Bag Leak: S=9, O=3, D=4 → RPN=108). Save as `data/composite_panel_fmea_demo.csv`. | CSV has 15 rows, all S/O/D values 1–10, no blanks |
| Sun | Mar 29 | Implement `src/rpn_engine.py`: `validate_input(df)` checks required columns + dtype. `calculate_rpn(df)` adds RPN column. | Functions written, no syntax errors, `python -c "from src.rpn_engine import calculate_rpn"` runs clean |
| Mon | Mar 30 | Implement `flag_critical(df)`: adds boolean columns `Flag_High_RPN` (RPN > 100), `Flag_High_Severity` (S ≥ 9), `Flag_Action_Priority_H` (AP = High per AIAG logic). Implement `rank_by_rpn(df)`: sorts by RPN descending, adds `Risk_Tier` column (Red/Yellow/Green). | `flag_critical()` flags correct rows when tested against demo dataset by hand |
| Tue | Mar 31 | Write `tests/test_rpn_engine.py`. Test cases: (1) RPN = 9×3×4 = 108, (2) Severity=9 triggers flag, (3) Severity=1 triggers no flags, (4) Missing column raises ValueError. Run tests: `python -m pytest tests/`. | All 4 test cases pass |
| Wed | Apr 1 | Write `fmea_analyzer.py` CLI entry point: `--input` flag reads CSV, calls rpn_engine pipeline, prints ranked table to terminal with color tiers labeled. **Checkpoint 1 Review:** Verify all Week 1 deliverables complete. Push final commit. | `python fmea_analyzer.py --input data/composite_panel_fmea_demo.csv` outputs ranked table, no errors |

---

### WEEK 2: Visualization

| Day | Date | Task | Done When |
|-----|------|------|-----------|
| Thu | Apr 2 | Implement `pareto_chart(df)` in `src/charts.py`. Use Plotly: bar chart of failure modes ranked by RPN (x-axis: Failure Mode name, y-axis: RPN). Add secondary y-axis with cumulative % line. | Chart renders in browser via `fig.show()`, top 3 failure modes visible |
| Fri | Apr 3 | Add color bands to Pareto: bars colored Red (top 20% failure modes driving 80% RPN), Yellow (next tier), Green (remainder). Add chart title: "Top Failure Modes by RPN — Composite Panel Layup PFMEA". | Color coding visually correct when verified against manual RPN sort |
| Sat | Apr 4 | Implement `risk_heatmap(df)` in `src/charts.py`. Plotly heatmap: Severity (y-axis, 1–10) × Occurrence (x-axis, 1–10). Cell color = max RPN in that zone (red ≥ 200, amber 100–199, green < 100). | Heatmap renders, red cells appear in correct high-S × high-O quadrant |
| Sun | Apr 5 | Expand demo dataset from 15 → 30 rows. Add: Autoclave cure temperature deviation, resin-rich zones, ply wrinkles during bagging, delamination at demold. Verify Pareto still shows meaningful 80/20 (top 6 modes ≥ 80% RPN). | Dataset has 30 rows, Pareto 80/20 pattern confirmed visually |
| Mon | Apr 6 | Wire `charts.py` to accept output of `rpn_engine.py`. Run full pipeline test: `fmea_analyzer.py --input data/demo.csv --charts` opens both charts in browser sequentially. | Both charts open in browser, no crashes, data matches ranked table |
| Tue | Apr 7 | Write `tests/test_charts.py`. Test: (1) `pareto_chart()` returns `plotly.graph_objs.Figure`, (2) heatmap returns `Figure`, (3) both functions fail gracefully on empty DataFrame. | All chart tests pass |
| Wed | Apr 8 | **Checkpoint 2 Review.** Run full CLI end-to-end with 30-row dataset. Verify: ranked table correct, flags correct, both charts render. Fix any visual issues. Push clean commit. | All Week 2 deliverables confirmed complete, pushed to GitHub |

---

### WEEK 3: Streamlit Application

| Day | Date | Task | Done When |
|-----|------|------|-----------|
| Thu | Apr 9 | Create `app.py`. Build layout skeleton: page title, sidebar (filters), main panel (2 columns). Add file upload widget (`st.file_uploader` accepting CSV/Excel). Add "Use Demo Dataset" button as fallback. | `streamlit run app.py` opens in browser, upload widget visible, no errors |
| Fri | Apr 10 | Wire upload → rpn_engine pipeline → display ranked table with `st.dataframe()`. Apply row color styling: Red rows = `Flag_High_RPN or Flag_High_Severity`, Yellow = mid-tier RPN, Green = low. | Uploading demo CSV displays color-coded ranked table in browser |
| Sat | Apr 11 | Embed Pareto chart: `st.plotly_chart(pareto_chart(df), use_container_width=True)`. Embed heatmap below it. Verify both charts load and are interactive (hover tooltips working). | Both charts interactive in Streamlit app |
| Sun | Apr 12 | Add sidebar filters: (1) RPN threshold slider (default 100, range 50–300), (2) "Show only Severity ≥ 9" toggle. Filters must re-run analysis and update table + charts in real time. | Adjusting slider updates ranked table count; Severity toggle shows subset only |
| Mon | Apr 13 | Add "Critical Items" panel below charts: `st.expander("⚠️ Critical Failure Modes")` showing filtered table of flagged rows only. Add metric badges: `st.metric("High RPN Items", count)`, `st.metric("Severity ≥ 9 Flags", count)`. | Critical items panel shows correct row count, metric badges update with filter changes |
| Tue | Apr 14 | Test 3 edge cases: (1) Upload demo dataset — all charts and flags render correctly. (2) Upload a CSV where all Severity = 1 — confirm zero flags, inform user via `st.info()`. (3) Upload malformed CSV (missing `Severity` column) — confirm graceful error via `st.error()`. | All 3 test scenarios produce expected behavior without app crash |
| Wed | Apr 15 | **Checkpoint 3 Review.** Run full app with demo dataset. Verify: upload → ranked table → Pareto → heatmap → critical panel → filters all work. Fix any layout issues. Push clean commit tagged `v0.3-streamlit-complete`. | `streamlit run app.py` delivers full functionality end-to-end |

---

### WEEK 4: Export + Deploy + Launch

| Day | Date | Task | Done When |
|-----|------|------|-----------|
| Thu | Apr 16 | Implement `export_excel(df)` in `src/exporter.py`. Use openpyxl: Sheet 1 = ranked FMEA table with cell color fills (red/yellow/green), Sheet 2 = metadata (run date, total failure modes, flag counts). Wire to `st.download_button()` in app. | Clicking "Download Excel" in app downloads a correctly formatted .xlsx file |
| Fri | Apr 17 | Implement `export_pdf(df, fig_pareto, fig_heatmap)` in `src/exporter.py`. Use reportlab: page 1 = summary metrics + critical items table, page 2 = Pareto chart (saved as PNG first), page 3 = heatmap PNG. Wire to download button. | Clicking "Download PDF" downloads a readable PDF with table + charts |
| Sat | Apr 18 | Write `README.md` (full structure per Section 9 below). Write `docs/FMEA_methodology_notes.md`: explain RPN formula, AIAG FMEA-4 Action Priority logic, Pareto principle applied to risk, Severity ≥ 9 rule rationale. | Both docs complete, no placeholder text remaining |
| Sun | Apr 19 | Test clean install: create fresh Python 3.11 venv, `pip install -r requirements.txt`, run `streamlit run app.py`, verify everything works. Fix any dependency issues found. Finalize `requirements.txt`. | Clean install completes without errors, app runs in fresh venv |
| Mon | Apr 20 | Deploy to Streamlit Community Cloud. Steps: (1) Push final code to GitHub, (2) Go to share.streamlit.io, (3) Connect GitHub repo, set `app.py` as entry point, (4) Verify live URL loads demo dataset correctly. | Public URL `https://[name].streamlit.app` loads and displays analysis |
| Tue | Apr 21 | Capture launch assets: (1) 3 screenshots (ranked table view, Pareto chart, heatmap). (2) Record 15-second screen recording GIF using Kap (mac) or LICEcap. (3) Update README with live URL + embed screenshots + GIF. Push final README. | README shows live URL, screenshots render on GitHub, GIF plays |
| Wed | Apr 22 | **Checkpoint 4 Review.** Final QC pass: (1) Open live Streamlit URL, upload demo CSV, download both PDF + Excel. (2) Read README from a recruiter's perspective — does it answer "what does this do + why does it matter" in 30 seconds? (3) Fix any final issues. Tag release `v1.0-launch`. | Live app works, exports download correctly, README passes 30-second test |
| Thu | Apr 23 | **LAUNCH DAY.** (1) Confirm GitHub repo is public. (2) Confirm live URL is accessible. (3) Publish LinkedIn post (draft from Section 12). (4) Update resume Projects section. | LinkedIn post live, GitHub repo public, live URL confirmed working |

---

## 7. TASK TRACKING SYSTEM

### Apple Reminders (Primary System)

**List Name:** `FMEA Project`

**Format for each reminder:**
```
Title: [W1D1] AIAG FMEA-4 rules → ASSUMPTIONS_LOG.md
Date: Mar 26, 2026
Alert: 9:00 AM
Notes: Done when: ≥3 rules documented with source, committed to GitHub
```

**All 29 daily reminders — create these now:**

| Reminder Title | Due Date |
|----------------|----------|
| [W1D1] AIAG rules research → ASSUMPTIONS_LOG | Mar 26 |
| [W1D2] FMEA CSV schema → schema doc | Mar 27 |
| [W1D3] Demo dataset v1 → 15-row CSV | Mar 28 |
| [W1D4] rpn_engine: validate_input + calculate_rpn | Mar 29 |
| [W1D5] rpn_engine: flag_critical + rank_by_rpn | Mar 30 |
| [W1D6] Unit tests for rpn_engine → all pass | Mar 31 |
| [W1D7] CLI entry point + Checkpoint 1 review | Apr 1 |
| [W2D1] Pareto chart function → renders in browser | Apr 2 |
| [W2D2] Pareto color bands + title | Apr 3 |
| [W2D3] Risk heatmap function → renders in browser | Apr 4 |
| [W2D4] Expand dataset to 30 rows | Apr 5 |
| [W2D5] Wire charts to rpn_engine pipeline | Apr 6 |
| [W2D6] Chart unit tests → all pass | Apr 7 |
| [W2D7] End-to-end CLI test + Checkpoint 2 review | Apr 8 |
| [W3D1] Streamlit app skeleton + upload widget | Apr 9 |
| [W3D2] Upload → ranked table with color styling | Apr 10 |
| [W3D3] Embed Pareto + heatmap in app | Apr 11 |
| [W3D4] Sidebar filters (RPN slider + Severity toggle) | Apr 12 |
| [W3D5] Critical Items panel + metric badges | Apr 13 |
| [W3D6] 3 edge case tests → all pass | Apr 14 |
| [W3D7] Full app test + Checkpoint 3 review | Apr 15 |
| [W4D1] Excel export → download button working | Apr 16 |
| [W4D2] PDF export → download button working | Apr 17 |
| [W4D3] README + FMEA methodology notes | Apr 18 |
| [W4D4] Clean install test + finalize requirements.txt | Apr 19 |
| [W4D5] Deploy to Streamlit Community Cloud | Apr 20 |
| [W4D6] Screenshots + GIF + update README | Apr 21 |
| [W4D7] Final QC + tag v1.0-launch | Apr 22 |
| [LAUNCH] GitHub public + LinkedIn post + resume update | Apr 23 |

---

### Secondary System: Notion Kanban Board (Recommended)

**Why Notion over Trello:** Notion lets you attach notes, links, and code snippets per card — critical for logging assumptions and decisions alongside tasks. Trello is task-only.

**Database Setup:**

Create a Notion database called `FMEA Project Tracker` with these properties:

| Property | Type | Options / Notes |
|----------|------|-----------------|
| Task | Title | Short imperative task name |
| Phase | Select | Phase 1 / Phase 2 / Phase 3 / Phase 4 |
| Week | Select | W1 / W2 / W3 / W4 |
| Status | Select | Not Started / In Progress / Done / Blocked |
| Due Date | Date | Specific calendar date |
| Done When | Text | Explicit completion criteria |
| Notes | Text | Decisions, bugs, links encountered |

**Views to create:**
1. **Board view** grouped by `Status` — your daily Kanban
2. **Calendar view** by `Due Date` — timeline visibility
3. **Table view** filtered by current week — weekly focus

**Example entries:**

```
Task: rpn_engine: flag_critical + rank_by_rpn
Phase: Phase 1
Week: W1
Status: In Progress
Due Date: March 30, 2026
Done When: flag_critical() flags correct rows against manual check of demo dataset
Notes: AIAG FMEA-4 Action Priority H = RPN ≥ 200 OR Severity ≥ 9. Source: AIAG 5th Ed. summary PDF
```

```
Task: Streamlit: sidebar filters
Phase: Phase 3
Week: W3
Status: Not Started
Due Date: April 12, 2026
Done When: Adjusting RPN slider updates ranked table row count in real time
Notes: Use st.session_state to preserve filter values on re-run
```

---

## 8. TOOLS & STACK

### Programming
| Library | Version | Purpose |
|---------|---------|---------|
| `pandas` | ≥ 2.0 | DataFrame operations, CSV/Excel I/O |
| `numpy` | ≥ 1.24 | Numerical operations |
| `plotly` | ≥ 5.18 | Pareto chart + risk heatmap (interactive) |
| `streamlit` | ≥ 1.32 | Web application framework |
| `openpyxl` | ≥ 3.1 | Excel export with cell formatting |
| `reportlab` | ≥ 4.1 | PDF generation |
| `kaleido` | ≥ 0.2 | Plotly → PNG export (required for PDF embedding) |
| `pytest` | ≥ 7.4 | Unit testing |

**Python version:** 3.11 (specify explicitly in README + `.python-version` file)

### Development Environment
- **IDE:** VS Code with Python extension
- **Virtual environment:** `python -m venv venv` — activate before every session
- **Package management:** `pip` with pinned `requirements.txt`

### Version Control
- **Platform:** GitHub (public repo)
- **Branch strategy:**
  - `main` — always deployable, represents current release
  - `dev` — active development
  - Merge `dev → main` at each weekly checkpoint
- **Commit convention:** `[Phase] short description` e.g., `[W1] Add RPN flag logic + unit tests`
- **Tags:** `v0.1-rpn-engine`, `v0.2-charts`, `v0.3-streamlit`, `v1.0-launch`

### Documentation
- **README:** Markdown (GitHub-rendered)
- **Engineering notes:** Markdown in `docs/`
- **Inline code comments:** Google-style docstrings on all public functions

### Visualization
- **Pareto chart:** Plotly `go.Bar` + `go.Scatter` (dual-axis)
- **Heatmap:** Plotly `go.Heatmap`
- **Color scheme:** Red `#d32f2f`, Amber `#f57c00`, Green `#388e3c` — AIAG risk color convention

### Screen Recording (for GIF)
- **Mac:** Kap (free, open-source) — records screen area → GIF
- **Export settings:** 10 fps, max 15 seconds, width 1200px

---

## 9. DELIVERABLE STRUCTURE (GITHUB)

### Repository Folder Structure

```
fmea-risk-analyzer/
│
├── app.py                          # Streamlit application entry point
├── fmea_analyzer.py                # CLI entry point
├── requirements.txt                # Pinned dependencies
├── .gitignore                      # Python standard gitignore
├── .python-version                 # Specifies Python 3.11
├── README.md                       # Recruiter-facing main documentation
│
├── src/
│   ├── __init__.py
│   ├── rpn_engine.py               # validate_input, calculate_rpn, flag_critical, rank_by_rpn
│   ├── charts.py                   # pareto_chart, risk_heatmap
│   └── exporter.py                 # export_pdf, export_excel
│
├── data/
│   └── composite_panel_fmea_demo.csv   # 30-row aerospace demo dataset
│
├── tests/
│   ├── __init__.py
│   ├── test_rpn_engine.py
│   └── test_charts.py
│
├── docs/
│   ├── FMEA_input_schema.md        # Column definitions + valid ranges
│   ├── FMEA_methodology_notes.md   # AIAG FMEA-4 theory notes
│   ├── ASSUMPTIONS_LOG.md          # Engineering judgment log
│   └── EXECUTION_ROADMAP.md        # This document
│
├── assets/
│   ├── screenshot_table.png
│   ├── screenshot_pareto.png
│   ├── screenshot_heatmap.png
│   └── demo.gif
│
└── reports/                        # Generated outputs (gitignored)
    └── .gitkeep
```

### File Naming Conventions
- Source modules: `snake_case.py`
- Data files: `descriptive_name_vN.csv` (e.g., `composite_panel_fmea_demo.csv`)
- Screenshots: `screenshot_[view_name].png`
- Documentation: `SCREAMING_SNAKE_CASE.md` for top-level docs, `Title_Case.md` for `docs/`

### README.md Structure

```markdown
# FMEA Risk Prioritization Tool

> Python/Streamlit tool for automated FMEA analysis — calculates RPN, flags critical
> failure modes per AIAG FMEA-4, and generates Pareto + heatmap reports.

**[🚀 Live Demo](https://[yourapp].streamlit.app)** | **[GitHub](https://github.com/[user]/fmea-risk-analyzer)**

---

## What This Does
[2-sentence problem statement — cost/pain of manual FMEA]
[2-sentence solution description]

## Demo
[Embed demo.gif here]

## Screenshots
[3 screenshots: ranked table, Pareto, heatmap]

## Features
- [bulleted list, 6–8 items]

## Engineering Methodology
[3-paragraph explanation: RPN logic, AIAG FMEA-4 flagging rules, Pareto application]

## How to Run Locally
[Step-by-step with code blocks]

## Project Structure
[Folder tree]

## Demo Dataset
[Describe the composite panel layup scenario]

## Resume Bullet
> [exact resume bullet — recruiters want to copy this]

## Author
[Name, LinkedIn, GitHub]
```

---

## 10. QUALITY CONTROL SYSTEM

### Data Validation
- `validate_input(df)` must check: required columns present, S/O/D values are integers 1–10, no nulls in core columns, at least 1 row
- All edge cases tested explicitly (see Week 3 Day 6)
- Demo dataset manually verified: RPN hand-calculated for 5 rows before trusting the engine

### Engineering Rigor Simulation
- **ASSUMPTIONS_LOG.md** is mandatory. Every non-obvious decision must be logged:
  - What threshold was chosen (e.g., RPN > 100 for High flag)
  - Why that value (AIAG FMEA-4 source, or explicit engineering judgment if no standard exists)
  - What alternatives were considered
- This log is your defense when an interviewer asks: "Why did you use RPN > 100?"

### Version Control Discipline
- No direct commits to `main` after Week 1
- All development on `dev` branch
- Merge to `main` only at weekly checkpoints after self-review
- Every commit message follows: `[Phase] action verb + what changed`
- Never commit: `.env`, `venv/`, `__pycache__/`, `*.pyc`, generated reports

### Accuracy Checks
| Check | Method | Frequency |
|-------|--------|-----------|
| RPN calculation | Manual spot-check 5 rows from demo dataset | After any change to rpn_engine.py |
| Flag logic | Compare `flag_critical()` output against hand-applied AIAG rules | End of Week 1 |
| Chart accuracy | Verify Pareto top-3 matches manual sort of ranked table | End of Week 2 |
| Export accuracy | Open PDF + Excel exports, verify table matches on-screen display | End of Week 4 |

---

## 11. RISKS & FAILURE POINTS

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Scope creep: adding DFMEA support** | High | High | Explicitly excluded in Section 1. If tempted, write the idea in a `FUTURE.md` file and keep moving. |
| **reportlab PDF export complexity** | High | Medium | Ship a simple plain-text PDF first. Add chart images only if time allows. Recruiter cares about the Streamlit app, not the PDF format. |
| **Research rabbit hole on AIAG standards** | High | High | Day 1 only. Use free summaries (Quality-One, ASQ, AIAG public FAQs). Do not purchase the standard. |
| **Demo dataset lacks realism** | Medium | High | Use your actual composites manufacturing knowledge. 5 process steps, real failure modes you've seen. This is your moat. |
| **Streamlit Cloud free tier limitations** | Low | Medium | App will sleep after inactivity. This is acceptable. Note it in README. Alternative: deploy to Render free tier. |
| **Week 3 app build takes longer than 7 days** | Medium | High | Cut the sidebar filters (Section 3, Module 3.2 Task 4). Core app = upload + table + charts. Filters are enhancement, not core. |
| **Lost motivation after Week 2** | Medium | Critical | The checkpoint system exists for this. After each checkpoint, post a brief LinkedIn update: "Week 2 of 4 building my FMEA tool — charts are live." Public commitment creates accountability. |
| **Deployment breaks on launch day** | Low | High | Test Streamlit Cloud deployment on Day 5 of Week 4 (April 20), not on launch day. |

---

## 12. FINAL LAUNCH PLAN

### What to Publish
1. GitHub repo set to **Public** (confirm in Settings)
2. Live Streamlit app URL confirmed accessible
3. README includes: live URL, demo GIF, 3 screenshots, resume bullet
4. `v1.0-launch` tag on the release commit

### GitHub Optimization
- **Repository description:** `Python/Streamlit FMEA Risk Prioritization Tool — automated RPN scoring, AIAG FMEA-4 flagging, Pareto + heatmap reports for manufacturing quality workflows`
- **Topics/tags to add:** `fmea`, `quality-engineering`, `manufacturing`, `streamlit`, `python`, `risk-analysis`, `aerospace`, `pareto-chart`
- **Pin this repo** on your GitHub profile

### LinkedIn Post (Copy-Paste Ready)

```
🚀 I just deployed my FMEA Risk Prioritization Tool — here's why it matters:

Every quality/manufacturing engineer has lived this: a 200-row FMEA spreadsheet where
the most critical failure modes are buried in manual RPN calculations. Engineers spend
hours sorting, highlighting, and formatting — with inconsistent results across teams.

I built a Python/Streamlit tool that automates this in seconds:

→ Upload any FMEA spreadsheet (CSV/Excel)
→ RPN scores calculated instantly (Severity × Occurrence × Detection)
→ Critical items auto-flagged per AIAG FMEA-4 rules (Severity ≥ 9, high-RPN threshold)
→ Pareto chart identifies the 20% of failure modes driving 80% of risk
→ Risk heatmap shows Severity × Occurrence concentration zones
→ Export clean PDF/Excel report for engineering review

Built using: Python | pandas | Plotly | Streamlit | AIAG FMEA-4 methodology

Demo dataset: composite panel layup PFMEA (my composites manufacturing background)

🔗 Live app: [STREAMLIT URL]
📁 GitHub: [GITHUB URL]

#ManufacturingEngineering #QualityEngineering #FMEA #Python #Aerospace #Composites
```

### Resume Update

**Add to Projects section (place above Education):**
```
FMEA Risk Prioritization Tool | Python, Streamlit, Plotly, pandas              Apr 2026
Developed open-source Python/Streamlit FMEA Risk Prioritization Tool implementing
AIAG FMEA-4 methodology; automatically ranks failure modes by RPN, flags critical items
(Severity ≥ 9), and generates Pareto + heatmap reports — reducing manual FMEA review
time by an estimated 60% versus spreadsheet-based workflows.
GitHub: github.com/[user]/fmea-risk-analyzer | Live Demo: [streamlit URL]
```

---

## 13. EXECUTION RULES

These are not suggestions. These are the operating conditions for this project.

1. **2 hours = 2 hours.** Set a timer. When it goes off, stop — commit what you have and close the laptop. Partial progress committed daily beats 4-hour Saturday binges.

2. **Daily reminder fires at 9:00 AM.** If you haven't started by 10:00 AM, you start. No negotiation.

3. **Each day's task ends with a git commit.** Even if the code doesn't work. Commit message: `[W1D3] WIP: demo dataset draft — 15 rows, S/O/D populated`. Progress > perfection.

4. **You are not learning Python.** You already know enough Python to build this. When you're unsure of a syntax, Google it for 2 minutes and move on. Do not spend 30 minutes reading documentation about best practices.

5. **When stuck for more than 20 minutes on a bug:** move to the next task. Write a TODO comment in the code. Come back tomorrow.

6. **Scope creep is the project killer.** If you think of a feature not in this document, write it in `FUTURE.md`. Do not build it. You have 29 days.

7. **Checkpoint reviews are mandatory.** Every Wednesday at the end of 2 hours, run the full deliverable checklist for that week. If something is not done, you cut scope to compensate — you do not extend the timeline.

8. **Ship on April 23, 2026.** A deployed, documented v1.0 beats a perfect, unreleased v2.0 by any measure a recruiter or hiring manager will apply to your portfolio.

---

*Blueprint prepared March 26, 2026 — Siddardth Portfolio Engineering Project #1*
*Priority Order: FMEA Tool → Defect Classifier → Digital Twin → SPC Dashboard → Autoclave Optimizer → NCR/CAPA Engine → Lean Simulator*
