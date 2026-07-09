# Definition of Done

**This is the contract.** Every issue links here instead of re-explaining the gates. Starting an
issue = read this file + the issue body, nothing else. It is mirrored as a **pinned GitHub issue**
(the canonical DoD issue) so it's one click from the issues tab.

> Adapted for this repo (a **uv workspace monorepo** with **per-surface coverage gates**) from the
> `ENGINEERING_SYSTEM_PLAYBOOK`. The mental model and the two review passes are unchanged; the
> coverage rule is expressed against this repo's actual gates.

---

## Per-issue gates — run in order, do not skip

1. **Implement minimally.** The laziest solution that actually works: reuse what's already in the
   repo (a helper, type, or pattern) before writing new code; stdlib / native platform before a new
   dependency; the shortest *correct* diff. Fix the root cause, not the symptom. Mark every
   deliberate shortcut with a `# ponytail:` comment naming the ceiling and the upgrade path.
   Non-trivial logic (a branch, loop, parser, money/security path) leaves **one runnable check**
   behind.

2. **Dedicated tester (separate pass).** A distinct pass — a `test-automator`-style agent, not the
   implementer — writes/extends the suite for the change. For cross-module or **any audit-type**
   issue, a `qa-expert`-style pass reviews the test *strategy* (are we testing the right things,
   not just that tests exist).

3. **Coverage learning loop — THE HARD STOP.** Loop *write test → run coverage → fill the gap* until
   the touched surface meets its gate **on line AND branch** and no gate has regressed. Branch
   coverage is mandatory (`branch = true` in `pyproject.toml`). **Do not start the next issue (or
   close the version) until this is met.** The per-surface gates:

   | Surface | Gate | Command |
   |---------|------|---------|
   | `quality_core.io` | **100%** line+branch | `uv run pytest packages/quality-core --cov=quality_core.io --cov-fail-under=100` |
   | `quality_core.schema` | **100%** line+branch | `uv run pytest packages/quality-core --cov=quality_core.schema --cov-fail-under=100` |
   | SPC testable surface | **≥95%** line+branch | `uv run pytest apps/spc --cov=spc_app.spc_engine --cov=spc_app.simulation --cov=spc_app.visualizer --cov=spc_app.exporter --cov=spc_app.schema --cov-fail-under=95` |
   | Whole workspace | no regression | `uv run pytest --cov` |

   **New modules are held to 100%** — the floor is a minimum; a fresh module dragging a surface down
   is a fail even if the number technically survives. `show_missing = true` prints the exact
   uncovered lines/branches — that's your worklist.

   *Accuracy ≠ coverage.* For anything correctness-bearing against a reference (e.g. the FMEA AP
   table, a future AI suggester), coverage proves the code *ran*; a **scorecard** proves it's
   *right*. Keep a labeled reference + a reproduce command with an explicit bar, tracked like
   coverage. (Precedent: the AIAG-VDA AP table was verified cell-by-cell against the handbook.)

4. **Code review on the diff.** Run `/code-review`. Resolve every correctness finding before merge.

5. **Over-engineering review on the diff.** A second, distinct pass whose *only* job is to find
   bloat: reinvented stdlib, unneeded dependencies, speculative abstractions, dead flexibility
   (`/ponytail-review`). Delete anything speculative.

6. **Green + clean + logged.** Full suite green (`uv run pytest`), `uv run ruff check .` clean,
   `uv run mypy` clean, and a `CHANGELOG.md` entry under `[Unreleased]` **in the same PR**.

7. **PR + squash-merge.** One branch per issue off `main` (`feat|fix|chore|docs/<#>-<slug>`). Open a
   PR whose body says *what* and *why* and **quotes the test/coverage evidence**. CI (the gate) must
   be green to merge. **Squash-merge**, then close the issue.

---

## Per-version gates — before any tag

- [ ] Every issue in the version milestone is closed.
- [ ] All per-surface coverage gates green on line+branch; consider **ratcheting a floor up** (never
      down) if a surface has durably climbed (e.g. SPC 95 → 96).
- [ ] Full `/code-review` of the *version* diff (not just per-issue).
- [ ] Whole-repo over-engineering audit (`/ponytail-audit`) + review the `# ponytail:` shortcut
      markers harvested this cycle (`/ponytail-debt`) — pay them down or consciously keep them.
- [ ] Live validation where the version calls for it (a dated `TRIAL_` doc with a real end-to-end
      run — required for the integration and AI versions; see the playbook §8).
- [ ] Roll `CHANGELOG.md` (`[Unreleased]` → `[x.y.z] - date`, open a fresh `[Unreleased]`) and bump
      the version in `pyproject.toml` + `packages/quality-core/pyproject.toml` — a `chore(release):`
      commit.
- [ ] **Tag + push — done by the human owner, never automated.**

---

## Sizing legend (issue fields / labels)

| Field | Values |
|---|---|
| **Size** | `S` ~<0.5d · `M` ~0.5–1.5d · `L` ~2–4d · `XL` ~1wk+ |
| **Complexity** | `low` (mechanical) · `med` (design/unknowns) · `high` (research/accuracy/cross-module) |
| **Priority** | `P0` (blocker) · `P1` (core to the version) · `P2` (when free) |

> **Bootstrap exception:** a pure-doc/config change with no logic (this file; a README edit) is N/A
> for gates 2–5. State that explicitly in the issue/PR so it isn't a silent skip.
