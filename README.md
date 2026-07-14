<!-- ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  HEADER  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ -->

<a href="https://quality-platform-nplyhc6rvsd3bfw6q9vvkd.streamlit.app/">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0b1220,60:1a2f4a,100:e65100&height=200&section=header&text=Quality%20Platform&fontSize=54&fontColor=ffffff&fontAlignY=40&desc=The%20AIAG%20core%20quality%20toolset%20%E2%80%94%20unified,%20typed,%20and%20tested&descAlignY=62&descSize=16" alt="Quality Platform" width="100%">
</a>

<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=600&size=21&pause=1200&color=E65100&center=true&vCenter=true&width=780&height=45&lines=FMEA+//+SPC+//+Control+Plan+//+MSA;The+AIAG+core+toolset%2C+actually+connected;Proven+on+real+semiconductor+data+(SECOM);One+core+//+one+quality+gate+//+one+URL" alt="Quality Platform tagline">

<br>

[![CI](https://github.com/Siddardth7/quality-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Siddardth7/quality-platform/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-410%20passing-2ea043?logo=pytest&logoColor=white)](#-the-quality-gate)
[![Coverage](https://img.shields.io/badge/coverage-core%20100%25%20%C2%B7%20SPC%20%E2%89%A595%25-2ea043)](#-the-quality-gate)
[![Release](https://img.shields.io/github/v/release/Siddardth7/quality-platform?sort=semver&color=e65100&label=release)](https://github.com/Siddardth7/quality-platform/releases/latest)
[![Last commit](https://img.shields.io/github/last-commit/Siddardth7/quality-platform?color=1a2f4a)](https://github.com/Siddardth7/quality-platform/commits/main)

[![Python 3.11](https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white)](.python-version)
[![uv](https://img.shields.io/badge/built%20with-uv-261230?logo=astral&logoColor=white)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/badge/lint-ruff-261230?logo=ruff&logoColor=white)](https://github.com/astral-sh/ruff)
[![mypy](https://img.shields.io/badge/types-mypy-2a6db2)](https://mypy-lang.org/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)

<br>

**A working manufacturing-quality engineering platform — the AIAG core tools (FMEA, SPC, Control Plan, MSA)<br>brought under one URL, one typed core, and one CI-enforced quality bar.**

<br>

<a href="https://quality-platform-nplyhc6rvsd3bfw6q9vvkd.streamlit.app/"><img src="https://img.shields.io/badge/%E2%96%B6%20Live%20Demo-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Live Demo"></a>
&nbsp;
<a href="ROADMAP.md"><img src="https://img.shields.io/badge/%F0%9F%97%BA%20Roadmap-0b1220?style=for-the-badge" alt="Roadmap"></a>
&nbsp;
<a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/%F0%9F%A7%A9%20Contributing-1a2f4a?style=for-the-badge" alt="Contributing"></a>
&nbsp;
<a href="CHANGELOG.md"><img src="https://img.shields.io/badge/%F0%9F%93%9D%20Changelog-1a2f4a?style=for-the-badge" alt="Changelog"></a>

</div>

---

## 🔎 What this is

In real quality departments, the **AIAG / IATF-16949 core tools** live in disconnected spreadsheets and
one-off apps. A failure mode found in an **FMEA** never automatically becomes a control on a **Control
Plan**, and an out-of-control point on an **SPC** chart never flows back to update the FMEA's risk
rating. The methodology *describes* a closed loop; the tooling almost never *implements* one.

**Quality Platform builds that loop for real** — credible standalone tools first, everything they share
promoted into a single typed core (`quality_core`), then wired into an end-to-end workflow, and
**proven on real semiconductor process data**. Every week ships a tested, released rung. *No week ships a
stub.*

> Built in public, one release per week, on a strict green-gate discipline — an engineering portfolio
> that doubles as a genuinely usable quality toolkit.

---

## 🖥️ See it running

<div align="center">
<table>
  <tr>
    <td width="50%" valign="top">
      <img src="assets/fmea-risk-dashboard.png" alt="FMEA Risk Analyzer dashboard with risk-tier KPIs and auto-generated insight"><br>
      <sub><b>🛡️ FMEA Risk Analyzer</b> — RPN &amp; AIAG-VDA Action Priority, risk-tier triage, auto-generated insight.</sub>
    </td>
    <td width="50%" valign="top">
      <img src="assets/spc-control-chart.png" alt="Xbar-R control chart with Western Electric rule overlays"><br>
      <sub><b>📈 SPC Control Charts</b> — X̄-R / I-MR / c-charts with Western Electric &amp; Nelson rule overlays.</sub>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <img src="assets/capability-gauge.png" alt="Process capability Cpk gauge with a stability-gate warning"><br>
      <sub><b>📊 Process Capability</b> — Cp/Cpk/Pp/Ppk with a <b>stability gate</b>: no capability claim on an out-of-control process.</sub>
    </td>
    <td width="50%" valign="top">
      <img src="assets/platform-home.png" alt="Unified platform shell landing page"><br>
      <sub><b>🏭 Unified shell</b> — every tool under one <code>st.navigation</code> surface, one theme, one URL.</sub>
    </td>
  </tr>
</table>

**▶ [Open the live demo →](https://quality-platform-nplyhc6rvsd3bfw6q9vvkd.streamlit.app/)**

</div>

---

## 🔄 The closed loop

The architectural payoff: the AIAG core-tools loop, wired end to end and run on real data.

```mermaid
flowchart LR
    FMEA["🛡️ FMEA<br/>score S·O·D →<br/>RPN / Action Priority"]
    CP["🧩 Control Plan<br/>failure mode → characteristic,<br/>spec, method, sample plan,<br/>recommended chart"]
    SPC["📈 SPC<br/>control charts +<br/>capability (Cp/Cpk)"]
    MSA["📏 MSA / Gage RR<br/>is the measurement<br/>system even trustworthy?"]
    SECOM[("🏭 SECOM<br/>real semiconductor<br/>process data")]

    FMEA -->|"high-risk items<br/>become controls"| CP
    CP -->|"auto-configures<br/>the chart"| SPC
    SPC -->|"out-of-control →<br/>occurrence feedback / CAPA"| FMEA
    MSA -.->|"prove the gage<br/>before trusting the chart"| SPC
    SECOM -.->|"runs through<br/>every tool"| SPC

    classDef live fill:#0b1220,stroke:#e65100,stroke-width:2px,color:#fff;
    classDef soon fill:#0b1220,stroke:#2a6db2,stroke-width:1.5px,color:#cfe3ff,stroke-dasharray:4 4;
    class FMEA,SPC live;
    class CP,MSA,SECOM soon;
```

---

## 🧰 The tools

| Tool | What it does | Status |
| ---- | ------------ | ------ |
| **🛡️ FMEA Risk Analyzer** | Failure Mode &amp; Effects Analysis — RPN + AIAG-VDA **Action Priority**, editable S/O/D scales, relational model (Function → FM → Effect / Cause / Control), action tracking, Pareto + risk heatmap, Excel/PDF/CSV export | ![live](https://img.shields.io/badge/-live-2ea043) |
| **📈 SPC Dashboard** | Statistical Process Control — variables &amp; attributes control charts, Western Electric / Nelson rules, Cp/Cpk/Pp/Ppk **with a stability gate**, live disturbance simulator | ![live](https://img.shields.io/badge/-live-2ea043) |
| **🧩 Control Plan connector** | Turns FMEA failure modes into a Control Plan (characteristic, spec, method, sample plan, recommended chart) — the APQP-adjacent bridge that closes the loop | ![v0.6.0](https://img.shields.io/badge/-next%20%C2%B7%20v0.6.0-e65100) |
| **📏 MSA / Gage R&amp;R** | Measurement Systems Analysis — Gage R&amp;R (Average-and-Range; ANOVA), %GRR vs study &amp; tolerance, `ndc`, accept/marginal/reject vs AIAG thresholds | ![v0.8.0](https://img.shields.io/badge/-planned%20%C2%B7%20v0.8.0-2a6db2) |
| **🏭 SECOM case study** | The whole platform run on **real semiconductor sensor data** — SPC, real Cp/Cpk, yield/DPPM, Pareto of failing signals | ![v0.9.0](https://img.shields.io/badge/-planned%20%C2%B7%20v0.9.0-2a6db2) |

> Standards context: **FMEA** — AIAG-VDA (2019) + AIAG FMEA-4 · **SPC** — AIAG SPC 4th Ed. · capability target **Cpk ≥ 1.33**.
> The AIAG-VDA Action Priority table is verified cell-by-cell against the primary handbook.

---

## 🏗️ Architecture

A **uv workspace monorepo**: independent Streamlit apps mounted under one shell, every cross-cutting
concern written **once** in `quality_core` and consumed by all of them.

```mermaid
flowchart TB
    subgraph Shell["🏭 Unified shell · app.py (st.navigation)"]
        Home["Landing + one theme + one nav"]
    end
    subgraph Apps["Apps"]
        FMEA["🛡️ FMEA<br/>apps/fmea"]
        SPC["📈 SPC<br/>apps/spc"]
        CP["🧩 Control Plan<br/>apps/controlplan · next"]:::soon
        MSA["📏 MSA<br/>apps/msa · planned"]:::soon
    end
    subgraph Core["📦 packages/quality-core → import quality_core"]
        Schema["schema/<br/>flat + relational contracts (Pydantic v2)"]
        IO["io/<br/>validated ingest · CSV/Excel/PDF export"]
        Theme["theme/<br/>palette · style"]
    end

    Home --> FMEA & SPC & CP & MSA
    FMEA --> Schema & IO & Theme
    SPC --> IO & Theme
    CP --> Schema
    MSA --> Schema & IO & Theme

    classDef soon opacity:0.7,stroke-dasharray:4 4;
```

**Why it's built this way**
- **Shared core, consumed many times.** `quality_core.io` owns CSV/Excel/PDF export (formula-injection
  safe) and validated ingest — so upload validation and export are *guaranteed identical* across tools.
  That's the economic argument of a monorepo, made concrete and coverage-gated at 100%.
- **Schema promoted only when stable.** Contracts lived inside the FMEA app until they earned promotion
  to `quality_core.schema` — deferred extraction, done once, correctly.
- **History preserved.** The FMEA and SPC apps were previously standalone repos, migrated here with
  **full commit history intact** — the histories are part of the engineering story.

---

## 🚀 Quickstart

```bash
# 1 · clone
git clone https://github.com/Siddardth7/quality-platform.git
cd quality-platform

# 2 · install the locked workspace (uv lives at ~/.local/bin/uv)
uv sync

# 3 · run the whole platform — one URL, every tool
uv run streamlit run app.py
```

<details>
<summary><b>Run a single app standalone</b></summary>

```bash
cd apps/fmea && streamlit run app.py   # FMEA Risk Analyzer
cd apps/spc  && streamlit run app.py   # SPC Dashboard
```
Each app still runs unchanged from its own directory.
</details>

---

## 🛡️ The quality gate

The whole workspace shares **one** quality bar (`ruff.toml`, `mypy.ini`, pytest config in
`pyproject.toml`). It runs locally and, identically, in CI on **every push and PR to `main`** — a
protected branch that requires the gate to pass before merge.

```bash
uv run ruff check .     # lint + format check
uv run mypy             # strict static types
uv run pytest --cov     # 410 tests + coverage across core + apps
```

**Coverage gates — CI-enforced, cannot silently regress:**

| Surface | Bar |
| ------- | --- |
| `quality_core.io` — shared export + ingest | **100%** |
| `quality_core.schema` — shared FMEA contracts | **100%** (line + branch) |
| SPC testable surface — engine + simulation + visualizer + exporter | **≥ 95%** |

**Workflow discipline:** one logical change per commit (conventional commits) · one issue at a time ·
multi-agent code review before finishing · push → CI green → close issue → tag a release each week ·
if a week can't ship green, **cut scope, not quality**.

---

## 🗺️ Roadmap

Twelve tracked weeks, one release each, ending on a portfolio-grade `v1.0.0`.

| Phase | Weeks | Focus |
| ----- | ----- | ----- |
| **A · Foundation** | 1–2 | Monorepo, shared core, shell, one CI gate · `v0.1–v0.2` ✅ |
| **B · Standards-correct cores** | 3–5 | AP-native + relational FMEA, shared validation/export · `v0.3–v0.5` ✅ |
| **C · Integration & core-tool completion** | 6–9 | Control Plan → close the loop → **MSA** → **SECOM** real-data case study |
| **D · Depth & legibility** | 10–12 | Modern SPC depth, DOE on SECOM, then a hardening pass → **`v1.0.0-portfolio`** |

<sub>An explainable **AI FMEA copilot** (LLM + RAG + eval harness) is a documented, unscheduled future
phase. The full plan — vision, diagrams, week-by-week detail — lives in **[ROADMAP.md](ROADMAP.md)**.</sub>

---

## 📁 Repository layout

```
quality-platform/
├── app.py                  # unified platform shell (st.navigation)
├── shell/                  # landing page + shared chrome
├── ROADMAP.md              # the full project guide (vision, diagrams, 12-week plan)
├── packages/
│   └── quality-core/       # shared core  →  import quality_core
│       └── src/quality_core/
│           ├── schema/     # flat (FMEARow) + relational (Function→FM→…) contracts
│           ├── io/         # validated ingest · CSV/Excel/PDF export (injection-safe)
│           └── theme/      # palette · style
└── apps/
    ├── fmea/               # FMEA Risk Analyzer  (full original history preserved)
    └── spc/                # Manufacturing SPC Dashboard  (full original history preserved)
```

<sub>Migrated from the standalone repos
[`fmea-risk-analyzer`](https://github.com/Siddardth7/fmea-risk-analyzer) and
[`manufacturing-spc-dashboard`](https://github.com/Siddardth7/manufacturing-spc-dashboard),
now archived → moved here.</sub>

---

## 🧱 Built with

<div align="center">

![Python](https://img.shields.io/badge/Python%203.11-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458?logo=pandas&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic%20v2-E92063?logo=pydantic&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?logo=plotly&logoColor=white)
![uv](https://img.shields.io/badge/uv-261230?logo=astral&logoColor=white)
![Ruff](https://img.shields.io/badge/Ruff-261230?logo=ruff&logoColor=white)
![mypy](https://img.shields.io/badge/mypy-2A6DB2)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?logo=pytest&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)

</div>

---

<div align="center">

**New here?** Start with the **[ROADMAP.md](ROADMAP.md)** · **Contributing?** See **[CONTRIBUTING.md](CONTRIBUTING.md)** and the [Definition of Done](docs/DEFINITION_OF_DONE.md).

<br>

<sub>Manufacturing-quality engineering, built like software — typed, tested, and shipped weekly.</sub>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:e65100,40:1a2f4a,100:0b1220&height=120&section=footer" alt="" width="100%">

</div>
