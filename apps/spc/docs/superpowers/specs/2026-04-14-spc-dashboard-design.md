# SPC Manufacturing Quality Dashboard — Design Spec
**Date:** 2026-04-14
**Author:** Siddardth | M.S. Aerospace Engineering, UIUC
**Target Roles:** Manufacturing Quality Engineer, Process Engineer (eVTOL / Composites)
**Status:** Approved — ready for implementation planning

---

## 1. Project Summary

A production-grade, multi-page Streamlit web application implementing Statistical Process Control (SPC) for composites and aerospace machining processes. The dashboard combines control charts, process capability analysis, and a live simulation mode with real-time disturbance injection. Deployed on Streamlit Cloud with a live URL for resume and LinkedIn.

**What makes this different from a typical SPC portfolio project:**
- Live simulation mode — control charts update in real time, disturbance injection triggers visible rule violations
- Dual rule engine — Western Electric (AIAG) and Nelson rules, user-toggled in sidebar
- Domain-specific demo data — composites layup + autoclave cure + aerospace machining parameters, directly relevant to eVTOL/composites manufacturing roles
- Multi-page layout — three dedicated pages, more polished than a single-page Streamlit app

---

## 2. Architecture

**Pattern:** SPC engine as a standalone pure-Python library + Streamlit as a thin UI layer. Same separation-of-concerns pattern as the FMEA Risk Analyzer.

```
manufacturing-spc-dashboard/
├── app.py                          # Streamlit entry point (multi-page router)
├── pages/
│   ├── 1_Control_Charts.py         # X̄-R, X̄-S, I-MR, p, c, u chart page
│   ├── 2_Process_Capability.py     # Cp, Cpk, Pp, Ppk + distribution page
│   └── 3_Live_Simulation.py        # Real-time simulation page
├── src/
│   ├── spc_engine/
│   │   ├── control_charts.py       # UCL/LCL/CL calculations per chart type
│   │   ├── rule_detection.py       # Western Electric + Nelson rule engines
│   │   ├── capability.py           # Cp, Cpk, Pp, Ppk, normality test
│   │   └── data_generator.py       # Demo dataset (composites + machining params)
│   ├── simulation/
│   │   └── engine.py               # SimulationEngine state machine
│   └── visualizer.py               # All Plotly chart builders (pure functions)
├── tests/
│   ├── test_control_charts.py
│   ├── test_rule_detection.py
│   └── test_capability.py
├── data/
│   └── demo_composites_aerospace.csv
├── docs/
│   ├── EXECUTION_ROADMAP.md
│   └── superpowers/specs/          # This file
├── requirements.txt
└── README.md
```

**Data flow:**
`data_generator` or CSV upload → `spc_engine` (pure math, no Streamlit) → `visualizer` (pure Plotly, no Streamlit) → Streamlit pages (render only, no logic)

`SimulationEngine` holds process state in `st.session_state`, appends new subgroups on each rerun cycle, and pushes data through the same engine/visualizer stack.

---

## 3. SPC Engine

### 3.1 Control Charts

Six chart types covering variables and attributes data:

| Chart | Use Case | Demo Parameter |
|-------|----------|---------------|
| X̄-R | Variables, small subgroups (n=2–9) | Ply thickness (composites layup) |
| X̄-S | Variables, larger subgroups (n≥10) | Cure temperature — autoclave (°C) |
| I-MR | Individual measurements | Bond line adhesive thickness (mm) |
| p-chart | Proportion defective, variable n | Visual inspection reject rate |
| c-chart | Defect count, fixed n | Porosity indications per panel |
| u-chart | Defect count, variable n | Surface defects per unit area |

**Constants:** AIAG standard A2, D3, D4, d2, E2 constants hardcoded per subgroup size. Every constant has a source comment referencing AIAG SPC Reference Manual, 4th Ed.

### 3.2 Rule Detection

Dual rule engine, user-toggled via sidebar radio button:

**Western Electric Rules (4 rules) — AIAG SPC Reference Manual:**
1. 1 point beyond ±3σ
2. 2 of 3 consecutive points beyond ±2σ (same side)
3. 4 of 5 consecutive points beyond ±1σ (same side)
4. 8 consecutive points on same side of centerline

**Nelson Rules (8 rules) — Nelson 1984, Journal of Quality Technology:**
1–4: Same as Western Electric
5. 6 consecutive points trending up or down
6. 14 consecutive points alternating up/down
7. 15 consecutive points within ±1σ (stratification)
8. 8 consecutive points outside ±1σ on both sides (mixture)

**Violation rendering:** Red markers on the Plotly chart. Hover tooltip names the exact rule (e.g., "Nelson Rule 5: 6 consecutive trending up").

### 3.3 Capability Analysis

Per AIAG SPC Reference Manual 4th Ed.:

| Index | Formula | Interpretation |
|-------|---------|---------------|
| Cp | (USL−LSL) / 6σ̂ | Potential capability (spread) |
| Cpk | min[(USL−x̄)/3σ̂, (x̄−LSL)/3σ̂] | Actual capability (centering) |
| Pp | (USL−LSL) / 6σ | Long-term potential |
| Ppk | min[(USL−x̄)/3σ, (x̄−LSL)/3σ] | Long-term actual |

Where σ̂ = R̄/d2 (short-term, within-subgroup) and σ = sample std dev (long-term, overall).

**Color-coded gauge (AIAG thresholds):**
- Cpk < 1.00 → Red (process not capable)
- 1.00 ≤ Cpk < 1.33 → Yellow (marginally capable)
- Cpk ≥ 1.33 → Green (capable — AS9100/IATF 16949 minimum)

**Additional output:** Shapiro-Wilk normality test p-value displayed. If p < 0.05, a warning is shown: "Non-normal distribution detected — capability indices assume normality."

---

## 4. Live Simulation Engine

`SimulationEngine` is a class stored in `st.session_state`. It is a pure-Python state machine with no Streamlit imports — testable independently.

### 4.1 State
- Current process mean (μ), standard deviation (σ), subgroup size (n)
- Accumulated subgroup history (list of subgroup arrays)
- Active disturbance state (type, duration, progress)
- Selected process stream (composites / machining)

### 4.2 User Controls (sidebar)

| Control | Type | Range |
|---------|------|-------|
| Process stream | Dropdown | Composites / Aerospace Machining |
| Target μ | Number input | Composites: 0.250 mm / Machining: 10.000 mm |
| Target σ | Number input | Composites: 0.001 mm / Machining: 0.005 mm |
| Subgroup size (n) | Slider | 1–10 |
| Update interval | Slider | 0.5s – 3.0s |

### 4.3 Disturbance Injection (buttons)

| Button | Effect | Visible SPC Signal |
|--------|--------|-------------------|
| Inject Mean Shift | μ shifts +1.5σ for 10 subgroups | Points approach UCL; WE Rule 2 / Nelson Rule 5 |
| Inject Spike | Single point at μ +4σ | Immediate WE Rule 1 violation |
| Inject Drift | μ drifts linearly +2σ over 15 subgroups | Nelson Rule 5 (6 consecutive trending) |
| Reset Process | Returns to in-control baseline | Chart stabilizes, no violations |

### 4.4 Rendering Loop
`st.rerun()` + `time.sleep(interval)` drives updates. Each cycle:
1. `engine.step()` → generates one new subgroup
2. Engine recalculates UCL/LCL/CL on full window
3. `visualizer.build_control_chart()` returns updated Plotly figure
4. `st.plotly_chart()` renders it (last 50 subgroups visible, scrolling window)

---

## 5. Demo Dataset

Five process streams in `demo_composites_aerospace.csv` — covering all 6 chart types:

| Stream | Parameter | Spec Limits | Chart Type | Subgroups |
|--------|-----------|------------|------------|-----------|
| Composites Layup | Ply thickness (mm) | LSL=0.245, USL=0.255 | X̄-R, n=5 | 25 |
| Autoclave Cure | Temperature (°C) | LSL=175, USL=185 | I-MR | 30 |
| CNC Machining | Hole diameter (mm), n=12/subgroup | LSL=9.985, USL=10.015 | X̄-S | 20 |
| Final Inspection | Proportion defective panels | — | p-chart | 25 (variable n) |
| Panel Inspection | Surface defects/m² | USL=3.0 | u-chart | 20 (variable n) |

Note: c-chart (fixed-n defect count) is accessible via CSV upload with fixed sample size; demo focuses on u-chart as the more general attributes case.

Values generated to produce a realistic SPC story: process starts in-control, drifts slightly out in the last 8 subgroups of the ply thickness stream — giving the audience something to notice immediately.

---

## 6. Testing Strategy

Target: 50+ unit tests. No Streamlit UI tests — pages are thin renderers.

| File | What is tested | Target count |
|------|---------------|-------------|
| `test_control_charts.py` | UCL/LCL/CL math per chart type; AIAG constants correct | ~18 tests |
| `test_rule_detection.py` | Every WE + Nelson rule fires on a rule-violating sequence; no false positives on clean data | ~20 tests |
| `test_capability.py` | Cp/Cpk/Pp/Ppk formulas; unilateral spec limits; Cpk < 0 when mean outside spec; normality flag | ~15 tests |

All tests use `pytest`. Every flagging threshold and formula has a comment referencing AIAG SPC Reference Manual, 4th Ed. or Nelson (1984).

---

## 7. Deployment

- **Platform:** Streamlit Cloud (free tier, same as FMEA)
- **Config:** `.streamlit/config.toml` — wide layout, page title "SPC Manufacturing Quality Dashboard"
- **Requirements:** `requirements.txt` with pinned versions (streamlit, plotly, pandas, numpy, scipy)
- **GitHub:** Public repo `Siddardth7/manufacturing-spc-dashboard`

---

## 8. Industry Standards Referenced

| Standard | Application in this project |
|----------|---------------------------|
| AIAG SPC Reference Manual, 4th Ed. (2005) | Control chart constants, Cp/Cpk/Pp/Ppk formulas, WE rules, Cpk ≥ 1.33 threshold |
| Nelson, L.S. (1984). "The Shewhart Control Chart — Tests for Special Causes." *Journal of Quality Technology* 16(4):238–239. | Nelson Rules 5–8 |
| AS9100 Rev D | Cpk ≥ 1.33 as minimum capability requirement for aerospace suppliers |

---

## 9. Resume Bullet (draft)

**SPC Manufacturing Quality Dashboard** | Python · Streamlit · Plotly · SciPy · pandas
[[GitHub](https://github.com/Siddardth7/manufacturing-spc-dashboard)] [[Live Demo](#)]

Built a multi-page Streamlit SPC dashboard implementing 6 control chart types (X̄-R, X̄-S, I-MR, p, c, u), dual Western Electric + Nelson rule detection engines with real-time violation flagging, and Cp/Cpk/Pp/Ppk process capability analysis per AIAG SPC Reference Manual 4th Ed. Includes a live simulation mode with disturbance injection (mean shift, spike, drift) that animates rule violations in real time — demonstrated on composites layup and autoclave cure process streams representative of eVTOL manufacturing. Deployed on Streamlit Cloud.

---

*Spec approved 2026-04-14 — Implementation planning next.*
