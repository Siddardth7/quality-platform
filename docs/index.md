# Quality Platform

**Verified AIAG core-tool engines — FMEA, SPC, Control Plan and MSA / Gage R&R — callable by
hand in a Streamlit UI, or by any AI agent through an MCP server and a set of Agent Skills.**

The same typed core (`quality_core`) runs underneath both entry points, so an agent and a
human get byte-identical numbers from the same validated ingest and the same export path.

- [Quickstart](quickstart.md) — configure the MCP server, or run the UI locally.
- [Two ways to use it](two-ways-to-use.md) — UI vs. agent, and when each one is right.
- [The loop](loop.md) — FMEA → Control Plan → SPC → back to FMEA, over a project directory.
- [MCP tool catalog](tools.md) — all 49 tools, grouped by method.
- [Worked example](demo.md) — the loop run end to end on real SECOM sensor data.

## What it is

- **On-demand analysis over files you already have.** You point a tool (or an agent) at a
  dataset or a project directory and it computes a result.
- **Standards-anchored.** Every constant, threshold and rating table is cited in the owning
  app's `ASSUMPTIONS_LOG.md`; MSA's citations are machine-checked in CI. See
  [Standards & fidelity](standards.md).
- **Local by default.** The MCP server's default transport is stdio: the host launches the
  process on your machine, and your data never leaves it.

## What it is not

- **Not real-time or 24/7 monitoring.** Nothing polls, streams or watches a line. Every
  result is produced by a call you (or your agent) make.
- **Not a data historian and not an EQMS.** There is no database, no equipment integration
  and no record-retention or e-signature layer.
- **Not an autowrite.** The SPC → FMEA arrow *proposes* an occurrence rating as a candidate
  action for a human to review. It never overwrites a rating.
- **Not a replacement for engineering judgment.** The tools compute and cite; a qualified
  engineer decides.

The full list, with the reasoning behind each line, is on [Limitations](limitations.md).
