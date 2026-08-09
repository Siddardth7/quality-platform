# Web Platform Migration — Scope & Approach

**Status:** scoped · decisions locked · ready for issue breakdown
**Date:** 2026-07-26
**Supersedes:** `frontend-migration.md` §1–§8 (Reflex default path) — **Reflex is cancelled**
**Activates:** `frontend-migration.md` §11 (React + FastAPI), via the §10 GO-FULL gate
**Amends:** `showcase-website.md` — the separate-repo decision is **reversed** (§2.1)
**Driver:** the website **becomes the product** — a surface presentable to a hiring manager as a real application

---

## 1. Decision and why it's consistent

**Stop the Reflex migration. Build a real web application** — FastAPI over `quality_core` plus a Next.js frontend — with the landing page as the first web deliverable and the five tools migrated one at a time behind it.

Not a plan reversal. `frontend-migration.md` §10 defined three GO-FULL triggers; the third fires exactly:

> *"You want the frontend itself as a senior full-stack hiring artifact and can budget the XL."*

With **no deadline**, both halves are satisfied. Reflex was the right answer to the *old* driver (portfolio polish at minimum cost). The driver changed; the answer changes with it.

### 1.1 Locked decisions

| # | Decision | Choice |
|---|---|---|
| 1 | Repo structure | **Single repo** — `web/` at root inside `quality-platform` |
| 2 | Frontend stack | **Next.js 16 App Router** + TypeScript + Tailwind |
| 3 | Design system | **Deferred** — decided by building the landing page first |
| 4 | First web deliverable | Landing + `/projects` + `/decisions` |
| 5 | `apps/api` coverage gate | **100%** line + branch |
| 6 | Streamlit page deletion | **Per-tool**, during migration |
| 7 | API hosting | Free tier + a real loading state; upgrade only if it demonstrably hurts |
| 8 | Audit execution | New **`/auditor`** agent → proposes findings → you approve → issues → `/ship` |
| 9 | Audit issue granularity | **One issue per theme**, findings as a checklist inside |
| 10 | Audit gating | **Audit blocks the API** — never publish a contract over unverified math |
| 11 | Monorepo | Stays whole. No polyrepo split. |

---

## 2. ⚠️ Two corrections to earlier decisions

### 2.1 The separate web repo is reversed — one repo

`showcase-website.md` decided a **separate repo** for the site. That was correct **for its premise**: a standalone static showcase that only *linked* to the app — different language, different cadence, no shared contract.

**That premise died when the website became the app.** The frontend now consumes the API through a generated type contract, so an API change and a frontend change are **one logical change**. Two repos make every P4 tool migration two PRs plus a contract sync — the identical version-lockstep cost we rejected for `quality_core`. The monorepo argument was applied to Python and not to the frontend; correcting that now.

| | Two repos | **One repo** |
|---|---|---|
| Tool migration (P4) | 2 PRs + contract sync | 1 commit, 1 gate |
| OpenAPI → TS drift | possible between deploys | **impossible** — same commit |
| Weekly release signal | split across two changelogs | unbroken, one semver line |
| Deploy | native | native (Vercel/Cloudflare support subdirectory roots) |
| Cross-repo doc drift (`showcase-website.md` §9.1) | a real problem to mitigate | **dissolved** |

**Location: top-level `web/`, not `apps/web/`.** The uv workspace is `members = ["packages/*", "apps/*"]`; a Node app under `apps/` gets globbed as a Python workspace member and needs an exclusion hack. Top-level `web/` avoids it.

**The portfolio-hub concern is solved by routing, not repos** — `/` hub, `/projects`, `/app/*`. If toolkit #2 ever arrives, extract the hub *then*, knowing what it actually needs. Extraction later is cheap; coordinating two repos for months is not.

### 2.2 The coverage-gap audit is dropped

Four audit areas were requested. One is invalid:

| Requested | Verdict | Rationale |
|---|---|---|
| **Coverage gap — 3,122 ungated LOC** | ❌ **DROP** | That's `apps/*/pages/` + `apps/fmea/ui/` + `shell/` — the Streamlit presentation layer, which this migration **deletes**. Testing code scheduled for removal is pure waste. |
| **Domain correctness vs AIAG/VDA** | ✅ **DO — first** | Verifies the engines about to become a public API contract. Highest credibility value. |
| **Security, dependencies, dead code** | ✅ **DO** | The API widens the trust boundary; input validation matters more once endpoints are public. |
| **Architecture & code quality** | ✅ **DO — survivors only** | `quality_core` + engines (~8,900 LOC). Skip the pages, same reason as row 1. |

**Principle: audit what survives the migration, not what it replaces.**

The 3,122 LOC doesn't go untested — it **decomposes**:

```
Streamlit page  (untestable — needs a runtime)
      ├──→  business logic  ──→  FastAPI handler   (Python · pytest · 100% gate)
      └──→  view logic      ──→  React component   (TS · Vitest · gated)
```

Coverage improves as a **structural consequence** of the migration rather than through effort spent on doomed code.

---

## 3. Target architecture

```
quality-platform/                      ← ONE repo, one gate, one semver line
  packages/quality-core/                   schema · io · scoring · theme tokens
  apps/{fmea,spc,msa,controlplan,secom}/   engines (KEEP) · Streamlit pages (DELETE per-tool)
  apps/api/                            ← NEW · FastAPI over quality_core · 100% gate
  web/                                 ← NEW · Next.js 16 · TS · Tailwind
      app/                                 /  ·  /projects  ·  /decisions
      app/app/{fmea,spc,capability,msa,control-plan}/
  .github/workflows/ci.yml                 job: gate (py)  ·  job: web-gate (ts)
  .claude/agents/auditor.md            ← NEW · read-only
  .claude/commands/audit.md            ← NEW · Team Lead orchestration
```

**Why this shape**

- **`apps/api` imports `quality_core` directly** — must share the workspace and the gate.
- **`quality_core.schema` (Pydantic v2) is already the contract.** FastAPI consumes it; `openapi-typescript` generates the TS types. One source of truth across two languages — a genuinely strong architecture claim, and the W05 schema-promotion finally paying off.
- **Landing/content pages are SSG** — served from a CDN, instantly. This is the real fix for the cold-start finding (`showcase-website.md` §3.4).

### 3.1 Explicitly NOT building

`frontend-migration.md` §2's warning applies at full force: *"Do not let it become an excuse to build auth/RBAC/multi-tenancy for users who don't exist yet."*

| Deferred | Why | Revisit when |
|---|---|---|
| **Auth / login** | A hiring manager will not sign up. Auth is *friction* on a demo, not polish. | Real multi-user need |
| **Database / Supabase** | Every tool is stateless compute→render. Nothing to persist. | "I want to save and return to an FMEA" |
| **Multi-tenancy, RBAC, audit trails** | No users | A committed/paying user |
| **Realtime** | Nothing to push | Same |

**The apps being stateless is what makes this migration affordable.** Session state lives client-side in React. Adding a database now means building the hardest part of a SaaS for zero users — **the single most likely way this plan fails.**

---

## 4. The `/auditor` role

A fifth team member, fitting the existing `research → coder → tester → reviewer` pipeline.

**Read-only, always.** An auditor that fixes code bypasses `/ship` entirely — findings would land without research → code → test → review, and outside CI. That is precisely what the pipeline exists to prevent.

```
/audit <scope>
   │
   ├─ auditor agent  (READ-ONLY: Read · Grep · Glob · WebFetch · read-only Bash)
   │     └─ writes .pipeline/audit-<scope>.md — findings, severity-ranked, file:line
   │
   ├─ Team Lead triages → proposes a themed issue list
   ├─ SME approves / rejects / edits                          ← you are the gate
   ├─ gh issue create — one issue per theme, findings as a checklist
   └─ each issue runs through /ship as a normal feature branch
```

| Scope | Covers |
|---|---|
| `/audit domain` | AIAG/VDA handbook verification — SPC constants, Cp/Cpk/Pp/Ppk, AP tables, Gage R&R, `ndc`, thresholds |
| `/audit security` | Dependency/supply-chain, secrets, input validation at trust boundaries, dead code |
| `/audit architecture` | Coupling, duplication, structural drift across `quality_core` + the five engines |

**Issue convention:** one issue per theme (e.g. *"Verify SPC control-chart constants against AIAG SPC 4th Ed."*) with findings as a checklist. Keeps the milestone readable and each issue sized to one `/ship` rung.

---

## 5. Sequencing

One person — so phases are sequential, and each ships something. The working app never breaks.

| Phase | Work | Ships | Blocks |
|---|---|---|---|
| **P0** | Build `/auditor` + `/audit`; issue breakdown | the pipeline | — |
| **P1 · Audit** | `/audit domain` · `/audit security` · `/audit architecture` → themed issues → `/ship` each | verified core + audit reports | **blocks P3** |
| **P2 · Web foundation** | `web/` · Next.js · **landing** · `/projects` · `/decisions` · design system falls out of building | **the public site, live** | — |
| **P3 · API** | `apps/api` FastAPI over `quality_core`; OpenAPI schema; TestClient tests @ 100% | tested, documented API | needs P1 |
| **P4 · Tool migration** | Strangler fig, one tool per rung; delete each Streamlit page as it lands | one tool per release | needs P2+P3 |
| **P5 · Cutover** | Retire the Streamlit deploy · `v1.0.0` | the product | — |

### 5.1 ⚠️ One reorder from your answer — flagging it, not slipping it

You answered *"P1 blocks P2 — audit the core before it becomes an API."* The intent is unambiguous: **never publish an API over unverified math.** That is preserved exactly.

But I've **swapped web foundation ahead of the API**, because the landing page needs no API at all. Consequences:

- ✅ A **public artifact ships earlier** — if the plan stalls anywhere later, the highest-value piece is already live
- ✅ The **design-system decision resolves sooner** (decision #3 — you chose to settle it by building)
- ✅ Routing, deploy pipeline, and the TS gate exist **before** any tool depends on them
- ✅ Audit still strictly precedes the API — your actual constraint, untouched

If you'd rather API-before-web, say so and I'll swap them back.

### 5.2 Tool migration order (P4)

By state complexity — `frontend-migration.md` §3.3's analysis still holds:

1. **Process Capability** — pure `render_capability()`, zero session state → **the pilot**
2. **SPC charts** — 2 session-state sites
3. **MSA / Gage R&R** — 0 session-state sites
4. **Control Plan** — 4 session-state sites
5. **FMEA relational editor** — **55 of ~59 session-state sites.** The long pole. Last, budget most.

Each rung: endpoint → view → verify parity against the Streamlit page → **delete the Streamlit page** → release. Streamlit stays live for every tool not yet migrated.

---

## 6. The quality gate across two languages

Your strongest signal is *"one quality bar, CI-enforced, cannot silently regress."* Two languages must not become one gated language and one ungated one.

| Job | Paths | Lint | Types | Tests | Coverage |
|---|---|---|---|---|---|
| `gate` | `packages/**`, `apps/**` | ruff | mypy strict | pytest | existing bars + **`apps/api` 100%** |
| `web-gate` | `web/**` | eslint | `tsc --noEmit` | vitest + playwright | components + one real E2E path |

Both required on protected branches.

**Non-negotiable:** `web/` ships with its gate green from its **first commit**, never retrofitted. A second language without a gate is worse than not adding it.

**Contract testing is the seam that matters.** Generate TS types from the OpenAPI schema in CI and fail on drift. That makes two gates one system — a stronger claim than either alone. In a single repo this is a same-commit check, not a cross-repo race.

---

## 7. Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | **Scope creep into auth/DB/SaaS** | **High** | §3.1 deferral table with explicit triggers. Revisit only when one fires. |
| 2 | **Losing the weekly-release cadence** — your rarest signal | **High** | Every phase slices into weekly rungs; P1 and P4 are naturally one-per-release. |
| 3 | **Audit becomes unbounded** | **High** | Read-only agent · themed issues · you approve before anything is filed · each issue sized to one `/ship`. |
| 4 | **Breaking the working app mid-migration** | Medium | Strangler fig. Streamlit stays live per-tool until its replacement reaches parity. No big-bang cutover. |
| 5 | **The TS gate never materializes** | Medium | §6 — green from commit #1, non-negotiable. |
| 6 | **API cold start** re-creates the §3.4 problem at tool level | Medium | Landing/content is SSG, unaffected. Tools get a real loading state. Upgrade to always-on (~$5/mo) if it demonstrably hurts — decision #7. |
| 7 | **XL effort (~10–13 wks) slips** | Medium | No deadline; every phase ships independently. P2 alone is a complete deliverable. |
| 8 | **Half-migrated `main`** carrying dead Streamlit pages | Low | Per-tool deletion (decision #6). |

---

## 8. Doc changes this triggers

- **`ROADMAP.md`** — Week 12 (Reflex) cancelled. Phase D replaced by this plan. `v1.0.0-portfolio` now means the web platform.
- **`frontend-migration.md`** — mark §1–§8 superseded; §10 GO-FULL fired; §11 is the active path. **Keep the document whole** — a decision revisited when its driver changed is a stronger interview artifact than the original recommendation was.
- **`showcase-website.md`** — §7.1's static-front-door reasoning still holds and is now served by Next.js SSG. **§9's separate-repo decision and §9.1's cross-repo drift mitigation are void** (§2.1 above).
- **`docs/AGENT_TEAM_FRAMEWORK.md`** — add the `auditor` role.
- **README badge** — 410 → 815 tests. Still stale. Fix independently.
- **Epic #107** — stays open; its scope is now this plan.

---

## 9. Ready to start

P0 is the only thing not yet specified in enough detail to execute: build `.claude/agents/auditor.md` and `.claude/commands/audit.md`, then run `/audit domain` as the first real exercise of the pipeline.
