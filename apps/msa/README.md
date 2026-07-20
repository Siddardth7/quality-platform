# MSA — Measurement System Analysis

Scaffold for the Measurement System Analysis app. It mounts into the unified
Quality Platform shell alongside FMEA and SPC, sharing `quality_core`.

Today it provides validated ingest of a crossed gage-study CSV
(`part, appraiser, trial, measurement`) through `quality_core.io`, with
study-level tolerance (USL/LSL) captured as page inputs. It computes Gage R&R
(%GRR vs study and vs tolerance, ndc, AIAG verdict) using the Average-and-Range
method and exports the study/results as CSV, Excel, and PDF.
