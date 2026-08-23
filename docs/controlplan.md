# Control Plan

The APQP-adjacent bridge: turn a relational FMEA into a Control Plan — one row per failure
mode, highest risk first, carrying characteristic, specification, measurement method, sample
plan and a **recommended control chart** drawn from the AIAG SPC chart-selection rule table.

- **UI** — the Control Plan page of the unified shell.
- **MCP tools** — `controlplan_build`, `controlplan_recommend_chart`,
  `controlplan_source_index`, `controlplan_build_from_project`. See the
  [tool catalog](tools.md).
- **Skill** — `skills/control-plan/SKILL.md`.

`controlplan_source_index` traces every Control Plan row back to the FMEA failure mode and
cause it came from, so no row appears without a source.

| Read next | Where |
|---|---|
| App README | [`apps/controlplan/README.md`](https://github.com/Siddardth7/quality-platform/blob/main/apps/controlplan/README.md) |
| Every constant and threshold, with its citation | [`apps/controlplan/docs/ASSUMPTIONS_LOG.md`](https://github.com/Siddardth7/quality-platform/blob/main/apps/controlplan/docs/ASSUMPTIONS_LOG.md) |
