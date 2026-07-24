# Documentation index

Every doc, grouped by purpose. **Filenames are stable** — code, tests, and cross-doc links reference
these paths, so living docs are never moved once created. Each entry is one line: *what it is* and
*why it exists*.

## Start here
| Doc | What / why |
|---|---|
| [`../README.md`](../README.md) | Front door — what the platform is, how to run it. |
| [`../ROADMAP.md`](../ROADMAP.md) | Canonical plan: vision, architecture (diagrams), the 12-week version ladder, done + planned. |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | The one-page process: setup, test hygiene, the bar, workflow, architecture ground rules. |

## Contracts (how we work)
| Doc | What / why |
|---|---|
| [`DEFINITION_OF_DONE.md`](DEFINITION_OF_DONE.md) | The per-issue + per-version gates. Mirrored as a pinned issue; every issue links here. |
| [`ENGINEERING_SYSTEM_PLAYBOOK.md`](ENGINEERING_SYSTEM_PLAYBOOK.md) | The whole system end-to-end, adapted to this monorepo. |
| [`AGENT_TEAM_FRAMEWORK.md`](AGENT_TEAM_FRAMEWORK.md) | The 5-role AI agent team + the `feature → test → dev → main` branch ladder; agent/command files ready to build from. |

## Baselines, audits & trials (point-in-time evidence)
| Doc | What / why |
|---|---|
| [`COVERAGE_BASELINE_2026-07-09.md`](COVERAGE_BASELINE_2026-07-09.md) | Per-surface line+branch coverage at the branch-gate flip (#41); the one gap closed. |
| [`../apps/secom/docs/CASE_STUDY.md`](../apps/secom/docs/CASE_STUDY.md) | Short, honest SECOM case-study write-up (W09 series) — what was analyzed, verified numbers, and limitations. |

> New point-in-time docs (audits, scorecards, trials, designs) are **date-stamped** and land here as
> they're produced. Per-app deep docs live under `apps/fmea/docs/` and `apps/spc/docs/`.
