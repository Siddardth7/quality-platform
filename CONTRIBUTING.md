# Contributing

The whole process on one page. The gates themselves live in
[`docs/DEFINITION_OF_DONE.md`](docs/DEFINITION_OF_DONE.md) (the contract); this page is the
day-to-day mechanics.

## 1. Dev setup

```bash
# uv lives at ~/.local/bin/uv
uv sync                 # install the workspace + dev tools (locked)
uv run pytest -q        # tests across quality-core + both apps
uv run ruff check .     # lint
uv run mypy             # type-check
```

The repo is a **uv workspace**: `packages/quality-core` (shared code) + `apps/fmea` + `apps/spc`.
`pytest` runs in `--import-mode=importlib`; shared test fixtures go in a `tests/conftest.py`, not a
sibling importable module.

## 2. Test hygiene

- Tests are **hermetic**: never touch the user's real home/files, never hit the network. Use
  `tmp_path` / monkeypatch for anything filesystem-bound.
- Each shared surface is **self-sufficiently covered** — `quality_core.io` and `quality_core.schema`
  are tested by their *own* suites in `packages/quality-core/tests`, not only incidentally via an
  app. That's what lets the per-surface gates hold at 100%.

## 3. The bar (what CI enforces)

`.github/workflows/ci.yml` runs the full gate on every push and PR to `main`: **ruff → mypy →
pytest (with coverage) → per-surface coverage gates**. **Branch coverage is on** (`branch = true`),
so a missing `else` fails the build, not just a missing line. Green CI is **required to merge**.

| Surface | Floor |
|---------|-------|
| `quality_core.io` | 100% line+branch |
| `quality_core.schema` | 100% line+branch |
| SPC testable surface | ≥95% line+branch |

Floors only ratchet **up** (recorded in a dated `docs/COVERAGE_BASELINE_*.md` before any flip).

## 4. How work is structured

- **One issue = one change = one PR = one CHANGELOG entry.** No "while I was in there" changes.
- Every issue sits on a **version milestone** and carries Size / Complexity / Priority.
- The canonical **Definition of Done** is a pinned issue; issue bodies link to it, they don't repeat it.
- **Small slices ship dark** — land the plumbing (tested) before the feature that drives it.
- **Branch per issue**, off `main`:
  ```
  feat/<#>-<slug>    fix/<#>-<slug>    chore/<#>-<slug>    docs/<slug>
  ```
- **Conventional commits**, scope in parens, **issue number in the subject**:
  ```
  feat(core): relational FMEA domain model + loss-less adapters (#35)
  fix(io): crash-safe row-error echo; drop dead branch (#41)
  chore(release): v0.5.0 — relational FMEA + schema→core (#40)
  ```
- **Squash-merge** every PR. The PR body says *what* + *why* and **quotes the coverage/pytest
  evidence**. The CHANGELOG entry lands in the **same PR**.
- Tags are cut by the **human owner**, never automated.

## 5. Architecture ground rules (a reviewer will reject a PR that breaks these)

- **Shared code is written once in `quality_core` and consumed twice.** Export/ingest/validation
  logic lives in `quality_core.io`; data contracts in `quality_core.schema`; theme in
  `quality_core.theme`. Don't re-implement any of these inside an app — reuse or extend the core.
- **Schema is promoted only when stable.** New per-app schema may start in the app; promote it to
  `quality_core.schema` (with a re-export shim + its own 100% gate) once it's shared, not before.
- **Boundaries stay safe.** All file ingest goes through `quality_core.io` validated readers (never
  a bare `pd.read_csv`); all exports go through the injection-safe exporters. No new bare I/O.
- **Standards correctness is testable.** Anything tied to a published standard (AIAG-VDA AP table,
  S/O/D scales) is validated against the primary source, not a web copy, and locked by a test.
- **No silent drops.** If code caps, truncates, or discards data, it must say so (log/return),
  never swallow.

See [`docs/ENGINEERING_SYSTEM_PLAYBOOK.md`](docs/ENGINEERING_SYSTEM_PLAYBOOK.md) for the full system
and [`ROADMAP.md`](ROADMAP.md) for where the project is going.
