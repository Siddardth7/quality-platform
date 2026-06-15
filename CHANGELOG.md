# Changelog

All notable changes to the Quality Platform are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to adhere to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-15

First public release — Week 01: monorepo + shared core. The platform now publicly exists.

🔗 Live: <https://quality-platform-nplyhc6rvsd3bfw6q9vvkd.streamlit.app/>

### Added

- **Monorepo** housing the FMEA Risk Analyzer (`apps/fmea`) and Manufacturing SPC Dashboard
  (`apps/spc`), each migrated with full original commit history preserved.
- **`quality_core`** shared package — schema, IO, and a unified theme (amber/violet palette +
  RPN risk-tier tokens) consumed by both apps.
- **Unified shell** (`app.py`) — a single `st.navigation` surface mounting a landing page, FMEA,
  and the three SPC workflows (Control Charts, Process Capability, Live Simulation). One
  `set_page_config` + theme, mounted render callables.
- **Unified tooling** — one `ruff.toml`, one `mypy.ini`, and a workspace pytest config covering
  `quality-core` + both apps with combined coverage.
- **CI** (`.github/workflows/ci.yml`) — `uv sync → ruff → mypy → pytest` on every push and PR to
  `main`, Python 3.11 via `astral-sh/setup-uv`.
- **`requirements.txt`** exported from `uv.lock` (third-party, pinned) as the Streamlit Cloud
  deploy fallback; the shell resolves all first-party code from the repo via `sys.path`.

### Notes

- FMEA: 105 tests, ruff + mypy clean. SPC: 83 tests (ruff/mypy lint cleanup scheduled for W02).
- uv is the toolchain; the workspace runs on Python 3.11.

[0.1.0]: https://github.com/Siddardth7/quality-platform/releases/tag/v0.1.0
