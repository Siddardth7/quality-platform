# FMEA

Failure Mode & Effects Analysis: RPN plus the AIAG-VDA (2019) **Action Priority** table,
editable S/O/D rating scales, a relational model (Function → Failure Mode → Effect / Cause /
Control), action tracking, Pareto and risk-heatmap charts, and Excel / PDF / CSV export.

- **UI** — `uv run streamlit run apps/fmea/app.py`, or the FMEA page of the unified shell.
- **MCP tools** — `fmea_score`, `fmea_run`, `fmea_run_relational`, `fmea_list_scales`,
  `fmea_get_scale`, plus the FMEA export/chart tools. See the
  [tool catalog](tools.md).
- **Skill** — `skills/fmea/SKILL.md`.

Standards context: AIAG-VDA (2019) and AIAG FMEA-4. The Action Priority table is verified
cell by cell against the primary handbook.

| Read next | Where |
|---|---|
| App README | [`apps/fmea/README.md`](https://github.com/Siddardth7/quality-platform/blob/main/apps/fmea/README.md) |
| Every constant and threshold, with its citation | [`apps/fmea/docs/ASSUMPTIONS_LOG.md`](https://github.com/Siddardth7/quality-platform/blob/main/apps/fmea/docs/ASSUMPTIONS_LOG.md) |
