# Engineering System Playbook

**What this is:** the working system for building `quality-platform` — how every issue is worked,
the review/coverage loop, CI, branching, releases, and the documentation set. Adapted from the
system proven on `networking-agent` and reconciled with this repo's reality: a **uv workspace
monorepo** with **per-surface coverage gates** (not a single repo-wide floor).

**Reading order for someone new:** §1 (mental model) → [`DEFINITION_OF_DONE.md`](DEFINITION_OF_DONE.md)
(the contract — read it first) → §6 (repo scaffold) → [`../CONTRIBUTING.md`](../CONTRIBUTING.md) →
then work issues per §4.

---

## 1. The mental model (four ideas)

1. **One issue = one change = one PR = one CHANGELOG entry.** The smallest shippable unit. No "and
   while I was in there" changes. Every branch, commit, and changelog line traces to an issue number.

2. **The Definition of Done is a contract, written once, referenced everywhere.** It lives in
   [`docs/DEFINITION_OF_DONE.md`](DEFINITION_OF_DONE.md) and is mirrored as a **pinned issue**. Issue
   bodies link to it; they don't re-explain the gates.

3. **Coverage is a ratchet, never a wish.** Hard `--cov-fail-under` gates in CI, on **line AND
   branch**. Floors only move up. New code is held to 100%. This is the *learning loop*: write test →
   run coverage → fill the gap → repeat — and you are **not allowed to start the next issue** until
   the touched surface meets its gate.

4. **Small slices ship dark.** Land the deterministic/plumbing layer (tested) before the feature that
   drives it. Releases are deliberately small and weekly (v0.1 → v0.2 → … → v0.5 …) so quality never
   drops from cramming.

> These already matched this repo before the playbook was written down (weekly milestones, one-issue
> commits, self-covered shared surfaces). The playbook adds the parts that were missing: branch
> coverage, the DoD as a pinned artifact, PR-per-issue, and the doc taxonomy.

---

## 2. The whole loop, end to end

```
   ROADMAP → MILESTONE (a version) → ISSUE → BRANCH → IMPLEMENT
                                         │
                                         ▼
     ┌──── per-issue Definition of Done gates (in order) ─────────┐
     │ 1. implement (lazy/minimal, ponytail)                      │
     │ 2. dedicated tester writes/extends the suite               │
     │ 3. COVERAGE LEARNING LOOP  ← hard stop, per-surface, +branch│
     │ 4. /code-review on the diff → fix findings                 │
     │ 5. /ponytail-review on the diff → delete speculative code  │
     │ 6. green suite + ruff + mypy + CHANGELOG [Unreleased] entry │
     │ 7. PR → CI gate green → squash-merge → close issue         │
     └────────────────────────────────────────────────────────────┘
                                         │
                   (milestone complete)  ▼
     PER-VERSION gates → roll CHANGELOG → bump version →
     (ratchet a floor if earned) → human tags + pushes
```

The per-issue gates are the heart of it — specified in [`DEFINITION_OF_DONE.md`](DEFINITION_OF_DONE.md).

---

## 3. What's different here vs the source playbook

| Topic | Source (`networking-agent`) | This repo (`quality-platform`) |
|---|---|---|
| Layout | single package `src/` + `tests/` | **uv workspace monorepo**: `packages/quality-core` + `apps/fmea` + `apps/spc` |
| Coverage gate | one repo-wide `fail_under` in `pyproject` | **per-surface** `--cov-fail-under` gates in CI (io 100%, schema 100%, SPC ≥95%) — stricter for a monorepo |
| Branch coverage | `--cov-branch` in addopts | `branch = true` in `[tool.coverage.run]` — every gate reads it |
| Test import mode | default | `--import-mode=importlib` → shared fixtures in `conftest.py`, not sibling imports |
| DoD pin | issue #1 | a dedicated **pinned issue** (#1 was already used by W01-1) |
| Version SSOT | `pyproject.toml` | root `pyproject.toml` **and** `packages/quality-core/pyproject.toml` |
| Agent stack | ponytail / test-automator / qa-expert / code-review | same skills/agents available here |

Everything else (mental model, the two distinct review passes, small releases, doc taxonomy) carries
over unchanged.

---

## 4. Working a single issue (day-to-day)

**Before code:** read [`DEFINITION_OF_DONE.md`](DEFINITION_OF_DONE.md) + the issue body — that's the
full context by design. If you need more, the issue is under-specified; fix the issue first. Confirm
it's on the current milestone with Size/Complexity/Priority.

**Branch** (one per issue, off `main`): `feat|fix|chore|docs/<#>-<slug>`.

**The coverage learning loop in practice:**
```bash
uv run pytest packages/quality-core --cov=quality_core.io --cov-report=term-missing   # or the surface you touched
# read the Missing column → write the test that hits the red line/branch → repeat until the floor is met
uv run ruff check . && uv run mypy
```
`show_missing = true` prints the worklist. Do not move on while the loop is red.

**Commit + PR:** conventional commits with the issue number in the subject (`feat(core): … (#35)`);
squash-merge; PR body quotes the coverage/pytest evidence; CHANGELOG entry in the same PR; CI green
required. See [`CONTRIBUTING.md`](../CONTRIBUTING.md).

---

## 5. Coverage system (the ratchet, in detail)

Config in the root `pyproject.toml`:
```toml
[tool.coverage.run]
source = ["quality_core", "fmea_app", "ui", "spc_app"]
omit = ["*/tests/*"]
branch = true            # mandatory — catches the missing else a 100%-line file hides

[tool.coverage.report]
show_missing = true      # uncovered lines/branches become an actionable worklist
```
The floors are enforced as separate CI steps (`--cov-fail-under`) per surface, so a weak module can't
hide behind a strong one:

- `quality_core.io` — **100%** (shared export + validated ingest; every tool depends on it)
- `quality_core.schema` — **100%** (shared FMEA/relational contracts)
- SPC testable surface — **≥95%** (engine + simulation + visualizer + exporter + schema; Streamlit
  `pages/` excluded — they need a runtime)

Rules that make it work: **branch coverage is non-negotiable**; **the number only goes up** (ratchet
at a version close, recorded in a dated `COVERAGE_BASELINE_*.md` *before* the flip); **new modules
held to 100%**; **accuracy ≠ coverage** — for standards/AI correctness keep a scorecard against a
primary source, tracked like coverage.

---

## 6. Repo scaffold (the files that *are* the system)

```
.
├── README.md                      # front door → links to ROADMAP + docs
├── ROADMAP.md                     # canonical plan + version ladder + architecture diagrams
├── CHANGELOG.md                   # Keep a Changelog; [Unreleased] on top, entry per PR
├── CONTRIBUTING.md                # the one-page process
├── pyproject.toml                 # workspace + pytest + coverage ratchet (branch=true)
├── .github/workflows/ci.yml       # ruff → mypy → pytest → per-surface coverage gates
├── docs/
│   ├── README.md                  # docs index, grouped by purpose
│   ├── DEFINITION_OF_DONE.md      # the contract → pinned issue
│   ├── ENGINEERING_SYSTEM_PLAYBOOK.md   # this file
│   ├── COVERAGE_BASELINE_<date>.md      # per-surface line+branch before a gate flip
│   ├── <AUDIT>_<date>.md          # (as needed) defect catalog → fix issues
│   ├── <SCORECARD>_<date>.md      # (as needed) accuracy baseline + reproduce command
│   └── <TRIAL>_<date>.md          # (as needed) live end-to-end run evidence
├── packages/quality-core/         # shared code (schema, io, theme) — new modules held to 100%
└── apps/{fmea,spc}/               # the two Streamlit apps (full original history preserved)
```

**CI** already runs the gate on push + PR to `main` with a concurrency guard. The coverage floors are
CI steps (not a single `fail_under`) because the monorepo has multiple surfaces with different bars.
Keep actions on non-deprecated versions. **Add a platform matrix job only when shipping something
platform-specific** — a CI job that exercises the real entry point finds bugs unit tests can't.

---

## 7. Documentation taxonomy (the part most projects miss)

Distinct **kinds** of docs, each with a job. Date-stamp the point-in-time ones; keep the living ones
undated and update in place.

| Type | Pattern | Job | Cadence |
|---|---|---|---|
| **Roadmap** | `ROADMAP.md` | canonical plan + version ladder + architecture | living |
| **Process contract** | `DEFINITION_OF_DONE.md` | the gates; pinned issue | living |
| **Playbook** | `ENGINEERING_SYSTEM_PLAYBOOK.md` | the whole system (this file) | living |
| **Baseline** | `COVERAGE_BASELINE_<date>.md` | per-module line+branch before a gate flip | point-in-time |
| **Audit** | `<AREA>_AUDIT_<date>.md` | defect catalog, severity-ranked, routed to issues | point-in-time |
| **Scorecard** | `<AREA>_SCORECARD_<date>.md` | accuracy baseline + reproduce command + bar | point-in-time |
| **Trial** | `TRIAL_<name>_<date>.md` | live end-to-end run; per-version "does it work" evidence | point-in-time |
| **Design** | `<FEATURE>_DESIGN_<date>.md` | the thinking before a non-trivial feature | point-in-time |

**CHANGELOG.md** — Keep a Changelog + SemVer. `[Unreleased]` on top with `Added/Fixed/Changed`; every
user-visible change adds an entry **in its own PR**. At a version close the "roll" renames
`[Unreleased]` to the version+date and opens a fresh empty one (a `chore(release):` commit). Entries
are explanatory (symptom → root cause → fix), because the changelog doubles as the incident record.

**Wiki:** depth lives in `docs/` (versioned, reviewed in PRs), not the GitHub wiki. If a wiki is used,
mirror only stable, non-versioned content (home, architecture overview, FAQ, glossary) — never the
roadmap, DoD, or changelog.

---

## 8. Releases and the version ladder

- **Phased, deliberately small, weekly releases.** v0.1 → v0.5 shipped one per week; the ladder runs
  to v0.11 then a v1.0-portfolio (or a product renumber) at the Week-12 architecture-fork gate. See
  [`ROADMAP.md`](../ROADMAP.md).
- **Every version = a GitHub milestone** holding its issues.
- **A release is a `chore(release):` commit/PR** that rolls the CHANGELOG and bumps the version in
  **both** `pyproject.toml` files. Then the **human owner tags + pushes**.
- **Live validation gates the integration/AI versions** — a dated `TRIAL_` doc with a real
  end-to-end run is the evidence, not "it should work."

---

## 9. Agent-assisted execution (the roles that matter)

| Gate | Role / tool |
|---|---|
| 1. Implement minimally | `ponytail` reflex — reuse > stdlib > native > one line > minimal new code |
| 2. Dedicated tester | `test-automator` writes the suite; `qa-expert` supervises strategy for complex/audit issues |
| 3. Coverage loop | `uv run pytest --cov=<surface> --cov-report=term-missing`, iterated to the floor (line+branch) |
| 4. Correctness review | `/code-review` on the diff |
| 5. Over-engineering review | `/ponytail-review` on the diff; `/ponytail-audit` + `/ponytail-debt` at version close |
| 6. Log | CHANGELOG entry + green CI |

The discipline regardless of tooling: **the tester is a separate pass from the implementer, and the
two review passes (correctness, then bloat) are distinct.** One agent wearing all the hats is how
quality erodes.

---

## 10. One-screen checklist (pin this)

**Per issue:**
- [ ] Branch `feat|fix|chore|docs/<#>-<slug>` off `main`
- [ ] Shortest correct diff; mark shortcuts `# ponytail:`
- [ ] Separate tester writes/extends the suite
- [ ] Coverage loop: touched surface meets its floor on **line+branch** — **hard stop**
- [ ] `/code-review` → fix every correctness finding
- [ ] `/ponytail-review` → delete speculative code
- [ ] `ruff` + `mypy` clean, full suite green
- [ ] CHANGELOG `[Unreleased]` entry in the same PR
- [ ] PR with evidence quoted; **CI green required**; squash-merge; close issue

**Per version:**
- [ ] All milestone issues closed
- [ ] Every per-surface gate green (line+branch); ratchet a floor up if earned
- [ ] Version-diff `/code-review` + `/ponytail-audit` + `/ponytail-debt`
- [ ] Live `TRIAL_` doc where required
- [ ] Roll CHANGELOG + bump both `pyproject.toml` versions (`chore(release):`)
- [ ] **Human tags + pushes**
