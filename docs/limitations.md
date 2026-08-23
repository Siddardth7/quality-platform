# Limitations

Stated once, plainly, so no other page has to hedge.

## It is on-demand, not real-time

Nothing polls, streams, subscribes or watches. Every number this platform produces comes from
a call somebody made — a click in the UI, a tool call from an agent, or a `run_project_loop`
over a directory. There is no monitoring service, no alerting and no 24/7 anything.

## It is not a data historian and not an EQMS

There is no database, no equipment or PLC integration, no MES/SCADA connector, and no
record-retention, workflow, approval or e-signature layer. Inputs are files you supply;
outputs are files it writes. It does not become a system of record for anything.

## The SPC → FMEA feedback proposes; it never autowrites

The feedback arrow computes a *candidate* occurrence rating from an out-of-control chart and
attaches an open `Action` whose `owner` points at the evidence file. `Cause.occurrence` is
left exactly as the FMEA author set it. In the source's own words: *"it NEVER writes a new
rating, it only proposes one for a human to review."* A human accepts or rejects the
proposal; the tool does not.

## The MSA gate does not currently gate

`spc/msa-gate.json` records `pass` / `warn` / `block` per monitored characteristic, but a
`block` row does **not** presently stop the feedback arrow from producing a candidate. This
is a known limitation, recorded rather than quietly fixed. Read the gate file alongside the
feedback file.

## `spc/results/*.json` is an input

No arrow in the loop produces control-chart results. Persisting a chart run against live
process data is not any arrow's contract, so the loop treats whatever is on disk as the trace
of a prior charting session. With none present, the feedback leg no-ops and returns `null`.

## It is not a replacement for engineering judgment

Ratings, tolerances, sample plans and dispositions are engineering decisions. The tools
compute, cite and refuse; they do not decide. Standards fidelity means the numbers are
traceable, not that the conclusions are automatic.

## Nothing is published to a package index yet

`uvx quality-mcp` does not work. The registry manifests (`apps/mcp/server.json`,
`apps/mcp/smithery.yaml`, root `glama.json`) exist, but no artifact has been uploaded
anywhere ([#292](https://github.com/Siddardth7/quality-platform/issues/292)). Install from a
local clone.

## No hosted MCP endpoint

The HTTP transport works and is always authenticated, but no public endpoint is provisioned.
Web-host connectors (Claude.ai, ChatGPT) therefore stay `PENDING` — see [Hosts](hosts.md) for
the two independent blockers.

## The standalone status product is not live

MCP tools and Agent Skills are what exists today. A standalone status-product website is a
Phase-2 roadmap item; it is **not built and not live**.
