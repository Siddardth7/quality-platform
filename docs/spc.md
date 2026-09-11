# SPC

Statistical Process Control: variables and attributes control charts (X̄-R, X̄-s, I-MR, p, c,
u, EWMA, CUSUM), Western Electric and Nelson rule detection, Phase I limit freezing and
Phase II application, normality and stability assessment, and Cp/Cpk/Pp/Ppk **behind a
stability gate** — no capability claim is made on an out-of-control process.

- **UI** — `uv run streamlit run apps/spc/app.py`, or the SPC page of the unified shell.
  Includes a live disturbance simulator.
- **MCP tools** — 19 `spc_*` charting/analysis tools plus the SPC export tools and the
  project-file arrows (`spc_config_from_project`, `spc_msa_gate_from_project`,
  `spc_fmea_feedback_from_project`). See the [tool catalog](tools.md).
- **Skill** — `skills/spc/SKILL.md`.

Standards context: AIAG SPC 4th Edition; the capability target used throughout is
**Cpk ≥ 1.33**.

| Read next | Where |
|---|---|
| App README | [`apps/spc/README.md`](https://github.com/Siddardth7/quality-platform/blob/main/apps/spc/README.md) |
| Every constant and threshold, with its citation | [`apps/spc/docs/ASSUMPTIONS_LOG.md`](https://github.com/Siddardth7/quality-platform/blob/main/apps/spc/docs/ASSUMPTIONS_LOG.md) |
