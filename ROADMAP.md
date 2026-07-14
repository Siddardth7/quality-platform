# Quality Platform — Roadmap & Project Guide

> **Read this first.** This is the single, self-contained map of the project: what it is, why it
> exists, how it's built, everything shipped so far, and everything planned. If you've never seen
> this repo before, this document should get you from zero to *"I understand the whole thing"* in
> one read.

- **Repo:** <https://github.com/Siddardth7/quality-platform>
- **Live demo:** <https://quality-platform-nplyhc6rvsd3bfw6q9vvkd.streamlit.app/>
- **Status (2026-07-13):** Weeks 1–5 shipped (v0.1.0 → v0.5.0). **Week 6 up next** — Control Plan connector.
- **Roadmap rerouted 2026-07-10:** the AI-copilot phase is **deferred**; **MSA / Gage R&R** and a **SECOM real-semiconductor case study** take its place (see §5 and §9).
- **Canonical schedule:** GitHub **Milestones** (`Week 01` … `Week 12`). This file mirrors and explains them.

---

## Table of contents

1. [What this project is (and why)](#1-what-this-project-is-and-why)
2. [Current status at a glance](#2-current-status-at-a-glance)
3. [System architecture](#3-system-architecture) — *flowchart*
4. [The target workflow: closed-loop quality](#4-the-target-workflow-closed-loop-quality) — *flowchart*
5. [The 12-week plan (phase flow)](#5-the-12-week-plan-phase-flow) — *flowchart*
6. [Tech stack & the quality gate](#6-tech-stack--the-quality-gate)
7. [Repository layout](#7-repository-layout)
8. [What we've done — week by week](#8-what-weve-done--week-by-week)
9. [Future work — weeks 6–12](#9-future-work--weeks-612)
10. [Release history](#10-release-history)
11. [How to run & develop](#11-how-to-run--develop)
12. [Glossary](#12-glossary)

---

## 1. What this project is (and why)

**Quality Platform** brings the core **AIAG / IATF-16949 manufacturing-quality tools** — **FMEA**
(risk analysis), **SPC** (process control), a **Control Plan** connector, and **MSA / Gage R&R**
(measurement-system analysis) — under **one URL, one design system, and one engineering quality
bar**, over a shared typed core.

**The problem it solves.** In practice these tools live in disconnected spreadsheets and one-off
apps. A failure mode identified in an FMEA never automatically becomes a control on a Control Plan,
and an out-of-control signal on an SPC chart never flows back to update the FMEA's risk rating. The
loop that the AIAG core-tools methodology *describes* is almost never *implemented*.

**The thesis.** Build the two credible standalone tools first, promote everything they share into a
single core (`quality_core`), wire them into an actual **closed loop** (FMEA → Control Plan →
SPC → back to FMEA), complete the **AIAG core-tools story with MSA / Gage R&R**, and prove the whole
platform on **real semiconductor process data (SECOM)**. Each week ships a real, tested, released
rung — *no week ships a stub.* *(An explainable AI copilot was the original topper; it is now a
documented **deferred** phase — see §9.)*

**Who it's for.** Quality / manufacturing engineers as the domain users; and as an engineering
portfolio piece, it demonstrates monorepo architecture, a shared-core economic argument, standards
correctness, and trustworthy applied AI.

---

## 2. Current status at a glance

| | |
|---|---|
| **Phase** | C — Integration & core-tool completion (Weeks 6–9) |
| **Active milestone** | Week 06 · Control Plan connector (due 2026-07-26) |
| **Shipped releases** | v0.1.0, v0.2.0, v0.3.0, v0.4.0, v0.5.0 |
| **Next release** | v0.6.0 (end of Week 6) |
| **Apps live** | FMEA Risk Analyzer, Manufacturing SPC Dashboard (unified shell) |
| **Shared core** | `quality_core` → `schema` (flat + relational), `io`, `theme` |
| **Quality gate** | ruff + mypy + pytest/coverage; CI-enforced; `quality_core.io` & `.schema` gated at **100%**, SPC at ≥95% |

> **Roadmap rerouted (2026-07-10).** The plan's back half changed: instead of topping the platform
> with an AI copilot, we **complete the AIAG core-tools story** (APQP-adjacent loop, FMEA, SPC,
> Control Plan, **MSA**) and **prove it on real semiconductor data** (the SECOM dataset). The AI FMEA
> copilot moves to a documented **Deferred** phase at zero schedule cost. Rationale: real quality
> tools proven on real process data beat a synthetic demo with an AI headline. Details: §5, §9.

---

## 3. System architecture

The platform is a **uv workspace monorepo**: two Streamlit apps mounted under one shell, both
depending on a shared core package. Everything cross-cutting (data contracts, file IO, theme) is
written once in `quality_core` and consumed twice.

```mermaid
flowchart TB
    subgraph Shell["Unified shell (app.py · st.navigation)"]
        Home["🏠 Landing page"]
    end

    subgraph Apps["Apps"]
        FMEA["📋 FMEA Risk Analyzer<br/>apps/fmea<br/>RPN + AIAG-VDA Action Priority"]
        SPC["📈 Manufacturing SPC Dashboard<br/>apps/spc<br/>control charts · capability · live sim"]
        CP["🧩 Control Plan connector<br/>apps/controlplan (Week 6)"]:::planned
        MSA["📏 MSA / Gage R&R<br/>apps/msa (Week 8)"]:::planned
    end

    subgraph Core["packages/quality-core — quality_core"]
        Schema["schema/<br/>fmea (flat rows) · relational · _base"]
        IO["io/<br/>export (CSV/Excel/PDF) · validate (ingest)"]
        Theme["theme/<br/>palette · style"]
    end

    Home --> FMEA & SPC & CP & MSA
    FMEA --> Schema & IO & Theme
    SPC  --> IO & Theme
    CP   --> Schema
    MSA  --> Schema & IO & Theme
    SPC  -.consumes schema (Week 7).-> Schema

    classDef planned stroke-dasharray: 5 5,opacity:0.7;
```

**Key architectural choices**
- **Shared core, consumed twice.** `quality_core.io` owns CSV/Excel/PDF export (with formula-injection
  escaping) and validated ingest, so both tools are guaranteed identical on those boundaries. This is
  the "economic argument" of the monorepo made concrete.
- **Schema promoted only when stable.** Schema stayed inside the FMEA app until Week 5, then was
  promoted to `quality_core.schema` (deferred extraction — done once, correctly), so SPC / Control
  Plan can share one contract.
- **History-preserved migration.** The two apps were previously standalone repos; they were brought
  in with full commit history intact.

---

## 4. The target workflow: closed-loop quality

The architectural payoff (Weeks 6–7) is turning the bundle into a **workflow** — the AIAG core-tools
loop, actually implemented end to end:

```mermaid
flowchart LR
    A["FMEA<br/>identify failure modes,<br/>score S·O·D → RPN / Action Priority"]
    B["Control Plan<br/>failure mode → characteristic,<br/>spec/tolerance, method, sample n/freq,<br/>recommended SPC chart, reaction plan"]
    C["SPC<br/>monitor the characteristic;<br/>control charts + capability (Cp/Cpk)"]
    A -->|"high-risk items<br/>become controls"| B
    B -->|"auto-configures<br/>the SPC view"| C
    C -->|"out-of-control signal →<br/>occurrence-rating feedback / CAPA"| A
```

> A user walks **FMEA → Control Plan → SPC → back to FMEA** without leaving the platform. Today the
> three surfaces exist (SPC + FMEA live; Control Plan lands Week 6); the *connections* are Weeks 6–7.

---

## 5. The 12-week plan (phase flow)

```mermaid
flowchart TB
    subgraph PA["Phase A · Foundation (Wk 1–2)"]
        W1["Wk1 v0.1.0<br/>Monorepo + core + shell + CI"]
        W2["Wk2 v0.2.0<br/>SPC engineering parity"]
    end
    subgraph PB["Phase B · Standards-correct cores (Wk 3–5)"]
        W3["Wk3 v0.3.0<br/>AP-native FMEA"]
        W4["Wk4 v0.4.0<br/>Shared validation + export"]
        W5["Wk5 v0.5.0<br/>Relational FMEA + schema→core"]
    end
    subgraph PC["Phase C · Integration & core-tool completion (Wk 6–9)"]
        W6["Wk6 v0.6.0<br/>Control Plan connector"]
        W7["Wk7 v0.7.0<br/>Close the loop ⭐"]
        W8["Wk8 v0.8.0<br/>MSA / Gage R&R module"]
        W9["Wk9 v0.9.0<br/>SECOM semiconductor case study ⭐"]
    end
    subgraph PD["Phase D · Depth & legibility (Wk 10–12)"]
        W10["Wk10 v0.10.0<br/>Modern SPC depth (cuttable)"]
        W11["Wk11 v0.11.0<br/>DOE on SECOM + JMP"]
        W12["Wk12 v1.0.0-portfolio<br/>Legibility + hardening"]
    end
    DEF["Deferred · AI FMEA copilot<br/>LLM + RAG + evals — unscheduled"]:::deferred
    W1-->W2-->W3-->W4-->W5-->W6-->W7-->W8-->W9-->W10-->W11-->W12
    W12 -.-> DEF

    classDef done fill:#1b5e20,color:#fff;
    classDef active fill:#e65100,color:#fff;
    classDef deferred stroke-dasharray: 5 5,opacity:0.6;
    class W1,W2,W3,W4,W5 done;
    class W6 active;
```

- **Phase A — Foundation (Wks 1–2):** one repo, one quality bar, shared theme, shell. *De-risks everything.*
- **Phase B — Standards-correct cores (Wks 3–5):** FMEA goes AP-native + relational; SPC gets shared validation + export. *Both tools become individually credible.*
- **Phase C — Integration & core-tool completion (Wks 6–9):** Control Plan connector, the FMEA↔CP↔SPC loop, the MSA / Gage R&R module, and the SECOM real-semiconductor case study. *The platform becomes a workflow, completes the AIAG core-tools story, and runs on real process data.* ← **we are here**
- **Phase D — Depth & legibility (Wks 10–12):** modern SPC depth (first thing cut if the schedule tightens), DOE screening on SECOM, then a legibility + hardening pass ending in **v1.0.0-portfolio**.
- **Deferred — AI FMEA copilot:** the old Weeks 9–11 (LLM + RAG + eval harness) and the Week-12 architecture-fork gate are documented in §9 but **unscheduled**. They reopen only if they become the priority again.

*Rerouted 2026-07-10 (post-v0.5.0): the AI phase was replaced by MSA + SECOM so every remaining week
either completes an AIAG core tool or proves the platform on real semiconductor data.*

*Dates are targets at ~35 hrs/week (Mon-start, Sun-ship). Rule: if a week can't ship green, cut
scope, not quality.*

---

## 6. Tech stack & the quality gate

**Stack**
- **Language:** Python 3.11
- **UI:** Streamlit (multipage `st.navigation` shell) + Plotly / Matplotlib charts
- **Data / validation:** pandas, **Pydantic v2** (typed schema contracts)
- **Export:** openpyxl (Excel), fpdf2 + matplotlib (PDF), CSV — all injection-safe
- **Tooling:** **uv** (workspace + locked deps), **ruff** (lint/format), **mypy** (strict types), **pytest** + pytest-cov
- **CI/CD:** GitHub Actions (`.github/workflows/ci.yml`) on Python 3.11 via `astral-sh/setup-uv`; deploy on Streamlit Cloud
- **Planned (Wk 9):** the SECOM dataset (UCI) — real semiconductor sensor data with pass/fail yield labels
- **Deferred (AI copilot):** Claude via the Anthropic API (LLM + RAG) with an eval harness + guardrails — unscheduled, see §9

**The gate (runs locally *and* in CI on every push/PR to `main`):**

```bash
uv sync                 # install workspace + dev tools (locked)
uv run ruff check .     # lint
uv run mypy             # type-check
uv run pytest --cov     # tests + coverage across packages + apps
```

**Dedicated coverage gates (CI-enforced, cannot silently regress):**

| Surface | Bar |
|---------|-----|
| `quality_core.io` (shared export + ingest) | **100%** |
| `quality_core.schema` (shared FMEA contracts) | **100%** |
| SPC testable surface (engine + simulation + visualizer + exporter + schema) | **≥95%** |

**Workflow discipline:** one logical change per commit (conventional commits) · one issue at a time
· multi-agent code review before finishing · push → CI green → close issue → tag a release each week.

---

## 7. Repository layout

```
quality-platform/
├── app.py                     # unified platform shell (st.navigation)
├── shell/                     # landing page + shared chrome
├── ROADMAP.md                 # ← this file
├── README.md
├── pyproject.toml             # uv workspace + pytest/coverage config
├── ruff.toml · mypy.ini       # one quality bar for the whole workspace
├── .github/workflows/ci.yml   # the gate + per-surface coverage gates
│
├── packages/
│   └── quality-core/          # shared core package  →  import quality_core
│       └── src/quality_core/
│           ├── schema/         # fmea.py (flat FMEARow/FMEADataset)
│           │                   # relational.py (Function→FM→Effect/Cause/Control + adapters)
│           │                   # _base.py (StrictModel, find_duplicates — shared validators)
│           ├── io/             # export.py (CSV/Excel/PDF) · validate.py (validated ingest)
│           └── theme/          # palette.py · style.py
│
└── apps/
    ├── fmea/                   # FMEA Risk Analyzer (full original history preserved)
    │   ├── app.py · fmea_app/  # rpn_engine, ap_engine, rating_scales, exporter, schema (re-export), charts
    │   └── data/               # composite_panel_fmea_demo.csv, input template
    └── spc/                    # Manufacturing SPC Dashboard (full original history preserved)
        └── spc_app/            # spc_engine (control_charts, capability, rule_detection),
                                # simulation, visualizer, exporter, pages/
```

---

## 8. What we've done — week by week

### ✅ Week 1 — Monorepo + shared core + shell · **v0.1.0** *(Phase A)*
- Created the public `quality-platform` monorepo; brought both standalone apps in under `apps/fmea`
  and `apps/spc` with **full commit history preserved**.
- Scaffolded `packages/quality-core`; merged the two apps' separate `theme.py` into `quality_core.theme`.
- One root toolchain — shared `ruff.toml`, `mypy.ini`, pytest config, and **one CI workflow** running
  the gate across the core + both apps (this gave SPC its first-ever CI).
- Built the Streamlit shell (`shell/`) with a landing page mounting FMEA + SPC under one nav; deployed
  to Streamlit Cloud (one live URL).

### ✅ Week 2 — SPC engineering parity · **v0.2.0** *(Phase A)*
- Brought SPC up to the shared engineering bar: ruff clean, mypy clean, coverage gate enforced,
  version single-source-of-truth, `CLAUDE.md` + assumptions log.
- Surfaced the implemented **c-chart** in the UI (killed dead-ish code).
- Domain win: a **stability gate** on the capability page — run rule detection first and warn if the
  process is out-of-control *before* reporting Cpk (an unstable process makes Cpk meaningless).

### ✅ Week 3 — AP-native FMEA · **v0.3.0** *(Phase B)*
- Implemented the full **AIAG-VDA Action Priority** engine (S×O×D → High / Medium / Low) alongside RPN,
  with a toggle to switch prioritization basis across app and exports.
- Data-driven, editable **S/O/D rating tables** (AIAG-VDA defaults or custom 1–10), replacing
  hardcoded thresholds.
- Wired the FMEA version single-source-of-truth.
- *(The AP rating table was later verified cell-by-cell against the AIAG-VDA handbook — a shifted
  S9–10 block was found and corrected.)*

### ✅ Week 4 — Shared validation + export · **v0.4.0** *(Phase B)*
- Extracted FMEA's **exporter** (Excel/PDF, CSV-injection-safe) and **validated ingest** into
  `quality_core.io` — written once, consumed by both apps.
- Wired **export to SPC**: downloadable control-chart + capability reports (Excel/PDF).
- Wired **validated CSV ingest to SPC**: a real schema boundary with friendly errors (no more bare
  `pd.read_csv`).
- Held `quality_core.io` at **100% coverage** with its own tests + a CI gate.

### ✅ Week 5 — Relational FMEA + schema → core · **v0.5.0** *(Phase B)*
- **✅ W05-1** — Promoted the (now-stable) FMEA schema into `quality_core.schema`
  (`FMEARow` / `FMEADataset`), re-exported from the FMEA app; added a 100% schema coverage gate.
- **✅ W05-2** — Added the **relational domain model** `quality_core.schema.relational`:
  **Function → FailureMode → Effect / Cause / Control**, with S/O/D placed per AIAG (**Severity on the
  Effect, Occurrence on the Cause, Detection on the Control**), plus **loss-less
  `flat_to_relational` / `relational_to_flat` adapters** so a flat dataset round-trips through the
  nested model and back, equivalent on the canonical columns. The model enforces the canonical
  invariants (ID uniqueness; no two entities share a `(description, rating)` pair; every entity is
  referenced by ≥1 link) so the round-trip is loss-less in both directions. Shared validators
  (`StrictModel`, `find_duplicates`) were factored into `schema/_base.py`.
- **✅ W05-3** — **Action tracking** with before/after S·O·D and effectiveness scoring (recommended
  action → owner → status → re-scored RPN/AP after completion).
- **✅ W05-4** — **Engine integration**: the relational model runs through the full
  validate → score → export pipeline with content-level export parity to the flat pipeline
  (test-proven); action-tracking columns surfaced in CSV/Excel/PDF exports.
- **✅ W05-5** — FMEA app **relational hierarchy view + action-tracking UI** (flat uploads
  auto-convert via the `flat_to_relational` adapter; new Relational and Actions tabs).
- **✅ W05-6** — Consolidated **schema guardrail contract test** (entity-addressed error reporting
  for malformed relational payloads); the 100% line+branch coverage gate on `quality_core.schema` held.
- **✅ W05-7** — Tagged **v0.5.0**.

---

## 9. Future work — weeks 6–12

### ⬜ Week 6 — Control Plan connector · **v0.6.0** *(Phase C)*
New `apps/controlplan`: ingests FMEA failure modes → emits a **Control Plan** (characteristic,
spec/tolerance, measurement method, sample size/frequency, **recommended SPC chart type**, reaction
plan). Its schema derives from `quality_core.schema`. FMEA → Control Plan round-trips, live in the shell.

### ⬜ Week 7 — Close the loop · **v0.7.0** *(Phase C · the architectural headline)*
SPC **consumes** the Control Plan (a characteristic's spec / n / frequency / chart-type
auto-configures the SPC view) and **emits** out-of-control signals back toward FMEA as candidate
occurrence-rating feedback / a CAPA hook. The full FMEA → Control Plan → SPC → FMEA loop works in one
platform.

### ⬜ Week 8 — MSA / Gage R&R module · **v0.8.0** *(Phase C)*
New MSA surface over the same shared core (validated ingest, typed schema, export, theme):
- **Gage R&R study** — repeatability (equipment variation) and reproducibility (appraiser variation)
  by the **Average-and-Range method**; the **ANOVA method** if time allows.
- **Outputs:** %GRR vs **study variation** and vs **tolerance**, **ndc** (number of distinct
  categories), and a clear **accept / marginal / reject** verdict against AIAG thresholds
  (ndc ≥ 5; %GRR < 10% good, 10–30% marginal, > 30% reject).
- *(stretch)* bias, linearity, and stability studies.
- **Loop link:** the Control Plan names a measurement method per characteristic — MSA proves that
  measurement system is capable *before* the SPC chart on it can be trusted.

### ⬜ Week 9 — SECOM semiconductor case study · **v0.9.0** *(Phase C · the real-data week ⭐)*
Wire the **SECOM dataset** (UCI — real semiconductor manufacturing sensor data with pass/fail yield
labels) through the platform's tools, inside the platform (not a separate repo):
- **SPC:** control charts on selected sensor signals — in-control vs special-cause behavior on real
  process data.
- **Capability:** real **Cp / Cpk** on individual sensor characteristics against their limits.
- **MSA:** a Gage R&R where a repeated-measure structure exists or can be constructed; otherwise a
  plain-English note on why MSA needs a designed measurement study.
- **Yield / DPPM:** pass/fail counts as a defect-rate view + a **Pareto of failing signals**.
This turns the platform from a synthetic demo into an analysis of real semiconductor process data.

### ⬜ Week 10 — Modern SPC depth · **v0.10.0** *(Phase D · first to cut if the schedule tightens)*
**Phase I/II** control-limit freezing (establish from a baseline, then monitor new data against frozen
limits); **EWMA + CUSUM** small-shift charts; *(stretch)* non-normal (Box-Cox) capability + confidence
intervals.

### ⬜ Week 11 — DOE screening on SECOM · **v0.11.0** *(Phase D)*
One **screening analysis** on the most influential SECOM signals — which factors move the response —
capstoning the platform's real-data story. *(Paired externally with the JMP-STIPS statistics
curriculum so the DOE method is both applied and certified.)*

### ⬜ Week 12 — Portfolio release · **v1.0.0-portfolio** *(Phase D)*
Legibility + hardening pass: 60-second README, hosted demo, short demo video/GIF, architecture
diagram, plain-English framing for a non-domain reviewer — then tag **v1.0.0-portfolio**.

### 🅿️ Deferred — AI FMEA copilot *(documented, unscheduled)*
The original Phase D/E content, preserved as a future phase. Reopens only if it becomes the priority
again.
- **Copilot (build):** an **LLM + RAG** assistant — given a component / function / process step,
  suggest failure modes / effects / causes / controls + S/O/D, **each with a rationale**, grounded on
  AIAG standards + prior FMEAs. Human-in-the-loop (accept/edit); **never auto-commits**.
- **Copilot (trust):** an **eval harness** (reference set + scoring), hallucination guardrails,
  rationale display, cost controls — *then* ship. Built on Claude via the Anthropic API.
- **AI on SPC:** explainable **special-cause interpretation** (*"Rule 2 fired at point 17 → probable
  mean shift; candidate causes from the linked FMEA"*).
- **Architecture-fork gate:** the deliberate go/no-go on a FastAPI + React/Next + Supabase rewrite —
  only relevant if a full-stack fork or a real product signal appears.

---

## 10. Release history

| Version | Week | Theme | Status |
|---------|------|-------|--------|
| **v0.1.0** | 1 | Monorepo + shared core + shell + unified CI | ✅ released |
| **v0.2.0** | 2 | SPC engineering parity | ✅ released |
| **v0.3.0** | 3 | AP-native FMEA (AIAG-VDA Action Priority) | ✅ released |
| **v0.4.0** | 4 | Shared validation + export (`quality_core.io`) | ✅ released |
| **v0.5.0** | 5 | Relational FMEA + schema → core | ✅ released |
| **v0.6.0** | 6 | Control Plan connector | ⬜ planned |
| **v0.7.0** | 7 | Close the loop (FMEA↔CP↔SPC) | ⬜ planned |
| **v0.8.0** | 8 | MSA / Gage R&R module | ⬜ planned |
| **v0.9.0** | 9 | SECOM semiconductor case study | ⬜ planned |
| **v0.10.0** | 10 | Modern SPC depth (Phase I/II, EWMA/CUSUM) | ⬜ planned |
| **v0.11.0** | 11 | DOE screening on SECOM | ⬜ planned |
| **v1.0.0-portfolio** | 12 | Legibility + hardening (portfolio release) | ⬜ planned |
| *(deferred)* | — | AI FMEA copilot + AI on SPC + architecture-fork gate | 🅿️ unscheduled |

---

## 11. How to run & develop

**Run the unified platform (recommended):**
```bash
uv run streamlit run app.py      # one URL: Home + FMEA + the three SPC workflows
```

**Run a single app standalone (unchanged from its original repo):**
```bash
cd apps/fmea && streamlit run app.py
cd apps/spc  && streamlit run app.py
```

**Develop / verify (the full gate):**
```bash
uv sync                 # install workspace + dev tools (locked)
uv run ruff check .     # lint
uv run mypy             # type-check
uv run pytest --cov     # tests + coverage
```

> `uv` lives at `~/.local/bin/uv`. Every push/PR to `main` runs the same gate in CI; `main` should
> require the **CI / gate** status check before merging.

---

## 12. Glossary

| Term | Meaning |
|------|---------|
| **FMEA** | *Failure Mode & Effects Analysis* — structured method to identify how a process/product can fail, the effects, causes, and controls, and to prioritize risk. |
| **RPN** | *Risk Priority Number* = Severity × Occurrence × Detection (1–10 each). The classic FMEA prioritization number. |
| **AIAG-VDA Action Priority (AP)** | The modern replacement for RPN: a lookup from the S·O·D combination to **High / Medium / Low** action priority, per the AIAG-VDA FMEA handbook. |
| **S / O / D** | *Severity* (how bad the effect), *Occurrence* (how often the cause happens), *Detection* (how likely current controls catch it) — each rated 1–10. In the relational model: **S on the Effect, O on the Cause, D on the Control**. |
| **Relational FMEA** | The nested domain model **Function → FailureMode → Effect / Cause / Control** (vs. the flat one-row-per-combination representation), with loss-less adapters between the two. |
| **Control Plan** | The AIAG document linking each characteristic to its spec/tolerance, measurement method, sample size/frequency, control method (often an SPC chart), and reaction plan. |
| **SPC** | *Statistical Process Control* — monitoring a process over time with **control charts** to distinguish normal variation from special causes. |
| **Control chart** | A time-series chart with control limits (e.g. X̄-R, I-MR, c-chart) used to detect out-of-control conditions. |
| **Western Electric / Nelson rules** | Standard pattern rules (e.g. "point beyond 3σ", "2 of 3 beyond 2σ") that flag special-cause signals on a control chart. |
| **Cp / Cpk / Pp / Ppk** | Process **capability** indices — how well a stable process fits within its spec limits (Cpk also accounts for centering). |
| **Phase I / Phase II** | SPC practice of *establishing* control limits from a baseline (Phase I) then *monitoring* new data against those frozen limits (Phase II). |
| **EWMA / CUSUM** | Control charts tuned to detect **small, sustained shifts** faster than standard charts. |
| **MSA** | *Measurement Systems Analysis* — the AIAG core tool that quantifies how much of observed variation comes from the measurement system itself, before trusting the data. |
| **Gage R&R / %GRR** | The MSA study splitting measurement variation into **repeatability** (same appraiser, same gage) and **reproducibility** (between appraisers); %GRR compares it to study variation or tolerance (AIAG: <10% good, 10–30% marginal, >30% reject). |
| **ndc** | *Number of distinct categories* a measurement system can reliably distinguish in the data; AIAG requires **ndc ≥ 5**. |
| **SECOM** | A public UCI dataset of real semiconductor manufacturing sensor readings with pass/fail yield labels — the platform's real-data case study (Week 9). |
| **Yield / DPPM** | Semiconductor QE vocabulary: the fraction of units passing, and *Defective Parts Per Million* — the defect-rate view of pass/fail counts. |
| **DOE** | *Design of Experiments* — structured experimentation (here: a screening analysis) to find which factors actually move a response. |
| **CAPA** | *Corrective And Preventive Action* — the follow-up loop when a problem/signal is found. |
| **RAG** | *Retrieval-Augmented Generation* — grounding an LLM's answers in retrieved source documents (here: AIAG standards + prior FMEAs) to reduce hallucination. |
| **uv** | Fast Python package/workspace manager (by Astral) used for locked deps and the monorepo workspace. |

---

*This document tracks the plan; the **GitHub Milestones** and **issues** track the live state. When
they disagree, the milestones win — and this file should be updated to match.*
