# FMEA Risk Analyzer — Version Plan (0.1 → 1.0)

> **What this document is.** The single source of truth for *where this product is going and why*. It holds (a) a refreshed 2026 market/technology research pass and (b) the locked **0.1 → 1.0 version ladder** that turns today's MVP into an industry-standard, AI-assisted FMEA product a real quality team can adopt.
>
> **Relationship to other docs.** This supersedes `FUTURE_SCOPE_AND_MARKET_RESEARCH.md` as the active strategy doc; that file is left untouched as the original research record. Execution discipline (audit → fix → build → release, gates, conventional commits) still comes from `AUDIT_AND_ROADMAP_PROMPT.md` and `CLAUDE_CODE_PLAYBOOK.md`. Durable project context lives in `FMEA-Memory.md`.
>
> *Created: 2026-06-13. Status: ladder LOCKED; architecture decision (v0.4) OPEN.*

---

## 1. North star

**Integrate AI with manufacturing quality — make the Quality Engineer's job easier.**

FMEA is the first concrete instrument of that thesis: the most universal, standards-driven risk tool in manufacturing, currently stuck between an Excel "graveyard" at the low end and €5k+/seat enterprise suites at the high end. **v1.0 = a free-to-start, AP-native, AI-assisted, audit-trailed FMEA web product a real company can onboard and run seamlessly.**

---

## 2. 2026 research refresh

A focused research sprint (June 2026) updating the original strategy doc for the elevated AI-×-manufacturing north star. The original two gaps still hold; what changed is the *urgency and shape* of the AI opportunity and a sharper read on what actually blocks real-company adoption.

### 2.1 AI in manufacturing quality is now mainstream, not future

- **47%** of manufacturers use AI in quality processes — **up from 33% in 2025**; another **43%** plan to within two years; **51%** of AI users are already on **GenAI/LLMs**.
- Top AI use cases: **document automation (48%)**, training (46%), **defect detection (44%)**.
- **71%** expect quality spend to rise in 2026 (up from 60%); **63%** now treat quality as a company-wide strategic initiative (up from 38%).
- The pain is quantified: **78%** hit by labor/skills shortages, **85%** say it degrades product quality, **75%** had a recall in the last 5 years (59% of those cost **$10M–$50M**).
- *Source: Octave "Pulse of Quality in Manufacturing 2026" survey, n=2,263 directors, US/UK/DE.*

**Implication:** an AI copilot that makes a stretched QE faster is selling into an open, funded wound — not a speculative nice-to-have.

### 2.2 The academic literature already validates AP + AI-assisted FMEA

- Multiple 2025–26 papers on **LLM + RAG + multi-agent FMEA automation** (Lund/Cambridge *Design Science*; Springer *Int. J. System Assurance Eng. & Mgmt*) — automating failure-data extraction, risk identification, and AP/RPN scoring with humans in the loop.
- An MDPI paper, *"An Intelligent Framework for Implementing AIAG-VDA FMEA and Action Priority (AP) Assessment,"* targets exactly our headline feature.

**Implication:** the AP engine (v0.2) and AI copilot (v0.6) are where the field is moving — building them reads as domain-current, not derivative.

### 2.3 "Explainable AI" is the 2026 demand

As AI adoption grows, buyers explicitly demand **auditable rationale** for every AI recommendation (hybrid SPC-+-AI, "explainable AI" cited as a top 2026 QMS trend).

**Implication:** our AI must be **assistive + explainable + human-in-the-loop** — every suggestion carries a rationale and is accept/edit, never an opaque autofill.

### 2.4 The real adoption blocker is trust, not features

- Cloud QMS only displaced on-prem once vendors delivered **audit trails, RBAC, e-signatures, and validation evidence** for **FDA 21 CFR Part 11** and **IATF 16949**.
- Incumbents (Siemens Opcenter Quality, Octave/ETQ Reliance, MasterControl, PTC Windchill) embed FMEA inside closed-loop QMS, connected by **REST APIs**.

**Implication:** persistence + revision history/audit trail (v0.5), an API (v0.8), and a compliance posture (v0.9) are the *price of entry* for a company to adopt us — not optional polish.

### 2.5 The low-end middle is still unclaimed

The only notable free/OSS FMEA tool is the dated "Open FMEA" (SourceForge). A modern, AP-native, AI-assisted, audit-trailed, free-to-start tool has **no direct competitor** in that segment.

**Net thesis (sharpened):** *Be the AP-native, AI-assisted, audit-trailed FMEA tool that's as easy to start as a spreadsheet but trustworthy enough for a real quality team.*

---

## 3. The version ladder (LOCKED)

Each rung is one coherent, demoable, shippable theme. Today is re-based as **v0.1**.

> The code currently hardcodes `_TOOL_VERSION = "1.0.0"` in `src/exporter.py`. That is an internal artifact, **not** the product version. A real single-source-of-truth version (starting at `0.1.x`) gets wired up as part of v0.2.

| Ver | Theme | What ships | Research anchor |
|---|---|---|---|
| **0.1** | **MVP (today)** | Streamlit · RPN · CSV→charts/PDF/Excel · validation · 105 tests · live demo | Baseline |
| **0.2** | **Standards-correct core** | Full **AIAG-VDA AP engine** (S×O×D→H/M/L) shown beside RPN w/ toggle · editable/custom S/O/D rating tables w/ AP defaults · version SSOT | §2.2 — closes the #1 credibility gap |
| **0.3** | **Escape the spreadsheet** | Relational **Function→Failure Mode→Effect→Cause→Control** model (not flat rows) · **action tracking** (owner/due/status + before/after S/O/D) | §2.5 — structural thing Excel does badly |
| **0.4** | **Dashboard → product** *(major fork / go-no-go gate)* | **Architecture split:** API core (OpenAPI/Pydantic) + React/Next front end + Postgres/Supabase persistence + auth · save/load multiple FMEA **projects** · Streamlit retained as "labs" | "Product not dashboard"; foundation step |
| **0.5** | **Regulated-ready basics** | **Revision history / audit trail** · frozen issued versions · comments · shareable read-only links · RBAC | §2.4 — the real adoption blocker |
| **0.6** | **AI copilot (the "wow")** | **LLM+RAG assistant:** suggest failure modes/effects/causes/controls + S/O/D **with rationale**, grounded on standards + past FMEAs · explainable, accept/edit, human-in-loop | §2.1 + §2.3 — north star, most shareable |
| **0.7** | **Ongoing instrument** | Trend/analytics dashboard (risk burn-down across revisions, recurring causes, action burn-down) · **what-if simulation** (live S/O/D→AP/RPN/matrix) | Turns one-shot analysis into a monitored process |
| **0.8** | **Fits the QE's stack** | Industry **templates** (automotive PFMEA/DFMEA, ISO 14971 medical, electronics) · **public REST API** · QMS/PLM import-export | §2.4 — integration is how incumbents connect FMEA |
| **0.9** | **Enterprise trust** | SSO · e-signatures · validation evidence pack · observability/logging · scale + a11y · docs-as-product (arch diagram, API ref, design decisions) | §2.4 — the "engineering-standard bar" |
| **1.0** | **GA — adoptable** | Polished, multi-tenant, AP-native, AI-assisted, collaborative, integrable, compliance-aware. A real company onboards & runs FMEAs seamlessly. SemVer 1.0 = stable public API | The goal |

---

## 4. Per-version scope & definition of done

**v0.2 — Standards-correct core.** Implement the full AIAG-VDA 2019 Action Priority logic (the published S×O×D → High/Medium/Low rules) as a new engine path alongside RPN; user toggles the prioritization basis. Make S/O/D rating tables data-driven (load AIAG-VDA defaults or custom 1–10 scales) instead of hardcoded thresholds. Stand up a real version single-source-of-truth and make `_TOOL_VERSION` read from it. Update methodology docs + `ASSUMPTIONS_LOG.md`. *DoD:* AP column + toggle live in the app and exports; AP logic covered by tests against the published table; gate green.

**v0.3 — Escape the spreadsheet.** Move the data model from flat rows to the relational FMEA structure (Function → Failure Mode → Effect → Cause → Control). Add recommended-action tracking: owner, due date, status, and re-evaluated S/O/D (before/after). *DoD:* structured model round-trips through validation, scoring, and export; action records persist within a session; tests cover the new schema.

**v0.4 — Dashboard → product (architecture fork).** *Gated — see §5.* Split the proven Python analysis core behind an API (OpenAPI docs, Pydantic validation), build a real front end, and add a database so multiple FMEA projects can be saved/loaded. Keep Streamlit as an internal "labs" surface. *DoD:* a user can sign in, create/save/reopen named FMEA projects via the new stack; engine parity with v0.3; CI/CD + deploy pipeline visible.

**v0.5 — Regulated-ready basics.** Revision history with frozen "issued" versions, a change/audit log, comments, shareable read-only links, and role-based access. *DoD:* an issued version is immutable; every change is attributed and logged; a read-only link renders without auth.

**v0.6 — AI copilot.** An LLM+RAG assistant that, given a component/function/process step, suggests likely failure modes, effects, causes, controls, and S/O/D ratings — each with a rationale and an accept/edit action, grounded on standards + the user's prior FMEAs. *DoD:* suggestions are explainable, never auto-committed, and measurably speed up authoring; guardrails + evals in place.

**v0.7 — Ongoing instrument.** Trend/analytics dashboard (risk reduction across revisions, top recurring causes, action burn-down) and live what-if simulation (adjust S/O/D, watch AP/RPN and the risk matrix update). *DoD:* analytics reflect real revision history; what-if recompute is instant and correct.

**v0.8 — Fits the QE's stack.** Industry templates (automotive PFMEA/DFMEA, ISO 14971 medical-device risk, electronics), a documented public REST API, and import/export to common QMS/PLM formats. *DoD:* a new user can start from a template in one click; the API is documented and exercised by tests.

**v0.9 — Enterprise trust.** SSO, e-signatures, a validation evidence pack, structured logging/observability, performance at scale, accessibility, and docs-as-product (architecture diagram, API reference, design-decisions write-up). *DoD:* the "engineering-standard bar" from §2.4 is met and demonstrable.

**v1.0 — GA.** Everything above, polished, multi-tenant, documented, and deployed such that a real company can onboard and run FMEAs without hand-holding. SemVer 1.0.0 marks a stable public API contract.

---

## 5. Sequencing & the v0.4 go/no-go gate

- **v0.2 + v0.3 are the near-term "do-it" block.** Cheap, high-credibility, no architecture risk, and they stay in the current Streamlit repo. They harden the core and force a real data model — exactly what makes a later migration clean.
- **v0.4 is the real commitment gate.** This is where we decide *"yes, this becomes a standalone product"* and pay the migration cost (API + front end + database + auth). We make that call deliberately — a **go/no-go checkpoint** — once v0.2–0.3 prove the core is right and the appetite is confirmed. (This is the "decide if it has potential for the elaborate website" checkpoint.)
- **Tier discipline holds:** ship each rung cleanly and green before starting the next; one logical change per commit; full gate (`pytest --cov`, `ruff`, `mypy`) + `/review` after each.

---

## 6. Architecture note (decision OPEN, to be finalized before v0.4)

The leading candidate is the stack already proven on the author's `job-pipeline` → **HyreAgent-ai** migration:

- **Front end:** React / Next.js (Vite) — a real product UI, not a dashboard.
- **Persistence + auth:** Supabase (Postgres) — rows, RLS, audit-friendly.
- **Analysis core:** the existing Python engine, exposed behind an API (FastAPI or serverless functions) — our Pydantic v2 schema layer ports cleanly.
- **Deploy:** serverless (Vercel/Netlify) with visible CI/CD.

Streamlit remains the "labs"/internal surface. Alternatives to weigh at the gate: FastAPI-on-Render, or a Next-only full-stack. **The formal architecture decision is a separate step and will be recorded before any v0.4 work begins.**

---

## 7. Open decisions & next steps

1. **Architecture decision** (this is the next working step) — choose and record the v0.4 stack.
2. **Decompose the ladder into GitHub issues**, sorted per milestone — same playbook as `job-pipeline` → HyreAgent-ai.
3. Begin **v0.2 (AP engine)** implementation under the standard build discipline.

---

## Sources (June 2026 refresh)

- Octave Intelligence / Censuswide — *Pulse of Quality in Manufacturing 2026* (n=2,263). globenewswire.com release, 2026-06-03.
- *Top QMS Trends for 2026: AI, eQMS, Predictive Quality & Industry 4.0* — Quality Magazine.
- *AI-driven FMEA: integration of LLMs for faster, more accurate risk analysis* — Lund University / Cambridge *Design Science*.
- *A framework for automating FMEA using LLMs and RAG* — Springer, *Int. J. System Assurance Engineering & Management* (2026).
- *An Intelligent Framework for Implementing AIAG-VDA FMEA and Action Priority (AP) Assessment* — MDPI *Applied Sciences*.
- Siemens Opcenter Quality — FMEA / closed-loop QMS capabilities.
- *Cloud Quality Management System: The Definitive Guide* & *21 CFR Part 11 Compliance for SaaS/Cloud* — eLeaP.
- *6 Best FMEA Software for 2026* — Centrum FMEA; *Open FMEA* — SourceForge.
- Carried forward from `FUTURE_SCOPE_AND_MARKET_RESEARCH.md`: AIAG-VDA AP replacement of RPN (2019), Excel "spreadsheet graveyard," FMEA market structure & pricing.
