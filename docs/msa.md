# MSA / Gage R&R

Measurement Systems Analysis — crossed Gage R&R by Average-and-Range (default) or ANOVA with
the part × appraiser interaction. Reports %EV / %AV / %GRR / %PV against both the study
variation and the tolerance, `ndc`, and an accept / marginal / reject verdict against the
AIAG thresholds.

- **UI** — the Gage R&R page of the unified shell.
- **MCP tools** — `msa_gage_rr`, plus the MSA export tools
  (`msa_export_excel`, `msa_export_pdf`, `msa_export_study_csv`, `msa_export_results_csv`).
  See the [tool catalog](tools.md).
- **Skill** — `skills/msa/SKILL.md`.

MSA is the only app with a **machine-checkable citation manifest**: every quotation from the
MSA Reference Manual is listed in `CITATIONS.tsv` and asserted in CI by
`apps/msa/tests/test_citations.py`. See [Standards & fidelity](standards.md).

| Read next | Where |
|---|---|
| App README | [`apps/msa/README.md`](https://github.com/Siddardth7/quality-platform/blob/main/apps/msa/README.md) |
| Every constant and threshold, with its citation | [`apps/msa/docs/ASSUMPTIONS_LOG.md`](https://github.com/Siddardth7/quality-platform/blob/main/apps/msa/docs/ASSUMPTIONS_LOG.md) |
| Citation manifest | [`apps/msa/docs/CITATIONS.tsv`](https://github.com/Siddardth7/quality-platform/blob/main/apps/msa/docs/CITATIONS.tsv) |
