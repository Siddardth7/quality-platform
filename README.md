# Quality Platform

[![CI](https://github.com/Siddardth7/quality-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Siddardth7/quality-platform/actions/workflows/ci.yml)
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://quality-platform-nplyhc6rvsd3bfw6q9vvkd.streamlit.app/)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](.python-version)
[![Built with uv](https://img.shields.io/badge/built%20with-uv-261230.svg)](https://github.com/astral-sh/uv)
[![Release](https://img.shields.io/github/v/release/Siddardth7/quality-platform?sort=semver)](https://github.com/Siddardth7/quality-platform/releases/latest)

Integrated manufacturing quality platform — **FMEA**, **SPC**, and **Control Plan** tools over a
shared core, aligned with the AIAG / IATF-16949 core quality toolset.

**Why:** the AIAG core quality tools are normally scattered across disconnected spreadsheets and
one-off apps. This platform brings them under **one URL, one theme, and one quality bar** — risk
analysis (FMEA) and process control (SPC) side by side, sharing a typed core.

**Shared by both tools:** a single `quality_core/io` library (covered at 100%, CI-gated) owns
CSV/Excel/PDF export and validated CSV/Excel ingest — written once and reused across FMEA and SPC,
so formula-injection escaping and friendly upload validation are guaranteed identical in both.

🔗 **Live demo:** **<https://quality-platform-nplyhc6rvsd3bfw6q9vvkd.streamlit.app/>** — one URL, Home + FMEA + the three SPC workflows.

🗺️ **New here? Read the [ROADMAP.md](ROADMAP.md)** — the full project guide: vision, architecture (with diagrams), the 12-week plan, what's shipped, and what's next.

🛠️ **Contributing?** [`CONTRIBUTING.md`](CONTRIBUTING.md) is the one-page process; [`docs/`](docs/README.md) holds the Definition of Done and the engineering-system playbook.

This is a monorepo. Two previously standalone apps now live here with their **full commit history
preserved** (the histories are part of the engineering story):

| App | Path | What it does |
| --- | ---- | ------------ |
| FMEA Risk Analyzer | [`apps/fmea/`](apps/fmea/) | Failure Mode & Effects Analysis — RPN / AIAG-VDA Action Priority, exports |
| Manufacturing SPC Dashboard | [`apps/spc/`](apps/spc/) | Statistical Process Control — control charts (incl. c-chart), capability with a stability gate, live simulation |

> Migrated from the standalone repos
> [`fmea-risk-analyzer`](https://github.com/Siddardth7/fmea-risk-analyzer) and
> [`manufacturing-spc-dashboard`](https://github.com/Siddardth7/manufacturing-spc-dashboard),
> which are now **archived → moved here**.

## Run an app

Each app still runs unchanged from its own directory:

```bash
cd apps/fmea && streamlit run app.py
cd apps/spc  && streamlit run app.py
```

## Unified shell

Both apps are also mounted under one `st.navigation` shell — a single URL with a landing page,
FMEA, and the three SPC workflows:

```bash
uv run streamlit run app.py
```

## Repository layout

```
app.py            # unified platform shell (st.navigation)
shell/            # landing page + shared chrome
packages/
  quality-core/   # shared schema, IO, and theme
apps/
  fmea/   # FMEA Risk Analyzer (full original history)
  spc/    # Manufacturing SPC Dashboard (full original history)
```

## Development & CI

The whole workspace shares one quality bar (`ruff.toml`, `mypy.ini`, pytest config in
`pyproject.toml`). The gate runs locally and in CI:

```bash
uv sync                 # install workspace + dev tools (locked)
uv run ruff check .     # lint
uv run mypy             # type-check
uv run pytest --cov     # tests + coverage across packages + apps
```

CI (`.github/workflows/ci.yml`) runs exactly this gate on every push and pull request to `main`,
on Python 3.11 via [`astral-sh/setup-uv`](https://github.com/astral-sh/setup-uv). It also enforces
a dedicated **SPC coverage gate** — the testable SPC surface (engine + simulation + visualizer) must
stay ≥95% covered.

> **Branch protection:** `main` should require the **CI / gate** status check to pass before
> merging (GitHub → Settings → Branches → add a rule for `main`, require status checks). This makes
> the gate mandatory — the protection SPC never had as a standalone repo.
