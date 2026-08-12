# Skill authoring conventions

> **Status:** active (#270, M2-1). Every skill in this repo follows it; `scripts/skill_lint.py`
> enforces the mechanical half in CI.

## 1. What a skill is

A **skill** is a folder of markdown (plus optional scripts and references) that teaches an
agent host *how to run one of this platform's workflows*. It is instructions, not a service:
the compute already exists behind the MCP server (`apps/mcp`), and the skill is the layer that
knows which tool to call, in what order, and how to present the result. Hosts discover skills
by reading frontmatter only, so a skill costs nothing until it is relevant.

Layout — one folder per skill, folder name **is** the skill name:

```
skills/
  CONVENTIONS.md            this file
  <skill-name>/
    SKILL.md                required — frontmatter + orchestration body
    references/*.md         optional — deep detail, linked from the body
    scripts/*.py            optional — runnable helpers, MCP client only
    assets/                 optional — templates, sample files
```

Frontmatter contract (flat `key: value` between two `---` fences):

| Key | Required | Constraint |
|---|---|---|
| `name` | yes | `^[a-z0-9]+(-[a-z0-9]+)*$`, <=64 chars, **must equal the folder name** or the skill will not load |
| `description` | yes | non-empty, <=1024 chars, no `<` or `>` (frontmatter is loaded verbatim — angle brackets are a prompt-injection footgun) |
| anything else | no | spec-compliant hosts ignore unrecognized keys; do not rely on them |

## 2. The invariant

**Engine decides, skill orchestrates.** A skill calls MCP tools (`mcp_app.server` — see
`apps/mcp/README.md` for the tool catalog and the `<domain>_` naming convention); it never
imports or reimplements `quality_core`/`fmea_app`/`spc_app`/`msa_app`/`controlplan_app`/
`secom_app` math. `skill-lint` enforces the import half of this mechanically; a reviewer still
checks for smuggled formulas the lint's denylist misses.

This is the same discipline the MCP layer already keeps one level down: every tool is a thin
typed wrapper over a shipped engine function, and no math is reimplemented at the tool
boundary. `mcp_app` is the repo's one sanctioned exception to "apps never import each other"
(SME sign-off, #262) — **skills must not become a second exception.**

Hard rules:

1. A `scripts/*.py` file imports the MCP client (`fastmcp`) plus stdlib. Nothing else.
2. A SKILL.md body carries no formula. Naming a metric in prose ("report the RPN and Action
   Priority") is fine; writing the assignment that produces it is not.
3. Engine results are presented verbatim. No rounding, re-deriving or second-opinion
   arithmetic in the skill.
4. Rating-scale text, thresholds and AIAG/ISO constants live in the owning app's docs and
   `ASSUMPTIONS_LOG.md` — never copied into a skill, where they would silently fork.

## 3. Description house style

One sentence, stating both **what** the skill does and **when** to use it — the description is
the only thing a host loads at discovery, so it is a trigger, not a summary. The mechanical
ceiling is the spec's 1024 chars (what `skill-lint` enforces); aim for **~200 chars**. That
target is a recommendation, not a lint rule.

## 4. Progressive disclosure

Three levels, and content belongs at the shallowest one that works:

| Level | Loaded when | Content |
|---|---|---|
| 1 | always, for discovery | frontmatter (`name`, `description`) |
| 2 | the host judges the skill relevant | the SKILL.md body — keep it under ~500 lines |
| 3 | on demand, from a link in the body | `references/*.md`, `scripts/`, `assets/` |

Anything deeper than the orchestration steps — wire formats, error tables, tool catalogs,
worked examples — goes in `references/*.md` and is **linked** from the body, never inlined.

## 5. Install path

```bash
npx skills add Siddardth7/quality-platform
```

That resolves this repo's root `skills/` directory and offers each subfolder containing a
valid `SKILL.md`. There is no manifest, no `package.json`, no marketplace entry — the
directory *is* the wiring, which is why `skills/` lives at the repo root next to `apps/` and
`packages/` rather than inside the `apps/mcp` workspace package.

## 6. `skill-lint`

```bash
uv run python scripts/skill_lint.py     # from the workspace root
```

Exits non-zero on any violation and runs as its own step in the CI `gate` job (right after the
README drift check, before ruff) — the same pattern as `scripts/check_readme_test_count.py`.
The authoritative list of checks is the module docstring of
[`scripts/skill_lint.py`](../scripts/skill_lint.py); it is not duplicated here so the two
cannot drift.

Two known limitations, stated rather than papered over:

- The import check is a **source-text scan**, not an `ast` walk or a dependency resolution. It
  catches `import quality_core` and `from quality_core import ...`; it does not catch a
  dynamic `importlib.import_module` call.
- The math check keys on an `=` assignment for a small symbol denylist. Reviewers, not the
  linter, are the backstop for a formula written in prose.

## 7. Template

Copy [`skills/example-skill/`](example-skill/) — it is a real, working, lint-clean skill
demonstrating the full pattern end to end: SKILL.md orchestration steps, a
`scripts/call_fmea_score.py` that drives the `fmea_score` MCP tool over stdio, and a
`references/mcp-tool-contract.md` holding the level-3 detail. It is a template, not a shipped
skill: its own description says so. After copying, rename the folder, replace `name` and
`description` to match, and rewrite the body — then run `skill-lint` before you commit.
