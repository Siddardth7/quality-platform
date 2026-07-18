# Frontend Migration — Scoping & Recommendation (reconciled)

**Status:** research / decision doc (no code changes)
**Author:** Team Lead synthesis — reconciles two independent research passes (Claude + Kimi)
**Date:** 2026-07-18
**Branch:** `docs/frontend-migration-research`
**Driver (SME-confirmed):** (1) portfolio / investor / recruiter polish — a branded "real product" surface with marketing/landing pages Streamlit can't produce; (2) escape *specific* Streamlit walls, named concretely below. **Not selected:** "real users / product" (multi-user auth, teams, persistence). Timing left to this doc.

---

## 0. How to read this doc

Two independent research passes were run: one by **Claude** (codebase-grounded, recommended **Reflex**), one by **Kimi** (broad 10-option survey, recommended **React + FastAPI + Supabase**). They **agree on the foundation** and **diverge on the frontend target** — and the divergence is entirely about *which driver* is being served. This document reconciles them:

- **Default path (your chosen driver):** **Reflex**, via strangler-fig, Weeks 10–12 (§1–§8).
- **Documented escalation (only if a real product signal appears):** **React + FastAPI + Supabase** (§11) — which is exactly what your own `ROADMAP.md` already defers to that condition.
- **Decision gate to choose between them:** the Go/No-Go framework (§10), adopted from Kimi.

§9 is the head-to-head reconciliation and fact-check. If you read one section, read §9.

---

## 1. Executive summary & recommendation

**Recommendation: migrate to [Reflex](https://reflex.dev/) (Python-native, compiles to React), via a strangler-fig, starting *after* v0.9.0 (SECOM), landing as the spine of Weeks 10–12 so that v1.0.0-portfolio ships on the new surface.**

Why this is the leanest path that actually satisfies the driver:

- **Polishing Streamlit fails the driver.** No amount of CSS makes Streamlit read as a *branded product* to an investor — shallow theming, vertical-flow layout, no real landing page. Keep it as the *bridge*, not the destination (§5).
- **A full Next.js/React SPA over-buys.** Highest polish ceiling, but XL effort, a second language, and a JS test/type stack the current gates don't cover — two codebases to demo four calculators. Not justified *by the current driver* (but see §11 for when it would be).
- **Reflex hits ~90% of the polish ceiling for a fraction of that effort** and **preserves `quality_core` and every quality gate unchanged**, because those were never coupled to Streamlit (§3). One language, real React output, true URL routing, 60+ styleable components, Tailwind/custom CSS, SEO landing pages, built-in auth. It imports your pure Python engines directly; the only thing thrown away is the disposable Streamlit page layer that was always meant to be disposable.

**The single most important finding:** the gated, correctness-bearing surface of this repo (`quality_core.io`/`schema`/`scoring` + the SPC engine/visualizer/exporter + the FMEA/Control-Plan engines) is **already 100% Streamlit-free**. Exactly **one** file in `quality_core` imports `streamlit` (`packages/quality-core/src/quality_core/theme/style.py`, a 116-line CSS injector). The migration is therefore not a rewrite — it's a **presentation-layer swap** on top of a portable core the team already extracted (the W05 promotions to `quality_core`). Roughly **2:1 keep-to-throwaway** by LOC. The full suite is at **815 tests**, all green.

**The durable decision is the API boundary, not the framework.** Reflex auto-generates a Starlette/FastAPI backend, so "Reflex now" already gives you the FastAPI seam over `quality_core`. If a product signal later justifies hand-written React/Next + a database, you swap the *frontend* without touching the core or the API (§11). That makes Reflex a low-regret first step, not a dead end.

---

## 2. Ponytail gut-check — do you even need to migrate?

Yes, but only because the driver is *explicitly* portfolio polish + a branded product surface — a want Streamlit structurally cannot serve. If the driver were "ship more quality features," the answer would be **no, stay on Streamlit**. Hold that line: this migration buys **presentation**, not capability. Do not let it become an excuse to re-architect the (already clean) core, or to build auth/RBAC/multi-tenancy for users who don't exist yet.

The lazy version of "a real product surface" is **not** a React rewrite. It is: keep the pure Python you already have, swap the ~2,265 lines of Streamlit pages for a framework that emits real React from Python. That's Reflex. Everything heavier is unrequested ceiling **until a product signal changes the driver** — at which point §11 is the deliberate, gated upgrade, not an impulse.

---

## 3. Codebase grounding (the keep-vs-throwaway line)

### 3.1 What's portable (KEEP — pure, typed, tested Python)

| Surface | Path | LOC | Streamlit? |
|---|---|---|---|
| Shared core: schema / io / scoring / palette | `packages/quality-core/src/quality_core/` | 1,631 | **No** (except `theme/style.py`) |
| SPC engine + simulation | `apps/spc/spc_app/spc_engine/`, `apps/spc/spc_app/simulation/` | 695 | **No** |
| SPC Plotly figure builders | `apps/spc/spc_app/visualizer.py` | (in above tree) | **No** |
| FMEA engines (RPN, AP, exporter, schema, rating scales, plotly) | `apps/fmea/fmea_app/` | 1,723 | **No** |
| Control Plan connector + exporter + schema | `apps/controlplan/controlplan_app/{connector,exporter,schema}.py` | 541 | **No** |

Verified: `grep -rl 'import streamlit' apps/fmea/fmea_app/` → **none**; same for the Control-Plan engine files; only `quality_core/theme/style.py` imports `streamlit` inside the core package. **~4,600 LOC of logic is framework-agnostic and moves unchanged.**

Two portability bonuses that make any option cheaper:
- **Plotly is framework-agnostic.** `visualizer.py` / `fmea_app/plotly_charts.py` return `plotly` figures — they render in Reflex (`rx.plotly`), Dash, *and* React (`react-plotly.js`). The chart layer ports with a one-line host swap.
- **Export bytes are pure.** `quality_core/io/export.py` and each app's exporter build `bytes` (CSV/xlsx/PDF) with **no Streamlit** — the OWASP formula-injection escaping (`sanitize_for_export`, `FORMULA_PREFIXES` at `packages/quality-core/src/quality_core/io/export.py:37-79`) lives here. Only the `st.download_button` wrapper is throwaway; the security boundary transfers intact.

### 3.2 What's disposable (THROWAWAY — the Streamlit presentation layer)

| Surface | Path | LOC |
|---|---|---|
| All app pages + FMEA UI widgets | `apps/*/**/pages/*.py`, `apps/fmea/ui/*.py` | 2,125 |
| Unified shell (`st.navigation` mount) | `app.py` | 139 |
| Theme CSS injector (design tokens survive, the injector doesn't) | `packages/quality-core/src/quality_core/theme/style.py` | 116 |

`theme/palette.py` (the amber/violet/dark **design tokens** + Inter font) is the brand system and carries over verbatim; the `[data-testid="stSidebar"]`-style selectors in `style.py:21-111` are Streamlit-internal and get rewritten as component styles.

### 3.3 The Streamlit coupling surface a migration must re-implement

Real `st.*` call sites in non-test source (histogram):

- `st.session_state` — **50** (statefulness)
- `st.markdown` 43, `st.sidebar` 37, `st.columns` 23 (layout/chrome)
- `st.download_button` 12, `st.file_uploader` 4 (I/O boundary)
- `st.data_editor` 3, `st.column_config` 10 (editable grids)
- `st.plotly_chart` 6, `st.dataframe` 7, `st.metric`/`st.error`/`st.warning`/… (render)

**The long pole is the FMEA relational editor.** Session state is concentrated there — **55** of the ~59 `session_state` sites live in `apps/fmea` (vs 4 in Control Plan, 2 in SPC, 0 in MSA), driving the `st.data_editor` grids in `apps/fmea/ui/relational.py`. SPC/MSA/Capability pages are mostly **stateless compute→render** (see `apps/spc/spc_app/pages/process_capability.py` — pure `render_capability()` with no session state), making them ideal **pilot pages**; FMEA's stateful editor is the piece to migrate last and budget most.

### 3.4 Quality bars that must survive (and why they transfer for free)

From `.github/workflows/ci.yml` (job `gate`) and `docs/DEFINITION_OF_DONE.md`:

- `quality_core.io` — **100%** line+branch
- `quality_core.schema` — **100%** line+branch
- `quality_core.scoring` — **100%** (AIAG-VDA AP table, cell-verified against the handbook)
- SPC testable surface (`spc_engine`+`simulation`+`visualizer`+`exporter`+`schema`) — **≥95%**
- Control Plan connector+schema — **100%**
- `ruff` clean, `mypy` clean (incl. `apps/controlplan` since #95), whole-suite no-regression

**Every gated surface above is Streamlit-free**, so **all coverage/type gates transfer 1:1 to any option.** The Streamlit `pages/` are *already excluded* from coverage ("they need a runtime"). Under Reflex those pages become plain Python `State` classes and event handlers — **testable without a browser**, so the migration can *raise* the covered fraction. This is the crux of why Reflex is low-risk here: the hard architectural work (pushing logic out of the view into a pure, tested core) is **already done**.

---

## 4. The option ladder (cheapest → heaviest)

This merges Claude's ladder with Kimi's fuller survey. The full 10-approach table is in Appendix A.

### Rung 0 — Stay & polish Streamlit
Custom theme + injected CSS (already done in `theme/style.py`), `streamlit-elements`, custom components (React bridges), `st.App` ASGI entry (2026 — custom routes/middleware + FastAPI mounting), custom domain, auth proxy.
**Ceiling (honest):** a *nicer Streamlit*, not a product. Layout stays vertical-flow; theming stays shallow; multipage is a `pages/` dir with **no true routing, nested layouts, or shared cross-page state**; custom components are sandboxed iframes with [documented limitations](https://docs.streamlit.io/develop/concepts/custom-components/components-v1/limitations). No real marketing/landing page. **Does not clear the driver.**

### Rung 1 — Python-native "sophisticated" frameworks (keep one language, import `quality_core` directly)
- **[Reflex](https://reflex.dev/) — recommended.** Compiles Python to a **real React** frontend + a Starlette/FastAPI backend; app logic and state stay in server-side Python. True URL routes + nested layouts + SEO pages, 60+ components, Tailwind/custom CSS, [built-in auth](https://reflex.dev/migration/streamlit/) (Local/Google/Magic-Link/Clerk). Reactive state model (no full-script rerun). `rx.plotly` renders your existing figures. Imports `quality_core`/engines unchanged.
- **[NiceGUI](https://nicegui.io/)** — FastAPI + Vue + Tailwind, backend-first, very fast to build. Lower ceiling than Reflex for a *branded marketing site*; great for internal tools.
- **[Dash/Plotly](https://dash.plotly.com/)** — best-in-class for dense dashboards, but **stateless self-contained callbacks** fight the stateful FMEA editor and get callback-heavy at scale; enterprise polish needs Dash Enterprise. Kimi rates this a *lateral* move — agreed.
- **Panel/HoloViz**, **Shiny for Python (Posit)** — strong for analytics dashboards; weaker "branded product" story; Kimi correctly flags Shiny's paid commercial hosting and thin ecosystem.

### Rung 2 — API boundary + lightweight frontend
FastAPI wrapping `quality_core` + **HTMX/Alpine** (server-rendered HTML fragments, ~35–40 KB JS, zero build — see [blakecrosley.com](https://blakecrosley.com/guides/fastapi-htmx)) or a small React island. "Expose the core as an API; the frontend becomes swappable."
**Tradeoff:** highest *flexibility* per unit polish and a clean seam, but you own a second templating/JS layer, request/serialization plumbing, and the editable-grid interactions by hand. **More effort than Reflex for the same 90% polish**, unless a public API is itself a goal.

### Rung 3 — Full SPA / full-stack
FastAPI backend + **[Next.js](https://nextjs.org/) 16.x** (current stable mid-2026) / Remix / SvelteKit — with a real DB + auth this becomes the §11 escalation target. Kimi surveys React / Next.js / Vue / SvelteKit variants here (Appendix A).
**Ceiling:** the best polish/branding ceiling and the "obviously a real product" feel. **Cost:** XL; two codebases, two languages; JS lint/type/test stack the current gates don't cover; you re-implement every calculator's UI in React. Justified only if the platform becomes a genuine multi-user product — see §10/§11.

### Comparison table (Rung heads; full 8-column matrix in Appendix A)

| Rung | Effort | `quality_core` reuse | Polish/brand ceiling | Gates transfer? | One language? | Auth story | Hosting |
|---|---|---|---|---|---|---|---|
| **0** Polish Streamlit | **S** | 100% | **Low** (fails driver) | Yes (unchanged) | Yes | Proxy only | Streamlit Cloud |
| **1 Reflex** ✅ | **M** | **100% unchanged** | **High** | **Yes, 1:1 + pages become testable** | **Yes** | Built-in | Reflex Cloud / any container |
| 1 NiceGUI/Dash | M | 100% | Med–High | Yes | Yes | Add-on/proxy | Any container |
| **2** FastAPI+HTMX | **M–L** | 100% (behind API) | High | Yes (+ new API tests) | No (adds templates/JS) | DIY/library | Any container |
| **3** Next.js SPA + DB | **XL** | 100% (behind API) | **Highest** | Core yes; **new JS stack ungated** | No | Full (NextAuth/Supabase) | Vercel + API host + DB |

---

## 5. Migration strategy — strangler-fig (recommended over big-bang)

Both research passes independently landed on strangler-fig — it's the right call. Big-bang means the platform is dark until all four apps + shell are rebuilt — a multi-week freeze that stalls the domain roadmap and risks the v1.0.0 date. Instead:

1. **Stand up Reflex** alongside the repo with **one pilot page** — `Process Capability` (stateless: `apps/spc/spc_app/pages/process_capability.py`). It imports the *same* `compute_capability`, `detect_we_violations`, `build_cpk_gauge`, and exporter functions. Proves the pattern (engine import, Plotly render, download endpoint, theme tokens) end-to-end with minimal state.
2. **Serve both:** Reflex serves migrated pages on the new branded shell + landing page; Streamlit keeps serving the rest behind the sidebar. Route by path.
3. **Migrate in order of ascending state:** MSA → SPC (3 pages) → Control Plan → **FMEA relational editor last** (the 55-session-state / `data_editor` long pole).
4. **Retire `app.py` + Streamlit** once FMEA lands. Delete `apps/*/pages/`, `apps/fmea/ui/`, `theme/style.py`; keep `theme/palette.py`.

Because the engines are shared, a page is "migrated" when its *view* is re-expressed — no logic is rewritten, and the gate on that logic never moves.

---

## 6. Hosting / deploy implications

Current: **Streamlit Community Cloud** follows `main`. Free, zero-ops, Streamlit-only.

Reflex emits a **static React frontend + a Python (Starlette/FastAPI) backend**, so hosting becomes a standard containerized Python app + static assets:

| Host | Fit | ~Cost | Notes |
|---|---|---|---|
| **Reflex Cloud** | One-command deploy of a Reflex app | free tier → paid | Lowest-friction for Reflex specifically |
| **Fly.io** | Container, global | ~$2–10/mo | Cheapest steady-state; IPv4/volumes add up |
| **Render** | "Boring production", auto-detects ASGI/uvicorn | $7/mo starter | Simple GitHub-push deploys |
| **Railway** | Fast prototyping, metered | ~$5/mo hobby | Great for preview envs |
| **Vercel** | Front-end + serverless; pairs with a separate Python API host | $0–20+ | Best for a Next.js (§11) split, overkill for Reflex |
| **Supabase / Neon** | Postgres + auth (only if §11) | free → $25/mo | Not needed for the polish driver |

**CI/CD fit:** the existing `gate` job (`ruff` + `mypy` + `pytest --cov` + per-surface floors) is unchanged — it tests Python. Add a build/deploy step on `main` (Render/Fly auto-deploy mirrors today's Streamlit-Cloud-follows-`main` flow). **Custom domain + preview deploys** (the branded-demo win) are first-class on Render/Railway/Fly/Vercel and absent on Streamlit Cloud — a concrete driver payoff. One `Dockerfile` for portability; `uv sync --frozen` already gives reproducible installs.

---

## 7. Auth (note, don't over-invest)

Not a current driver (single-user portfolio demo). When/if multi-user matters, Reflex ships **Local / Google / Magic-Link / Clerk** auth built-in — adopt then, not now. Until then, host-level basic-auth / access-proxy gates a demo page. **Do not build RBAC speculatively.** (Kimi's full Supabase-Auth + Postgres-RLS design is the right answer *for the §11 product scenario*, not for polish.)

---

## 8. Effort estimates & proposed timing

**Effort (T-shirt) to a v1.0.0-worthy branded surface:**

| Option | Size | Rationale |
|---|---|---|
| 0 Polish Streamlit | S | Doesn't reach the goal |
| **1 Reflex (recommended)** | **M** | Shell + landing + 4 apps re-viewed; engines reused; FMEA editor is the L sub-task |
| 2 FastAPI+HTMX | M–L | + API layer + hand-built interactions |
| 3 Next.js SPA (§11) | XL | Second codebase + ungated JS stack + DB/auth |

Within Rung 1: pilot Capability page **S** · SPC+MSA+Control-Plan views **M** · FMEA relational editor **L** · landing/marketing page **S–M**.

**Proposed timing against the roadmap:**

- **Weeks 7–9 (v0.7.0 close-the-loop, v0.8.0 MSA, v0.9.0 SECOM ⭐): stay on Streamlit.** These are the *content* headlines — what makes the portfolio piece worth showing. Do not divert them.
- **Optional de-risking spike (S):** during Week 8/9 slack, stand up Reflex + the Capability pilot behind a subdomain. Pure proof-of-pattern, no roadmap cost, kills the biggest unknown before committing Week 10.
- **Weeks 10–12: run the migration as the spine.** Reallocate the **Week 10 "modern SPC depth (first to cut)"** budget to the frontend track; carry through 11–12 so **v1.0.0-portfolio ships on Reflex** with the SECOM proof already in hand. Order: substance (Wk 7–9) → surface (Wk 10–12) → release.

If the schedule tightens, the fallback is not "half-migrate" — it's **ship v1.0.0 on Streamlit and slip the migration to a v1.1.0 track.** A half-migrated dual-surface release is worse than either whole one.

---

## 9. Reconciliation: Claude vs Kimi — the head-to-head

Two passes, two headline picks. This section is the honest fact-check and verdict.

### 9.1 Where they agree (the durable foundation — trust this)
- **Preserve `quality_core` + engines + tests; never rewrite the FMEA/SPC math in JS.** (Kimi §6 "Engine/Schema/Test Preservation Rules" = Claude §3.)
- **Put the core behind an API; the frontend becomes swappable.**
- **Strangler-fig, one tool at a time, Streamlit stays live during migration.**
- **Now is the inflection point** — the shared core is stable and extracted.

### 9.2 Where they diverge, and why
| | Claude (this doc's default) | Kimi |
|---|---|---|
| Headline | **Reflex** (Rung 1) | **React + FastAPI + Supabase** (Rung 3) |
| Implied driver | Portfolio polish, solo dev, no product signal | Become a real multi-user SaaS product |
| Effort | M (~Weeks 10–12) | 10–13 weeks full rewrite |
| Adds auth/DB/RBAC/realtime | No (deferred) | Yes (core of the plan) |

**The divergence is 100% about the driver.** You selected *portfolio polish* and explicitly **did not** select *real users/product*. Kimi's plan is the honest answer to the driver you *didn't* pick.

### 9.3 Fact-check of Kimi's linchpin claim
Kimi asserts (3×) that React+FastAPI+Supabase is *"the architecture the project's own ROADMAP.md already gates at Week 12 (v0.11.0, the GO/NO-GO architecture fork)."* **Verified against `ROADMAP.md` — this is wrong on every count:**
- **v0.11.0 = DOE screening on SECOM**, not a rewrite (`ROADMAP.md:359, 397`).
- **Week 12 = "Portfolio release — legibility + hardening"** (README, hosted demo, video, diagram) — explicitly *not* a React rewrite (`ROADMAP.md:364-366`).
- The React/Next + FastAPI + Supabase fork is under **🅿️ Deferred / unscheduled**, worded: *"the deliberate go/no-go on a FastAPI + React/Next + Supabase rewrite — **only relevant if a full-stack fork or a real product signal appears**"* (`ROADMAP.md:378-379, 399`).

So the roadmap treats Kimi's headline as a **conditional, deferred maybe**, gated on a product signal that — per your driver — has **not** appeared. Kimi presented a deferred conditional as the committed plan; that inflates its recommendation.

### 9.4 What Kimi gets genuinely right (adopted here)
- **Breadth:** 10 approaches individually evaluated → folded into Appendix A.
- **The Go/No-Go framework** → adopted as §10 (corrected).
- **The multi-user/auth/DB target** → kept as the §11 escalation branch (its correct home).
- **Hosting/cost specifics** and the **PyScript "offline edition"** side-idea → §12.

### 9.5 Where Kimi over-reaches (weighed down)
- **Over-buys against the driver** (builds auth/RBAC/Postgres/realtime for zero users) — the exact thing the Ponytail ladder exists to stop.
- **Not code-grounded:** cites "410+ tests" (**actually 815**), and its endpoint samples invent names (`calculate_rpn`, `rank_by_rpn`, `FMEAProject`, `export_to_excel`) not verified against the repo. This doc's numbers are from `grep`/coverage runs.
- **Under-weights its own math:** admits Reflex is 6–8 wks and emits real React, then demotes it mainly on *"hiring signal"* — but your driver is *investor/visual polish*, where the rendered product matters more than the framework's résumé legibility.
- **Timeline realism:** a 12-week React rewrite "in parallel" for a solo dev **is** the entire remaining roadmap; it would eat the actual differentiator (closed-loop engine + SECOM).

### 9.6 Verdict
**For your selected driver, Reflex (default) wins; Kimi's stack is the correct *escalation*, not the starting point.** They aren't rivals — Reflex's auto-generated FastAPI backend is the *first step toward* Kimi's architecture. Take the M-sized Reflex path now; if a product signal appears, escalate to §11 by swapping only the frontend, keeping `quality_core` and the API seam intact.

---

## 10. Go/No-Go decision framework (adopted from Kimi, corrected)

Run this at the **Week 9/10 boundary** (after SECOM), or sooner if a product signal appears. Note: your roadmap does **not** schedule the architecture fork — it defers it to "a real product signal," so this framework *is* the gate the roadmap points to.

**GO-LEAN → Reflex (this doc's default) if:**
- [ ] Driver is portfolio/investor polish (✅ confirmed) and no multi-user product signal has appeared.
- [ ] You want a branded, real-React surface without a second language or ungated JS stack.
- [ ] `quality_core` gates are green (✅ they are) so the migration is a view-swap, not a rewrite.

**GO-FULL → React + FastAPI + Supabase (§11) if:**
- [ ] A **real product signal** appears: inbound pilot interest, a paying/committed user, or a deliberate pivot to multi-tenant SaaS.
- [ ] Multi-user auth, per-project persistence, audit trails, or team RBAC become *requirements*, not speculation.
- [ ] You want the frontend itself as a senior full-stack hiring artifact and can budget the XL.

**NO-GO → stay on Streamlit + a standalone landing page if:**
- [ ] A hard external deadline (< ~4 weeks) precludes any migration → ship v1.0.0-portfolio on Streamlit with a separate branded landing page, migrate later.
- [ ] The remaining effort is better spent on domain depth (Weeks 7–9 content).

---

## 11. The escalation branch — React + FastAPI + Supabase (only on a product signal)

This is Kimi's recommendation, relocated to its correct trigger. **Do not build this now.** It becomes right the moment the driver changes from "polish" to "product."

**Target architecture:**
```
Frontend: React 19 + TypeScript + Vite + Tailwind + shadcn/ui + React Router (or Next.js 16 if SEO/SSR matters)
Backend:  FastAPI + Pydantic v2 + uv + quality_core engines (preserved, imported)
Data/Auth: Supabase (Postgres + Auth + RLS + Realtime + Storage) — or Neon + Clerk
Hosting:  Vercel (frontend) + Render/Fly/Railway (API) + Supabase (data)
```

**Why it's a clean escalation, not a restart:**
- `quality_core.schema` (Pydantic v2) *is already* the API contract — FastAPI consumes it directly; `openapi-typescript` generates the frontend types. The W05 schema-to-core promotion pays off here.
- The **API boundary you already stood up under Reflex** is the same seam — you replace the Reflex-generated frontend with hand-written React, backend and core unchanged.
- The 815 tests keep gating the engines; you *add* API tests (`httpx`/`TestClient`), component tests (Vitest), and E2E (Playwright). Additive, not destructive.
- The closed loop becomes a real API workflow (e.g. `POST /api/control-plans {fmea_id}` → SPC reads the CP characteristic/spec), and Supabase Realtime can push SPC out-of-control signals back to FMEA occurrence — the "workflow, not a bundle" thesis made literally true.

**What it costs (honest):** XL (~10–13 wks), a second language + JS gate stack, two deploys, and ongoing DB/auth surface. Worth it **only** when there are users to justify it. Effort estimate is Kimi's; treat endpoint names in Kimi's doc as illustrative — bind them to real `quality_core` functions at build time.

---

## 12. Side-differentiator — PyScript/WASM "offline edition" (optional flourish)

Kimi's Approach H, kept as a *small* portfolio differentiator, not an architecture. A single `/offline-calculator` page running the pure Python engines client-side via **[PyScript/Pyodide](https://pyscript.net/)** — upload a CSV, get FMEA scores / SPC charts / a PDF, **with no data leaving the browser**. Genuinely novel for defense/aerospace sensitivity, and it reuses the same framework-agnostic engines. Ceiling: WASM Python is 10–100× slower and Pyodide+pandas is a ~50–100 MB first load — fine for a *single showcase page*, not the platform. Build it (if at all) as one page *inside* the Reflex app, late, for flair.

---

## 13. Open questions for the SME

1. **Timing commit:** accept "migrate Weeks 10–12, v1.0.0 on Reflex," or must the SECOM case study (Wk 9) demo on the *new* surface — pulling the pilot into Week 9?
2. **Host:** any objection to leaving Streamlit Cloud? Render (simplest) / Fly (cheapest) / Reflex Cloud (least-friction)?
3. **Landing-page scope:** branded hero + tool launcher, or full marketing site (about, case-study write-up, contact)? Sizes S vs M.
4. **FMEA editor fidelity:** must the migrated FMEA keep the exact inline `st.data_editor` spreadsheet UX, or is a redesigned editing flow acceptable? (Sets FMEA = L vs XL.)
5. **Public API as a goal:** is exposing `quality_core` as a documented API a portfolio artifact in itself? If yes, Rung 2 (FastAPI+HTMX) rises vs Rung 1.
6. **Reflex lock-in tolerance:** Reflex is younger than Next.js. Comfortable with that maturity risk for the 1-language / gates-transfer payoff, or prefer the FastAPI+HTMX seam (Rung 2) that keeps the frontend fully swappable — and eases a later §11 escalation?
7. **Product-signal watch:** what concrete event flips you from GO-LEAN to GO-FULL (§10)? Naming it now prevents a premature rewrite.

---

## Appendix A — Full 10-approach survey (from Kimi's pass, condensed)

| # | Approach | Effort | Verdict | Note |
|---|---|---|---|---|
| A | Stay on Streamlit + polish | Low | ⚠️ ceiling remains | Bridge only |
| B | Shiny for Python / NiceGUI | Low–Med | ⚠️ niche | "Better Streamlit", not a product |
| C | **React + FastAPI + Supabase** | High | ✅ **escalation target (§11)** | Right *on a product signal* |
| D | Next.js + FastAPI | High | ✅ if SEO/SSR matters | Vercel-native; marketing site |
| E | Vue + FastAPI | Med–High | ✅ valid | Smaller ecosystem than React |
| F | SvelteKit + FastAPI | Med | ✅ solo-dev joy | Smallest ecosystem, bold pick |
| G | Gradio / Panel | Low | ❌ lateral | Same class as Streamlit |
| H | PyScript / WASM | Med–High | ⚠️ premature | Keep as §12 offline page |
| **I** | **Reflex** | **Med** | ✅ **default (§1)** | Python→React, gates transfer |
| J | Dash / Plotly | Low–Med | ⚠️ lateral | Better callbacks, same ceiling |

Kimi's 10-dimension star matrix (UI/perf/auth/DB/API/SEO/hiring/scalability/effort/ecosystem/solo-speed) is a useful artifact; its scores skew toward the full-SPA options because it implicitly scores against a *product* driver. Read it with §9.2 in mind.

## Appendix B — Corrections applied to Kimi's pass
- **"410+ tests" → 815** (current suite; Kimi's context predated Weeks 5–6).
- **Roadmap attribution** — architecture fork is **Deferred/unscheduled + conditional** (`ROADMAP.md:378-379, 399`), **not** v0.11.0 / Week 12.
- **API sample names** (`calculate_rpn`, `rank_by_rpn`, `FMEAProject`, `export_to_excel`) are illustrative — real symbols live in `apps/fmea/fmea_app/` and `quality_core`; bind at build time.
- **"Next.js 14" → 16.x** (current stable, mid-2026).

---

## Sources
- [Reflex](https://reflex.dev/) · [Reflex vs Streamlit (2026)](https://reflex.dev/migration/streamlit/) · [Reflex vs Plotly Dash](https://reflex.dev/blog/reflex-dash/) · [Top Python web frameworks 2026](https://reflex.dev/blog/2026-01-09-top-python-web-frameworks-2026/) · [GitHub: reflex-dev/reflex](https://github.com/reflex-dev/reflex)
- [NiceGUI](https://nicegui.io/) · [Streamlit/Dash/Reflex/Rio comparison](https://dev.to/sn3llius/a-quick-comparison-streamlit-dash-reflex-and-rio-57gf)
- [Streamlit 2026 release notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026) · [Streamlit custom-component limitations](https://docs.streamlit.io/develop/concepts/custom-components/components-v1/limitations)
- [FastAPI](https://fastapi.tiangolo.com/) · [FastAPI + HTMX no-build full-stack](https://blakecrosley.com/guides/fastapi-htmx)
- [React 19](https://react.dev/) · [Next.js releases](https://github.com/vercel/next.js/releases) · [Tailwind](https://tailwindcss.com/) · [shadcn/ui](https://ui.shadcn.com/) · [SvelteKit](https://kit.svelte.dev/)
- [Supabase](https://supabase.com/docs) · [Clerk](https://clerk.com/) · [Neon](https://neon.tech/)
- [PyScript / Pyodide](https://pyscript.net/)
- [PaaS comparison: Railway/Render/Fly/Vercel 2026](https://www.birjob.com/blog/paas-comparison-railway-render-fly-vercel-2026) · [Render FastAPI deployment](https://render.com/articles/fastapi-deployment-options)
- Internal: `ROADMAP.md` (§9 fact-check), `.github/workflows/ci.yml`, `docs/DEFINITION_OF_DONE.md`, `packages/quality-core/`
