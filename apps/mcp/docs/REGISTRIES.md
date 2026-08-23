# MCP registry listings (M6-3, #294)

"Listed everywhere" is a claim until proven. This file records, per registry, which
manifest file backs the listing, how submission actually happens, and whether the server
is really listed — with evidence, not assertions. It is the MCP-server analogue of
[`skills/COMPATIBILITY.md`](../../../skills/COMPATIBILITY.md).

The manifests themselves are committed and correctly shaped. **No listing exists yet**:
every submission step is an out-of-repo action against a third party, and CI cannot verify
that a third party accepted a listing.

## Server identity

One string has to match in three places, exactly and case-sensitively:

| Where | Value |
|---|---|
| `apps/mcp/server.json` → `name` | `io.github.siddardth7/quality-platform-mcp` |
| `apps/mcp/README.md` → ownership marker | `<!-- mcp-name: io.github.siddardth7/quality-platform-mcp -->` |
| PyPI distribution (`apps/mcp/pyproject.toml`) | `quality-mcp`, version `1.0.0` |

The registry verifies PyPI ownership by fetching the published package's
`long_description` — which *is* `apps/mcp/README.md`, per `readme = "README.md"` in
`apps/mcp/pyproject.toml` — and looking for a literal `mcp-name: <server name>` string. An
HTML comment is fine; a mismatch is not. **A mismatch fails only when `mcp-publisher
publish` is attempted — no CI check catches it**, so diff the two strings by hand before
publishing (see the pre-flight below).

## The matrix

Cells: `PASS ✓` (listing live, evidence linked) · `PENDING` (submission not yet run).

| Registry | Manifest | Submission mechanism | Status |
|---|---|---|---|
| Official MCP registry | `apps/mcp/server.json` | `mcp-publisher login github` → `mcp-publisher publish` (CLI, GitHub device-flow auth) | **PENDING** — blocked on real PyPI |
| Smithery | `apps/mcp/smithery.yaml` | Smithery web UI, "Add Server" pointed at the GitHub repo (account required) | **PENDING** — SME account action |
| Glama | `glama.json` (repo root) | Auto-indexed; `glama.json` claims ownership of the auto-created listing | **PENDING** — SME claim action |

### Why PENDING, not done

- **MCP registry — a real packaging gap, not just an unclicked button.** The registry's
  PyPI verification supports `https://pypi.org` only, and `mcp-publisher publish`
  validates that the named package version actually resolves there. `quality-mcp` is on
  **TestPyPI only** today (#292, M6-1: the publish workflow is `workflow_dispatch`-only
  and real PyPI is deferred to the v1.0.0 release — see `README.md`, "Publishing to
  TestPyPI"). `server.json` is correct and ready; it cannot be published until the
  distribution is live on real PyPI.
- **Smithery and Glama — no packaging gap.** Both are blocked only on an SME performing an
  account action (sign in, add/claim). Nothing in the repo has to change first.

## Canonical tags

Neither `server.json` nor `smithery.yaml` carries tags — all three registries take
descriptive keywords in their **web UI**, after listing. Type these seven, verbatim, into
every registry so the listings agree with each other:

```
fmea, spc, msa, control-plan, aiag-vda, manufacturing-quality, six-sigma
```

## What to say in a listing description

Registry descriptions should describe the **server**, not promise that every tool runs out
of the box:

- **49 registered tools** across FMEA, SPC, MSA, Control Plan, export/report, and a loop
  orchestrator. The catalog lives in [`../README.md`](../README.md) and the `@app.tool`
  registrations in `../mcp_app/server.py` — deliberately **not** duplicated here, because a
  second copy of a 49-item list is the kind of thing that drifts.
- **One tool is not zero-config.** `qdb_answer_question` (private-corpus RAG) needs a built
  index and a configured generator module (`QUALITY_DATABASE_CORPUS_OUT`,
  `QDB_GENERATOR_IMPORT_PATH`) — a fresh `uvx quality-mcp` install does not satisfy those.
  Do not write a description implying all 49 tools work on a bare install.
- The documented stdio invocation is `uv run python -m mcp_app.server` (workspace root) or
  `uvx --from . quality-mcp` from `apps/mcp`. Any listing's install command must match one
  of those exactly.

## Per-registry runbook (how to turn a PENDING row green)

### 1. Official MCP registry

**Pre-flight** (do this first — it is the failure mode that only shows up at publish time):

```bash
grep -n 'mcp-name:' apps/mcp/README.md
uv run python -c "import json; print(json.load(open('apps/mcp/server.json'))['name'])"
```

The two strings must be identical. Then confirm the version matches what is actually on
PyPI:

```bash
uv run python -c "import json; d=json.load(open('apps/mcp/server.json')); print(d['version'], d['packages'][0]['version'])"
grep -n '^version' apps/mcp/pyproject.toml
```

**Publish** (only after `quality-mcp` is live on real PyPI):

```bash
cd apps/mcp
mcp-publisher login github     # GitHub device flow; namespace io.github.siddardth7/*
mcp-publisher publish          # validates server.json against the real PyPI metadata
```

Confirm the server resolves in the registry, save the listing URL and the `publish` output
to `apps/mcp/docs/registry-evidence/mcp-registry.txt`, link it, flip the row to `PASS ✓`.

### 2. Smithery

1. Sign in to Smithery with the GitHub account that owns `Siddardth7/quality-platform`.
2. "Add Server" → point it at the repo. Smithery reads `apps/mcp/smithery.yaml`.
3. Confirm the resolved start command is `uv run python -m mcp_app.server` — if the UI
   shows anything else, that divergence is the quirk to record, not to accept.
4. Add the canonical tags above. Save the listing URL to
   `apps/mcp/docs/registry-evidence/smithery.txt`, flip the row.

### 3. Glama

Glama auto-indexes public GitHub repos, so a listing may already exist as *unclaimed*;
`glama.json` at the repo root is what attributes it to a maintainer.

1. Find the auto-created listing on glama.ai.
2. Claim it with the `Siddardth7` GitHub account; Glama reads root `glama.json`
   (`maintainers: ["Siddardth7"]`).
3. Confirm the listing shows the maintainer rather than "unclaimed", add the canonical
   tags, save the URL to `apps/mcp/docs/registry-evidence/glama.txt`, flip the row.

## Release checklist addition

`server.json` carries the workspace version in **two** places (`version` and
`packages[0].version`). The workspace bumps every version together at release (root
`CLAUDE.md`, "## Version"), and unlike the `pyproject.toml` pins — which are self-enforcing,
since a stale pin fails `uv lock` — **nothing fails if `server.json` is missed**: the
manifest would simply claim a version that does not exist on PyPI, and only
`mcp-publisher publish` would notice. Add both fields to the release bump, alongside the
`__version__` strings and the internal dependency pins.

No gate is wired for this in #294 — that is scope beyond "registry listings". If the drift
recurs, the lazy fix is one assert in the existing publish-metadata test, not a new module.
