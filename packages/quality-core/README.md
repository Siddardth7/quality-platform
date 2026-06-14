# quality-core

Shared core package for the [Quality Platform](../../README.md) monorepo.

Houses cross-app primitives consumed by the FMEA, SPC, and Control Plan apps:

- **schema** — Pydantic models / data contracts (promoted from FMEA in a later issue)
- **io** — validated ingest + injection-safe Excel/PDF export (extracted in Week 04)
- **theme** — the single shared palette (merged in W01-6)

Importable as `quality_core`. Today it is an intentionally thin package that
establishes the workspace boundary; modules are filled in by subsequent issues.
