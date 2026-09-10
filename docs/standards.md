# Standards & fidelity

A quality tool that cannot show where its numbers come from is not a quality tool. Three
mechanisms keep that claim checkable rather than rhetorical.

## 1 · Every constant is cited, per app

Each app carries an assumptions log listing every AIAG/ISO constant, threshold and quotation
it depends on, with its source. Changing a value without updating its log is a repo-level
rule, not a convention.

| App | Log |
|---|---|
| FMEA | [`apps/fmea/docs/ASSUMPTIONS_LOG.md`](https://github.com/Siddardth7/quality-platform/blob/main/apps/fmea/docs/ASSUMPTIONS_LOG.md) |
| SPC | [`apps/spc/docs/ASSUMPTIONS_LOG.md`](https://github.com/Siddardth7/quality-platform/blob/main/apps/spc/docs/ASSUMPTIONS_LOG.md) |
| Control Plan | [`apps/controlplan/docs/ASSUMPTIONS_LOG.md`](https://github.com/Siddardth7/quality-platform/blob/main/apps/controlplan/docs/ASSUMPTIONS_LOG.md) |
| MSA | [`apps/msa/docs/ASSUMPTIONS_LOG.md`](https://github.com/Siddardth7/quality-platform/blob/main/apps/msa/docs/ASSUMPTIONS_LOG.md) |
| SECOM | [`apps/secom/docs/ASSUMPTIONS_LOG.md`](https://github.com/Siddardth7/quality-platform/blob/main/apps/secom/docs/ASSUMPTIONS_LOG.md) |

Where **no published standard exists**, the module says so in its own docstring rather than
implying one — `secom_app/selection.py` and `secom_app/doe_screening.py` are the worked
examples of that discipline.

## 2 · Citations are machine-checked (MSA)

MSA goes further than prose: every quotation from the MSA Reference Manual is recorded in a
manifest,
[`apps/msa/docs/CITATIONS.tsv`](https://github.com/Siddardth7/quality-platform/blob/main/apps/msa/docs/CITATIONS.tsv),
and asserted against the source by
[`apps/msa/tests/test_citations.py`](https://github.com/Siddardth7/quality-platform/blob/main/apps/msa/tests/test_citations.py)
in the CI gate. A drifted or fabricated quotation fails the build.

## 3 · The quality gate

One bar for the whole workspace, run identically locally and in CI on Python 3.11:

```bash
uv run ruff check .     # lint + format check
uv run mypy             # strict static types
uv run pytest --cov     # tests + coverage across core + apps
```

Plus a core dependency contract (`quality-core` must never resolve a Streamlit-chain
dependency) and **nine per-surface coverage gates, each at 100% with branch coverage on**:

| Gate | Surface |
|---|---|
| Core (4 gates) | `quality_core.io`, `.schema`, `.scoring`, `.spc` |
| SPC | the SPC app's engine, simulation, visualizer, exporter, schema, control-plan config and FMEA-feedback modules |
| Control Plan | `controlplan_app.connector`, `.schema` |
| MSA | `msa_app.gage_rr_engine`, `.schema`, `.exporter` |
| SECOM | all seven engine modules (no UI to exclude) |
| MCP | `mcp_app.server` |

Streamlit `pages/` and entry scripts are excluded from the app gates — they need a runtime.

## Refusals count as fidelity

The platform refuses analyses the data cannot support, and says why:

- **No capability claim on an out-of-control process.** `spc_capability` sits behind a
  stability gate.
- **No Gage R&R on SECOM.** The dataset structurally has no part / appraiser / trial axis;
  the refusal is documented in `apps/secom/docs/MSA_APPLICABILITY.md` and enforced in
  `secom_app.msa`.
- **No Cp/Cpk on SECOM.** It ships no tolerances, so none are invented.

See [the worked example](demo.md) for all three in one place.
