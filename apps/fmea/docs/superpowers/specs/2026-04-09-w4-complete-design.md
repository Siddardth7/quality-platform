# W4 Completion Design — FMEA Risk Analyzer
**Date:** 2026-04-09  
**Scope:** Issues #17–#21 — Excel/PDF export, docs, deploy config, launch assets  
**Status:** Approved by user

---

## Context

Phases 1–3 are complete (RPN engine, CLI, visualizations, Streamlit app, 49 tests passing, tagged `v0.3-streamlit-complete`). This spec covers everything needed to ship Phase 4 and go live.

---

## Decisions Made

| Decision | Choice | Reason |
|---|---|---|
| PDF library | `fpdf2` | Simpler API than `reportlab`, pure Python, Streamlit Cloud compatible, no system deps |
| Chart → PNG | `kaleido` via `plotly.io.to_image()` | Already using Plotly; kaleido is the standard Plotly PNG exporter |
| Screenshots/GIF | Manual capture by user post-deploy | Avoids headless browser dependency; ~5 min of user time |
| Deploy | Streamlit Community Cloud (free) | Zero cost, direct GitHub integration, native Streamlit support |

---

## Component Design

### `src/exporter.py`

Two public functions, both return `bytes` for use with `st.download_button`.

**`export_excel(df: pd.DataFrame) -> bytes`**
- Sheet 1 `"FMEA Analysis"`: full ranked table with openpyxl PatternFill color-coding per Risk_Tier (Red=#fde8e8, Yellow=#fef9e7, Green=#eafaf1). Bold header row. Column widths auto-sized.
- Sheet 2 `"Metadata"`: run timestamp, row count, flag counts (High RPN, Severity≥9, Action Priority H), tool version.
- Returns in-memory bytes via `io.BytesIO`.

**`export_pdf(df: pd.DataFrame, pareto_fig, heatmap_fig) -> bytes`**
- Uses `fpdf2` (`FPDF` class).
- Page 1: Title header, run date, summary metrics table (6 key counts), ranked FMEA table (ID, Failure Mode, S, O, D, RPN, Tier, Flags). Rows striped by Risk_Tier background.
- Page 2: Pareto chart PNG (Plotly → `kaleido` → PNG bytes → temp file → `fpdf.image()`).
- Page 3: Risk heatmap PNG (same flow).
- Returns bytes via `io.BytesIO`.

### `app.py` additions

Two `st.download_button` calls placed in a row below the ranked table:
- "📥 Download Excel" → calls `export_excel(df_filtered)`, MIME `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- "📄 Download PDF Report" → calls `export_pdf(df_filtered, pareto_fig, heatmap_fig)`, MIME `application/pdf`

Charts are generated once and stored in `st.session_state` to avoid regeneration on every button click.

### `docs/FMEA_methodology_notes.md`

Sections:
1. What is FMEA? (2 paragraphs — definition + aerospace context)
2. RPN Formula — S × O × D, scale explanation, limitations of RPN alone
3. AIAG FMEA-4 Action Priority — three tiers (H/M/L), thresholds used in this tool
4. Severity ≥ 9 Safety Rule — why it overrides RPN
5. Pareto 80/20 Applied to Risk — how to read the chart, 80% cumulative threshold
6. References

### `README.md`

Full rewrite. Sections:
1. Header with live demo badge + tech stack badges
2. Problem statement (3 sentences — why FMEA, why automate it)
3. Features list (bullet points with emoji)
4. Screenshot placeholder section (3 images: table, pareto, heatmap)
5. Quick Start — local run in 3 commands
6. Project structure tree
7. Demo dataset description
8. How to use your own FMEA file (column schema table)
9. Tech stack table
10. Resume bullet (copy-paste ready)
11. Engineering references

### `requirements.txt`

Pinned versions matching the installed environment. Includes: `streamlit`, `pandas`, `plotly`, `kaleido`, `fpdf2`, `openpyxl`, `numpy`, `matplotlib`.

### `.streamlit/config.toml`

Sets theme (light mode), page title, and disables telemetry for clean deploy.

### `assets/`

Empty directory with `README_ASSETS.md` explaining what screenshots to capture (ranked table view, Pareto tab, Heatmap tab) and GIF instructions.

### Launch (issue #21)

- Set repo public via `gh repo edit --visibility public`
- Draft LinkedIn post saved to `docs/LAUNCH_POST.md`
- Draft resume bullet included in README
- Tag `v1.0-launch` on final commit

---

## Files Changed / Created

| File | Action |
|---|---|
| `src/exporter.py` | Create |
| `app.py` | Edit (add export buttons, session_state for charts) |
| `docs/FMEA_methodology_notes.md` | Create |
| `README.md` | Rewrite |
| `requirements.txt` | Create |
| `.streamlit/config.toml` | Create |
| `assets/README_ASSETS.md` | Create |
| `docs/LAUNCH_POST.md` | Create |

---

## Out of Scope

- Automated screenshot / GIF capture
- DFMEA support
- User authentication
- Database persistence
- Any paid service
