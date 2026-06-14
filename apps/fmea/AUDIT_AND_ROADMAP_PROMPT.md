# FMEA Risk Analyzer — Complete Audit + Future Features Prompt

> **How to use this file.** This is a self-contained mission brief for a **fresh Opus 4.8 agent running in the Claude Code CLI** inside this repository. Open the repo, start a new session, and paste the **Mission Brief** section (or point the agent at this file: *"Read AUDIT_AND_ROADMAP_PROMPT.md and execute it end to end"*). Each phase names the **best skill / plugin / command** to use and how to install it if it is missing. Work the phases in order; do not skip the verification gates.

> **This file does not stand alone.** It is the *execution* half of a two-document plan. The companion file **`FUTURE_SCOPE_AND_MARKET_RESEARCH.md`** (same folder) is the *strategy* half — it contains the market-gap analysis, the prioritized feature roadmap (Tier 1/2/3), and the rationale for every feature. **Read that file before Phase 9**, and use its roadmap as the source of truth for what to build. This prompt tells you *how to work*; the research doc tells you *what is worth building and why*.

---

## The overall workflow (read this first)

Execute in three sequential stages. Do not let a later stage begin until the prior stage's gate is green.

1. **AUDIT (Phases 1–7, read-only).** Understand the codebase, then hunt for bugs, security holes, dependency rot, architectural debt, performance and UX problems, and test gaps. Produce `AUDIT_REPORT.md` with a prioritized fix queue. **No code is changed in this stage.**
2. **FIX (Phase 8).** Clear the fix queue from the audit, smallest-blast-radius first, one logical change per commit, tests green after each. This stabilizes the foundation *before* any new feature is built on top of it.
3. **BUILD (Phases 9–10).** Only once the codebase is clean and green, open `FUTURE_SCOPE_AND_MARKET_RESEARCH.md`, pull the Tier 1→2→3 roadmap, implement features in tier order, and ship them as properly versioned SemVer releases with a changelog and tag.

The order is deliberate: **never build features on an unaudited, buggy base.** Auditing first means the fixes and the new code share a stable, tested foundation, and the version bump at the end reflects a codebase you actually trust. Three checkpoints with the user: after the baseline (Phase 1), after the audit report (Phase 7), and before the release (Phase 10).

```
AUDIT (read-only) ──▶ FIX (clear the queue) ──▶ BUILD (roadmap, tier by tier) ──▶ RELEASE (SemVer + tag)
   Phases 1–7              Phase 8                Phase 9 (uses research doc)        Phase 10
   → AUDIT_REPORT.md       → green gate           → ROADMAP.md + features            → CHANGELOG + tag
```

---

## 0. Context the agent must load first

You are auditing **fmea-risk-analyzer** — a Streamlit web app that performs Failure Mode and Effects Analysis (FMEA): users upload a CSV of failure modes, the tool computes RPN (Risk Priority Number = Severity × Occurrence × Detection), visualizes risk, and exports PDF/CSV/Excel reports.

**Stack & shape (verify, don't trust):**

- Python 3.11, Streamlit `1.56.0`, pandas `3.0.2`, plotly `6.6.0`, fpdf2 `2.8.7`, openpyxl `3.1.5`, numpy `2.4.4`, matplotlib `3.10.8`, pydantic `>=2.0`.
- Entry point `app.py` (~739 LOC, thin orchestrator). Core logic in `src/` — `rpn_engine.py`, `exporter.py`, `plotly_charts.py`, `visualizer.py`, `schema.py` (Pydantic v2 models). UI helpers in `ui/` — `filters.py`, `charts.py`, `exports.py`. Legacy `fmea_analyzer.py` at root (~258 LOC) — check whether it is still wired in or dead.
- Tests in `tests/` (pytest + pytest-cov). CI in `.github/workflows/ci.yml` runs ruff, mypy (`src/`, `ui/`), and pytest with coverage. Pre-commit hooks: ruff + ruff-format + mypy.
- **Current tool version: `1.0.0`** — defined as `_TOOL_VERSION` in `src/exporter.py`. There is no single source of truth for version yet; note that as a finding.

**Your two goals:** (1) a rigorous bug + quality audit with concrete, prioritized fixes, and (2) a future-features roadmap culminating in a justified semantic version bump and a tagged release.

**Operating rules:**

- Ground every claim in code you actually read or a command you actually ran. No speculation presented as fact.
- Do **read-only investigation first**; do not change code until Phase 8, and only after the audit report exists.
- Produce a written `AUDIT_REPORT.md` (findings) and `ROADMAP.md` (features) in the repo root. Use the `docx`/`pdf` skills only if the user later asks for a shareable version.
- Every finding gets: severity (Critical / High / Medium / Low), file:line, evidence, recommended fix, and effort estimate.

---

## Tooling reference — what to invoke, and the install fallback

These are referenced throughout. Confirm availability at the start; install what is missing.

| Capability | Primary tool | How to get it if missing |
|---|---|---|
| PR / diff code review | **`/review`** (built-in slash command) | Ships with Claude Code. |
| Security review of changes | **`/security-review`** (built-in slash command) | Ships with Claude Code. |
| Deep engineering skills: `code-review`, `debug`, `architecture`, `testing-strategy`, `tech-debt`, `deploy-checklist`, `documentation`, `system-design`, `incident-response` | **`engineering` plugin** (marketplace: `knowledge-work-plugins`) | In Claude Code: `/plugin marketplace add knowledge-work-plugins` then `/plugin install engineering`. Invoke a skill via `/engineering:code-review`, `/engineering:tech-debt`, etc. |
| Parallel codebase search | **Explore** subagent (Task tool) | Built-in. Use for "where is X used / defined". |
| Implementation planning | **Plan** subagent (Task tool) | Built-in. Use to design refactors before touching code. |
| Independent second-opinion review | **general-purpose / code-reviewer** subagent | Built-in. Use to verify high-stakes findings. |
| Generate `CLAUDE.md` repo guide | **`/init`** (built-in slash command) | Ships with Claude Code. |
| Word / PDF / Excel / slide deliverables | **`docx` / `pdf` / `xlsx` / `pptx`** skills | Already available in this environment. |
| De-AI-ify written docs | **`humanizer`** skill | Already available. |
| Shell-based scanners (ruff, mypy, pytest, pip-audit, bandit, vulture, radon, deptry) | **Bash** tool + `pip install` | `pip install pip-audit bandit vulture radon deptry --break-system-packages`. |

> If a recommended skill/plugin is not installed and cannot be installed, fall back to the Bash equivalent named in that phase and note the substitution in the report.

---

## Phase 1 — Reconnaissance & baseline (read-only)

**Goal:** know the territory before judging it.

- **1.1** Build a mental map of the repo. **Tool:** `Explore` subagent — ask it to list every module, what each exports, and the call graph from `app.py` down. Also run `git log --oneline -30` and `git shortlog -sn` for history and ownership.
- **1.2** Generate / refresh a `CLAUDE.md` so the agent (and future ones) have a durable repo guide. **Tool:** `/init`.
- **1.3** Establish the green baseline: run the existing suite and linters exactly as CI does. **Tool:** Bash — `pip install -r requirements.txt -r requirements-dev.txt --break-system-packages`, then `python -m pytest tests/ -v --cov=src --cov-report=term-missing`, `ruff check .`, `mypy src/ ui/ --ignore-missing-imports`. Record pass/fail and coverage % as the **baseline metrics**.
- **1.4** Identify dead/duplicated code, especially whether root `fmea_analyzer.py` duplicates `src/rpn_engine.py`. **Tool:** Bash `vulture . --min-confidence 70` and `Explore` to trace imports.

**Gate:** Do not proceed until the baseline (tests, lint, coverage, dead-code list) is written down.

---

## Phase 2 — Correctness & bug hunt

**Goal:** find logic bugs, edge-case failures, and silent data corruption.

- **2.1** Audit the RPN engine (`src/rpn_engine.py`). **Tool:** `/engineering:debug` skill (or Bash + close reading). Verify: RPN bounds (1–1000), divide-by-zero / NaN handling, integer vs float coercion, behavior when S/O/D are out of the 1–10 range, empty-DataFrame and single-row cases, and tie-breaking in ranking. Cross-check against `docs/FMEA_methodology_notes.md` — flag any deviation from standard FMEA math (including AP / Action Priority if used).
- **2.2** Audit input validation & schema (`src/schema.py`, Pydantic models). Confirm malformed CSVs, missing columns, duplicate headers, unicode, and huge files are rejected gracefully (not with a stack trace shown to the user).
- **2.3** Audit exporters (`src/exporter.py`). Verify PDF/CSV/Excel outputs survive: special characters, very long text fields, missing optional columns, and empty result sets. Check the export cache-key logic (DataFrame hashing) for index-sensitivity or hash collisions.
- **2.4** Audit charts (`src/plotly_charts.py`, `src/visualizer.py`, `ui/charts.py`) for failures on degenerate data (all-equal RPNs, one row, zero rows) and for the matplotlib-vs-plotly split being consistent.
- **2.5** Audit Streamlit state in `app.py` — session-state lifecycle, re-run behavior, file-uploader edge cases, and any work done on every rerun that should be cached.

**Tool for the pass:** invoke `/engineering:code-review` over each module; use the **Explore** subagent to find all call sites of any suspect function. For each confirmed bug, write a **failing test first** (Phase 6 will formalize), then record it.

---

## Phase 3 — Security & dependency audit

**Goal:** no exploitable input paths, no vulnerable or stale dependencies.

- **3.1** Static security scan of the diff and the codebase. **Tool:** `/security-review` (built-in) for a structured pass; back it with Bash `bandit -r src/ ui/ app.py fmea_analyzer.py`.
- **3.2** Threat-model the upload path: CSV/Excel parsing (formula injection / CSV injection in exported files, zip-bomb via openpyxl, pandas `read_*` arguments), file-size limits, and any `eval`/`exec`/`pickle`/`subprocess` usage. **Tool:** `Explore` to grep for dangerous calls.
- **3.3** Dependency vulnerability + freshness audit. **Tool:** Bash — `pip-audit -r requirements.txt` for CVEs; `pip list --outdated` and `deptry .` for unused/missing/transitive issues. Cross-check that pinned versions actually resolve together. **Search the web** for known advisories on the exact pinned versions (Streamlit, pandas 3.x, fpdf2, openpyxl).
- **3.4** Secrets & config hygiene: scan for committed secrets, review `.streamlit/config.toml`, `.gitignore`, and `.devcontainer` for anything leaking or over-permissive.

**Gate:** every Critical/High security finding must have a remediation and, where feasible, a regression test.

---

## Phase 4 — Architecture, design & tech-debt review

**Goal:** assess maintainability and the cost of future change.

- **4.1** Architecture review: is the `app.py → src/ → ui/` separation clean, or is logic leaking into the orchestrator? Is `fmea_analyzer.py` legacy debt to delete? **Tool:** `/engineering:architecture` and `/engineering:system-design` skills.
- **4.2** Tech-debt inventory: complexity hotspots, long functions, duplicated logic, weak typing. **Tool:** `/engineering:tech-debt` skill + Bash `radon cc -s -a src/ ui/ app.py` (cyclomatic complexity) and `radon mi src/` (maintainability index). Rank debt by (impact × frequency-of-change).
- **4.3** Type-safety review: run `mypy --strict` (beyond CI's relaxed mode) and report the gap; identify modules that should be tightened.
- **4.4** Error-handling & logging review: are user-facing errors friendly, are internal errors logged, is there any logging at all?

---

## Phase 5 — Performance & UX review

**Goal:** the app stays responsive and usable at realistic data sizes.

- **5.1** Performance: profile RPN compute, chart build, and export on a large synthetic input (e.g., 10k+ rows — generate it in Bash). Look for unnecessary recompute on rerun, missing `@st.cache_data`, and O(n²) patterns. **Tool:** Bash with `cProfile` / `time`.
- **5.2** UX/accessibility review of the Streamlit UI: loading states, error messaging, mobile/narrow layout, color-contrast on the risk heatmap, empty states, and the upload→result happy path. **Tool:** reason from the code; if **Claude in Chrome** tooling is available, run the app (`streamlit run app.py`) and click through.
- **5.3** Docs/UX consistency: does `README.md` (and `docs/`) match actual behavior? Flag stale claims. **Tool:** `/engineering:documentation` skill.

---

## Phase 6 — Test-coverage hardening

**Goal:** lock in correctness and prevent regressions of everything found above.

- **6.1** Coverage-gap analysis from the Phase 1 baseline: which `src/`/`ui/` branches are untested? **Tool:** `/engineering:testing-strategy` skill + `pytest --cov` HTML report.
- **6.2** Write a failing test for **every** confirmed bug from Phases 2–3, then keep them as regression tests.
- **6.3** Add property/edge-case tests for the RPN engine (boundary S/O/D values) and exporters (special chars, empty sets).
- **6.4** Target a coverage threshold (propose one, e.g. ≥85% on `src/`) and wire it into CI as a `--cov-fail-under` gate.

**Gate:** the full suite must be green before any refactor lands.

---

## Phase 7 — Write the Audit Report

**Goal:** a single authoritative findings document.

- **7.1** Compile `AUDIT_REPORT.md` in repo root: executive summary, baseline metrics, then findings grouped by phase, each with severity / file:line / evidence / fix / effort. End with a **prioritized fix queue** (Critical→Low).
- **7.2** Get an independent second opinion on the Critical/High findings. **Tool:** spawn a `general-purpose` (or `code-reviewer`) subagent with the specific finding + file:line and ask it to confirm or refute. Adjust the report accordingly.
- **7.3** (Optional, on request) Produce a shareable version with the **`docx`** or **`pdf`** skill; run the **`humanizer`** skill over prose first.

---

## Phase 8 — Implement fixes (now you may edit code)

**Goal:** clear the fix queue safely, smallest-blast-radius first.

- **8.1** Plan the change set before editing. **Tool:** `Plan` subagent for any non-trivial refactor (e.g., deleting `fmea_analyzer.py`, restructuring `app.py`).
- **8.2** Fix in priority order. One logical change per commit, conventional-commit messages (the repo already uses `feat:` / `fix:` / `refactor:` / `docs:` / `ci:` / `style:`). Run the relevant tests after each.
- **8.3** After the change set, run the **full gate**: `pytest --cov`, `ruff check .`, `mypy src/ ui/`. Then run **`/review`** on the diff and **`/security-review`** to confirm nothing regressed.
- **8.4** Update `README.md` / `docs/` for any behavior change.

---

## Phase 9 — Build the future features (driven by the research doc)

**Goal:** implement the roadmap that already exists — do not reinvent it.

> **Start by reading `FUTURE_SCOPE_AND_MARKET_RESEARCH.md`.** It contains the finished market-gap analysis and a three-tier, impact-ranked roadmap. Your job here is to *execute* it in order, not to brainstorm a new list. The most important finding in that doc: the tool computes **RPN**, but the AIAG-VDA standard replaced RPN with **Action Priority (AP)** in 2019 — so the **AP engine is the #1 Tier-1 feature** and the top priority of this phase.

- **9.1** Load the roadmap. Read `FUTURE_SCOPE_AND_MARKET_RESEARCH.md` and extract the Tier 1 / Tier 2 / Tier 3 feature list and the "Recommended next 3 moves" section. Treat that as the backlog.
- **9.2** Build in tier order, smallest-viable-first. **Tier 1 (standards & correctness) ships in the next minor release; Tier 2 (adoption/collaboration) spans the next major; Tier 3 (AI/analytics "wow") becomes headline features for later majors.** Do not start Tier 2 until Tier 1 is merged and green.
- **9.3** For each feature, before writing code: confirm it still fits the current architecture or flag that it forces the Streamlit→FastAPI/React split discussed in the research doc. **Tool:** `/engineering:architecture` for the redesign-or-not call, then the **`Plan`** subagent to design the change set.
- **9.4** Implement each feature the same disciplined way as Phase 8: a failing test or acceptance check first, one logical change per commit, full gate (`pytest --cov`, `ruff`, `mypy`) green after each, then `/review`. Update `README.md` and `docs/` as behavior changes.
- **9.5** Write/refresh `ROADMAP.md` in the repo root: the tiers, what's now done, what's next, and each item's target SemVer version (feeds Phase 10). Keep it in sync with the research doc rather than duplicating its analysis.
- **9.6** (Optional) If the user wants a stakeholder/portfolio deck of the roadmap, build it with the **`pptx`** skill; run prose through the **`humanizer`** skill first.

> **Scope guard:** a single release should not try to land all three tiers. Per the research doc's "quality over quantity" guidance, ship Tier 1 cleanly first; pick *one* Tier-3 "wow" feature (AI-assisted failure-mode suggestion is the most demo-able) only after the foundation is solid.

---

## Phase 10 — Version bump & release

**Goal:** ship a correctly versioned, tagged release.

- **10.1** Decide the bump using **SemVer** and the actual change set: breaking API/CSV-schema change → **major**; new backward-compatible feature → **minor**; bug/security/docs only → **patch**. State the reasoning in the release notes. (Current = `1.0.0`.)
- **10.2** Create a **single source of truth** for version if one does not exist (e.g., `__version__` in `src/__init__.py` or a `[project] version` in a new `pyproject.toml`), and make `src/exporter.py`'s `_TOOL_VERSION` read from it instead of hardcoding `"1.0.0"`. **Tool:** `Plan` then Edit.
- **10.3** Write `CHANGELOG.md` (Keep a Changelog format) covering Added / Changed / Fixed / Security from this audit.
- **10.4** Pre-release checklist. **Tool:** `/engineering:deploy-checklist` skill. Confirm: CI green, coverage gate passing, README/CHANGELOG updated, no Critical/High findings open.
- **10.5** Commit, then tag: `git tag -a vX.Y.Z -m "..."`. Open a PR (or push to a release branch) and run **`/review`** + **`/security-review`** one final time. Draft GitHub release notes from the CHANGELOG. **Do not push tags or publish a release without explicit user confirmation.**

---

## Final deliverables checklist

*(Stage 1 — AUDIT)*
- [ ] `CLAUDE.md` — repo guide (Phase 1)
- [ ] `AUDIT_REPORT.md` — prioritized findings with fix queue (Phase 7)

*(Stage 2 — FIX)*
- [ ] Code fixes committed, full gate green, `/review` + `/security-review` clean (Phase 8)
- [ ] New/updated regression tests, coverage gate in CI (Phase 6)

*(Stage 3 — BUILD)*
- [ ] `FUTURE_SCOPE_AND_MARKET_RESEARCH.md` read; roadmap pulled from it (Phase 9)
- [ ] Tier-1 features (AP engine first) implemented, tested, green (Phase 9)
- [ ] `ROADMAP.md` — tiers mapped to SemVer versions, kept in sync with the research doc (Phase 9)
- [ ] Single source-of-truth version + `CHANGELOG.md` + git tag drafted (Phase 10)

*(Wrap-up)*
- [ ] One-paragraph summary back to the user: what was broken, what was fixed, which Tier-1 features shipped, the recommended next version, and the top 3 roadmap items still ahead.

---

## Guardrails (read before executing)

1. **Investigate before you edit.** Phases 1–7 are read-only. Code changes start at Phase 8.
2. **Evidence over assertion.** Cite file:line and command output for every finding.
3. **Tests gate everything.** Never mark a fix done while the suite is red.
4. **Ask before destructive/irreversible actions** — deleting modules, force-pushes, publishing a release, or tagging.
5. **Prefer the named skill/command; fall back to Bash and note the substitution** if a plugin is unavailable.
6. **Keep the user in the loop** at three checkpoints: after the baseline (Phase 1), after the audit report (Phase 7), and before the release (Phase 10).
