# SPC Manufacturing Quality Dashboard

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red)
![Status](https://img.shields.io/badge/Status-Local%20Build%20Ready-brightgreen)

A manufacturing-focused Streamlit application for Statistical Process Control across composites layup, autoclave curing, and aerospace machining workflows. The app combines classical SPC math with an interactive live simulator so process behavior is visible instead of buried in tables.

## Current Status

- GitHub: `Siddardth7/manufacturing-spc-dashboard`
- Live Demo: pending Streamlit Cloud deployment
- Local verification: `74` automated tests passing

## What The App Includes

- Multi-page Streamlit interface
- Variables and attributes control charts
- Western Electric and Nelson rule detection
- Cp, Cpk, Pp, and Ppk capability analysis
- Shapiro-Wilk normality check
- Real-time disturbance simulation with mean shift, spike, and drift injection
- Plotly-based interactive visualizations

## Implemented Chart Types

- `Xbar-R`
- `Xbar-S`
- `I-MR`
- `p`
- `u`

## Standards Context

- AIAG SPC Reference Manual, 4th Edition
- Western Electric run rules
- Nelson run rules
- Common aerospace capability threshold reference: `Cpk >= 1.33`

## Project Structure

```text
manufacturing-spc-dashboard/
├── app.py
├── data/
│   └── demo_composites_aerospace.csv
├── pages/
│   ├── 1_Control_Charts.py
│   ├── 2_Process_Capability.py
│   └── 3_Live_Simulation.py
├── src/
│   ├── simulation/
│   │   └── engine.py
│   ├── spc_engine/
│   │   ├── capability.py
│   │   ├── constants.py
│   │   ├── control_charts.py
│   │   └── rule_detection.py
│   └── visualizer.py
├── tests/
│   ├── test_capability.py
│   ├── test_control_charts.py
│   ├── test_data_generator.py
│   └── test_rule_detection.py
└── requirements.txt
```

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Start the app with `streamlit run app.py`.
4. Open the local URL shown by Streamlit.

## Demo Dataset

The bundled dataset covers five manufacturing scenarios:

- `ply_thickness`: composites layup, `Xbar-R`
- `autoclave_temp`: curing temperature, `I-MR`
- `hole_diameter`: aerospace machining, `Xbar-S`
- `reject_proportion`: inspection reject rate, `p`
- `surface_defects`: defects per unit area, `u`

## CSV Schema

The demo CSV uses these columns:

- `stream`: logical dataset identifier
- `parameter`: display label
- `chart_type`: recommended control chart
- `subgroup`: subgroup or sample index
- `value`: measurement or count value
- `sample_size`: subgroup size or opportunity size
- `lsl`: lower spec limit when available
- `usl`: upper spec limit when available

## Verification

Local verification commands used during implementation:

```bash
pytest tests -v
python3 -m py_compile app.py pages/1_Control_Charts.py pages/2_Process_Capability.py pages/3_Live_Simulation.py
streamlit run app.py --server.headless true --browser.gatherUsageStats false
```

## Notes

- The live demo URL should be added here after Streamlit Cloud deployment.
- External publication steps such as deployment, tagging, and profile pinning still need to be completed outside this local repo workflow.
