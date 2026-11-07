# Quality Platform — Roadmap

**Stable · v1.0.0 · actively maintained.** This page covers what has shipped, what comes next,
and how to propose a stage. The live state is tracked in the
[GitHub milestones](https://github.com/Siddardth7/quality-platform/milestones).

---

## Where it stands

**v1.0.0 shipped on 2026-09-11.** It contains the four AIAG / IATF-16949 core tools over one
shared, typed core (`quality_core`):

- **FMEA:** RPN and AIAG-VDA Action Priority, plus a relational model and action tracking.
- **SPC:** control charts, run rules, capability behind a stability gate, Phase I/II, EWMA/CUSUM.
- **Control Plan:** turns FMEA failure modes into controls.
- **MSA / Gage R&R:** both the Average-and-Range and the ANOVA method.

The tools are wired into a **closed loop**: FMEA → Control Plan → SPC → proposed FMEA occurrence
update, which a human reviews. The same engines are exposed to AI agents through an **MCP server
(49 tools)** and **Agent Skills**. The platform is proven on the **SECOM** real semiconductor
dataset, and every constant cites its standard in an `ASSUMPTIONS_LOG.md`. All of it is held to a
CI gate with nine surfaces at 100% line and branch coverage.

- Release-by-release detail: **[CHANGELOG.md](CHANGELOG.md)**
- Docs site: **<https://siddardth7.github.io/quality-platform/>**
- How the project got here, week by week: **[docs/history.md](docs/history.md)**

---

## Next stages

None of these stages has a date. Stages are picked up when there is a reason to build them.

### v1.0.x · Maintenance (ongoing)

Bug fixes, standards-fidelity corrections and hardening on the stable line, tracked in the
[`v1.0.x · Maintenance`](https://github.com/Siddardth7/quality-platform/milestone/28) milestone.
The three engine-hardening items queued before release (#234, #235, #237) shipped in v1.0.0.

### v2 options (planned)

- **Web platform (planned):** a Next.js + FastAPI front end over `quality_core` that replaces
  the Streamlit shell, one tool at a time. Epic #107; milestone
  [`v2 · Web platform (planned)`](https://github.com/Siddardth7/quality-platform/milestone/27).
- **OAuth for web MCP hosts (planned):** a live, hosted Claude.ai / ChatGPT connector on top of
  the opt-in OAuth resource-server mode that already ships (#355).
- **AI FMEA copilot (planned):** LLM + RAG suggestions for failure modes, effects, causes and
  S/O/D, each with a rationale and backed by an eval harness. It is human-in-the-loop and never
  auto-commits.

**New tools and skills are welcome.** Examples include another AIAG core tool (PPAP, APQP
artifacts), a new SPC chart, or an Agent Skill for a host that isn't covered yet. Open an issue.

---

## How to contribute / propose a stage

1. Read **[CONTRIBUTING.md](CONTRIBUTING.md)** and the
   **[Definition of Done](docs/DEFINITION_OF_DONE.md)** (pinned as #43).
2. To propose a stage, open an issue that covers the user problem, the standard it rests on
   (if any) and the smallest first release. A maintainer will label it `roadmap` and place it
   in a milestone.
3. Changes land through a PR into `test`, pass the `CI / gate` check, and are promoted
   `test → dev → main`.
