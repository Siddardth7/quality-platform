# Spike #108 — Reflex pilot: SPC Process Capability page

**Throwaway de-risking spike** for the frontend migration (epic #107). Not wired
into `main`, not part of the workspace, not covered by the gate. Lives only here.

## What it proves

Rebuilds the *simplest* SPC page (stateless `process_capability`) in **Reflex**,
importing the SPC **engine, visualizer, and exporter unchanged**. Validates the
four migration mechanics before Weeks 10–12 commit to them:

| # | Migration claim | Where proven |
|---|-----------------|--------------|
| 1 | Engine imports work with **no Streamlit** | `proof_headless.py` [1], `_capability_pilot.compute_pilot` |
| 2 | `rx.plotly` renders the **existing** Cpk gauge figure | app `rx.plotly(data=State.figure)`; figure asserted a `go.Figure` in proof [2] |
| 3 | `rx.download` returns the **unchanged** exporter bytes | app `download_xlsx/pdf`; real xlsx+PDF bytes asserted in proof [3] |
| 4 | Brand tokens apply (not default Reflex) | `quality_core.theme.palette` imported as-is; asserted in proof [4] |

No `quality_core` or engine code is touched.

## Run

```bash
# 1. headless proof (no browser, ~1s) — the CI-speed evidence
.venv-spike/bin/python proof_headless.py

# 2. the actual Reflex app (needs the JS toolchain reflex downloads on first run)
.venv-spike/bin/reflex run          # then open http://localhost:3000
```

The spike venv (`.venv-spike/`, Python 3.11) already has `reflex==0.9.7` + engine
deps. Recreate with `uv venv --python 3.11 .venv-spike && uv pip install --python
.venv-spike/bin/python -r requirements-spike.txt`.

## Files

- `_engine_bridge.py` — sys.path shim to import `spc_app` + `quality_core` unchanged
- `_capability_pilot.py` — streamlit-free capability core (engine calls only), shared by proof + app
- `proof_headless.py` — asserts all four claims without a browser
- `reflex_capability/reflex_capability.py` — the Reflex page (State + rx.plotly + rx.download + tokens)
- `rxconfig.py`, `requirements-spike.txt`

## Notes for the migration plan (findings)

See the write-up posted back on epic #107.
