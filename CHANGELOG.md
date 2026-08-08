# Changelog

All notable changes to the Quality Platform are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to adhere to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.13.0] - 2026-08-08

### Changed

- **FMEA default S/O/D rating scale is now the AIAG & VDA 2019 PFMEA scale (#256).** The 30
  anchors ship as `apps/fmea/data/rating_scales_2019_pfmea.json` — Severity from Table P1
  ("Impact to End User"), Occurrence from Table C2.3.1 ("Incidents per 1000 items/vehicles"),
  Detection from Table P3 ("Opportunity for Detection") — each line-pinned in
  `apps/fmea/docs/CITATIONS.tsv` and re-verified against the handbook by `test_citations.py`.
  This closes the mismatch flagged in #197: the default scale and the shipped Action Priority
  table (RULE 7) now come from the same handbook and are calibrated together. **AIAG FMEA-4 is
  retained as a selectable legacy option** (`data/rating_scales.json`, now named
  `AIAG FMEA-4 (legacy)`, loaded by `load_legacy_fmea4_scales()`); the rating-scale sidebar
  selector is now three-way (2019 default / FMEA-4 legacy / custom upload). **No math changed** —
  RPN and AP are pure functions of the integer S/O/D scores; only what a score *means* changed.

### Fixed

- **FMEA standards provenance: the "AIAG FMEA 5th Edition" does not exist (#197).** The 2019
  document is the **AIAG & VDA FMEA Handbook, 1st Edition** — a joint publication that restarted
  the edition count. The phantom edition was cited in `apps/fmea/docs/ASSUMPTIONS_LOG.md` and in
  four live app files, two of which printed it onto **exported Excel and PDF reports**
  (`fmea_app/exporter.py`); in an IATF 16949 core-tools context a report citing a nonexistent
  standard edition is itself an audit finding. Every live citation now names the handbook
  correctly; dated planning records under `docs/plans/` and `docs/superpowers/plans/` are left
  alone as historical artifacts.
- **RULE 2 was attributing a repo heuristic to AIAG (#197).** `ASSUMPTIONS_LOG.md` claimed both
  editions "state explicitly that Severity 9–10 failure modes require action independent of
  Occurrence and Detection." The handbook says the opposite: its Table AP rates S 9–10 with
  Occurrence 1 as **Low**, and §3.5.9 recommends only that S 9–10 effects *with AP High or
  Medium* be reviewed by management. `Flag_High_Severity` (every S ≥ 9 row, regardless of O/D)
  is now documented as this repo's deliberately-more-conservative safety heuristic. **No code
  behaviour changed** — the flag fires exactly as before. The same false claim is corrected in
  `apps/fmea/README.md` and `apps/fmea/docs/FMEA_COMPLETE_GUIDE.md`.
- **RULE 3 marked superseded, RULE 6's scope claim corrected (#197).** RULE 3 now describes
  `Flag_Action_Priority_H` as the RPN ≥ 200-or-S ≥ 9 proxy it is, with a forward pointer to
  RULE 7's real table lookup; the RPN-threshold rationale is kept and labelled a repo decision.
  RULE 6 no longer claims the rating scale is irrelevant to the AP result: the *math* is
  scale-independent, but AP fidelity depends on the scale that originated the S/O/D integer,
  and the bundled default is FMEA-4 (2008) while the shipped AP table is from the 2019 handbook.
  Shipping the 2019 S/O/D tables as the default scale is tracked in **#256** — split out of #197
  because the handbook's PFMEA Occurrence/Detection tables are OCR-mangled in the available
  conversion and cannot be transcribed verbatim without fabrication risk.

### Added

- **Machine-checked citation manifest for FMEA (#197).** `apps/fmea/docs/CITATIONS.tsv` plus
  `apps/fmea/tests/test_citations.py`, mirroring the MSA precedent (#223): every AIAG & VDA
  quotation in the FMEA docs is re-asserted against the licensed handbook at a pinned line
  (+/-2 for wrapping) under formatting-tolerant matching, and no blockquote may exist in
  `ASSUMPTIONS_LOG.md` without a manifest row backing it. The tests **skip** where the licensed
  handbook is absent (CI); `FMEA_HANDBOOK_PATH` points them at a local copy. Nothing is quoted
  from the OCR-mangled Table AP band-label or PFMEA scale cells, deliberately.
- **Reintroduction guard for the phantom edition (#197).**
  `apps/fmea/tests/test_docs_provenance.py` fails if `ASSUMPTIONS_LOG.md`, `app.py`,
  `fmea_analyzer.py`, `fmea_app/rpn_engine.py`, or `fmea_app/exporter.py` regains a
  case-insensitive "5th Ed"/"5th Edition". Runs on CI with no licensed source needed.
- **ANOVA (crossed, with interaction) Gage R&R method for MSA (#195).**
  `compute_gage_rr()` gains a `method=` selector: `"average_and_range"` (the **default**,
  behaviour unchanged on every existing call site) or `"anova"`, a new `_anova_method()`
  implementing AIAG MSA 4th Ed. Ch. III Sec. B / Appendix A's crossed two-factor ANOVA with
  replication. It estimates the part × appraiser interaction, tests it with
  `F = MS_AxP / MS_e` against `scipy.stats.f.ppf(1 − α, df_AxP, df_e)` at **α = 0.05** — the
  level in the manual's own worked example; **AIAG does not mandate a significance level**,
  and there is deliberately no `alpha=` parameter — and either pools a non-significant
  interaction into repeatability (the manual's additive model, `SS_pool = SS_e + SS_AxP` over
  `nkr − n − k + 1` df) or carries it into `GRR = sqrt(EV² + AV² + INT²)`. Negative variance
  components are clamped to zero per Appendix A. Three additive payload keys —
  `interaction`, `interaction_f`, `interaction_significant` — are `None` under
  Average-and-Range, which cannot estimate them; no existing key was renamed, removed, or
  changed in value. Both methods share one balance check, one `_STUDY_VARIATION_SIGMA` (the
  #190 ×6 guard), `_compute_ndc` and `_compute_verdict`. On the canonical 10×3×3 study
  (`apps/msa/data/aiag_reference_study.csv`) the new path reproduces the manual's published
  Table III-B 7/8 and Table A 4/5 figures: F = 0.4337 (manual 0.434), EV = 0.199933,
  AV = 0.226838, INT = 0 (pooled), GRR = 0.302373, PV = 1.042327, TV = 1.085, ndc = 4.
  Engine-only: no exporter, page or schema changes. New ASSUMPTIONS_LOG **RULE 17** with ten
  primary-source-verified `CITATIONS.tsv` rows; RULE 1 rewritten as "the default, not the
  only, method"; the "ANOVA not implemented" claims in `README.md`, `ROADMAP.md`,
  `apps/msa/CLAUDE.md` and the engine's own docstring / `METHOD_NOTE` retired. `scipy>=1.17.1`
  is now a declared `msa-app` dependency (already present in the workspace via `quality-core`).

### Fixed

- **SPC demo generator reproducibility (#226).** Instantiated local `rng = np.random.default_rng(42)` inside `generate_demo_dataset()` and threaded `rng` to all seven private stream helpers (`_ply_thickness`, `_autoclave_temperature`, `_hole_diameter`, `_reject_proportion`, `_surface_defects`, `_panel_defects`, `_ply_misalignment`), eliminating module-level `_RNG`. Subsequent calls in a single process now return byte-identical datasets.

### Security

- **Remediate 26 known security advisories across dependencies (audit A13, #201).**
  Bump `pillow` to `>=12.3.0` (remediating 18 advisories) and `gitpython` to `>=3.1.55` (remediating 8 advisories) via `override-dependencies` in `pyproject.toml` and updated lockfile. Added `pip-audit>=2.10.0` to `[dependency-groups] dev` and added a `Dependency vulnerability audit` gate step running `uv run pip-audit` to `.github/workflows/ci.yml`.

### Added

- **Repo-wide cross-app import guard (audit A12 acceptance criterion, #233).**
  New workspace-level `tests/test_cross_app_import_boundary.py` generalises the SECOM-only
  boundary test (#204/#205) to all five app packages, so "imports go downward only" is
  self-defending rather than held by hand-run `git grep` during review.
  **Part 1** runs one fresh, non-pytest interpreter per app — with `cwd` set to that app's
  own directory, because `fmea-app` and `controlplan-app` are `package = false` and resolve
  only via the implicit `sys.path[0]` — walks every submodule with `pkgutil.walk_packages`,
  and fails if any of the other four `*_app` packages appears in `sys.modules`. The
  subprocess is what makes the `sys.modules` check honest: in a full-workspace run other
  apps' suites have already imported their packages, so an in-process check would be
  import-order-dependent. An `assert walked` guard prevents a vacuous zero-submodule pass.
  **Part 2** is an `ast` scan of every `apps/*/tests/**/*.py` — covering `import`,
  `from … import`, and string-argument `importorskip` / `import_module` calls — that fails
  on any cross-app import not named in `_ALLOWED_TEST_ONLY_CROSS_APP_IMPORTS`, so adding a
  third test-only cross-app import is a conscious edit rather than a silent gap. `ast`
  rather than a regex because hand-written grep patterns have under-matched here before
  (#235), and the `importorskip` call form is invisible to an import-node-only walk — it
  accounts for two of the three allowlisted pairs.
  Stale allowlist entries are deliberately **not** a failure: only unlisted imports fail, so
  removing a cross-app import is never punished. No per-surface coverage gate is affected —
  the root `tests/` directory is outside every gate's collection path and outside
  `[tool.coverage.run] source` (verified against the core io and SECOM gates).
  `apps/secom/tests/test_import_boundary.py` is unchanged; the new guard is additive.

- **CI README test-count drift check script and workflow step (#210).**
  Added `scripts/check_readme_test_count.py` to compare `pytest --collect-only` counts against claims in `README.md` (badge and comment). Added `tests` to `testpaths` in `pyproject.toml`, updated `README.md` test counts to 1641, and added a CI step in `.github/workflows/ci.yml` to fail on drift.

- **MSA reports %EV, %AV and %PV on both AIAG bases alongside %GRR (audit A10-c, #225).**
  `compute_gage_rr()` gains six keys — `pev_study` / `pav_study` / `ppv_study` and
  `pev_tolerance` / `pav_tolerance` / `ppv_tolerance` — completing the
  `p{ev,av,grr,pv}_{study,tolerance}` family and giving parity with the AIAG Gage R&R Report
  Form (MSA 4th Ed., Ch. III §B, Figure III-B 16), whose published %EV = 17.62%,
  %AV = 20.04%, %GRR = 26.68% and %PV = 96.38% are now asserted as an oracle. All eight
  percentages reach the Excel/PDF detail table, the results CSV and the Gage R&R page.
  Every tolerance-basis figure routes through `_STUDY_VARIATION_SIGMA` on its own line
  (RULE 8 / #190), so the ×6 that #190 restored for %GRR cannot be dropped from a sibling.
  The new figures are **reporting-only — no verdict changes for any input** — and the six
  keys are **purely additive**: no existing key is renamed or removed. #225's suspected
  recurrence of #190 in %EV/%AV/%PV is **refuted**: those three were never computed at all.
  New **RULE 16** in `apps/msa/docs/ASSUMPTIONS_LOG.md` records both the refutation and the
  now-enforced ×6 guard.

- **Shared SPC primitives promoted into `quality_core.spc` (audit A12, #205 — PR 1 of 3).**
  The AIAG SPC chart constants, the Western Electric / Nelson rule detectors
  (`detect_we_violations`, `detect_nelson_violations`, `detect_violations`,
  `SHEWHART_CHART_TYPES`) and `subgroup_rows` now live in `quality_core.spc`, with the
  platform's chart vocabulary `SPCChart` alongside them in `quality_core.spc.constants`.
  `spc_app.spc_engine.constants` / `.rule_detection` / `.utils` became thin re-export shims
  (the `fmea_app.ap_engine` pattern), so every existing SPC caller is unchanged. SECOM's
  `charts.py` now imports the constants and the rule detectors *downward* from
  `quality_core` instead of sideways into `spc_app`; `controlplan_app.schema` and
  `spc_app.control_plan_config` consume the one `SPCChart` (the latter via
  `typing.get_args`), removing two of the four hand-typed copies of the chart key list.
  A new **Core SPC coverage gate** holds `quality_core.spc` at 100% line + branch from
  `packages/quality-core`'s own tests. **No values, formulas or citations changed** — a
  pure move — and **no new dependencies**: `quality-core`'s hard dependency set is still
  exactly `{pandas, pydantic, openpyxl, defusedxml}` and `uv.lock` is untouched. The
  numpy-dependent chart engine (#205 PR 2) and scipy-dependent capability (PR 3) follow;
  `apps/secom` still depends on `spc-app` until then.

- **SPC chart math, Phase I/II freezing and the stability gate promoted into `quality_core.spc`
  (audit A12, #205 — PR 2 of 3).** `control_charts` (the `compute_xbar_r/_s`, `compute_imr`,
  `compute_p/c/u`, `compute_ewma`, `compute_cusum` family and their TypedDict results), `phase`
  (`freeze_xbar_r/_s/_imr`, `FrozenLimits`) and `stability` (`assess_stability`,
  `stability_fields`) now live in `quality_core.spc`; `spc_app.spc_engine.control_charts` /
  `.phase` / `.stability` became thin re-export shims like PR 1's, so every existing SPC caller
  is unchanged. New **`imr_limits(xbar, mrbar)`** writes the AIAG I-MR limit formula
  (`Xbar ± E2·MRbar`, `D4·MRbar`, `LCL_mr = 0`, `MRbar/d2`) exactly once: both `compute_imr` and
  SECOM's `control_chart_for_signal` consume it, removing the duplicated copy SECOM carried for
  its OQ5 gap-pooled `mrbar` (the input differs, the formula no longer does). `secom_app/charts.py`
  now has no `spc_app` import at all. **No value, formula, threshold or citation changed** — the
  #191 baseline (19 signals on `ply_misalignment`, `sigma_hat 0.24489039329464862`) is
  byte-identical. `numpy>=2.4.4` is now a declared hard dependency of `quality-core` because
  `quality_core.spc.control_charts` imports it at module level; measured fact: the resolved
  dependency subtree is **unchanged** (numpy 2.4.4 was already pulled in transitively via pandas)
  and the banned-package count is still 0 — only `uv.lock`'s quality-core metadata block moves.

- **Process capability promoted into `quality_core.spc`, and the SECOM→SPC app boundary torn down
  (audit A12, #205 — PR 3 of 3, closes the finding).** `capability` (`compute_capability`,
  `normality_test`, `compute_capability_study`, `CapabilityStudy` and the non-normal Box-Cox /
  Yeo-Johnson / ISO 22514-2 fitted-percentile machinery) now lives in `quality_core.spc.capability`;
  `spc_app.spc_engine.capability` became a thin re-export shim like PRs 1 and 2, so every existing
  SPC caller is unchanged. `secom_app/capability.py` imports it *downward* from `quality_core`, so
  **`apps/secom` no longer imports `spc_app` anywhere** and the `spc-app` workspace-dependency
  stopgap is gone from `apps/secom/pyproject.toml` — asserted as an executable fact by a new
  clean-interpreter boundary test. **No value, formula, threshold or citation changed** — a pure
  move; the 745-line capability suite moved with the module to
  `packages/quality-core/tests/test_spc_capability.py` and runs under the Core SPC gate at 100%
  line + branch. `scipy>=1.17.1` is now a declared hard dependency of `quality-core` because
  `quality_core.spc.capability` imports it at module level; it was already in the workspace lock
  via `spc-app`/`secom-app`, its only runtime dependency is numpy, and the banned-package count is
  still 0. `spc_app/spc_engine/data_generator.py` deliberately stays app-local — it is the SPC
  app's demo dataset, not shared standards math. The one remaining `sys.path` shim in
  `apps/secom/conftest.py` served `apps/msa`, not `spc_app` — it was tracked as #231 and is
  **removed in this same release** (see "`apps/msa` is an installable workspace package" under
  Changed); `apps/secom/conftest.py` no longer exists.

- **MSA declares which Gage R&R method it ran, and what that method cannot see (audit A10, #194).**
  `compute_gage_rr()` now returns two additional keys — `method` (`"average_and_range"`) and
  `method_note` — exported from `gage_rr_engine` as the `METHOD` / `METHOD_NOTE` constants, and
  surfaced as "Method" / "Method Limitation" in the results CSV, the Excel Summary sheet and the PDF
  detail table. The engine implements only the Average-and-Range method, which per AIAG MSA 4th Ed.,
  Ch. III Sec. B "does not include" the operator-to-part interaction: that interaction is absorbed
  into the reported components, so `%GRR` is biased low when it is non-zero. Previously nothing in
  the payload or the exports said so, leaving a consumer unable to distinguish this `%GRR` from an
  ANOVA result. ASSUMPTIONS_LOG RULE 1 is rewritten with primary-source quotations and correct
  Chapter/Section locators (its previous "Section 3.2" citation does not exist in the 4th Edition).
  **No computed value changed** — `%GRR`, `ndc` and `verdict` are byte-identical. The ANOVA method,
  which would estimate the interaction, is tracked as #195 and is not implemented here.

### Changed

- **Root `CLAUDE.md` gains two hard-won rules on parallel-agent isolation.** "One agent, one
  worktree" — branch state is per-checkout, not per-agent, so a second agent running
  `git switch -c` moves the branch out from under the first and its `git reset` wipes the first's
  uncommitted work. Observed live: an Antigravity run took the main checkout while `/ship` was
  mid-flight on #233, leaving that feature branch empty and the tree clean, so nothing looked
  wrong. The companion rule covers `.pipeline/`, which is likewise shared per checkout — the
  pre-existing archive-before-`rm -rf` rule only protects the *previous* issue's handoff files,
  not the current one's, so the spec is now backed up as soon as research writes it.
  Documentation only — no code, no gate, no behavior change.
- **The duplicated `quality_core` helpers are single-sourced (audit A15, #207).** Two copy-paste
  clusters collapse into one definition each. (1) The pydantic raise/assert prefix strip is now
  `quality_core.io.validate.clean_pydantic_message`, called by the core row and dataset error
  formatters and by `controlplan_app.pages.control_plan._first_error_message`,
  `fmea_app.rating_scales._build` and `fmea_app.rpn_engine._format_pydantic_error` — the strip
  previously existed as **two** diverging hand-written copies (the core dataset formatter and one
  app site); they collapse into one helper, now applied uniformly to every call site above, so the
  core row formatter and `rating_scales._build` gain the strip they lacked before. (2) The link → (effect, cause, control) traversal is now
  the method `FailureMode.resolve(link)` in `quality_core.schema.relational`, replacing five
  copies of the same three id→entity dicts (`relational_to_flat`, `controlplan_app.connector`'s
  `_worst_link` / `build_control_plan` / `source_index`, and `fmea_app.rpn_engine.
  _relational_actions`). The traversal swap is **behaviour-identical** — worst-link tie-break,
  Control Plan sort order and `source_index` keys are unchanged. Two **user-visible message**
  improvements fall out of (1): a row-level model-validator error and a rating-scale error no
  longer surface pydantic's `Value error, ` / `Assertion failed, ` prefix before the validator's
  own sentence. Row-error echo stays **unconditional and truncated at 50 characters** exactly as
  #200 chose — only the prefix strip was adopted into the row formatter. The untruncated-echo bug
  named in the audit was already fixed by the earlier deletion of `controlplan_app.schema.
  _reject_bad_optional_values`; this change is the residual de-duplication. No AIAG/ISO constant,
  threshold or quotation is touched, so no `ASSUMPTIONS_LOG.md` changes.

- **`apps/msa` is now an installable workspace package, removing the last cross-app `sys.path`
  shim (audit A03 follow-up, #231).** `msa-app` drops `[tool.uv] package = false` for the same
  hatchling `[build-system]` + `[tool.hatch.build.targets.wheel] packages = ["msa_app"]` shape
  `spc-app` and `secom-app` have carried since #204, so `uv` installs it **editable** into
  `.venv` (`uv.lock`: `virtual` → `editable`). `apps/secom/conftest.py` — which existed only to
  insert `apps/msa` onto `sys.path` so `tests/test_msa.py` could `import msa_app.gage_rr_engine`
  (#68) — is **deleted**; `apps/secom` now has no `conftest.py` at all. The edge is recorded in
  `apps/secom/pyproject.toml` as a **dev-group** dependency (`[dependency-groups] dev =
  ["msa-app"]` + `[tool.uv.sources]`), deliberately *not* a `[project]` dependency: the import is
  test-only, and a runtime entry would re-create the cross-app coupling #205 PR 3 removed.
  `apps/secom/tests/test_import_boundary.py` gains
  `test_msa_app_is_an_installed_distribution`, which imports `msa_app.gage_rr_engine` **and**
  `msa_app.pages` in a clean non-pytest interpreter run from the workspace root, so neither cwd
  nor a conftest can supply the package. `apps/msa/conftest.py` **stays**, matching
  `apps/spc/conftest.py`, which #204 kept for the same reason: it puts the app directory on
  `sys.path` so the top-level `app` module — deliberately outside the wheel — stays importable.
  Removing it was measured, not assumed: the MSA gate still passes at 100% with byte-identical
  coverage paths, because no MSA test imports `app` today. It is kept as a live seam for tests
  that will, not because anything currently depends on it. **No engine math, threshold, table or citation changed**, and the
  CI coverage invocations are byte-identical — the editable install is a plain-path `.pth`, so
  `--cov=msa_app.*` still measures `apps/msa/msa_app/...` at 100% line + branch.

- **MSA acceptance bands: the disputed tolerance-basis band set was investigated and refuted; no
  code change, and the ×6 multiplier's provenance is upgraded to primary source (audit A07-b,
  #217, follow-up to #190).** #217 asserted that AIAG MSA 4th Ed. applies a *separate* `0–19%` /
  `20–30%` / `>30%` band set to the tolerance basis. It does not: **Table II-D 1 (Ch. II §D)** is a
  single "GRR Criteria" table with no basis qualifier (`Under 10 percent` / `10 percent to 30
  percent` / `Over 30 percent`), and **Ch. III §B** makes the tolerance basis a denominator swap
  only ("substituting the value of tolerance *divided by six* in the denominator … in place of the
  total variation (TV)") before redirecting acceptance back to Ch. II §D ("the rule of thumb for
  gage repeatability and reproducibility (%GRR) may be found in Chapter II, Section D"). The
  `0–19/20–30` figures trace to a Hamilton Sundstrand / UTC customer form whose own study-variation
  row also contradicts AIAG's 10/30. `_compute_verdict(ndc, pgrr)` is therefore correct as written
  and is unchanged — #190's F-12 collapse to two arguments stands. `ASSUMPTIONS_LOG.md` RULE 8 and
  RULE 10 now state **explicitly** that one band set (10/30) governs both the study-variation and
  tolerance bases, with the citations above and the rejected alternative recorded, so a future
  attempt to add a second band set is visibly wrong instead of silently plausible — RULE 8's
  silence on this is what let A07 hide. Separately, RULE 8's ⚠ "verified against a third-party
  reproduction, not the paywalled manual itself" caveat on `_STUDY_VARIATION_SIGMA = 6.0` (#190) is
  **withdrawn**: Ch. III §B's "tolerance divided by six" confirms 6.00 (not the 3rd-edition 5.15)
  from the primary manual, so the RTX PPAP form is now only a numeric cross-check. The same upgrade
  is applied to the `_STUDY_VARIATION_SIGMA` comment in `gage_rr_engine.py` and to the AIAG
  reference-study test's docstring. Documentation and comments only — no `.py` behaviour changed.

- **CI runs least-privilege, third-party actions are pinned to commit SHAs, and the blanket `F401`
  ignore is narrowed (audit A14, #203).** `.github/workflows/ci.yml` declares
  `permissions: contents: read` at workflow level — the `gate` job only checks out, resolves the
  lock, lints, type-checks and tests, so it never needs write, and any job added later now inherits
  least privilege by default. `actions/checkout@v5` (a moving major) and `astral-sh/setup-uv@v8.2.0`
  are pinned to the full commit SHAs they already resolved to (`fbc6f39…` = v5.1.0,
  `fac544c…` = v8.2.0) with the version kept in a trailing comment; this is a **freeze, not a
  bump**. `ruff.toml` no longer ignores `F401` globally: every re-export `__init__` declares
  `__all__`, which ruff already honours, so the ignore had been buying nothing — it is replaced by
  a single per-file ignore on `apps/fmea/fmea_app/exporter.py`, the one module that re-exports
  (`export_csv`) without `__all__`. Six genuinely unused test imports were removed and the
  deliberate `_escape_source_label` smoke-import in `test_streamlit_edge_cases.py` carries an
  explicit `# noqa: F401`. `.devcontainer/devcontainer.json` keeps
  `--server.enableCORS false --server.enableXsrfProtection false` and now carries a comment naming
  why: Codespaces forwards 8501 through a different-origin proxy where `st.file_uploader`'s
  `POST /_stcore/upload_file` is rejected 403 by the XSRF cookie check, and by the cross-origin
  check when CORS is on. The two flags are **independent**: Streamlit 1.56 warns that
  `enableCORS` "is being overridden to `true`" when XSRF is on, but that code path only logs —
  nothing assigns the option and `server_util.py:78` reads the raw `False`. Verified against the
  installed 1.56.0; the warning is not implemented and must not be relied on. Dev-container only.
  The `postAttachCommand` string is byte-identical. Also corrected a stale `ruff.toml`
  comment: `spc` and `secom` have been installed packages since #204, so only fmea / msa /
  controlplan are still `package = false`.

### Removed

- **Two dead infrastructure files deleted (audit A14, #203).** `apps/fmea/.github/workflows/ci.yml`
  — a 51-line nested workflow that has never executed, because GitHub reads workflows only from the
  repository-root `.github/workflows/`; it duplicated the gate with `pip`, no lock and no coverage
  thresholds. `apps/spc/spc_app/ui/__init__.py` — a 0-byte file, the sole occupant of
  `apps/spc/spc_app/ui/`, with no static or dynamic importer anywhere in the repo and no entry in
  `apps/spc/pyproject.toml`'s `packages = ["spc_app"]`. Both parent directories are gone.

### Fixed

- **Control Plan chart recommendation is bounded, and its placeholder rows now say so
  (audit A18, F-07 + F-10, #196).** `controlplan_app.connector.recommend_chart` returned
  `"Xbar-S"` for any variable subgroup size ≥ 10, including sizes the engine cannot compute —
  `quality_core.spc.constants.XBAR_S_CONSTANTS` stops at n=12 and `compute_xbar_s` raises above
  it. It now raises `ValueError` for variable data with `n > max(XBAR_S_CONSTANTS)`, reading the
  ceiling from the constants table rather than a literal. Attribute data (`p`/`c`/`u`) is
  unaffected — large sample sizes stay valid there — and no new AIAG constants were invented.
  Separately, `ControlPlanRow` gains an **optional, additive** `sample_plan_is_placeholder`
  boolean (default `False`), stamped `True` on every row `build_control_plan` emits, so a
  consumer can tell the connector's declared `sample_size` / `frequency` / `reaction_plan`
  placeholders — which the relational FMEA has no source for — from engineered values. Uploads
  without the column, or with a blank cell, still validate; `sample_size` remains required and
  `ge=1`. The CSV/Excel exports carry the new column, the fixed-width PDF table is unchanged.
  `apps/controlplan/docs/ASSUMPTIONS_LOG.md` RULE 1/RULE 2 record both, and RULE 2 of
  `apps/spc/docs/ASSUMPTIONS_LOG.md` is reworded from "n > ~10" to "n >= 10" so both logs state
  the same X-bar/R ↔ X-bar/S boundary the connector implements (SME decision on OQ-1). **No
  chart-selection boundary, constant or AIAG claim changed** — the existing third-party-sourced
  flag on n = 9 vs 10 stays flagged for primary-source confirmation.

- **SPC capability CIs moved off Cp/Cpk onto Pp/Ppk, where their degrees of freedom are valid
  (audit F-05, #193).** The χ² and Bissell (1990) intervals are derived for σ estimated by the
  ddof=1 sample standard deviation with ν = n−1, but `compute_capability` attached them to
  Cp/Cpk, which use the within-subgroup estimator (R̄/d₂ or MR̄/d₂) — whose effective degrees of
  freedom are fewer than n−1, so the reported intervals were **too narrow**. They now attach to
  Pp/Ppk (`pp_ci`, `ppk_ci`, `ppk_lower`), which do use `np.std(x, ddof=1)`; the normal and
  Box-Cox/Yeo-Johnson paths report **no** parametric CI for Cp/Cpk (`cp_ci`/`cpk_ci`/`cpk_lower`
  are `None` there). Two new keys, `ci_estimator` (`"sample_sd_ddof1"` |
  `"bootstrap_percentile"`) and `ci_df` (`n−1` | `None`), make the estimator/df pairing
  self-describing for API consumers and appear on the capability PDF as a "CI basis" row. The
  fitted-percentile path is **unchanged** — its nonparametric bootstrap CIs on the percentile
  indices stay in `cp_ci`/`cpk_ci`/`cpk_lower`. An effective-df correction for R̄/d₂ was
  considered and not adopted: no primary source is available on-machine, and the log carries no
  uncited constants. `apps/spc/docs/ASSUMPTIONS_LOG.md` RULE 14 records the pairing, the
  limitation, and the honestly-marked Montgomery/Bissell attribution.

- **MSA `ndc` now floors at one, not zero, per AIAG MSA 4th Edition (audit A10-b, #224).**
  `_compute_ndc()` truncated `1.41 × (PV / GRR)` and clamped to `[0, 100]`, so a valid study with
  positive GRR and PV but a calculated `ndc` below 1.0 reported **`ndc = 0`**. The manual is
  explicit (Ch. III §B): *"For analysis, the ndc is the maximum of one or the calculated value
  truncated to the integer. This result should be greater than or equal to 5."* — and names this
  exact failure a line later: *"To avoid a ndc = 0, which is possible with truncation alone…"* So
  the floor is the standard's, not a rounding preference. The non-positive guard
  (`grr <= 0 or pv <= 0 → 0`) is **retained**: that path is a degenerate-input sentinel, not a
  calculated `ndc`, so AIAG's floor does not govern it. **No verdict changes for any input** —
  `_compute_verdict()` rejects on `ndc < 2` and both `0` and `1` sit below that threshold, which
  refutes the concern recorded under #223 that this correction would flip RULE 13's
  degenerate-study verdict. The `ASSUMPTIONS_LOG.md` entry is rewritten accordingly and its section
  retitled from "ndc Clamping to [0, 100]" to "ndc Upper Clamp at 100": the lower bound is no
  longer a deviation from AIAG, only the upper clamp is. Coverage alone did not catch this defect —
  no test exercised `1.41 × PV/GRR < 1.0` — so `test_ndc_minimum_one` pins it, and reverting
  `max(1, …)` to `max(0, …)` turns it red.

- **Six fabricated AIAG quotations removed from the MSA assumptions log; every surviving citation
  is now machine-checked (audit A10-a, #223).** `apps/msa/docs/ASSUMPTIONS_LOG.md` attributed
  quotations to the AIAG MSA 4th Edition under RULES 3, 4, 5, 6, 9, 11 and 12 that do not appear
  in the manual, using a `Section 3.x` / `Equation 3.x.y` locator scheme the 4th Edition does not
  have (its scheme is `Chapter <roman> – Section <letter>`). RULE 12's invented quote was also
  arithmetically wrong (`10 × 3 × 3 = 270`; it is 90). A wrong number is falsifiable by
  recomputation — a fabricated quotation looks like verified evidence, so every decision
  downstream of it inherits unearned confidence. Each fabricated quote is **withdrawn** and, where
  the manual does support the decision, replaced with the real passage quoted verbatim: EV/AV/GRR/
  PV/TV are now cited to Ch. III Sec. B "Analysis of Results — Numerical", repeatability and
  reproducibility to their Ch. I Sec. E definitions, and the ndc definition to Ch. III Sec. B.
  **RULE 11** (balanced crossed data) keeps its requirement but withdraws the quotation entirely
  and is relabelled a **procedure-derived inference** — AIAG prescribes a balanced procedure but
  never states the requirement, and the word "crossed" does not occur in the manual. **RULE 14**
  is *upgraded* from `"AIAG MSA, implicit"` to a real citation (Ch. III Sec. B states the negative-
  AV² clamp outright); **RULE 13** is relabelled an internal design choice, which is what it is.
  Three wrong locators are corrected — most notably the basis-by-purpose rule, which is in
  **Ch. I Sec. B**, not Ch. II Sec. C. The ndc bands `2–4 Marginal` / `< 2 Reject` are relabelled
  an **internal design choice**: AIAG publishes only `ndc ≥ 5`, and they were printed under an
  "Acceptance Criterion (AIAG)" heading. New **`apps/msa/docs/CITATIONS.tsv`** manifests every
  surviving quotation against the line of the primary manual it came from, and new
  `apps/msa/tests/test_citations.py` re-asserts each row — quote **and** line number (±2), so it is
  a citation index rather than a substring test. Matching is formatting-tolerant: the genuine
  passage renders as `tolerance _divided by six_`, which a naive search reports as fabricated, and
  a false "fabricated" verdict is the same sin in the opposite direction. The manual is licensed
  and not in the repo, so those tests **skip** (never fail) unless `MSA_MANUAL_PATH` is set.
  **Documentation only: no computation, constant, formula, threshold or branch changed** — the sole
  production edit is a docstring in `_compute_verdict`, and the MSA coverage gate stays at 100%.
  Two defects found while verifying are tracked, not hidden: `_compute_ndc`'s floor of zero
  contradicts AIAG's floor of one (**#224**, a behaviour change), and the same non-AIAG ndc bands
  still appear in the UI subheader and exporter sentences (**#237**).

- **The SPC capability stability gate now lives in the engine, not only in the Streamlit page
  (audit A09, #191).** `assess_control_chart` (page-only, outside the coverage gate) moved to
  `spc_app/spc_engine/stability.py::assess_stability`; the page keeps only its stream →
  chart-type map. `CapabilityStudy` gains two keys — `stable: bool | None` and
  `stability_note: str | None` — populated on all four method paths (normal / boxcox /
  yeojohnson / percentile), and `compute_capability_study` gains a keyword-only
  `violations` parameter carrying the caller's out-of-control signal list. **`stable is None`
  means stability was *not assessed*** (no control-chart context supplied) and is never
  defaulted to `True`; `violations=[]` means assessed and in control. The engine does not
  derive the control chart itself — I-MR on flattened subgrouped data understates sigma and
  flips verdicts (RULE 7 / D3). Indices are annotated, never suppressed (SME: annotate, do not
  block). **`compute_capability` is unchanged** — same signature, same return keys (SECOM
  depends on it directly). No behavior change on the demo streams: all 7 report the same
  signal counts as before.

- **SPC run-rule fidelity: WE 2/3 same-side logic and Nelson's own 1–8 numbering (#192,
  F-03/F-04).** `_count_same_side` (Western Electric rules 2/3, and their Nelson
  equivalents) required the *opposite* side to have zero hits before counting a same-side
  signal, contradicting the documented "on the same side" rule and silently suppressing real
  out-of-control signals whenever one stray point landed on the other side. Fixed to count
  each side independently. Separately, `detect_nelson_violations` used to start from
  `detect_we_violations`'s output verbatim, so selecting the Nelson rule set emitted
  `"Western Electric Rule 1-4"` labels (including WE's 8-in-a-row) instead of Nelson's own
  numbering, and never emitted Nelson Test 2 (9-in-a-row) at all. The Nelson set now emits
  only `"Nelson Rule 1"`–`"Nelson Rule 8"` per Nelson (1984); Western Electric keeps its own
  `"Western Electric Rule 1-4"` labels and 8-in-a-row run length (the two rule sets are a
  mutually exclusive selector, never shown together). **Consumer impact:** no public
  signature changed, but every label string under the Nelson rule set changes, including
  `apps/secom`'s default chart output (`ruleset` defaults to `"nelson"`).

- **MSA `%GRR` vs tolerance was understated 6× (audit A07, #190).** `compute_gage_rr()` computed
  `pgrr_tolerance = (grr / tolerance) * 100`, dividing a bare 1-sigma `grr` (EV/AV/GRR/PV/TV are all
  carried in 1-sigma units, `K = 1/d2*`) by a full spec width — the AIAG MSA 4th Ed. tolerance-basis
  criterion requires the 6-sigma *study variation* as the numerator, not σ_GRR (§3.3). Verified
  against a reproduction of the manual's own report form (AIAG reference study, `apps/msa/data/
  aiag_reference_study.csv`): the engine reported 6.92%, the form's `% Tolerance (SV/Toler)` line
  reports 41.80%. New module constant `_STUDY_VARIATION_SIGMA = 6.0` in `gage_rr_engine.py` fixes
  the numerator; the same study's verdict correctly flips Marginal → Reject (41.5% > 30%, matching
  the source form's own "unacceptable" flag). `_compute_verdict()` also collapses from
  `(ndc, pgrr_tolerance, pgrr_study)` to `(ndc, pgrr)` — the caller already computed
  `max(pgrr_tolerance, pgrr_study)` before calling it, making the old third parameter dead code.
  `%GRR_study` and `ndc` are unaffected (the multiplier cancels there); no other app or exporter
  needed changes since `pgrr_tolerance`'s type and meaning are unchanged, only its value.

- **`quality_core.io` ingest is now reductive, not just assertive: `validate_table` returns only the
  columns it validated (#200).** `validate_table` checked `required_columns` and then returned the
  caller's frame verbatim, so any other column — SPC's `sample_size`, `lsl`, `usl` among them —
  reached the engines unvalidated; the only guard was the `try/except` in the Streamlit pages, the
  layer the web migration deletes. `TableSchema` gains `optional_columns`: columns that need not be
  present, but are validated by the same `row_model` and returned when they are. `validate_table`
  now returns a copy narrowed to the required columns plus the present optional ones, so an
  undeclared column cannot reach an engine through `load_table`. SPC declares
  `sample_size`/`lsl`/`usl`/`chart_type` (validated: `sample_size > 0` and finite — a u chart's
  area of opportunity is legitimately fractional — finite tolerances,
  `chart_type` restricted to the six engine chart keys) and drops the unused `parameter`; Control
  Plan's app-local `_reject_bad_optional_values` is deleted in
  favour of the core mechanism it prototyped. Related engine fix:
  `spc_engine._validate_attribute_inputs` now rejects a non-finite sample size — `np.nan <= 0` is
  `False`, so a NaN `n` previously slipped the positivity check and produced NaN control limits with
  no error.

- **`spc-app` and `secom-app` are now installable (editable) workspace packages, so
  `secom_app.charts`/`.capability` resolve `spc_app.spc_engine` (and `secom_app` itself
  resolves for `apps/api`) outside pytest (#204).** Declaring `spc-app` as a `secom-app`
  dependency alone was inert — every app set `[tool.uv] package = false`, so uv resolved
  the dependency but never installed the `spc_app` module. Both `apps/spc/pyproject.toml`
  and `apps/secom/pyproject.toml` now drop `package = false` for a
  `[build-system]`/`[tool.hatch.build.targets.wheel]` block (flat layout, mirroring
  `packages/quality-core`'s `src/` block), and `secom-app` declares `spc-app` as a
  `{ workspace = true }` dependency. `apps/secom/conftest.py`'s `sys.path` hacks for
  `apps/spc` (redundant — spc_app is now installed) and for `apps/secom` itself
  (redundant — secom_app is now installed) are removed; the `apps/msa` entry stayed at the time,
  because `msa-app` was not yet installable — **#231, in this same release, makes it installable
  and deletes `apps/secom/conftest.py` outright.** New
  `apps/secom/tests/test_import_boundary.py` proves both imports in a clean,
  non-pytest interpreter with no conftest involved. This remains a stopgap — #205
  (promoting the SPC engine into `quality_core`) is the real fix.

### Added

- **SPC UI wiring for Week-10 features + run-rule gating (W10-5, #145).** EWMA and CUSUM
  are now reachable from the Control Charts page (standards-default λ/L and k/h/FIR
  pre-filled from `constants.py`; `mu0`/`sigma` come from an independent I-MR baseline
  fit, never the z-series/accumulators themselves), alongside a Phase I (establish &
  freeze) / Phase II (monitor against frozen limits) toggle for X̄-R/X̄-S/I-MR built on
  W10-1's `phase.py`. **Load-bearing correctness fix:** a single gated chokepoint,
  `rule_detection.detect_violations(chart_type, ...)`, now routes every WE/Nelson caller
  (both the Control Charts page and the Capability page's stability gate) — it returns
  `[]` for any non-Shewhart `chart_type` (EWMA/CUSUM) or non-positive sigma, so run-rules
  statistically invalid on autocorrelated EWMA/CUSUM series can no longer fire, from any
  caller. The Capability page gained a `force_method` sidebar override
  (`compute_capability_study(..., force_method="auto"|"normal"|"boxcox"|"percentile")`)
  letting an analyst force normal-theory, Box-Cox/Yeo-Johnson, or fitted-percentile
  capability regardless of the Shapiro-Wilk result, with the histogram overlay now
  matching the selected method: the fitted-percentile winner's `.pdf` in raw space, or
  the exact back-transformed Box-Cox/Yeo-Johnson normal density via change-of-variables
  (`f_X(x) = φ((t(x)-μ_t)/σ_t)/σ_t · |t'(x)|`). The capability exporter gained Method / λ
  / Pp & Ppk 95% CI / Ppk lower bound / CI basis / fitted-distribution rows (CI attachment
  corrected to Pp/Ppk under #193). Documented in
  `apps/spc/docs/ASSUMPTIONS_LOG.md` RULE 15 (WE/Nelson restricted to Shewhart charts;
  Montgomery §9 autocorrelation rationale) plus an assumption note on the `force_method`
  override.

- **Non-normal capability via Box-Cox + Pp/Ppk confidence intervals (W10-4, #144).** New
  `compute_capability_study` in `apps/spc/spc_app/spc_engine/capability.py` orchestrates a full
  capability study on individuals or 2D subgroups: Shapiro-Wilk gate → Box-Cox (positive data)
  or Yeo-Johnson (`allow_yeojohnson=True` default; opt-in documented shift `c=1−min(x)` +
  Box-Cox otherwise) when non-normal → re-test the transformed data → normal-theory Cp/Cpk
  (parametric CIs on Pp/Ppk) in the transformed space, or a fitted-distribution percentile fallback (ISO 22514-2,
  `{lognorm, weibull_min, gamma, johnsonsu}` selected by minimum AIC, empirical `np.quantile`
  last resort if every candidate fit fails) when it stays non-normal. Within-σ reuses the
  existing `compute_imr`/`compute_xbar_r` estimators in the same (raw or transformed) space as
  the capability computation, preserving the Cp/Cpk-within vs Pp/Ppk-overall split; λ<0 is
  handled by a `sorted()` ordering guard on the transformed spec limits, never a literal swap.
  `compute_capability` (existing signature untouched) gains `alpha`, `n`, and χ² / Bissell (1990)
  large-sample CIs attached to **Pp/Ppk** (`pp_ci`, `ppk_ci`, `ppk_lower`) — the ddof=1-estimator
  indices the interval math is derived for (attachment corrected under #193; see the Fixed entry).
  The fitted-percentile path instead gets a **deterministic bootstrap** CI (fixed
  `BOOTSTRAP_SEED = 12345`, `BOOTSTRAP_RESAMPLES = 2000`, `scipy.stats.bootstrap(method=
  "percentile")`) for bit-reproducible audit trails. New constants `CAPABILITY_ALPHA`,
  `BOXCOX_LAMBDA_CANDIDATES`, `NONNORMAL_LOWER_PCTL`, `NONNORMAL_UPPER_PCTL`,
  `PERCENTILE_FIT_CANDIDATES`, `BOOTSTRAP_SEED`, `BOOTSTRAP_RESAMPLES` in `constants.py`.
  Documented in `apps/spc/docs/ASSUMPTIONS_LOG.md` RULE 14, with NIST §6.5.2/§6.1.6 as the
  primary/quotable Box-Cox and percentile-index sources, and Montgomery Ch. 8 / Bissell (1990) /
  ISO 22514-2 / Box & Cox (1964) / Efron & Tibshirani (1993) flagged secondary/paywalled where
  applicable.

- **CUSUM control chart (W10-3, #143).** New `compute_cusum` in
  `apps/spc/spc_app/spc_engine/control_charts.py` computes the tabular two-sided CUSUM on
  standardized individuals: `C+`/`C−` positive-accumulator recursions with a mandatory
  `max(0, …)` reset barrier on both arms, an optional FIR head-start (`h/2`) seeded on both
  arms, and `n_plus`/`n_minus` run-length counters estimating shift onset. `CUSUMResult`
  echoes `k`/`h`/`fir` alongside the series. New constants `CUSUM_DEFAULT_K = 0.5`,
  `CUSUM_DEFAULT_H = 5.0`, `CUSUM_FIR_FRACTION = 0.5` in `constants.py`. `build_cusum_chart`
  in `visualizer.py` is a standalone `go.Figure` (two accumulators, no symmetric CL, so it
  does not delegate to `build_control_chart`): `C+` plotted upward, `C−` negated for display
  only (Montgomery Fig. 9.2 two-sided style — the stored `c_minus` stays a positive
  accumulator), decision-interval lines at both `+h` and `−h`. No WE/Nelson run-rule gating
  on CUSUM points (autocorrelated; deferred to W10-5). Documented in
  `apps/spc/docs/ASSUMPTIONS_LOG.md` RULE 13, including the explicit flag that the issue's
  quoted ARL figures trace to Montgomery §9.1/Lucas (1976), not NIST §6.3.2.3, and the
  Lucas & Crosier (1982) FIR citation (paywalled primary, checked against Montgomery §9.1.4).

- **EWMA control chart (W10-2, #142).** New `compute_ewma` in
  `apps/spc/spc_app/spc_engine/control_charts.py` computes the exponentially weighted moving
  average on individuals from an independent Phase I `(mu0, sigma)` pair, with exact
  time-varying limits (not the asymptotic approximation) that widen from point 1 toward the
  asymptote. `EWMAResult` carries a soft-warn `pairing_adequate`/`pairing_note` pair (never
  raises) flagging a λ/L combination that deviates from the tabulated Lucas & Saccucci (1990)
  pairing by more than 0.01, mirroring W10-1's `baseline_adequate`/`baseline_note`. New
  constants `EWMA_DEFAULT_LAMBDA = 0.20`, `EWMA_DEFAULT_L = 2.860`, and `EWMA_L_BY_LAMBDA` in
  `constants.py`. `build_ewma_chart` in `visualizer.py` delegates to the existing
  `build_control_chart` (now with an additive `x_axis_title` param, default `"Subgroup"`)
  passing `x_axis_title="Observation"` and per-point limits/signal markers — no new plotting
  code. Documented in `apps/spc/docs/ASSUMPTIONS_LOG.md` RULE 12, including the
  Lucas & Saccucci-via-Montgomery paywall flag.

- **Phase I/II control-limit freezing (W10-1, #141).** New
  `apps/spc/spc_app/spc_engine/phase.py` adds `freeze_xbar_r/_s/_imr`, which screen a
  Phase I baseline (documented-cause exclusion via `ExcludedPoint`, non-empty `cause`
  required) and reuse the existing `compute_xbar_r/_s/_imr` on the retained points to
  produce a `FrozenLimits` TypedDict — an all-primitives, JSON-serializable audit record
  (no storage layer). A soft guardrail (`baseline_adequate` / `baseline_note`, never
  raises) flags baselines below `MIN_BASELINE_SUBGROUPS = 25` (NIST §6.3.2.1) or
  `MIN_BASELINE_INDIVIDUALS = 100` (Montgomery, secondary). `compute_xbar_r/_s/_imr` in
  `control_charts.py` gain an optional `frozen=` argument so Phase II data is plotted
  against fixed limits instead of recomputing them; a guard rejects a `frozen` struct
  whose chart type or subgroup size doesn't match the new data. New constants
  `MIN_BASELINE_SUBGROUPS`/`MIN_BASELINE_INDIVIDUALS` in `constants.py`, documented in
  `apps/spc/docs/ASSUMPTIONS_LOG.md` RULE 11.

- **SECOM DOE screening analysis (W11-1, #72).** New
  `apps/secom/secom_app/doe_screening.py` adds `screen_signals()`, an
  observational univariate effect screen of pass/fail on the
  `select_signals()`-kept candidate signals — Cohen's d effect size and
  Welch's two-sample t-test per signal (`scipy.stats.ttest_ind`,
  `equal_var=False`), with Benjamini-Hochberg FDR-adjusted significance
  (`scipy.stats.false_discovery_control`, q < 0.05, a screening convention
  not a quality-standard threshold). Explicitly labelled a screening
  ANALYSIS of association — SECOM's factor levels are observational, never
  set or randomized, so this is NOT a designed experiment and NOT causal.
  Adds `scipy>=1.17.1`/`numpy>=2.4.4` to `apps/secom/pyproject.toml`
  (already in the workspace lock via `spc-app`). Engine-only, no Streamlit
  page. `apps/secom/docs/ASSUMPTIONS_LOG.md` RULE 14 documents the method
  and standard-vs-convention labelling.

- **SECOM case-study writeup (W09-6, #70).** New
  `apps/secom/docs/CASE_STUDY.md`, a short, honest condensation of the W09-1..5
  series (ingest/selection -> SPC charts -> capability -> MSA applicability ->
  yield/DPPM/Pareto), citing only test-locked headline numbers (1567 x 590
  shape, 1463/104 pass/fail split, 93.363% yield, 66,368.86 DPPM) with a
  mandatory Limitations section covering honest missingness (NaN-preserved,
  never imputed) and SECOM's observational nature (no designed measurement
  study: MSA does not apply, capability limits are caller-supplied, the
  failing-signal Pareto is association not causation). Pure docs — no code,
  no new coverage surface; one-line pointers added from `apps/secom/README.md`
  and `docs/README.md`.

- **SECOM yield/DPPM + failing-signal Pareto (W09-5, #69).** New
  `secom_app/yield_dppm.py` adds `yield_summary()` (pass/fail counts ->
  yield fraction/pct and DPPM) and `failing_signal_pareto()`, an
  association/screening Pareto that reuses the *existing* W09-2 SPC
  violation detection (`control_charts_for_selection`, no anomaly rule
  re-derived) to rank kept signals by the number of special-cause violation
  events landing on failed wafers (SME resolution: events, not distinct
  failed-wafer count; zero-contributor signals dropped from the table).
  DPPM is explicitly labelled **defective units per million, not DPMO**
  (SECOM carries one pass/fail verdict per wafer, no defects-and-
  opportunities count) — no acceptance threshold is invented. The Pareto is
  explicitly labelled association/screening, not root-cause attribution
  (SECOM's label attributes no failure to any signal). Also ships a thin,
  non-gated Streamlit page, `secom_app/pages/yield_dppm.py`
  (`render_yield_dppm()`), rendering yield, DPPM, and the Pareto table/chart
  — the SME added this scope over the series' engine-only default because
  the issue itself asked for a "view." `apps/secom/docs/ASSUMPTIONS_LOG.md`
  RULE 12 (yield/DPPM, DPPM-not-DPMO) and RULE 13 (association Pareto
  construction, labelled a defensible heuristic) record both decisions.
  SECOM CI coverage gate extended to `secom_app.yield_dppm` (100%
  line+branch); `secom_app.pages` stays outside the gate, matching SPC/MSA.

- **SECOM MSA applicability guard (W09-4, #68).** SECOM has no
  `part`/`appraiser`/`trial` structure and none can be legitimately
  constructed (different sensors measure different characteristics, not
  repeat appraisals of one measurand; successive wafers are different parts,
  not re-measurements of the same part) — the honest deliverable is a
  standards-anchored "MSA does not apply" document plus an executable
  refusal guard, not a fabricated Gage R&R. New
  `apps/secom/docs/MSA_APPLICABILITY.md` records the AIAG MSA 4th ed.
  Section 3.1/3.2 justification, cross-referencing the SME-verified
  `apps/msa/docs/ASSUMPTIONS_LOG.md` RULE 1/RULE 11/RULE 12 (no new AIAG
  section numbers, tables, or thresholds introduced). New
  `secom_app/msa.py` adds `gage_rr_applicability()` /
  `assert_gage_rr_applicable()`, which detect missing
  `part`/`appraiser`/`trial` columns and return/raise a standards-anchored
  verdict — no Gage R&R math (EV/AV/%GRR/ndc/verdict) is reimplemented;
  a real study still runs through the existing `apps/msa` app
  (`compute_gage_rr`). `apps/secom/conftest.py` gained an `apps/msa`
  `sys.path` shim (mirroring the existing `apps/spc` block) so the test
  suite could import the real AIAG engine and prove it also rejects
  SECOM-shaped frames — **superseded by #231 in this same release, which
  makes `msa-app` installable and deletes that conftest entirely.** `apps/secom/docs/ASSUMPTIONS_LOG.md` RULE 11 records
  the finding. SECOM CI coverage gate extended to `secom_app.msa` (100%
  line+branch).

- **SECOM real capability, Cp/Cpk (W09-3, #67).** New `secom_app/capability.py`
  adds `capability_for_signal()`, which reuses the *existing* SPC
  `compute_capability` (`apps/spc/spc_app/spc_engine/capability.py`) unchanged
  against the W09-2 I-MR control chart's present values and within-process
  σ̂ = MR̄/d₂ — no Cp/Cpk math is re-derived. Limits are caller-supplied only
  (`lsl`/`usl`, either may be `None` for one-sided); the module never derives,
  defaults, or fabricates a limit (both `None` raises `ValueError`; `lsl >=
  usl` raises `ValueError`). Capability is coupled to the W09-2 stability
  gate: on a signal with any special-cause `violations`, the indices are
  still computed but returned with `stable=False` and a `stability_warning`
  (mirrors `apps/spc/spc_app/pages/process_capability.py:156`) rather than
  hard-suppressed. `charts.py` stays untouched and pure control-chart; the
  new code lives in a separate module. `apps/secom/docs/ASSUMPTIONS_LOG.md`
  RULE 9/RULE 10 record both resolutions with AIAG citations and standard-
  vs-heuristic labels. SECOM CI coverage gate extended to
  `secom_app.capability` (100% line+branch). No UI page (later W09 issue).

- **SECOM SPC control charts (W09-2, #66).** New `secom_app/charts.py` runs
  every `select_signals()`-kept sensor through the *existing* SPC I-MR engine
  (`apps/spc/spc_app/spc_engine/`: `compute_imr`, `detect_we_violations`,
  `detect_nelson_violations`), reused read-only via a `sys.path` shim added to
  `apps/secom/conftest.py` (mirrors the `fmea_app` cross-app precedent) — no
  control-limit math or rule detection is reimplemented. Handles SECOM's
  honest missingness by splitting each signal into maximal NaN-free runs
  before any moving-range math, so a moving range never spans a missing cell;
  within-run moving ranges pool into one control-limit set per signal.
  Attaches a per-signal lag-1 autocorrelation diagnostic (`lag1_autocorr`,
  `autocorr_flag`, threshold `1.96/sqrt(n)`, Bartlett's white-noise bound) —
  diagnostic only, never a filter or gate. `control_charts_for_selection()`
  charts every `status=="keep"` signal from a selection audit. RED LINE
  unchanged: no USL/LSL fabricated, no `compute_capability`, no Cp/Cpk/Pp/Ppk.
  Every resolution recorded in `apps/secom/docs/ASSUMPTIONS_LOG.md`. SECOM CI
  coverage gate extended to `secom_app.charts` (100% line+branch). No UI page
  (later W09 issue).

- **SECOM dataset ingest + signal selection (W09-1, #65).** New `apps/secom/`
  app package (mirrors msa/controlplan). `secom_app/ingest.py` (`load_secom`,
  `secom_missingness`) reads the two vendored raw UCI SECOM files
  (`data/secom.data`, `data/secom_labels.data`; 1567 runs x 590 sensors, no
  header) into an aligned, NaN-preserving `SecomDataset` — deliberately not
  routed through `quality_core.io.load_table`'s per-row validation, which would
  reject SECOM's honest missing cells; only `IngestError` is reused for
  structural failures (row-count mismatch, out-of-domain labels).
  `secom_app/selection.py` (`select_signals`) screens the 590 signals for
  SPC/capability suitability with three ordered filters — a `MIN_NON_MISSING =
  100` present-value floor (AIAG SPC capability sample-size guidance), an
  unconditional zero-variance drop, and a near-zero-variance drop
  (`caret::nearZeroVar` defaults, flagged as a third-party heuristic, not a
  quality standard) — returning a full per-signal audit table. Spec limits
  (USL/LSL) and Cp/Cpk remain out of scope: SECOM ships none, and no limits are
  fabricated. Every criterion and its source is recorded in
  `apps/secom/docs/ASSUMPTIONS_LOG.md`. New CI coverage gate
  (`secom_app.ingest` + `secom_app.selection`, 100% line+branch) mirrors the
  MSA/SPC gates. No UI yet — later W09 issues wire SECOM into SPC/capability/
  MSA/yield-Pareto.

- **MSA tests + CI coverage gate (W08-4, #57).** New engine reference test asserts
  `compute_gage_rr` against the AIAG MSA 4th-ed "study case 1" published
  EV/AV/%GRR/ndc/verdict, loaded from a new fixture
  `apps/msa/data/aiag_reference_study.csv` (raw 10x3x3 canonical study). New
  "MSA coverage gate" CI step enforces `--cov-fail-under=100` on
  `msa_app.gage_rr_engine` + `msa_app.schema` + `msa_app.exporter`, mirroring
  the SPC and Control Plan gates.
- **MSA app UI — study entry, results, verdict + export (W08-3, #56).** The Gage
  R&R page now shows a loop-link note (Control Plan → MSA → SPC) and a
  plain-English verdict interpretation sentence, and exports the study/results
  as CSV/Excel/PDF via `quality_core.io`. New `apps/msa/msa_app/exporter.py`
  (`GageStudyReport`, `export_csv`, `export_results_csv`, `export_excel`,
  `export_pdf`, `verdict_sentence`) mirrors the SPC/Control Plan exporter
  pattern; two CSV downloads are offered (the validated study frame, and a flat
  results table). New standalone `apps/msa/app.py`; the platform shell landing
  page (`shell/home.py`) now lists an MSA feature card.

### Changed

- **README + ROADMAP reconciled with the tree (A01, #208).** Both documents described a platform
  that no longer exists: README's architecture omitted SECOM and marked Control Plan / MSA as
  unshipped, and its layout tree listed two of five apps; ROADMAP §3 still described "two Streamlit
  apps ... consumed twice". Both now state **five workspace members — four mounted in the shell,
  SECOM engine-only** — with grep-verified `quality_core` dependency edges. ROADMAP Week 12 is
  rewritten from the **cancelled** Reflex migration to the decided web platform (FastAPI + Next.js,
  one repo, `web/` at root — `docs/research/web-platform-migration.md`). Documentation only.
- **SECOM recorded as engine-only (A02, #206).** ROADMAP §3, `apps/secom/README.md`, and
  `secom_app/__init__.py` now state that SECOM is a tested *library* — consumed by its suite and,
  from P3, by the API — deliberately not mounted in the Streamlit shell. Recorded so API-route
  enumeration reads the workspace members, not the shell's navigation map.

### Removed

- **Orphan SECOM Streamlit page deleted (A02, #206).** `secom_app/pages/yield_dppm.py`
  (`render_yield_dppm()`, W09-5) was mounted nowhere and, per the engine-only decision, never
  will be; the now-empty `secom_app/pages/` package goes with it. The engine
  (`secom_app/yield_dppm.py`) and its 100% CI gate are untouched — the page was ungated and
  untested, so no covered line was lost.

### Tests

- **#198's escaping is now actually asserted.** The fix originally shipped with no test: the io
  gate still read 100% because existing tests crossed the new lines incidentally, so reverting
  the fix left all 240 tests green. Five regression tests in
  `packages/quality-core/tests/test_export.py` cover header-label escaping, duplicate labels,
  `write_table_sheet` header + body, `write_keyvalue_sheet` label + value, and the
  numeric-exemption guard. All five were verified to fail against the pre-#198 code.

### Security

- **`defusedxml` is now a direct dependency of `quality-core`, and Streamlit is no longer one
  (audit A11, #202).** `quality_core.io.validate.read_table` parses uploaded `.xlsx` with
  `pd.read_excel`, which hardens the workbook XML against entity-expansion/quadratic-blowup attacks
  only while `openpyxl.xml.DEFUSEDXML` is true — i.e. only while `defusedxml` is importable. It was
  true by accident, transitively via `fpdf2`, which no core code path requires; the package that
  owns the Excel read now owns the hardening explicitly. In the same change `streamlit>=1.56.0` moved
  from `[project.dependencies]` to a `streamlit` **optional extra**, so a base `quality-core` install
  is exactly `pandas` + `pydantic` + `openpyxl` + `defusedxml` and no longer drags the Streamlit
  chain (`gitpython`, `tornado`, `protobuf`, `pyarrow`, `pydeck`, `altair`, …) into every consumer of
  the shared core — a scoped resolve of `quality-core` went from 6 of those packages to 0. Two guards
  keep it that way: a CI step that resolves `quality-core`'s own subtree from the lock and fails on
  any Streamlit-chain package, and `test_packaging.py`, which asserts the non-extra requirement set
  is *exactly* those four names (so dropping `defusedxml` as "unused" also fails). `theme/style.py`
  and its lazy `__getattr__` shim are retained deliberately — the shim is what lets a base install
  import `quality_core.theme` tokens at all, and the five Streamlit apps each declare `streamlit`
  themselves, so they and the README's standalone launches are unaffected. `requirements.txt` still
  lists Streamlit for that reason; that is correct, not a failed change.

- **`quality_core.io` ingest now fails closed (A05, #199).** Three findings in
  `read_table`/`load_table` fixed at the shared primitive, not in callers:
  (1) **HIGH, CWE-400** — the byte ceiling trusted a caller-supplied `.size`
  attribute and silently skipped the check for any source without one;
  `read_table` now *measures* the stream by seeking, and an unmeasurable source
  (not seekable, or missing `tell`/`seek`) is rejected with `IngestError`
  rather than let through. (2) **MEDIUM, CWE-918/CWE-73** — `read_table`
  accepted a `str`/`PathLike` and handed it to pandas, which resolves a string
  as a local path *or a URL*; `Source` is now `bytes | bytearray | BinaryIO`
  only (raw bytes are wrapped in `io.BytesIO`), and a filesystem path is
  reachable only via the new, separately named `read_table_from_path` /
  `load_table_from_path`, which `open()` the path directly — a URL-shaped
  string is simply an unreadable local path, not a network request, so no URL
  blocklist was added. New `DEFAULT_MAX_ROWS = 1_000_000` /
  `DEFAULT_MAX_COLUMNS = 1_000` caps (enforced during the parse via
  `nrows=max_rows + 1`, a secondary cell-count control) round out the DoD; all
  three (`max_bytes`/`max_rows`/`max_columns`) keep `None` as an explicit
  opt-out, distinct from "unmeasurable." The four Streamlit app loaders
  (`load_spc_csv`, `load_gage_study_csv`, `load_control_plan_csv`,
  `load_uploaded_fmea`) keep their `str | BinaryIO` signature and now dispatch
  to `load_table_from_path` for a `str` demo path, `load_table` otherwise; the
  FMEA CLI (`fmea_analyzer.py`) switched to `read_table_from_path`. (3)
  **MEDIUM, CWE-400 (JSON)** — `load_scales_from_json`
  (`apps/fmea/fmea_app/rating_scales.py`) only caught `JSONDecodeError`/
  `UnicodeDecodeError`, so a deeply nested "JSON bomb" escaped as an uncaught
  `RecursionError` past `ui/filters.py`'s `except ValueError`; it now checks a
  byte-length ceiling (reusing `quality_core.io.DEFAULT_MAX_UPLOAD_BYTES`,
  no second literal) before parsing and normalises every `json.loads` failure
  to `ValueError`. `secom_app` deliberately does not use this boundary and is
  unchanged; `validate_table`'s return value and the column-contract work are
  a separate issue and untouched here.

- **Export header row now escaped for formula injection (A04, #198).** `sanitize_for_export`
  (`packages/quality-core/src/quality_core/io/export.py`) previously escaped only cell values,
  leaving the CSV/Excel header row — including uploader-controlled column names reachable via
  `validate_table` — writable straight to row 1 unescaped; it now runs column labels through the
  same `sanitize_cell` apostrophe-prefix as values, after the value pass, preserving `MultiIndex`
  structure and non-string label dtypes. Also fixed a duplicate-column-label hole where
  `DataFrame.apply` handed `sanitize_cell` a whole `Series` instead of scalars, silently skipping
  escaping entirely: values are now sanitized positionally (`iloc`-based), covering duplicate
  labels too. `write_table_sheet`'s header cell and string body cells are now escaped the same
  way, so every caller inherits the fix from the shared primitive without depending on its own
  `columns=` allow-list. Per OWASP WSTG-INPV-21 (Testing for CSV Injection) / CWE-1236 (Improper
  Neutralization of Formula Elements in a CSV File); the `'` prefix is OWASP's named mitigation,
  not a universal guarantee — OWASP itself notes some spreadsheet applications strip it on
  save/re-open. `write_keyvalue_sheet` now escapes its labels and values too, so all four of its
  app callers (SPC, MSA, Control Plan, FMEA) inherit the guarantee from the primitive rather
  than owning it themselves — which is the whole point of this issue. To make that safe,
  `_is_numeric_literal` exempts text that parses as a number: openpyxl stores a leading
  apostrophe as a literal character, so escaping a formatted metric would have visibly corrupted
  `-3.0000` into `'-3.0000` in every summary sheet. A payload that merely *starts* like a number
  (`-3.0000+cmd|' /C calc'!A0`) does not parse and is still escaped. `FORMULA_PREFIXES` is
  unchanged.

### Tests

- **#198's escaping is now actually asserted.** The fix originally shipped with no test: the io
  gate still read 100% because existing tests crossed the new lines incidentally, so reverting
  the fix left all 240 tests green. Five regression tests in
  `packages/quality-core/tests/test_export.py` cover header-label escaping, duplicate labels,
  `write_table_sheet` header + body, `write_keyvalue_sheet` label + value, and the
  numeric-exemption guard. All five were verified to fail against the pre-#198 code.

## [0.12.0] - 2026-07-26

### Added

- **SPC UI wiring for Week-10 features + run-rule gating (W10-5, #145).** EWMA and CUSUM
  are now reachable from the Control Charts page (standards-default λ/L and k/h/FIR
  pre-filled from `constants.py`; `mu0`/`sigma` come from an independent I-MR baseline
  fit, never the z-series/accumulators themselves), alongside a Phase I (establish &
  freeze) / Phase II (monitor against frozen limits) toggle for X̄-R/X̄-S/I-MR built on
  W10-1's `phase.py`. **Load-bearing correctness fix:** a single gated chokepoint,
  `rule_detection.detect_violations(chart_type, ...)`, now routes every WE/Nelson caller
  (both the Control Charts page and the Capability page's stability gate) — it returns
  `[]` for any non-Shewhart `chart_type` (EWMA/CUSUM) or non-positive sigma, so run-rules
  statistically invalid on autocorrelated EWMA/CUSUM series can no longer fire, from any
  caller. The Capability page gained a `force_method` sidebar override
  (`compute_capability_study(..., force_method="auto"|"normal"|"boxcox"|"percentile")`)
  letting an analyst force normal-theory, Box-Cox/Yeo-Johnson, or fitted-percentile
  capability regardless of the Shapiro-Wilk result, with the histogram overlay now
  matching the selected method: the fitted-percentile winner's `.pdf` in raw space, or
  the exact back-transformed Box-Cox/Yeo-Johnson normal density via change-of-variables
  (`f_X(x) = φ((t(x)-μ_t)/σ_t)/σ_t · |t'(x)|`). The capability exporter gained Method / λ
  / Cp & Cpk 95% CI / Cpk lower bound / fitted-distribution rows. Documented in
  `apps/spc/docs/ASSUMPTIONS_LOG.md` RULE 15 (WE/Nelson restricted to Shewhart charts;
  Montgomery §9 autocorrelation rationale) plus an assumption note on the `force_method`
  override.


- **Non-normal capability via Box-Cox + Cp/Cpk confidence intervals (W10-4, #144).** New
  `compute_capability_study` in `apps/spc/spc_app/spc_engine/capability.py` orchestrates a full
  capability study on individuals or 2D subgroups: Shapiro-Wilk gate → Box-Cox (positive data)
  or Yeo-Johnson (`allow_yeojohnson=True` default; opt-in documented shift `c=1−min(x)` +
  Box-Cox otherwise) when non-normal → re-test the transformed data → normal-theory Cp/Cpk/CIs
  in the transformed space, or a fitted-distribution percentile fallback (ISO 22514-2,
  `{lognorm, weibull_min, gamma, johnsonsu}` selected by minimum AIC, empirical `np.quantile`
  last resort if every candidate fit fails) when it stays non-normal. Within-σ reuses the
  existing `compute_imr`/`compute_xbar_r` estimators in the same (raw or transformed) space as
  the capability computation, preserving the Cp/Cpk-within vs Pp/Ppk-overall split; λ<0 is
  handled by a `sorted()` ordering guard on the transformed spec limits, never a literal swap.
  `compute_capability` (existing signature/keys untouched) gains `alpha`, `n`, `cp_ci`, `cpk_ci`,
  `cpk_lower` — a χ² exact CI for Cp and a Bissell (1990) large-sample CI for Cpk. The
  fitted-percentile path instead gets a **deterministic bootstrap** CI (fixed
  `BOOTSTRAP_SEED = 12345`, `BOOTSTRAP_RESAMPLES = 2000`, `scipy.stats.bootstrap(method=
  "percentile")`) for bit-reproducible audit trails. New constants `CAPABILITY_ALPHA`,
  `BOXCOX_LAMBDA_CANDIDATES`, `NONNORMAL_LOWER_PCTL`, `NONNORMAL_UPPER_PCTL`,
  `PERCENTILE_FIT_CANDIDATES`, `BOOTSTRAP_SEED`, `BOOTSTRAP_RESAMPLES` in `constants.py`.
  Documented in `apps/spc/docs/ASSUMPTIONS_LOG.md` RULE 14, with NIST §6.5.2/§6.1.6 as the
  primary/quotable Box-Cox and percentile-index sources, and Montgomery Ch. 8 / Bissell (1990) /
  ISO 22514-2 / Box & Cox (1964) / Efron & Tibshirani (1993) flagged secondary/paywalled where
  applicable.


- **CUSUM control chart (W10-3, #143).** New `compute_cusum` in
  `apps/spc/spc_app/spc_engine/control_charts.py` computes the tabular two-sided CUSUM on
  standardized individuals: `C+`/`C−` positive-accumulator recursions with a mandatory
  `max(0, …)` reset barrier on both arms, an optional FIR head-start (`h/2`) seeded on both
  arms, and `n_plus`/`n_minus` run-length counters estimating shift onset. `CUSUMResult`
  echoes `k`/`h`/`fir` alongside the series. New constants `CUSUM_DEFAULT_K = 0.5`,
  `CUSUM_DEFAULT_H = 5.0`, `CUSUM_FIR_FRACTION = 0.5` in `constants.py`. `build_cusum_chart`
  in `visualizer.py` is a standalone `go.Figure` (two accumulators, no symmetric CL, so it
  does not delegate to `build_control_chart`): `C+` plotted upward, `C−` negated for display
  only (Montgomery Fig. 9.2 two-sided style — the stored `c_minus` stays a positive
  accumulator), decision-interval lines at both `+h` and `−h`. No WE/Nelson run-rule gating
  on CUSUM points (autocorrelated; deferred to W10-5). Documented in
  `apps/spc/docs/ASSUMPTIONS_LOG.md` RULE 13, including the explicit flag that the issue's
  quoted ARL figures trace to Montgomery §9.1/Lucas (1976), not NIST §6.3.2.3, and the
  Lucas & Crosier (1982) FIR citation (paywalled primary, checked against Montgomery §9.1.4).


- **EWMA control chart (W10-2, #142).** New `compute_ewma` in
  `apps/spc/spc_app/spc_engine/control_charts.py` computes the exponentially weighted moving
  average on individuals from an independent Phase I `(mu0, sigma)` pair, with exact
  time-varying limits (not the asymptotic approximation) that widen from point 1 toward the
  asymptote. `EWMAResult` carries a soft-warn `pairing_adequate`/`pairing_note` pair (never
  raises) flagging a λ/L combination that deviates from the tabulated Lucas & Saccucci (1990)
  pairing by more than 0.01, mirroring W10-1's `baseline_adequate`/`baseline_note`. New
  constants `EWMA_DEFAULT_LAMBDA = 0.20`, `EWMA_DEFAULT_L = 2.860`, and `EWMA_L_BY_LAMBDA` in
  `constants.py`. `build_ewma_chart` in `visualizer.py` delegates to the existing
  `build_control_chart` (now with an additive `x_axis_title` param, default `"Subgroup"`)
  passing `x_axis_title="Observation"` and per-point limits/signal markers — no new plotting
  code. Documented in `apps/spc/docs/ASSUMPTIONS_LOG.md` RULE 12, including the
  Lucas & Saccucci-via-Montgomery paywall flag.


- **Phase I/II control-limit freezing (W10-1, #141).** New
  `apps/spc/spc_app/spc_engine/phase.py` adds `freeze_xbar_r/_s/_imr`, which screen a
  Phase I baseline (documented-cause exclusion via `ExcludedPoint`, non-empty `cause`
  required) and reuse the existing `compute_xbar_r/_s/_imr` on the retained points to
  produce a `FrozenLimits` TypedDict — an all-primitives, JSON-serializable audit record
  (no storage layer). A soft guardrail (`baseline_adequate` / `baseline_note`, never
  raises) flags baselines below `MIN_BASELINE_SUBGROUPS = 25` (NIST §6.3.2.1) or
  `MIN_BASELINE_INDIVIDUALS = 100` (Montgomery, secondary). `compute_xbar_r/_s/_imr` in
  `control_charts.py` gain an optional `frozen=` argument so Phase II data is plotted
  against fixed limits instead of recomputing them; a guard rejects a `frozen` struct
  whose chart type or subgroup size doesn't match the new data. New constants
  `MIN_BASELINE_SUBGROUPS`/`MIN_BASELINE_INDIVIDUALS` in `constants.py`, documented in
  `apps/spc/docs/ASSUMPTIONS_LOG.md` RULE 11.



## [0.11.0] - 2026-07-24

### Added

- **SECOM DOE screening analysis (W11-1, #72).** New
  `apps/secom/secom_app/doe_screening.py` adds `screen_signals()`, an
  observational univariate effect screen of pass/fail on the
  `select_signals()`-kept candidate signals — Cohen's d effect size and
  Welch's two-sample t-test per signal (`scipy.stats.ttest_ind`,
  `equal_var=False`), with Benjamini-Hochberg FDR-adjusted significance
  (`scipy.stats.false_discovery_control`, q < 0.05, a screening convention
  not a quality-standard threshold). Explicitly labelled a screening
  ANALYSIS of association — SECOM's factor levels are observational, never
  set or randomized, so this is NOT a designed experiment and NOT causal.
  Adds `scipy>=1.17.1`/`numpy>=2.4.4` to `apps/secom/pyproject.toml`
  (already in the workspace lock via `spc-app`). Engine-only, no Streamlit
  page. `apps/secom/docs/ASSUMPTIONS_LOG.md` RULE 14 documents the method
  and standard-vs-convention labelling.

## [0.9.0] - 2026-07-24

### Added

- **SECOM case-study writeup (W09-6, #70).** New
  `apps/secom/docs/CASE_STUDY.md`, a short, honest condensation of the W09-1..5
  series (ingest/selection -> SPC charts -> capability -> MSA applicability ->
  yield/DPPM/Pareto), citing only test-locked headline numbers (1567 x 590
  shape, 1463/104 pass/fail split, 93.363% yield, 66,368.86 DPPM) with a
  mandatory Limitations section covering honest missingness (NaN-preserved,
  never imputed) and SECOM's observational nature (no designed measurement
  study: MSA does not apply, capability limits are caller-supplied, the
  failing-signal Pareto is association not causation). Pure docs — no code,
  no new coverage surface; one-line pointers added from `apps/secom/README.md`
  and `docs/README.md`.

- **SECOM yield/DPPM + failing-signal Pareto (W09-5, #69).** New
  `secom_app/yield_dppm.py` adds `yield_summary()` (pass/fail counts ->
  yield fraction/pct and DPPM) and `failing_signal_pareto()`, an
  association/screening Pareto that reuses the *existing* W09-2 SPC
  violation detection (`control_charts_for_selection`, no anomaly rule
  re-derived) to rank kept signals by the number of special-cause violation
  events landing on failed wafers (SME resolution: events, not distinct
  failed-wafer count; zero-contributor signals dropped from the table).
  DPPM is explicitly labelled **defective units per million, not DPMO**
  (SECOM carries one pass/fail verdict per wafer, no defects-and-
  opportunities count) — no acceptance threshold is invented. The Pareto is
  explicitly labelled association/screening, not root-cause attribution
  (SECOM's label attributes no failure to any signal). Also ships a thin,
  non-gated Streamlit page, `secom_app/pages/yield_dppm.py`
  (`render_yield_dppm()`), rendering yield, DPPM, and the Pareto table/chart
  — the SME added this scope over the series' engine-only default because
  the issue itself asked for a "view." `apps/secom/docs/ASSUMPTIONS_LOG.md`
  RULE 12 (yield/DPPM, DPPM-not-DPMO) and RULE 13 (association Pareto
  construction, labelled a defensible heuristic) record both decisions.
  SECOM CI coverage gate extended to `secom_app.yield_dppm` (100%
  line+branch); `secom_app.pages` stays outside the gate, matching SPC/MSA.

- **SECOM MSA applicability guard (W09-4, #68).** SECOM has no
  `part`/`appraiser`/`trial` structure and none can be legitimately
  constructed (different sensors measure different characteristics, not
  repeat appraisals of one measurand; successive wafers are different parts,
  not re-measurements of the same part) — the honest deliverable is a
  standards-anchored "MSA does not apply" document plus an executable
  refusal guard, not a fabricated Gage R&R. New
  `apps/secom/docs/MSA_APPLICABILITY.md` records the AIAG MSA 4th ed.
  Section 3.1/3.2 justification, cross-referencing the SME-verified
  `apps/msa/docs/ASSUMPTIONS_LOG.md` RULE 1/RULE 11/RULE 12 (no new AIAG
  section numbers, tables, or thresholds introduced). New
  `secom_app/msa.py` adds `gage_rr_applicability()` /
  `assert_gage_rr_applicable()`, which detect missing
  `part`/`appraiser`/`trial` columns and return/raise a standards-anchored
  verdict — no Gage R&R math (EV/AV/%GRR/ndc/verdict) is reimplemented;
  a real study still runs through the existing `apps/msa` app
  (`compute_gage_rr`). `apps/secom/conftest.py` gains an `apps/msa`
  `sys.path` shim (mirroring the existing `apps/spc` block) so the test
  suite can import the real AIAG engine and prove it also rejects
  SECOM-shaped frames. `apps/secom/docs/ASSUMPTIONS_LOG.md` RULE 11 records
  the finding. SECOM CI coverage gate extended to `secom_app.msa` (100%
  line+branch).

- **SECOM real capability, Cp/Cpk (W09-3, #67).** New `secom_app/capability.py`
  adds `capability_for_signal()`, which reuses the *existing* SPC
  `compute_capability` (`apps/spc/spc_app/spc_engine/capability.py`) unchanged
  against the W09-2 I-MR control chart's present values and within-process
  σ̂ = MR̄/d₂ — no Cp/Cpk math is re-derived. Limits are caller-supplied only
  (`lsl`/`usl`, either may be `None` for one-sided); the module never derives,
  defaults, or fabricates a limit (both `None` raises `ValueError`; `lsl >=
  usl` raises `ValueError`). Capability is coupled to the W09-2 stability
  gate: on a signal with any special-cause `violations`, the indices are
  still computed but returned with `stable=False` and a `stability_warning`
  (mirrors `apps/spc/spc_app/pages/process_capability.py:156`) rather than
  hard-suppressed. `charts.py` stays untouched and pure control-chart; the
  new code lives in a separate module. `apps/secom/docs/ASSUMPTIONS_LOG.md`
  RULE 9/RULE 10 record both resolutions with AIAG citations and standard-
  vs-heuristic labels. SECOM CI coverage gate extended to
  `secom_app.capability` (100% line+branch). No UI page (later W09 issue).

- **SECOM SPC control charts (W09-2, #66).** New `secom_app/charts.py` runs
  every `select_signals()`-kept sensor through the *existing* SPC I-MR engine
  (`apps/spc/spc_app/spc_engine/`: `compute_imr`, `detect_we_violations`,
  `detect_nelson_violations`), reused read-only via a `sys.path` shim added to
  `apps/secom/conftest.py` (mirrors the `fmea_app` cross-app precedent) — no
  control-limit math or rule detection is reimplemented. Handles SECOM's
  honest missingness by splitting each signal into maximal NaN-free runs
  before any moving-range math, so a moving range never spans a missing cell;
  within-run moving ranges pool into one control-limit set per signal.
  Attaches a per-signal lag-1 autocorrelation diagnostic (`lag1_autocorr`,
  `autocorr_flag`, threshold `1.96/sqrt(n)`, Bartlett's white-noise bound) —
  diagnostic only, never a filter or gate. `control_charts_for_selection()`
  charts every `status=="keep"` signal from a selection audit. RED LINE
  unchanged: no USL/LSL fabricated, no `compute_capability`, no Cp/Cpk/Pp/Ppk.
  Every resolution recorded in `apps/secom/docs/ASSUMPTIONS_LOG.md`. SECOM CI
  coverage gate extended to `secom_app.charts` (100% line+branch). No UI page
  (later W09 issue).

- **SECOM dataset ingest + signal selection (W09-1, #65).** New `apps/secom/`
  app package (mirrors msa/controlplan). `secom_app/ingest.py` (`load_secom`,
  `secom_missingness`) reads the two vendored raw UCI SECOM files
  (`data/secom.data`, `data/secom_labels.data`; 1567 runs x 590 sensors, no
  header) into an aligned, NaN-preserving `SecomDataset` — deliberately not
  routed through `quality_core.io.load_table`'s per-row validation, which would
  reject SECOM's honest missing cells; only `IngestError` is reused for
  structural failures (row-count mismatch, out-of-domain labels).
  `secom_app/selection.py` (`select_signals`) screens the 590 signals for
  SPC/capability suitability with three ordered filters — a `MIN_NON_MISSING =
  100` present-value floor (AIAG SPC capability sample-size guidance), an
  unconditional zero-variance drop, and a near-zero-variance drop
  (`caret::nearZeroVar` defaults, flagged as a third-party heuristic, not a
  quality standard) — returning a full per-signal audit table. Spec limits
  (USL/LSL) and Cp/Cpk remain out of scope: SECOM ships none, and no limits are
  fabricated. Every criterion and its source is recorded in
  `apps/secom/docs/ASSUMPTIONS_LOG.md`. New CI coverage gate
  (`secom_app.ingest` + `secom_app.selection`, 100% line+branch) mirrors the
  MSA/SPC gates. No UI yet — later W09 issues wire SECOM into SPC/capability/
  MSA/yield-Pareto.

## [0.8.0] - 2026-07-20

Week 08 — MSA / Gage R&R module. Adds Measurement Systems Analysis as a first-class app: a
typed gage-study schema and scaffold (#54); a Gage R&R engine computing repeatability (EV),
reproducibility (AV), %GRR vs study variation and vs tolerance, and ndc by the AIAG
Average-and-Range method, with an accept/marginal/reject verdict against AIAG thresholds (#55);
a Streamlit study-entry / results / verdict UI with CSV/Excel/PDF export and the platform-shell
feature card (#56); and an AIAG-reference regression test plus a 100% line+branch coverage gate
on the engine, schema, and exporter, mirroring the SPC and Control Plan gates (#57). Milestone
issues #54, #55, #56, #57 closed; every coverage bar green on `dev` (quality_core.io 100%,
quality_core.schema 100% line+branch, SPC 100%, MSA engine/schema/exporter 100%).

### Added

- **Gage R&R engine — Average-and-Range method (W08-2, #55).** New
  `apps/msa/msa_app/gage_rr_engine.py` (`compute_gage_rr`) computes repeatability
  (EV) and reproducibility (AV), %GRR against both study variation and tolerance,
  and the number of distinct categories (ndc), returning an accept / marginal /
  reject verdict against AIAG thresholds (ndc ≥ 5; %GRR <10% good, 10–30%
  marginal, >30% reject). Formulas are anchored to the AIAG MSA 4th-edition
  reference — no invention — with the derivation recorded in the MSA
  `ASSUMPTIONS_LOG`.
- **MSA app UI — study entry, results, verdict + export (W08-3, #56).** The Gage
  R&R page now shows a loop-link note (Control Plan → MSA → SPC) and a
  plain-English verdict interpretation sentence, and exports the study/results
  as CSV/Excel/PDF via `quality_core.io`. New `apps/msa/msa_app/exporter.py`
  (`GageStudyReport`, `export_csv`, `export_results_csv`, `export_excel`,
  `export_pdf`, `verdict_sentence`) mirrors the SPC/Control Plan exporter
  pattern; two CSV downloads are offered (the validated study frame, and a flat
  results table). New standalone `apps/msa/app.py`; the platform shell landing
  page (`shell/home.py`) now lists an MSA feature card.
- **MSA tests + CI coverage gate (W08-4, #57).** New engine reference test asserts
  `compute_gage_rr` against the AIAG MSA 4th-ed "study case 1" published
  EV/AV/%GRR/ndc/verdict, loaded from a new fixture
  `apps/msa/data/aiag_reference_study.csv` (raw 10x3x3 canonical study). New
  "MSA coverage gate" CI step enforces `--cov-fail-under=100` on
  `msa_app.gage_rr_engine` + `msa_app.schema` + `msa_app.exporter`, mirroring
  the SPC and Control Plan gates.


## [0.7.0] - 2026-07-18

Week 07 — Close the loop. Completes the AIAG improvement loop end to end: a Control Plan
characteristic auto-configures the SPC view (spec/tolerance, sample size/frequency,
recommended chart type) with no manual re-entry (#88); an out-of-control SPC signal emits
candidate occurrence-rating / CAPA feedback back to the source FMEA cause — human-in-the-loop,
never auto-committed, anchored to the AIAG FMEA-4 / SAE J1739 occurrence table (#89); and a
dedicated cross-app integration test proves the full FMEA → Control Plan → SPC → FMEA walk on
real sample data, with the SPC coverage floor ratcheted to 100% line+branch (#90). Milestone
issues #88, #89, #90, #91 closed; all coverage bars green on `dev`.

### Added

- **SPC — Control Plan → Control Charts config (W07-1, #88).** The Control
  Charts page now reads a loaded Control Plan from session state and offers a
  "Characteristic (from Control Plan)" selector; picking one preselects the
  chart type from `recommended_chart` (falling back to the manual selectbox
  when it's `None`/invalid) and shows an info panel with LSL/USL/target,
  sample size, and frequency. New pure module
  `apps/spc/spc_app/control_plan_config.py` (`plan_characteristics`,
  `config_for`, `chart_type_index`) does the derivation — no new SPC math, no
  visualizer changes, no `controlplan_app` import from `spc_app` (the
  standalone SPC app still imports cleanly). Added to the SPC coverage gate in
  CI and `apps/spc/CLAUDE.md`.

- **SPC → FMEA candidate occurrence feedback + loop close (W07-2, #89).** An
  out-of-control signal on a Control Plan characteristic's chart now emits a
  **candidate** occurrence-rating / CAPA payload toward the source FMEA
  cause — never auto-committed. New pure module `apps/spc/spc_app/
  fmea_feedback.py` (`summarize_violations`, `build_occurrence_feedback`)
  maps the chart's OOC failing-rate onto the AIAG FMEA-4 (2008) / SAE J1739
  occurrence rate table (cited in-module; AIAG-VDA 2019 defines no numeric
  occurrence table, so the rate mapping is anchored to the legacy AIAG-4/J1739
  standard — see `docs/ASSUMPTIONS_LOG.md` Rule 10). `ControlPlanRow` gained a
  nullable `source_cause_id` join key (`controlplan_app/schema.py`),
  populated by a refactored `connector.build_control_plan` /
  new `connector.source_index`, so the SPC↔FMEA linkage survives Control
  Plan CSV export/reimport. A new per-characteristic demo SPC stream
  (`ply_misalignment`) binds a real, out-of-control monitored parameter to
  the composite-panel FMEA demo's highest-risk characteristic. The FMEA page
  renders a read-only candidate panel (no `spc_app` import). Closes the full
  FMEA → Control Plan → SPC → FMEA walk in the unified shell. Added
  `spc_app.fmea_feedback` to the SPC coverage gate (CI + `apps/spc/CLAUDE.md`).

### Tests

- **Dedicated Week-7 loop integration test (W07-4, #90).** New
  `apps/spc/tests/test_loop_integration.py` walks the composite-panel FMEA
  demo through the full Control Plan → SPC → FMEA chain on real sample data
  (no stubbed boundaries) and asserts the join-key round-trips end to end —
  the candidate feedback's `source_cause_id` matches the originating Control
  Plan row's and names the correct FMEA cause — and that the human-in-the-loop
  invariant holds (`current_occurrence` echoes unchanged, `suggested_occurrence`
  is a distinct candidate, nothing mutates the FMEA source mapping). Guarded
  with `pytest.importorskip` so it runs under the full root `uv run pytest`
  and skips cleanly under the isolated SPC gate. SPC coverage floor ratcheted
  95% → 100% (`.github/workflows/ci.yml`, `apps/spc/CLAUDE.md`) — all gated
  SPC modules already sit at 100% line+branch, so the ratchet is earned and
  safe.

## [0.6.0] - 2026-07-18

Week 06 — Control Plan. Closes the FMEA → Control Plan half of the AIAG loop: a
connector engine that turns relational FMEA failure modes into typed Control Plan
rows (with the AIAG SPC chart-selection rule table and AP/RPN prioritization), a
Streamlit authoring UI (ingest → review/edit → injection-safe CSV/Excel/PDF
export), and the enforcement to keep it honest — a 100% line+branch coverage gate
on the connector + schema, plus the Control Plan app added to the mypy gate.
Milestone issues #83, #84, #85, #86, #95 closed; all coverage bars green on `dev`.

### Added

- **CI — Control Plan coverage gate (W06-4, #86).** New `Control Plan coverage gate`
  step in `.github/workflows/ci.yml`, mirroring the SPC gate pattern, holds
  `controlplan_app.connector` + `controlplan_app.schema` (the FMEA→Control Plan
  engine and validated ingest schema) at 100% line+branch coverage. Scope excludes
  `controlplan_app.exporter` (W06-3), which is out of scope for #86. No test or
  source files changed — `test_connector.py` + `test_schema.py` already meet the
  floor.

- **`apps/controlplan` — Control Plan app UI (W06-3, #85).** The Control Plan page
  now runs the full FMEA → Control Plan flow: upload a flat FMEA CSV (or click
  "Load demo FMEA") through the shared `quality_core.io.load_table` boundary,
  adapt it with `flat_to_relational`, and derive a draft plan via
  `controlplan_app.connector.build_control_plan`. The generated rows are shown in
  an editable `st.data_editor` (add/delete rows, a `recommended_chart`
  selectbox); edits are re-validated through the existing
  `ControlPlanRow`/`ControlPlanDataset` models before export — the trust
  boundary is never skipped. New `controlplan_app/exporter.py` composes the
  shared `quality_core.io.export` primitives (mirrors `fmea_app/exporter.py`,
  minus matplotlib/chart pages — a Control Plan is a table) for CSV/Excel/PDF
  download buttons. The FMEA demo and input template CSVs are copied
  locally into `apps/controlplan/data/` (SME-resolved: self-contained app, no
  cross-app path coupling). Adds `openpyxl`/`fpdf2` to the app's dependencies.

- **`apps/controlplan` — FMEA → Control Plan connector engine (W06-2, #84).** New
  `controlplan_app.connector` maps a relational FMEA
  (`quality_core.schema.relational.RelationalFMEA`) into the #83 typed
  `ControlPlanDataset` output contract: `build_control_plan(fmea)` emits one row per
  `FailureMode` (worst-link S/O/D via `quality_core.scoring.rpn`/`action_priority`),
  sorted highest-risk first (AP then RPN, mirroring `fmea_app.ap_engine.rank_by_ap`);
  `characteristic` is derived from the owning `Function`'s component + the failure
  mode (collision-safe); `measurement_method` comes from the worst link's Current
  Process Control. Fields the relational FMEA has no source for
  (`sample_size`, `frequency`, `reaction_plan`, `recommended_chart`) are documented
  placeholder defaults (`# ponytail:`-marked) the W06-3 authoring UI will make
  editable. Also ships the standalone, fully-cited `recommend_chart(...)` AIAG
  SPC chart-selection rule table (variable: I-MR/Xbar-R/Xbar-S by subgroup size;
  attribute: p/c/u by defect-vs-defective and constant-vs-variable sample) as the
  standards core for later enrichment. New
  `apps/controlplan/docs/ASSUMPTIONS_LOG.md` records the citation and flags the
  Xbar-R↔Xbar-S subgroup-size boundary (n≥10→S) for primary-source confirmation.
  Engine + typed output only — no UI (W06-3, #85) and no CP→SPC→FMEA loop (Week 7).

- **`apps/msa` — Measurement System Analysis scaffold.** A new `msa_app` package mounts into the
  unified shell under an "MSA" nav group (Gage R&R page), following the SPC app pattern. It ships an
  app-local typed gage-study schema (`GageStudyRow` / `GageStudyDataset`) and validated CSV ingest via
  `quality_core.io.load_table`: rows carry `part, appraiser, trial, measurement`; ingest checks row
  types and `(part, appraiser, trial)` uniqueness. Study-level tolerance (USL/LSL) is captured as page
  inputs, not a CSV column. Includes a `gage_rr_template.csv` input template + download button. The
  Gage R&R computation (%GRR, ndc, AIAG verdict) lands in a later issue (#54).
- **`apps/controlplan`** — Control Plan app scaffold: shell-mounted (`app.py`,
  "Control Plan" nav group), version SSOT, and conftest, following the `apps/msa`
  pattern. Adds an app-local typed Control Plan row/dataset schema
  (`controlplan_app.schema`) on the shared `quality_core.io` validated-ingest
  boundary — characteristic, spec/tolerance (LSL/target/USL), measurement method,
  sample size/frequency, a nullable recommended SPC chart, and reaction plan, with
  a USL>LSL check, a target-within-`[lsl, usl]` check, and duplicate-characteristic
  dataset rejection. Scaffold + schema only — FMEA→Control Plan mapping (W06-2) and
  the authoring UI (W06-3) land later (#83).

### Changed

- **Ship-pipeline model routing** — split the four subagents by stage instead of all-Opus: the
  reasoning gates stay on Opus 4.8 (`research` = spec-in, `reviewer` = quality-out), while the
  spec-constrained middle stages move to Sonnet 5 (`coder`, `tester`). Keeps Opus judgment exactly
  where a mistake is expensive to unwind and cuts per-run model cost ~43% (coder+tester are ~54% of
  pipeline tokens, Sonnet ≈ 1/5 the per-token cost). Config-only change to `.claude/agents/*.md`.

### Fixed

- **mypy gate now covers `apps/controlplan` (W06-5, #95).** Added
  `apps/controlplan/controlplan_app,` to `mypy.ini`'s `files=` list, closing the gap
  where the app's typed library package was silently skipped by CI's bare
  `uv run mypy`. Adding the app surfaced a real (pre-existing) error at
  `control_plan.py:55` — a `**dict` unpack into `FMEARow` — fixed with the same
  `cast("dict[str, Any]", ...)` pattern already used in `fmea_app/rpn_engine.py`
  (type-only change, no runtime behavior difference). `uv run mypy` is green.

## [0.5.0] - 2026-07-10

Week 05: **relational domain model + cross-tool schema contracts.** The FMEA schema moves into the
shared core and gains an AIAG/VDA relational model (Function → Failure Mode → Effect/Cause/Control)
with loss-less flat adapters, action tracking + effectiveness, and end-to-end relational scoring/
exports. The engineering system was written down (Definition of Done, playbook, PR workflow) and
branch coverage turned on across every gate.

### Added

- **`quality_core.schema`** — the FMEA row/dataset contracts (`FMEARow`, `FMEADataset`), promoted out
  of the FMEA app so every tool shares one schema; re-exported from `fmea_app.schema` (zero-behaviour
  change), held at 100% by its own tests + a CI gate (W05-1, #34).
- **`quality_core.schema.relational`** — the AIAG/VDA relational model **Function → FailureMode →
  Effect / Cause / Control** (Severity on the Effect, Occurrence on the Cause, Detection on the
  Control), with loss-less `flat_to_relational` / `relational_to_flat` adapters. The model enforces
  the canonical invariants (unique IDs; no two entities share a `(description, rating)` pair; every
  entity referenced by ≥1 link) so the flat↔relational round-trip is loss-less both directions
  (W05-2, #35).
- **Shared schema base** — `quality_core.schema._base` (`StrictModel`, `find_duplicates`); the flat
  and relational models reuse one blank-rejection validator and one duplicate finder instead of
  hand-copying (#35).
- **Engineering system docs** — `docs/DEFINITION_OF_DONE.md`, `docs/ENGINEERING_SYSTEM_PLAYBOOK.md`,
  `docs/README.md`, `CONTRIBUTING.md`, and the project `ROADMAP.md`, codifying the issue → gates → PR
  → release loop (#41).
- **`quality_core.scoring`** — the shared scalar risk scorers `rpn(s,o,d)` and `action_priority(s,o,d)`
  (the AIAG-VDA 2019 Action Priority table), promoted out of the FMEA app so `quality_core` can score
  without importing an app; held at 100% by its own tests + a CI gate. `fmea_app.ap_engine` now
  re-exports the scalar API and keeps its pandas `calculate_ap` / `rank_by_ap` layers — zero-behaviour
  change (W05-3a, #44).
- **`quality_core.schema.action`** — FMEA action tracking + effectiveness (the AIAG "optimization"
  loop): `Action` (owner, `due` date, `ActionStatus` enum, optional re-rated `s_after`/`o_after`/
  `d_after`) and `Action.effectiveness(severity, occurrence, detection)` → an `Effectiveness` value
  reporting RPN and Action Priority **before → after**, the RPN delta, and whether AP dropped a band.
  Unset `*_after` fall back to the original; the original assessment is never mutated (W05-3, #36).
- **Relational FMEA engine entrypoint** — `fmea_app.rpn_engine.run_pipeline_relational(model)` (and
  `relational_to_dataframe`) run the W05-2 relational model through the exact same
  validate → score → rank pipeline as the flat path, so structured input scores and exports
  identically. Proven by content-level export equivalence (CSV bytes, Excel data-sheet grid, and
  PDF with timestamps stripped) against the flat-equivalent (W05-4, #37).
- **Action-tracking columns in FMEA exports** — a `FailureLink` can now carry an optional `Action`;
  when present, `relational_to_dataframe` appends action columns (owner, status, due, S/O/D after,
  revised RPN/AP, RPN delta via `Action.effectiveness`, blank for rows without an action). Excel and
  CSV render the extra columns; the PDF gains an **"Action Tracking"** page. All formula-injection-safe;
  action-free models export identically to the flat path (W05-4b, #47).
- **Relational + action-tracking UI (FMEA app)** — a **Relational** tab shows the
  Function → Failure Mode → Effect/Cause/Control hierarchy (auto-built from any upload via the W05-2
  adapter), and an **Actions** tab provides a per-failure action editor (owner, status, due, re-rated
  S'/O'/D') that reports before→after RPN/AP + the RPN delta and offers an action-aware Excel/PDF/CSV
  download. Flat CSV/Excel uploads are unchanged and auto-convert to the relational view (W05-5, #38).

### Changed

- **Branch coverage is on** — `branch = true` + `show_missing = true` in `pyproject.toml`; every
  per-surface gate (io/schema 100%, SPC ≥95%) now measures line **and** branch. Baseline recorded in
  `docs/COVERAGE_BASELINE_2026-07-09.md` (#41).
- **`quality_core.schema` locked at 100%** — the relational + action model is held at the 100%
  line+branch CI gate (established W05-1), with a consolidated guardrail-contract test asserting every
  malformed relational payload surfaces a clear, entity/row-addressed error (W05-6, #39).
- **Workflow** — adopt PR-per-issue + squash-merge with CI-green-required, going forward (#41).

### Fixed

- **`quality_core.io` `_format_row_error`** — removed a dead defensive branch (`"input" in first`;
  Pydantic's default `errors()` always carries `input`) and made the value echo crash-safe via
  `.get`; io is now 100% line + branch (#41).

## [0.4.0] - 2026-06-24

Week 04: Shared validation + export. The reuse story is now demonstrable — a single
`quality_core/io` library owns CSV/Excel/PDF export and validated CSV/Excel ingest, and **both**
FMEA and SPC consume it. SPC gained downloadable reports and validated uploads; FMEA was pointed
at the shared library with zero behaviour change (exports byte-identical).

🔗 Live: <https://quality-platform-nplyhc6rvsd3bfw6q9vvkd.streamlit.app/>

### Added

- **`quality_core/io` export primitives** — app-agnostic CSV/Excel (openpyxl)/PDF (fpdf2) building
  blocks: formula-injection escaping (`sanitize_for_export`, scalar `sanitize_cell`), styled table
  and key/value sheets, and PDF chrome (`render_table`, `add_image_page`, `pdf_title`,
  `pdf_subheader`, `pdf_summary_cells`).
- **`quality_core/io` validated-ingest boundary** (`validate.py`) — `read_table` (CSV/Excel read +
  size guard), pluggable `TableSchema` (per-tool Pydantic model), and `load_table`, all surfacing a
  user-safe `IngestError` (a `ValueError`) with row-addressed messages instead of stack traces.
- **SPC report export** — downloadable Excel + PDF for control-chart (per-point values, the UCL/LCL
  each point was tested against, rule violations) and capability (Cp/Cpk/Pp/Ppk, distribution,
  normality, stability) reports; injection-safe.
- **SPC validated uploads** — control-chart and capability uploads run through `load_table` with an
  SPC schema (`spc_app/schema.py`), so a malformed CSV gives a friendly error.

### Changed

- **FMEA points at the shared `quality_core/io`** — its hand-rolled PDF chrome and upload/CLI read
  now compose the core helpers. Verified content-identical (xlsx/pdf/csv); FMEA's domain-specific
  validation messages are intentionally preserved.
- **One shared IO implementation across both tools** — "write export and validation once, consume
  twice" is now real, replacing per-app copies.

### Tested

- **`quality_core.io` at 100% coverage** from its own tests (injection + validation paths), locked
  by a CI gate; the SPC testable surface (now including the report exporter and upload schema) stays
  gated at ≥95%.

## [0.3.0] - 2026-06-16

Week 03: AP-native FMEA. FMEA moves from RPN-only to the AIAG/VDA 2019 Action Priority standard —
the full published S×O×D → High/Medium/Low table, a user-selectable prioritization basis, and
data-driven rating scales — with the AP table verified cell-by-cell against the AIAG & VDA FMEA
Handbook (2019) primary source.

🔗 Live: <https://quality-platform-nplyhc6rvsd3bfw6q9vvkd.streamlit.app/>

### Added

- **AIAG-VDA Action Priority (AP) engine** (`fmea_app/ap_engine.py`) — the complete published
  S×O×D → High/Medium/Low table (no approximation), with `action_priority()`, `calculate_ap()`,
  and `rank_by_ap()`. Severity-weighted (S → O → D), but high severity does not auto-escalate.
- **RPN ↔ AP toggle** in the FMEA app — both columns shown side by side; the selected basis drives
  ranking, tiering, the critical-items view, and the Excel / PDF / CSV exports.
- **Data-driven S/O/D rating scales** — AIAG default in `data/rating_scales.json` plus a validated
  custom-scale upload, with an in-app Rating Scale reference (`fmea_app/rating_scales.py`).
- **Primary-source verification of the AP table** — the engine matches the AIAG & VDA FMEA Handbook
  (2019) table for all 1000 S/O/D combinations, cross-checked against an external peer-reviewed
  case study (MDPI, Pop et al. 2026), guarded by an independent test oracle.

### Changed

- **FMEA version single-source-of-truth** — `fmea_app.__version__`, read by the exporter and the
  app sidebar, with a drift-guard test; the hardcoded `"1.0.0"` is removed.
- **FMEA docs** — methodology §4.2, `ASSUMPTIONS_LOG.md` Rule 7, and the README now document the AP
  engine and cite the verified handbook primary source.

### Fixed

- **Corrected the AP table's Severity 9-10 block** — a transcription from a third-party reproduction
  had shifted the occurrence rows (e.g. `S9-10/O1` was `H,M,L,L`; the handbook is all `Low`). Caught
  in code review, resolved against the primary source. Monotonicity alone did not catch it (the
  shifted block stayed monotonic), so the test oracle is now transcribed from the handbook.
- **Critical-items panel** cites the correct standard under the AP basis; **rating-scale upload**
  rejects custom keys that collide on integer coercion (`"1"` vs `"1.0"`).

### Notes

- FMEA: 266 tests; platform: 390 tests, ruff + mypy clean.

## [0.2.0] - 2026-06-15

Week 02: SPC parity. The SPC app is brought to the same engineering bar as FMEA — type-safe,
lint-clean, coverage-gated, with two capability/charting gaps closed and full planning docs.

🔗 Live: <https://quality-platform-nplyhc6rvsd3bfw6q9vvkd.streamlit.app/>

### Added

- **c-chart** surfaced in the Control Charts UI (`compute_c` was implemented but unwired): new
  constant-area `panel_defects` demo stream, render branch with WE/Nelson rule overlays, and
  metric tiles.
- **Capability stability gate** — the Process Capability page now runs Western Electric rule
  detection first and warns prominently that Cp/Cpk are not valid on an out-of-control process.
- **SPC coverage gate** in CI — the testable SPC surface (engine + simulation + visualizer) is
  enforced at ≥95% (`--cov-fail-under`); brought to 100% (incl. the previously-untested
  `simulation/engine.py`).
- **SPC planning docs** — `apps/spc/CLAUDE.md`, `apps/spc/docs/ASSUMPTIONS_LOG.md` (every AIAG
  constant + threshold cited), and a version single-source-of-truth (`spc_app.__version__`) with
  a drift-guard test.

### Changed

- **SPC is now mypy-clean and in the type gate** — replaced lossy `dict[str, float | list[float]]`
  engine returns with precise TypedDicts; `spc_app` added to `mypy.ini`.
- **SPC is now ruff-clean** under the unified root config (import-ordering enforced).
- **Dependency pins reconciled** to one coherent set — every dependency declared `>=<locked
  version>`, identical across `quality-core` and both apps; dev-tool floors aligned to locked.

### Removed

- Stray `apps/spc/docs/superpowers/` plan/spec artifacts from the standalone era.

### Notes

- FMEA: 105 tests. SPC: now 124 tests (engine/simulation/visualizer at 100%). Workspace: 229 tests,
  ruff + mypy clean, CI gate + SPC coverage gate green.

## [0.1.0] - 2026-06-15

First public release — Week 01: monorepo + shared core. The platform now publicly exists.

🔗 Live: <https://quality-platform-nplyhc6rvsd3bfw6q9vvkd.streamlit.app/>

### Added

- **Monorepo** housing the FMEA Risk Analyzer (`apps/fmea`) and Manufacturing SPC Dashboard
  (`apps/spc`), each migrated with full original commit history preserved.
- **`quality_core`** shared package — schema, IO, and a unified theme (amber/violet palette +
  RPN risk-tier tokens) consumed by both apps.
- **Unified shell** (`app.py`) — a single `st.navigation` surface mounting a landing page, FMEA,
  and the three SPC workflows (Control Charts, Process Capability, Live Simulation). One
  `set_page_config` + theme, mounted render callables.
- **Unified tooling** — one `ruff.toml`, one `mypy.ini`, and a workspace pytest config covering
  `quality-core` + both apps with combined coverage.
- **CI** (`.github/workflows/ci.yml`) — `uv sync → ruff → mypy → pytest` on every push and PR to
  `main`, Python 3.11 via `astral-sh/setup-uv`.
- **`requirements.txt`** exported from `uv.lock` (third-party, pinned) as the Streamlit Cloud
  deploy fallback; the shell resolves all first-party code from the repo via `sys.path`.

### Notes

- FMEA: 105 tests, ruff + mypy clean. SPC: 83 tests (ruff/mypy lint cleanup scheduled for W02).
- uv is the toolchain; the workspace runs on Python 3.11.

[0.3.0]: https://github.com/Siddardth7/quality-platform/releases/tag/v0.3.0
[0.2.0]: https://github.com/Siddardth7/quality-platform/releases/tag/v0.2.0
[0.1.0]: https://github.com/Siddardth7/quality-platform/releases/tag/v0.1.0
