# CLAUDE.md

Guidance for Claude Code (claude.ai/code) working anywhere in the `quality-platform`
repository. App-specific detail lives in `apps/<app>/CLAUDE.md` — read this file first,
then the one for the app you are touching.

## What this repo is

A **uv workspace monorepo** for manufacturing quality tooling: five Streamlit/engine apps
over one shared core. Python 3.11, workspace version `0.7.0`.

```
packages/quality-core/   shared, UI-free core — io, schema, scoring, spc
apps/fmea/               FMEA risk analyzer (RPN + AIAG-VDA Action Priority)
apps/spc/                Statistical Process Control (control charts, capability)
apps/msa/                Measurement System Analysis (crossed Gage R&R)
apps/controlplan/        Control Plan (+ FMEA -> Control Plan connector)
apps/secom/              SECOM semiconductor case study — engine-only, no UI (#206)
shell/ + app.py          unified Streamlit shell mounting FMEA, SPC, Control Plan, Gage R&R
```

**Imports go downward only.** Apps import from `quality_core`; apps never import each
other. SECOM enforces this with `apps/secom/tests/test_import_boundary.py`, and CI enforces
that `quality-core` never resolves a Streamlit-chain dependency (audit A11, #202).

## Commands

All commands run from the **workspace root** via `uv` — never `pip`, never from an app
directory. Per-app `requirements.txt` files are legacy leftovers; they are not the install path.

```bash
uv sync --frozen                     # install (locked deps + dev tools)
uv run streamlit run app.py          # unified platform shell
uv run streamlit run apps/spc/app.py # a standalone app
```

### The gate

CI (`.github/workflows/ci.yml`, job id `gate` — status context `CI / gate`) runs these on
Python 3.11. All must be green before merging:

```bash
uv run ruff check .
uv run mypy
uv run pytest --cov
```

Plus a **core dependency contract** (no Streamlit chain in `quality-core`) and **eight
per-surface coverage gates**, each at `--cov-fail-under=100` with branch coverage on
(`[tool.coverage.run] branch=true`):

| Gate | Surface |
|---|---|
| Core io / schema / scoring / spc (4 gates) | `quality_core.{io,schema,scoring,spc}`, each run from `packages/quality-core` |
| SPC | `spc_app.{spc_engine,simulation,visualizer,exporter,schema,control_plan_config,fmea_feedback}` |
| Control Plan | `controlplan_app.{connector,schema}` |
| MSA | `msa_app.{gage_rr_engine,schema,exporter}` |
| SECOM | all seven `secom_app` engine modules (no `pages/` exclusion — SECOM has no UI) |

Streamlit `pages/` and entry scripts are excluded from app gates — they need a runtime.

### Single test

```bash
uv run pytest apps/msa/tests/test_gage_rr_engine.py -q     # one module
uv run pytest apps/spc -k "capability" -q                  # by keyword
```

## Branch ladder

```
feature -> test -> dev -> main -> production
```

- **Base every feature branch on `origin/test`** — that is the PR target. Basing on
  `origin/dev` pulls dev's release lead and produces ~14-file phantom conflicts.
  (`docs/AGENT_TEAM_FRAMEWORK.md` line 125 still says "off dev" — it is wrong.)
- `test -> dev` and `dev -> main` promotions recurrently conflict in SPC files and
  `CHANGELOG.md`. Take the superset; resolve in a worktree.
- **Never merge or push to `test`, `dev`, or `main`.** Sid (SME) is the final gate.
  The pipeline leaves a branch, a PR, and a written verdict for sign-off.

## The agent pipeline

`/ship` runs research -> coder -> tester -> reviewer on a fresh feature branch and opens a
PR into `test`. Definitions live in `.claude/agents/*.md`; commands in `.claude/commands/`
(`ship`, `audit`, `promote`, `release`).

- The **reviewer is read-only by tool restriction** (`Read`, `Grep`, `Glob`, `Bash` — no
  `Write`). That restriction *is* the review gate; without it the gate is theatre.
- Stages hand off through `.pipeline/*.md` (`spec.md`, `changes.md`, `test-results.md`,
  `review.md`).
- Agent model pins use full IDs. **Do not fall back to the bare `opus` alias** — it may
  resolve to a degraded 4.8.

## Hard-won rules

Violating these has cost real rework.

- **`.pipeline/` is gitignored.** Its files exist only on disk. Never `rm -rf .pipeline`
  while a PR built from it is still open — archive to the scratchpad first.
- **Never `git add -A`.** `marketing/` and `spikes/` are untracked scratch and are *not*
  gitignored, so a blanket add stages them. Stage by explicit path.
- **Restore mutations by `cp` from a backup, verified with `shasum -a 256`.** Never
  `git checkout` / `git restore` — those revert to the branch base and destroy uncommitted
  work. Clear `__pycache__` between mutation runs.
- **Negative controls are mandatory**, and a control that does not fail is a FINDING.
  Mutate the fix and prove the tests are load-bearing.
- **Audit docs by `git grep <pattern>`, never by a hand-listed set of files.** Patterns have
  under-matched on four consecutive PRs — a line-wrapped phrase defeated one (issue #235).
- **A subagent that dies mid-run can leave mutation residue.** After any agent failure,
  check `git status` and grep for `# MUTATION` before branching or committing.
- **One agent, one worktree. Never run two agents in the same checkout.** Branch state is
  per-checkout, not per-agent: a second agent running `git switch -c` moves the branch out from
  under the first, and its `git reset` wipes the first's uncommitted work. This destroyed a whole
  coder stage on #233 — an Antigravity run took the main checkout while `/ship` was mid-flight,
  leaving the feature branch empty and the tree clean, so nothing *looked* wrong. Give every
  parallel agent its own `git worktree add`, and say so explicitly in the handoff prompt.
- **`.pipeline/` is shared per checkout too.** Two agents in one directory silently overwrite each
  other's `spec.md` / `changes.md` / `test-results.md` / `review.md`. Back the spec up to the
  scratchpad as soon as the research stage writes it — the existing archive-before-`rm -rf` rule
  above only protects the *previous* issue's files, not the current one's.
- **Conventional commits**: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`,
  `ci:`, `style:`. One logical change per commit.

## Standards fidelity

- Every AIAG/ISO constant, threshold, and quotation is cited in that app's
  `apps/<app>/docs/ASSUMPTIONS_LOG.md`. **Do not change a value without updating its log.**
- **For AIAG/ISO claims the on-machine manual is the ONLY valid source:**
  `/Users/sid/Documents/Upskill/SixSigma/MSA_Reference_Manual_4th_Edition.md`.
  Never verify a standards quotation via web search.
- Use **formatting-tolerant matching** when checking quotations. Markdown emphasis and
  inline `<sup>` footnote markup produce false "fabricated" verdicts — and a false
  fabrication verdict is as serious as a real fabrication. MSA keeps a machine-checkable
  manifest at `apps/msa/docs/CITATIONS.tsv`, enforced by `apps/msa/tests/test_citations.py`.
- Where no published standard exists, say so in the module docstring rather than implying
  one (see `secom_app/selection.py` and `secom_app/doe_screening.py`).

## Version

One version across the workspace: `0.7.0` in root `pyproject.toml` and in each
`<app>_app/__init__.py::__version__`. Each app has a `tests/test_version.py` pinning it.
Bump together at release.

## Documentation map

| Doc | What it is |
|---|---|
| `docs/ENGINEERING_SYSTEM_PLAYBOOK.md` | the working system — issues, review loop, CI, releases |
| `docs/DEFINITION_OF_DONE.md` | the contract (#43) — read before claiming done |
| `docs/AGENT_TEAM_FRAMEWORK.md` | five-role agent pipeline spec (note the stale base-branch line) |
| `CONTRIBUTING.md`, `ROADMAP.md`, `CHANGELOG.md` | contribution rules, plan, history |
| `apps/<app>/docs/ASSUMPTIONS_LOG.md` | every constant/threshold with its citation |
