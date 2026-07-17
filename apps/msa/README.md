# MSA — Measurement System Analysis

Scaffold for the Measurement System Analysis app. It mounts into the unified
Quality Platform shell alongside FMEA and SPC, sharing `quality_core`.

Today it provides validated ingest of a crossed gage-study CSV
(`part, appraiser, trial, measurement`) through `quality_core.io`, with
study-level tolerance (USL/LSL) captured as page inputs. The Gage R&R
computation (%GRR, ndc, AIAG verdict) lands in a later issue.
