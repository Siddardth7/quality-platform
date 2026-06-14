# Claude Code Operating Playbook — FMEA Risk Analyzer

> **What this file is.** The instruction manual for running the audit-and-build program inside the **Claude Code terminal**. It tells Claude *which document to read when*, *which model to use for which job* (Opus plans, Sonnet executes), and *which skills/commands to invoke at each step*. Paste this whole file into a fresh Claude Code session, or say: **"Read CLAUDE_CODE_PLAYBOOK.md and run the program."**

---

## The three documents and how they relate

You are working with a three-document system. Read them in this order and use them for these purposes:

1. **`CLAUDE_CODE_PLAYBOOK.md`** (this file) — *how to operate*: model strategy, session flow, skills. Start here.
2. **`AUDIT_AND_ROADMAP_PROMPT.md`** — *the execution plan*: 10 phases across three stages (AUDIT → FIX → BUILD → RELEASE), each with substeps and gates. This is your step-by-step script.
3. **`FUTURE_SCOPE_AND_MARKET_RESEARCH.md`** — *what to build and why*: the market-gap analysis and the Tier 1/2/3 feature roadmap. You only open this at the BUILD stage (Phase 9).

Rule of thumb: **this file = how, the audit prompt = the steps, the research doc = the backlog.**

---

## Model strategy: Opus plans, Sonnet executes

Use the right model for the right cognitive load. Switch models with `/model` in the terminal.

| Use **Opus** for (PLAN) | Use **Sonnet** for (EXECUTE) |
|---|---|
| Reading & interpreting all three documents | Writing the code for a planned change |
| Phase 1 recon and forming the audit strategy | Running tests, lint, type-check, scanners |
| Diagnosing root causes of complex/ambiguous bugs | Applying a fix that's already specified |
| Designing refactors and the feature architecture (Phase 9.3) | Mechanical edits, renames, boilerplate, test scaffolding |
| Writing `AUDIT_REPORT.md` and prioritizing the fix queue | Implementing one queue item per commit |
| The SemVer bump decision and release reasoning (Phase 10.1) | Generating the changelog, running the release checklist |
| Any "what should we do / why" judgment call | Any "do this specified thing" mechanical work |

**The handoff pattern that makes this work:**

1. **Opus plans → writes the plan down.** Opus must leave behind an artifact Sonnet can follow without re-deriving context: an entry in `AUDIT_REPORT.md`, a checklist of edits, or a `ROADMAP.md` item with acceptance criteria and exact file:line targets. *A plan that lives only in Opus's head cannot be handed off.*
2. **Switch `/model sonnet`.** Point Sonnet at the written plan: "Implement queue item #N from AUDIT_REPORT.md. Specs are there. One commit, tests green, then stop."
3. **Sonnet executes one bounded unit, then reports.** It does not improvise scope. If it hits ambiguity or the plan is wrong, it stops and escalates back to Opus rather than guessing.
4. **Switch `/model opus` to review** anything high-stakes (security fixes, architecture changes, the release) or when Sonnet got stuck.

Keep units small: one bug or one feature slice per Sonnet pass. Small units keep Sonnet accurate and keep the git history clean.

---

## Best skills & commands for each job

Install once at the start; fall back to the Bash equivalent if a plugin is unavailable.

**Setup (run first):**
- `/plugin marketplace add knowledge-work-plugins` then `/plugin install engineering` — unlocks the engineering skills below.
- `pip install pip-audit bandit vulture radon deptry --break-system-packages` — the shell scanners.
- `/init` — generate/refresh `CLAUDE.md` so every session has the repo map.

**By job:**

| Job | Best skill / command | Model |
|---|---|---|
| Map the codebase, find call sites | **Explore** subagent (Task tool) | Opus |
| Design audit strategy & refactors | **Plan** subagent; `/engineering:architecture`, `/engineering:system-design` | Opus |
| Bug diagnosis | `/engineering:debug` | Opus |
| Per-module code review | `/engineering:code-review`; `/review` on diffs | Opus to read, Sonnet to apply |
| Security pass | `/security-review`; Bash `bandit` | Opus to triage |
| Dependency / CVE audit | Bash `pip-audit`, `pip list --outdated`, `deptry` | Sonnet |
| Tech-debt & complexity | `/engineering:tech-debt`; Bash `radon cc/mi`, `vulture` | Opus to judge |
| Test strategy & coverage | `/engineering:testing-strategy`; Bash `pytest --cov` | Opus plans, Sonnet writes tests |
| Implement fixes & features | direct Edit + Bash; `/engineering:debug` if needed | Sonnet |
| Pre-release checklist | `/engineering:deploy-checklist` | Opus |
| Polish docs / reports | `docx`, `pdf` skills; `humanizer` on prose | Sonnet |
| Roadmap stakeholder deck | `pptx` skill | Sonnet |

---

## Session-by-session flow

Run the program as a sequence of focused sessions, not one marathon. Each session has a model, an input doc, and an exit gate.

**Session A — Recon & baseline (Opus).** Read this playbook + `AUDIT_AND_ROADMAP_PROMPT.md`. Execute Phases 1. Run `/init`, establish the green baseline (tests/lint/coverage), map the repo with **Explore**. *Exit gate: baseline metrics + repo map written down. Check in with the user.*

**Session B — The audit (Opus).** Execute Phases 2–7 of the audit prompt: bug hunt, security, dependencies, architecture, performance/UX, coverage gaps. Use the engineering skills + scanners. *Exit gate: `AUDIT_REPORT.md` exists with a prioritized fix queue (each item has severity, file:line, fix, effort). Have Opus second-opinion the Critical/High items. Check in with the user.*

**Session C — Fixes (Sonnet, with Opus on call).** Execute Phase 8. Sonnet clears the fix queue top-down: one item, one commit, tests green, repeat. Escalate to Opus for anything ambiguous or high-risk. After the batch, switch to Opus and run `/review` + `/security-review`. *Exit gate: queue cleared, full gate green, no open Critical/High.*

**Session D — Feature planning (Opus).** Now open `FUTURE_SCOPE_AND_MARKET_RESEARCH.md`. Pull the Tier 1/2/3 roadmap. Use `/engineering:architecture` to decide fit-vs-redesign per feature, and **Plan** to design each change set with acceptance criteria. Write/refresh `ROADMAP.md`. Remember: **Action Priority (AP) engine is the #1 Tier-1 feature.** *Exit gate: `ROADMAP.md` with planned, spec'd Tier-1 items.*

**Session E — Feature build (Sonnet).** Execute Phase 9. Sonnet implements Tier-1 features from the spec, one slice per commit, test-first, gate green, `/review` after each. Do not start Tier 2 until Tier 1 is merged and green. *Exit gate: Tier-1 shipped, tests green, docs updated.*

**Session F — Release (Opus decides, Sonnet executes).** Execute Phase 10. Opus makes the SemVer call and writes release reasoning; create the single source-of-truth version; Sonnet writes `CHANGELOG.md` and runs `/engineering:deploy-checklist`. Tag only after user confirmation. *Exit gate: release drafted, user sign-off requested.*

---

## Standing rules for every session

1. **Read before you act.** Whichever doc the current stage points to — read it fully first. Don't reconstruct the plan from memory.
2. **Plan in Opus, do in Sonnet, and always write the plan down** so the handoff survives the model switch.
3. **One bounded unit per execution pass.** One bug or one feature slice → one commit → tests green → report. No scope creep.
4. **Gates are hard stops.** Never enter a stage while the prior stage's gate is red (failing tests, open Critical findings).
5. **Audit before build, always.** Features go on top of a clean, tested base — never the reverse.
6. **Escalate, don't guess.** If Sonnet finds the written plan is wrong or ambiguous, stop and hand back to Opus.
7. **Ask the user before irreversible actions** — deleting modules, force-push, publishing/tagging a release.
8. **Keep the docs in sync.** As work lands, update `AUDIT_REPORT.md`, `ROADMAP.md`, and `CHANGELOG.md` so the three-document system stays the source of truth.

---

## One-line kickoff

> "Read `CLAUDE_CODE_PLAYBOOK.md`, then `AUDIT_AND_ROADMAP_PROMPT.md`. Start in Opus. Run Session A (recon + baseline) and stop at the gate for my review."
