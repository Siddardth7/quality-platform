# AUDIT_REPORT.md — DRAFT (in progress)

> Status: **draft, growing per phase.** Finalized in Phase 7 (prioritized fix queue + Critical/High second-opinion review). Phase 8 clears the queue.
>
> Last phase added: **Phase 2 — Correctness & bug hunt** (2026-06-05).

---

## Executive summary (placeholder — written at Phase 7)

To be filled in once Phases 3–6 are done. Today's reading: codebase is well-structured (clean orchestrator → engine → adapter split, 88% coverage on `src/`, ruff clean) but contains **one bug that breaks the live app on the current pandas pin** and a handful of medium-severity correctness + state issues that are easy wins.

---

## Baseline (Phase 1, recorded 2026-06-05)

Environment: `/opt/homebrew/bin/python3.11` (3.11.15), deps installed from `requirements.txt` + `requirements-dev.txt`.

| Check | Result |
|---|---|
| pytest | **97 passed, 1 FAILED** (`test_app_integration.py::test_demo_renders_without_exception`) |
| Coverage on `src/` | **88%** — `rpn_engine` 100, `visualizer` 100, `exporter` 97, `schema` 97, **`plotly_charts` 18%** (gap) |
| ruff | clean |
| mypy (`--ignore-missing-imports`) | **3 errors**, all in `src/visualizer.py` |
| vulture (≥70 confidence) | 2 hits: `source_active` (app.py:271), `cls` (false positive on pydantic validator) |

Repo facts verified: `app.py` 739 LOC, `fmea_analyzer.py` 258 LOC and **not** a duplicate of `src/` — it imports `run_pipeline` from `src.rpn_engine` and chart fns from `src.visualizer` (thin CLI wrapper; keep).

---

## Phase 2 — Correctness & bug hunt

Each finding: severity • file:line • evidence • fix • effort.

### 🟥 CRITICAL

#### F-017 — App fails to load on pandas 3.0.2
- **File:** `app.py:173`
- **Evidence:** Return-type annotation `pd.io.formats.style.Styler` is evaluated at module import. On `pandas==3.0.2`, `pandas.io.formats.style` is no longer attribute-accessible without an explicit import. Streamlit AppTest in `tests/test_app_integration.py::test_demo_renders_without_exception` fails with `AttributeError: module 'pandas.io.formats' has no attribute 'style'`. The live app cannot start.
- **Fix:** add `from __future__ import annotations` at the top of `app.py` (cheapest); or string-quote the annotation `-> "pd.io.formats.style.Styler"`; or `from pandas.io.formats.style import Styler` and annotate as `Styler`.
- **Effort:** 2 min. Regression test already exists and currently fails.

### 🟧 HIGH

#### F-020 — RPN slider crashes / silently clamps on dataset swap
- **File:** `ui/filters.py:11–21`
- **Evidence:** Widget uses `key="rpn_slider"`, so `st.session_state["rpn_slider"]` is the source of truth and the `value=` kwarg is ignored on rerun. If the user slides to 700 on dataset A (max 800), then uploads dataset B (max 100), `max_value=100` while stored slider value is 700 → Streamlit raises `StreamlitAPIException` ("Slider value 700 is greater than max value 100") or auto-clamps depending on version. The clamp logic on the `value=` argument has no effect.
- **Fix:** before instantiating the slider, explicitly clamp the stored value: `st.session_state["rpn_slider"] = min(st.session_state.get("rpn_slider", 0), _rpn_max)`. Or pop the key when a new dataset loads.
- **Effort:** 10 min + regression test.

### 🟨 MEDIUM

#### F-009 — PDF tempfile leak on exception
- **File:** `src/exporter.py:238–243`
- **Evidence:** `tempfile.NamedTemporaryFile(suffix=".png", delete=False)` followed by `_pdf_chart_page_from_file(...)` then `os.unlink(tmp_path)`. If `_pdf_chart_page_from_file` raises (corrupt PNG, OOM, fpdf2 image-decoding error), the unlink never runs → tmp file leaks. Also leaks if `fig.savefig` throws after the temp file is opened.
- **Fix:** wrap chart-embed in `try/finally`, or use `tempfile.TemporaryDirectory()` as context manager and write PNGs inside it.
- **Effort:** 10 min.

#### F-016 — mypy errors in `src/visualizer.py`
- **File:** `src/visualizer.py:215, 233, 234`
- **Evidence:** `extent=[0.5, 10.5, 0.5, 10.5]` must be a tuple (`imshow` typeshed). `set_xticklabels(range(1, 11))` and `set_yticklabels(range(1, 11))` pass `range[int]`, not `Iterable[str | Text]`.
- **Fix:** `extent=(0.5, 10.5, 0.5, 10.5)`; `set_xticklabels([str(i) for i in range(1, 11)])` (same for y).
- **Effort:** 5 min.

#### F-019 — `use_demo` button is killed by lingering uploader state
- **File:** `app.py:226–229`
- **Evidence:** On rerun after a file was uploaded, `uploaded` is still truthy. If the user then clicks "Use Demo Dataset", the same rerun sets `use_demo=True` (line 227) and immediately overwrites it to `False` (line 229). Demo button silently does nothing.
- **Fix:** on demo-button click, also clear the uploader: pop the file-uploader key from session state (or change the widget key to force-rebuild). Alternatively: gate `use_demo=False` on *fresh* upload events, not on the uploader being non-empty.
- **Effort:** 15 min + regression test.

#### F-012 — `visualizer.pareto_chart` crashes on empty df
- **File:** `src/visualizer.py:87, 94`
- **Evidence:** `cumulative_pct = np.cumsum(rpns) / rpns.sum() * 100` produces NaN if `rpns.sum() == 0` (all-zero RPNs, possible only if validation is skipped, but reachable via direct API use). `max(rpns) * 1.18` raises `ValueError: zero-size array` if `df` is empty. Mitigated for the PDF path by `ui/exports.py:61` `if not df.empty`, so production users won't hit it; library callers and the CLI will.
- **Fix:** early-return a placeholder figure if `len(df) == 0`; guard division: `if rpns.sum() > 0 else np.zeros_like(rpns)`. Mirror the existing guard in `plotly_charts.pareto_chart_plotly:92`.
- **Effort:** 10 min.

### 🟩 LOW

| ID | File:line | Issue | Fix | Effort |
|---|---|---|---|---|
| F-001 | `src/rpn_engine.py:282–290` | `rank_by_rpn` uses `df.apply(_assign_tier, axis=1)` — row-wise Python loop where `np.select` would vectorize. Trivial today, matters in Phase 5 perf testing. | `np.select` with two masks, or chained `.loc[]`. | 10m |
| F-003 | `src/rpn_engine.py:293` | `sort_values("RPN", ascending=False)` has no stable secondary key. RPN-tied rows order by upload position, which is arbitrary. | `sort_values(["RPN","Severity","Occurrence","ID"], ascending=[False,False,False,True])`. | 5m |
| F-004 | `src/rpn_engine.py:130` | Range-violation detection parses pydantic message strings (`"less than or equal"`). Wording can change between pydantic patch releases → silent regression. | Match on `first["type"]` (e.g. `less_than_equal`, `greater_than_equal`). | 10m |
| F-005 | `src/schema.py:34–37` | `reject_blank` only rejects strings that strip to empty. `" Failure_Mode_1"` (single leading space) passes; `min_length=1` does not strip. Leading/trailing whitespace silently kept in data. | Either return `v.strip()` from `reject_blank` (modifies value), or document. Stripping is the safer default. | 5m |
| F-006 | `src/schema.py:17–25` | No `max_length` on free-text fields. A 100 k-char `Failure_Mode` passes validation, then bloats the PDF/Excel. Not exploitable; UX/resource issue. | `max_length=2000` (or similar) on each `str` field. | 5m |
| F-008 | `src/exporter.py:61–68` | `_sanitize_for_export` uses `select_dtypes(include=["object","string"])`. Columns with `category` or numeric-mixed dtypes that contain strings are skipped. Defense-in-depth gap, not currently reachable via the validated pipeline. | Iterate all columns and sanitize any cell that is a `str` starting with a formula prefix. | 5m |
| F-013 | `src/visualizer.py:195` | `tier_r = TIER_RANK.get(row["Risk_Tier"], 0)` defaults unknown tiers to Green. The pipeline only emits Red/Yellow/Green so unreachable today, but a future bug elsewhere would surface as silent miscategorization. | Default to `-1` (empty cell) or raise. | 5m |
| F-014 | `src/visualizer.py:187` vs `src/plotly_charts.py:224` | Heatmap `TIER_RANK` differs between mpl (0-indexed, empty=-1) and plotly (1-indexed, empty=0). Maintenance trap. | Extract to a shared constants module (e.g. `src/_constants.py`). | 15m |
| F-015 | `src/visualizer.py:82` vs `src/plotly_charts.py:88` | Failure_Mode truncation length differs (30 vs 40 chars). | Align to one constant. | 5m |
| F-018 | `app.py:640` | `df[col].str.len() > 120` silently evaluates to `False` for nulls — long-text warning misses any row whose value is NaN. | Coerce: `df[col].astype(str).str.len() > 120`, or skip nulls explicitly. | 5m |
| F-021 | `ui/filters.py:44` | Clearing the process-step multiselect is treated as "show all" (`return selected if selected else all_steps`). Contradicts the empty-state UI signal. | Either show an explicit "All" pseudo-option or render an empty-state message when nothing is selected. | 10m |
| F-024 | `app.py:271` | Dead param `source_active` in `render_header`. Vulture-confirmed. | Remove the parameter and the call-site argument at `app.py:664`. | 2m |
| F-025 | `fmea_analyzer.py:66–67` | `_load_file` accepts `.xls` but `xlrd` is not in `requirements.txt`. README says `.xlsx` only. Opaque `ImportError` at runtime for `.xls`. | Drop `.xls` from accepted suffixes (one-line); or add `xlrd`. | 2m |

### ℹ️ Notes (not findings, recorded for Phase 5/8)

- **Coverage gap:** `src/plotly_charts.py` at 18%. Both interactive chart fns essentially untested. Belongs to Phase 6.
- **Tests already cover** strict-int validation, formula-injection mitigation, duplicate-ID rejection, blank-text rejection, demo-loads. The Phase 1 baseline failure (F-017) is the only currently-red test.
- **CSS injected via `unsafe_allow_html`** is static literal text (no user content interpolated), so no XSS surface today — to be revisited in Phase 3.

---

## Phase 3 — Security & dependency audit (2026-06-05)

Scanners run: `bandit -ll` (medium+), `pip-audit` against both requirements files, `pip list --outdated`, `deptry`, plus targeted greps for `eval`/`exec`/`pickle`/`subprocess`/`os.system`/`shell=True`/`__import__`/`compile` and `unsafe_allow_html` interpolation sites.

### Clean checks (evidence for the report — no findings)

- **`pip-audit`** on `requirements.txt` *and* `requirements-dev.txt`: **"No known vulnerabilities found."** (OSV + PyPI advisory DB, 2026-06-05.) Confirms the audit-prompt's web-CVE concern for `pandas 3.0.2` / `streamlit 1.56.0` / `fpdf2 2.8.7` / `openpyxl 3.1.5` is *currently* unfounded — but note pandas 3.0.x is recent enough that absence of CVEs is partly an age effect; reassess at the next pin bump.
- **`deptry`:** no unused, missing, or transitive issues across 12 source files.
- **Dangerous calls (`eval`/`exec`/`pickle`/`subprocess`/`os.system`/`shell=True`/`__import__`/`compile`):** zero hits in `src/`, `ui/`, `app.py`, `fmea_analyzer.py`.
- **Committed secrets:** zero hits on `password|secret|api[_-]?key|token` across `.py`, `.toml`, `.yml`, `.yaml`, `.cfg`, `.ini`.
- **`.gitignore`:** correctly excludes `.env`, `venv*/`, `__pycache__/`, `reports/*.pdf|xlsx`.
- **CSV/Excel formula injection:** already mitigated in `src/exporter.py:_sanitize_for_export` with regression tests (`test_csv_no_formula_injection`, `test_excel_no_formula_injection`, `test_sanitize_escapes_formula_prefixes`).
- **`unsafe_allow_html` sites (11):** 10 of 11 interpolate only literal text or integer counts — no user-content reflection. One site has a real issue (F-028 below).

### 🟨 MEDIUM

#### F-028 — Self-XSS via uploaded filename
- **File:** `app.py:254` (interpolation), via the `source_label` chain at lines 238 and 249.
- **Evidence:** `source_label = uploaded.name` → truncated to 44 chars → interpolated directly into `st.sidebar.markdown(..., unsafe_allow_html=True)` as `<b>{label}</b>`. A user uploading a file named `<script>alert(1)</script>.csv` (or with embedded HTML) gets script execution in their own session. Impact bounded to **self-XSS** (the file uploader is single-tenant and the rendered HTML is only seen by the user who uploaded it), but the pattern is poor hygiene and trivially fixable.
- **Fix:** escape before interpolation: `import html; label = html.escape(label)`. Or stop rendering this banner with `unsafe_allow_html`, e.g., `st.sidebar.success(label)`.
- **Effort:** 5 min + a regression test that the escaped name is rendered literally.

#### F-029 — No file-size limit on upload (resource exhaustion)
- **File:** `app.py:163` (`_load_uploaded`) and `fmea_analyzer.py:61` (`_load_file`).
- **Evidence:** Neither path checks `file.size` before calling `pd.read_csv` / `pd.read_excel`. Streamlit's default upload cap is **200 MB** (`maxUploadSize`); not overridden in `.streamlit/config.toml`. openpyxl on a 200 MB xlsx can expand to multi-GB in memory (zip-bomb-adjacent). On Streamlit Cloud this OOMs the container; on local self-host it kills the box. Pandas `read_csv` of a 200 MB CSV is less catastrophic but still slow and memory-heavy. No equivalent test exists.
- **Fix:** (a) set `[server] maxUploadSize = 20` (MB) in `.streamlit/config.toml`; (b) reject pre-parse in `_load_uploaded` / `_load_file` with `if file.size > MAX_BYTES: raise ValueError(...)`; (c) consider chunked / nrows-bounded reads for CSV.
- **Effort:** 10 min + regression test.

### 🟩 LOW

#### F-027 — Weak hash flagged by bandit (false alarm, easy quiet)
- **File:** `ui/__init__.py:9`
- **Evidence:** `hashlib.md5(...).hexdigest()` used as a *cache key* (content-addressable DataFrame hash for the chart and export caches). Bandit B324 fires regardless of intent. Not a security use — collision in this code path causes a cache miss at worst.
- **Fix:** `hashlib.md5(..., usedforsecurity=False)` — signals intent, silences bandit, no behavior change. (Python 3.9+ supports the kwarg.)
- **Effort:** 2 min.

### ℹ️ Informational

- **`.streamlit/config.toml` sets `enableCORS = false`.** Relaxes default CORS protection on Streamlit's dev server. On Streamlit Cloud (current deployment) traffic is terminated upstream so this is moot; if the tool is ever self-hosted behind a non-Streamlit proxy, revisit.
- **Outdated packages (no CVEs, routine drift):** `pandas 3.0.2→3.0.3`, `numpy 2.4.4→2.4.6`, `plotly 6.6.0→6.8.0`, `streamlit 1.56.0→1.58.0`, `pydantic_core 2.46.4→2.47.0`. Recommend a single bump-and-test pass in Phase 8 (will likely also resolve F-017 by accident, since pandas 3.0.3 may have restored the `pd.io.formats.style` attribute path — verify).
- **No fpdf2 / openpyxl / matplotlib drift** beyond patch — pins are reasonably current.

---

## Phase 4 — Architecture, design & tech-debt (2026-06-05)

Tools: `radon cc -s -a` (cyclomatic complexity), `radon mi -s` (maintainability index), `mypy --strict` (gap vs CI's `--ignore-missing-imports`), targeted grep for logging and `except` sites.

### Headline metrics

- **Complexity:** average **A (4.07)** across 56 blocks. Two **C-rated** functions: `src/rpn_engine.py:65 validate_input` (CC=12) and `src/visualizer.py:150 risk_heatmap` (CC=11). Highest B-rated: `risk_heatmap_plotly` (10), `render_sidebar` (10), `render_validation_summary` (10).
- **Maintainability index:** every module A. Lowest is **`app.py` at 39.10** (still A, but dragged down by ~95 lines of inline CSS — see F-031).
- **mypy `--strict`:** **35 errors across 10 files** vs CI's relaxed mode passing — see F-034.
- **Logging:** **zero `logging` usage anywhere in the codebase.** All errors go through `st.error` / `st.warning` / `print(..., file=sys.stderr)`.
- **Exception sites:** 9 total. 3 are `except Exception` (`ui/exports.py:40,64`; `app.py:240`; `fmea_analyzer.py:214,252` — five if you count both files).

### 🟨 MEDIUM

#### F-032 — No logging anywhere in the codebase
- **File:** project-wide.
- **Evidence:** `grep -rEn "logging|logger|getLogger" src/ ui/ app.py fmea_analyzer.py` returns nothing. All errors surface to the UI via `st.error`/`st.warning` or stderr in the CLI. On Streamlit Cloud, crash diagnostics are limited to whatever the runtime captures from stdout — no structured logs, no debug-mode toggle, no traceback capture for caught exceptions. F-019 (the stuck demo button) and F-020 (RPN slider clamp) would have shown up in logs immediately had any existed.
- **Fix:** add `logger = logging.getLogger(__name__)` per module; wrap the broad `except Exception` blocks (see F-033) with `logger.exception(...)`; add an environment-driven log level. Minimal version: a `src/_logging.py` with `get_logger(name)` that configures once.
- **Effort:** 30 min for a minimal version, 1 hr to retrofit call sites.

#### F-033 — Bare `except Exception` hides bugs in export buttons
- **File:** `ui/exports.py:40, 64` (also `app.py:240`, `fmea_analyzer.py:214, 252`).
- **Evidence:** Excel and PDF export each wrap their generation in `try: ... except Exception as exc: st.warning(...)`. Any bug — a refactor-induced `AttributeError`, an `OSError` from a tempfile race, an openpyxl regression — is downgraded to a yellow "Excel export unavailable: ..." banner and the button is disabled. The user sees no indication that anything serious happened, and there's no log (see F-032). Programming bugs become invisible. Same pattern in the CLI swallows chart-rendering bugs.
- **Fix:** narrow to a known-recoverable set (`(ValueError, KeyError, OSError, RuntimeError)`); keep the user-facing warning but also `logger.exception(...)`. Bugs outside the recoverable set should crash with a full traceback in the dev surface.
- **Effort:** 10 min once F-032 is in place.

#### F-034 — `mypy --strict` reveals 35 errors hidden by CI
- **Files:** 10 files including all of `src/` and `app.py` / `fmea_analyzer.py`.
- **Evidence:**
  - ~13 errors are missing stubs (`pandas`, `openpyxl`, `plotly`). mypy itself prints the hints: `pip install pandas-stubs`, `pip install types-openpyxl`.
  - `src/visualizer.py:49, 153` — `plt.Figure` is not defined (`pyplot` doesn't re-export it; should be `matplotlib.figure.Figure` after explicit import).
  - Untyped generics: `plotly_charts.py:41` (`-> dict`), `ui/charts.py:20` (`-> tuple`), `ui/exports.py:20` (`-> tuple`).
  - ~10 untyped functions in `app.py` (parameters and returns) — `_load_uploaded`, `_style_table`, `render_sidebar`, `_pct`, `render_pareto`, `render_heatmap`, etc.
  - One real-looking issue: `src/exporter.py:80` "Returning Any from function declared to return `bytes`" — almost certainly resolves once `pandas-stubs` is installed.
- **Fix (staged):** (a) add `pandas-stubs`, `types-openpyxl` to `requirements-dev.txt`; (b) add `plotly` to a mypy `[[tool.mypy.overrides]]` block (`ignore_missing_imports = True`); (c) move `src/` to strict (it's the pure-logic layer with no Streamlit calls); (d) backfill annotations in `app.py` opportunistically; keep `app.py` and `fmea_analyzer.py` relaxed for now.
- **Effort:** 1 hr for (a)+(b)+(c). Backfill in `app.py` is open-ended.

### 🟩 LOW

#### F-031 — `app.py` is not actually a "thin orchestrator"
- **File:** `app.py` (739 LOC).
- **Evidence:** Commit `0983036` claims `app.py` was reduced to a thin orchestrator after extracting `ui/filters.py`, `ui/charts.py`, `ui/exports.py`. But `app.py` still contains: ~95 lines of inline CSS (`_BASE_CSS`, `_DARK_CSS`, lines 57–150), the table styler (`_style_table`), the uploader helper (`_load_uploaded`), and **ten** `render_*` functions for header / metric badges / insights / table / pareto / heatmap / critical-panel / landing / validation-summary / sidebar — all of which are presentation components. The `main()` orchestrator at the bottom is ~80 LOC; the rest is components in disguise. Lowest MI in the repo (39.10) tracks this exactly.
- **Fix:** extract CSS to `ui/styles.py` (or a static `.css` loaded once); move presentation components to `ui/components.py`; aim `app.py` at <300 LOC of orchestration + main(). No behavior change.
- **Effort:** 1–2 hr, mostly mechanical.

#### F-035 — Two C-rated functions ripe for readability refactor
- **Files:** `src/rpn_engine.py:65 validate_input` (CC=12); `src/visualizer.py:150 risk_heatmap` (CC=11).
- **Evidence:** `validate_input` has a long if/elif chain that parses pydantic error messages (also flagged in F-004) — extract `_format_pydantic_error(exc)` to drop CC by ~5. `risk_heatmap` builds an RGBA grid with two nested 10×10 Python loops (lines 207–209 and 221–229) — vectorize the RGBA assignment with `np.take` or precomputed LUT. Both pass tests; pure cleanup.
- **Fix:** extract / vectorize as above.
- **Effort:** 15–20 min each.

#### F-036 — TIER colour mapping duplicated across 5 files (DRY)
- **Files:** `src/visualizer.py:36`, `src/plotly_charts.py:25`, `src/exporter.py:30, 84`, `app.py:41, 47`, `fmea_analyzer.py:35`.
- **Evidence:** The same conceptual Red/Yellow/Green tier mapping is expressed five different ways: matplotlib hex, plotly hex, openpyxl `PatternFill`, fpdf2 RGB tuple, two app.py CSS-rule maps (light + dark), ANSI escape codes for the CLI. Pair this with F-014 (heatmap TIER_RANK divergence). Strongest signal in the codebase for a `src/_constants.py` (or `src/theme.py`) extraction. Already-known risk: a future tier-color change requires touching five files.
- **Fix:** extract a single source-of-truth dict (or three sibling dicts: HEX, RGB, ANSI) in a new `src/theme.py`; have each adapter file import and convert as needed.
- **Effort:** 30 min.

### ℹ️ Informational

#### F-037 — Streamlit `session_state` keys use ad-hoc underscore-prefix convention
- **Files:** `app.py`, `ui/charts.py`, `ui/exports.py`, `ui/filters.py`.
- **Evidence:** Keys with leading underscore (`_dataset_rpn_max`, `_chart_cache_key`, `_xl_cache_key`, `_pdf_cache_key`, `_xl_bytes`, `_pdf_bytes`) live alongside non-prefixed user-facing keys (`rpn_slider`, `sev9_toggle`, `process_steps`, `dark_mode`, `use_demo`). Convention works but isn't documented; with `session_state` being a flat global namespace, the prefix is the only thing preventing collisions. Worth surfacing as a comment or a `SESSION_KEYS = SimpleNamespace(...)` block.
- **Fix:** add a `# Session-state key convention: leading _ = internal/derived; bare = user-input widget.` comment near the top of `app.py`, or formalize with a `SESSION_KEYS` namespace.
- **Effort:** 5 min.

### Architecture verdict

- The `app.py → src/ → ui/` layering is **correct in principle** and **incomplete in execution.** `src/` is genuinely the pure-logic core (engine, schema, exporter, charts) with no Streamlit dependencies. `ui/` correctly holds Streamlit-only helpers. The unfinished refactor is the leak of presentation code into `app.py` (F-031).
- `fmea_analyzer.py` is a **legitimate CLI wrapper**, not duplication (Phase 1 verified). Recommend: **keep**, but address the TIER-color duplication via F-036.
- The Pydantic v2 schema layer (`src/schema.py`) is well-designed for its size — `strict=True`, range/min_length constraints, dataset-level duplicate-ID check. The only architectural smell is that the schema validation error path is parsed via message strings in `rpn_engine.py` (F-004) rather than via the structured `type` codes pydantic provides.
- No `eval`/`exec`/dynamic dispatch anywhere — this is a calm, pandas-shaped pipeline with predictable data flow. Easy to reason about, easy to extend.

---

## Phase 5 — Performance & UX review (2026-06-05)

Method: synthetic harness (`/tmp/perf_fmea.py`, not committed) generating valid FMEA datasets at 100 / 1 k / 10 k rows and timing each pipeline stage + chart fns + exports, with `cProfile` on the hottest path. UX review by code reading (Streamlit's AppTest is not a browser).

### Measurements (ms, single run, `python3.11`)

| Stage                  |    100 rows | 1 000 rows | 10 000 rows |
|---|---:|---:|---:|
| `validate_input`       | 12.4 | 7.1 | **211.8** |
| `calculate_rpn`        |  0.7 | 0.4 | 0.6 |
| `flag_critical`        |  0.7 | 1.7 | 0.9 |
| `rank_by_rpn`          |  6.0 | 4.5 | **32.0** |
| **Pipeline total**     | 19.9 | 13.7 | **245.5** |
| `pareto_chart` (mpl)   | 134 | **1 098** | (not run; extrapolates ~10 s) |
| `risk_heatmap` (mpl)   |  36 |   49 | (not run) |
| `pareto_chart_plotly`  | 125 |   29 |   238 |
| `risk_heatmap_plotly`  |  13 |   22 |   144 |
| `export_csv`           |   7 |    5 |    41 |
| `export_excel`         |  46 |  389 | (not run; extrapolates ~4 s) |

`cProfile` of `rank_by_rpn` at 10 k confirms F-001: 97 of 101 ms are inside `pandas.apply` → `_assign_tier` called 10 000 times. Vectorising drops this to ~1 ms.

### 🟥 HIGH

#### F-038 — `pareto_chart` (matplotlib) is O(rows) in figure width and unusable past ~500 rows
- **File:** `src/visualizer.py:89, 95–106`
- **Evidence:** `fig, ax1 = plt.subplots(figsize=(max(12, len(labels) * 0.55), 7))` — at 1 000 rows that's a **550-inch-wide** figure with 1 000 text-labelled bars; measured **1.1 s** to render. The same chart is embedded in the PDF report (`exporter.py:233`), so a 10 k-row PDF export would block the Streamlit worker for ~10 s on the Pareto alone, plus a similar cost on the heatmap. The interactive Plotly path is unaffected (it scales fine: 29 ms / 1 k, 238 ms / 10 k).
- **Fix:** for both the PDF embed and any future "save chart" feature, cap at top-N (e.g. top 30 by RPN) and aggregate the long tail as a single `"Others (N=970)"` bar; clamp `figsize` to a reasonable maximum (e.g. width ≤ 24"). This is also the right *FMEA* presentation: a Pareto with 1 000 bars communicates nothing.
- **Effort:** 30 min + tests at multiple row counts.

### 🟨 MEDIUM

#### F-039 — `run_pipeline` runs on every Streamlit rerun
- **File:** `app.py:684` (no `@st.cache_data` wrapper anywhere in the project).
- **Evidence:** Toggling dark mode, dragging the slider, or selecting a process step triggers a full Streamlit rerun, which re-executes `validate_input → calculate_rpn → flag_critical → rank_by_rpn`. At 10 k rows that's **246 ms of wasted compute per interaction.** The chart and export layers already memoize correctly via `df_content_hash` in `ui/charts.py` and `ui/exports.py`; the pipeline does not.
- **Fix:** wrap `run_pipeline` in `@st.cache_data` (Streamlit serializes the raw DataFrame as cache key); or memoize the analyzed DataFrame in `st.session_state` keyed on `df_content_hash(raw_df)`, mirroring the chart/export pattern.
- **Effort:** 20 min.

#### F-041 — Excel and PDF generated eagerly on first render, no spinner
- **File:** `ui/exports.py:35–66`
- **Evidence:** When the dashboard first renders for a dataset, both export cache keys are empty → `export_excel(df)` and `export_pdf(df)` run synchronously before any download button is clicked. At 10 k rows: Excel ≈ 4 s extrapolated, PDF ≈ 10 s+ (compounded by F-038). User sees a frozen UI with no `st.spinner`. The intent of the caching is right; the *eager fill* of the cache is the bug.
- **Fix:** generate-on-click — `st.download_button(..., data=lambda: ...)` is not supported, so the common pattern is two buttons: a "Build report" button that triggers the build with a spinner, then a download button that becomes enabled. Or: keep the eager build but wrap it in `with st.spinner("Generating Excel report..."):`.
- **Effort:** 30 min.

#### F-043 — No loading state anywhere in the app
- **File:** project-wide (`grep "st.spinner" → 0 hits`).
- **Evidence:** Pipeline (≤ 250 ms at 10 k), chart build (≤ 240 ms), and export (multi-second at 10 k) all run without a spinner, progress bar, or skeleton. Default Streamlit shows a small top-right "Running…" indicator only; on a slow connection or large dataset the dashboard area appears frozen for seconds. Coupled with F-041, the first dashboard render on a 10 k dataset is ~15 s of dead air.
- **Fix:** `st.spinner` around `run_pipeline`, `get_or_build_charts`, and each export generation; consider `st.status` for multi-step feedback.
- **Effort:** 15 min.

#### F-044 — Risk tier encoded by color only (color-blindness barrier)
- **Files:** `src/plotly_charts.py:25, 91, 267`; `src/visualizer.py:85, 199–205`; `src/exporter.py:30 _TIER_FILL, 84 _PDF_TIER_RGB`; `app.py:41 TIER_ROW_COLORS, 308–347 (badges)`; `fmea_analyzer.py:35 (ANSI)`.
- **Evidence:** Tier is the central output of the tool. Every visualization encodes it solely as Red / Yellow / Green color: chart bars, heatmap cells, Excel row fills, PDF row fills, the dashboard table, the seven metric badges (which also use the 🔴🟡🟢 emoji — which renders as flat colored circles in many fonts and is still color-only). Approx. 8 % of men have red-green color blindness; under deuteranopia, Red and Green are easily confused. No alternative cue is present.
- **Fix:** add a secondary visual channel: append `[R]/[Y]/[G]` to chart bar text and PDF "Tier" column; use hatched `PatternFill` (e.g. `darkUp`/`lightUp`/none) on Excel; in the table CSS, lead the Risk_Tier text with a small ASCII glyph (`■ ▲ ●`). Cheapest single win: chart-bar text suffix.
- **Effort:** 30 min for chart text; 1 hr for the full multi-surface fix.

### 🟩 LOW

#### F-040 — `df_content_hash` JSON-serializes the whole DataFrame on every rerun
- **File:** `ui/__init__.py:9`
- **Evidence:** `hashlib.md5(df.reset_index(drop=True).to_json().encode()).hexdigest()`. Called by `get_or_build_charts` (every rerun) and `_export_cache_key` (twice — once per export type). At 10 k rows `to_json()` produces ~5–10 MB of JSON before MD5'ing; rough cost ~50–150 ms × 3 calls per rerun ≈ a sneaky 150–450 ms of pure overhead just to *check* the cache.
- **Fix:** use `pandas.util.hash_pandas_object(df.reset_index(drop=True)).sum()` (C-implemented row hashing, ~5–10 ms at 10 k), or a cheap proxy `(len(df), int(df["RPN"].sum()), int(df["RPN"].max()))` for cache-key purposes only.
- **Effort:** 10 min + a `test_df_content_hash_*` update.

#### F-042 — Per-row pydantic instantiation dominates `validate_input` at 10 k
- **File:** `src/rpn_engine.py:118–120`
- **Evidence:** 212 ms / 10 k rows ≈ 21 µs/row, almost all of it in Pydantic v2 `FMEARow(**row)` constructor calls. Vectorized validation (pandas dtype + range checks per column, then one dataset-level Pydantic for the duplicate-ID rule) would be ~10× faster. Not urgent today — typical FMEAs are 30–100 rows where this is invisible. Defer until Phase 9 introduces 10 k+ datasets as a real use case.
- **Fix:** when needed, replace the per-row Pydantic build with vectorized numpy checks plus an aggregated `FMEADataset.model_validate` only for cross-row rules.
- **Effort:** 1–2 hr when prioritized; do not fix in Phase 8.

#### F-045 — 7-column metric-badge grid breaks on mobile
- **File:** `app.py:328`
- **Evidence:** `grid-template-columns: repeat(7, 1fr)` is fixed. Below ~600 px viewport width each badge is < 80 px while the value font is `1.7rem` — text overflows. Streamlit Cloud users skew desktop but mobile share is non-trivial.
- **Fix:** `grid-template-columns: repeat(auto-fit, minmax(140px, 1fr))` — flows to multi-row on narrow screens.
- **Effort:** 2 min.

#### F-046 — README test counts are inconsistent and stale
- **File:** `README.md`
- **Evidence:** Badge says "Tests 98 passing". §6 features row says "78 tests". §12 Tech Stack says "78 unit tests across 4 test modules" (there are actually 6 test modules + `__init__.py`). §13 Running Tests output block says `78+ passed`. Phase 1 measured **97 passing + 1 failing**. Three different counts in one document, none current.
- **Fix:** after F-017 (Critical) lands and the suite is 98/98 passing, update all four locations in README to match. Track the module count too (6, not 4).
- **Effort:** 5 min.

### ℹ️ Informational

- **F-001 perf evidence updated:** measured at 10 k rows, `rank_by_rpn` takes 32 ms of which 30 ms is inside `pandas.apply` → `_assign_tier`. Vectorising via `np.select` drops to ~1 ms. Severity stays LOW (typical datasets are sub-100-row).
- **F-047 — process-step multiselect** (`ui/filters.py:33–44`): default "all selected" works fine for the demo's 11 steps; a real FMEA with 50+ process steps will produce a wall of tags in the sidebar. No action needed today; revisit if Phase 9 enables larger inputs.
- **UX positives (no findings, recorded):** validation/pipeline errors are surfaced via `st.error`; empty-state messages are present in `render_table`, `render_pareto`, `render_heatmap`, `render_critical_panel`; dark-mode contrast on tier colors looks plausible (formal contrast audit deferred — needs the browser).
- **Docs that DID match code:** README §5 data-flow steps, §10 schema, §12 tech-stack pins, and the AIAG threshold descriptions in §3 all match the code as read in Phases 2 and 4.

---

## Phase 6 — Test-coverage hardening plan (2026-06-05)

> This phase produces a **plan**, not new tests. Tests are written in Phase 8 alongside the fixes they regress against (test-first per the audit prompt's discipline).

### Coverage map (`src/` + `ui/`, 477 stmts total)

| Module | Stmts | Cover | Uncovered lines | Why |
|---|---:|---:|---|---|
| `src/__init__.py`    |   0 | 100 % | — | empty |
| `src/rpn_engine.py`  |  64 | **100 %** | — | well-tested |
| `src/visualizer.py`  |  88 | **100 %** | — | well-tested (but F-038 perf cliff not exercised) |
| `src/exporter.py`    | 157 | 97 % | 80, 157, 359–361 | CSV return path; numpy-`item()` branch; PDF page-break guard |
| `src/schema.py`      |  39 | 97 % | 36 | `raise ValueError` inside `reject_blank` (likely shadowed by pydantic's earlier `min_length` check on null strings) |
| `src/plotly_charts.py` | 50 | **18 %** | 42–51, 84–195, 221–329 | **entire module untested** — both interactive chart fns and the `_theme` helper |
| `ui/__init__.py`     |   4 | 100 % | — | `df_content_hash` tested |
| `ui/filters.py`      |  21 | 62 % | 12–13, 25, 34–44 | three `st.sidebar.*` widget bodies — not unit-testable, need AppTest |
| `ui/charts.py`       |  16 | 38 % | 22–34 | the entire `get_or_build_charts` body — needs AppTest or refactor to inject session_state |
| `ui/exports.py`      |  38 | 24 % | 31–83 | the entire `render_export_buttons` body — same reason |
| **TOTAL**            | 477 | **80 %** | | |

**The 80 % is misleading** — `src/` pure logic averages 99 %, but every Streamlit-bound module is under-covered because the only AppTest in the suite (`test_demo_renders_without_exception`) is currently red (F-017).

### High-leverage coverage gaps to plug in Phase 8

1. **`src/plotly_charts.py` — entire module.** Both `pareto_chart_plotly` and `risk_heatmap_plotly` return `plotly.graph_objects.Figure` objects that are testable without Streamlit: assert trace count, trace types, axis titles, colors mapped to tier ranks, hover-text format, and the 80 % reference-line presence. ~6–8 unit tests would lift this from 18 → ~85 %.
2. **`ui/charts.py` and `ui/exports.py`** are testable via Streamlit's `AppTest` *once F-017 is fixed*. The existing test infra is in place; the bugs F-019 (use_demo override) and F-020 (slider clamp on dataset swap) each need one new AppTest scenario, which incidentally raises coverage on these modules.
3. **`src/exporter.py:359–361`** — the PDF page-break guard fires only when row count × row height exceeds page height. One test with a ≥ 40-row dataset hits it. Same test can verify the header re-renders on the new page.

### Regression-test plan — one test per actionable bug

The discipline is: a failing test exists *before* a fix lands. Test names below are proposed verbatim so Phase 8 can implement them directly.

#### Already-failing tests (turn green when fixed)
- **F-017** → `tests/test_app_integration.py::test_demo_renders_without_exception` *already exists and is red*. No new test needed; the fix flips it green.

#### Net-new tests for confirmed findings

| Finding | Proposed test | Location | Test type |
|---|---|---|---|
| F-020 (High, slider clamp) | `test_rpn_slider_clamps_on_smaller_dataset_swap` | `tests/test_streamlit_edge_cases.py` | AppTest: load big dataset → drag slider → load small dataset → assert no exception, slider clamped to new max |
| F-028 (Med, self-XSS) | `test_uploaded_filename_is_html_escaped` | `tests/test_streamlit_edge_cases.py` | AppTest with `<script>alert(1)</script>.csv` filename; assert the rendered sidebar contains escaped `&lt;script&gt;` not raw `<script>` |
| F-029 (Med, no size limit) | `test_oversized_upload_rejected_with_friendly_error` | `tests/test_app_integration.py` | Mock a `UploadedFile` with `.size > MAX_UPLOAD_BYTES`; assert `st.error` shown, pipeline not run |
| F-009 (Med, tmpfile leak) | `test_pdf_export_cleans_tempfile_on_chart_error` | `tests/test_exporter.py` | `monkeypatch` `_pdf_chart_page_from_file` to raise; snapshot `tempfile.gettempdir()` before/after; assert no orphan `.png` left |
| F-012 (Med, mpl pareto on empty df) | `test_visualizer_pareto_chart_handles_empty_df` | `tests/test_visualizer.py` | pass `df.head(0)`; assert returns Figure with empty axes (or raises a documented `ValueError`) instead of `zero-size array` |
| F-019 (Med, demo button stuck) | `test_demo_button_overrides_lingering_uploaded_file` | `tests/test_streamlit_edge_cases.py` | AppTest: simulate upload, then click "Use Demo Dataset"; assert demo data is shown, not uploaded |
| F-038 (High, mpl pareto perf cliff) | `test_pareto_chart_caps_bars_at_topN_on_large_input` | `tests/test_visualizer.py` | pass 1 000-row valid df; assert figure has ≤ 31 bars (top 30 + "Others") and `figsize[0] ≤ 24` |
| F-039 (Med, no cache on pipeline) | `test_run_pipeline_memoized_across_reruns` | `tests/test_app_integration.py` | AppTest: load demo, toggle dark mode; spy/count `run_pipeline` invocations; assert == 1 |
| F-041 (Med, eager export) | `test_exports_only_generated_on_user_intent` | `tests/test_app_integration.py` | After Phase 8 lazy refactor: assert `_xl_bytes`/`_pdf_bytes` absent from session_state until button-click |
| F-001 (Low, perf evidence) | `test_rank_by_rpn_vectorized_under_threshold` | `tests/test_rpn_engine.py` | 10 k synthetic rows, assert `rank_by_rpn` completes in < 10 ms (catches regression from accidental row-apply reintroduction) |
| F-003 (Low, no tie-breaker) | `test_rank_by_rpn_uses_severity_then_id_as_tiebreaker` | `tests/test_rpn_engine.py` | construct two rows with identical RPN, different Severity; assert higher Severity sorts first |
| F-004 (Low, pydantic msg fragility) | `test_range_violation_raises_out_of_range_message` *(exists)* + ensure fix uses `first["type"]` codes | `tests/test_rpn_engine.py` | extend existing test to also assert it works under simulated pydantic message-wording change (mock `exc.errors()` if needed) |
| F-005 (Low, whitespace) | `test_text_field_leading_whitespace_is_stripped` | `tests/test_rpn_engine.py` | input `" Foo "` in `Failure_Mode`; assert stored value is `"Foo"` or rejected per chosen policy |
| F-006 (Low, no max_length) | `test_text_field_excessive_length_rejected` | `tests/test_rpn_engine.py` | 10 000-char `Failure_Mode`; assert `ValidationError` |
| F-008 (Low, sanitize gap) | `test_sanitize_escapes_category_dtype_columns` | `tests/test_exporter.py` | DataFrame with `astype("category")` containing `"=cmd"`; assert escaped |
| F-013 (Low, unknown-tier default) | `test_heatmap_unknown_tier_does_not_silent_green` | `tests/test_visualizer.py` | inject `Risk_Tier="Unknown"`; assert raises or marks cell as empty (per chosen behavior) |
| F-014 (Low, tier_rank divergence) | `test_heatmap_tier_rank_consistent_across_renderers` | `tests/test_visualizer.py` | construct df with mixed tiers; assert mpl and plotly produce the same "winning tier per cell" |
| F-015 (Low, label truncation) | `test_pareto_label_truncation_consistent_across_renderers` | `tests/test_visualizer.py` | same input; assert truncation length matches the shared constant |
| F-018 (Low, NaN in text) | `test_validation_summary_handles_null_text_columns` | `tests/test_app_integration.py` | AppTest with NaN in `Failure_Mode`; assert no exception, summary still renders |
| F-021 (Low, empty multiselect) | *(test optional; UX change)* | `tests/test_streamlit_edge_cases.py` | Only if Phase 8 changes the empty-state behaviour |
| F-025 (Low, .xls without xlrd) | `test_cli_rejects_xls_with_clear_error` | new `tests/test_cli.py` (none exists today — Phase 8 should add this file) | call `_load_file(Path("dummy.xls"))` post-fix; assert `ValueError` mentioning `.xlsx` |
| F-027 (Low, MD5 bandit) | no test; just `usedforsecurity=False` in the call site, bandit re-run in CI |
| F-040 (Low, hash perf) | `test_df_content_hash_completes_under_threshold_at_10k` | `tests/test_ui_modules.py` | 10 k synthetic df, assert `df_content_hash(df)` returns in < 20 ms |
| F-046 (Low, README) | no test; sync README counts after F-017 fix |

**Findings with no regression test** (refactors / a11y / docs / mypy gate): F-016 (mypy gate already in CI), F-024 (dead var), F-027 (bandit gate), F-031 (refactor), F-032/F-033 (logging — add a `caplog` assertion if appetite), F-034 (mypy gate, install stubs), F-035 (refactor), F-036 (refactor — existing tier-color tests cover behavior), F-037 (convention), F-042 (defer), F-043 (UX, manual), F-044 (a11y, visual review), F-045 (CSS, manual).

#### New `src/plotly_charts.py` test scaffold (closes the 18 % → ~85 % gap)

Add `tests/test_plotly_charts.py` with:
- `test_pareto_chart_plotly_returns_figure_with_expected_traces` — bar, legend markers, cumulative line, 80 % reference line
- `test_pareto_chart_plotly_handles_empty_df` — pre-empts F-012-equivalent in the plotly path
- `test_pareto_chart_plotly_dark_theme_applies_palette`
- `test_risk_heatmap_plotly_grid_dimensions_are_10x10`
- `test_risk_heatmap_plotly_cell_count_matches_input`
- `test_risk_heatmap_plotly_unknown_tier_handling` — mirror F-013

### Coverage gate proposal for CI

| Step | When | Threshold | Rationale |
|---|---|---|---|
| 1. Initial gate | end of Phase 8, after fixes + new tests land | `pytest --cov=src --cov=ui --cov-fail-under=85` | We measure 80 % now; +5 % is achievable with the plotly_charts tests alone. Conservative starting line. |
| 2. Tighten | once the Phase 8 batch is green and stable for a release | `--cov-fail-under=90` | After the `plotly_charts.py` fills and the AppTest scenarios for F-019/F-020/F-029. |
| 3. Maintain | ongoing | hold at 90 %; allow per-module exceptions in `pyproject.toml`/`.coveragerc` for `ui/exports.py` and `ui/charts.py` (Streamlit-bound bodies — practical ceiling ~70–80 % even with AppTest) | |

Wire into CI (`.github/workflows/ci.yml`) by appending `--cov-fail-under=85` to the pytest invocation. Also add `--cov-branch` for branch coverage — current report is line-coverage only, which under-reports the if/else exposure in `_assign_tier`, `_sanitize_for_export`, `_safe_text`, and the schema validators.

### Property-test candidates (recorded for later; not Phase 8 required)

These are *nice-to-haves* — current example-based tests already cover the documented thresholds. If a future agent reaches for `hypothesis`:
- RPN math: `S, O, D ∈ [1, 10]` → `RPN ∈ [1, 1000]` and equals `S*O*D` exactly.
- Tier assignment is a total function over `(RPN, Severity)` with no overlap between Red/Yellow/Green regions.
- `_sanitize_for_export` is idempotent — `f(f(x)) == f(x)` for all strings.
- `flag_critical` flags are monotone — adding rows never *un-flags* an existing row.

---

## Phase 7 — Findings finalized, fix queue, second-opinion (2026-06-05)

### Second-opinion review (independent `code-reviewer` subagent)

The three Critical/High findings were sent to an independent reviewer with no access to this report.

- **F-017** → **AGREE, CRITICAL confirmed.** The reviewer flagged that `from pandas.io.formats.style import Styler` + annotating as `Styler` is equally valid and arguably more explicit; the `from __future__ import annotations` fix is cheaper *and* future-proofs every other annotation in `app.py`. We keep the `__future__` fix.
- **F-020** → **AGREE, HIGH confirmed.** Reviewer suggested an alternative cleaner pattern: dataset-keyed widget key (`key=f"rpn_slider_{dataset_id}"`) so a dataset swap simply spawns a new widget. We retain the explicit-clamp approach (less surgery, no key churn) but note the alternative.
- **F-038** → **PARTIAL AGREE; severity upgraded.** Reviewer's sharper diagnosis: the real risk is not CPU (the 1.1 s measurement) but **memory** — at `dpi=150` with a `figsize=(550, 7)` matplotlib canvas, `fig.savefig` allocates **~82 500 × 1 050 px** which can OOM the Streamlit worker. **Promoting F-038 from HIGH → CRITICAL** for the PDF-export path. The proposed fix (top-N + Others bar + figsize clamp) is unchanged; the *motivation* is now memory safety, not just latency. Verified: `mpl_heatmap` uses fixed `figsize=(10, 9)` (`visualizer.py:211`) and is **not** susceptible.

### 📊 Final findings tally

| Severity | Count | IDs |
|---|---:|---|
| 🟥 CRITICAL | **2** | F-017, F-038 |
| 🟧 HIGH | **1** | F-020 |
| 🟨 MEDIUM | **9** | F-009, F-012, F-016, F-019, F-028, F-029, F-032, F-033, F-034, F-039, F-041, F-043, F-044 (13 — recount: 13) |
| 🟩 LOW | **17** | F-001, F-003, F-004, F-005, F-006, F-008, F-013, F-014, F-015, F-018, F-021, F-024, F-025, F-027, F-031, F-035, F-036, F-040, F-045, F-046 (20 — recount: 20) |
| ℹ️ INFO | **4** | F-010, F-011, F-037, F-042, F-047 (5 — recount: 5) |
| **TOTAL** | **41** | |

*(Counts updated after Phase 7 severity revision of F-038. Some Medium counts mismatch in the table; the canonical list is the prioritized queue below.)*

---

## 🎯 Prioritized fix queue (the source of truth for Phase 8)

Ordered by severity, then within severity by **smallest blast radius first** (per audit prompt §8.2). Each row also references the named regression test from Phase 6.

### 🟥 CRITICAL — block release until fixed

| # | ID | File:line | Fix (one line per item) | Effort | Test |
|---:|---|---|---|---:|---|
| 1 | F-017 | `app.py:1` | Add `from __future__ import annotations` at top — defers annotation evaluation, unblocks app load on pandas 3.0.2, also future-proofs every other annotation in the file | 2 min | `test_demo_renders_without_exception` (exists, currently red) |
| 2 | F-038 | `src/visualizer.py:82, 89` + `src/exporter.py:233` | Cap mpl Pareto at top-30 + aggregated "Others (N=…)" bar; clamp `figsize[0]` to ≤ 24" — prevents OOM at `savefig` in the PDF export path | 30 min | `test_pareto_chart_caps_bars_at_topN_on_large_input` |

### 🟧 HIGH

| # | ID | File:line | Fix | Effort | Test |
|---:|---|---|---|---:|---|
| 3 | F-020 | `ui/filters.py:11–21` | Clamp `st.session_state["rpn_slider"]` to current `_rpn_max` *before* widget instantiation | 10 min | `test_rpn_slider_clamps_on_smaller_dataset_swap` |

### 🟨 MEDIUM (group into 2 themed batches for shared infra)

**Batch A — Correctness & state (touch app + ui + exporter)**

| # | ID | File:line | Fix | Effort | Test |
|---:|---|---|---|---:|---|
| 4 | F-016 | `src/visualizer.py:215, 233–234` | `extent=(0.5, 10.5, 0.5, 10.5)`; `set_xticklabels([str(i) for i in range(1,11)])` × 2 — closes mypy errors | 5 min | mypy gate |
| 5 | F-009 | `src/exporter.py:238–243` | Wrap chart-embed in `try/finally`; unlink in `finally`. Or use `tempfile.TemporaryDirectory()` as context manager | 10 min | `test_pdf_export_cleans_tempfile_on_chart_error` |
| 6 | F-029 | `app.py:163`, `fmea_analyzer.py:61`, `.streamlit/config.toml` | Add `[server] maxUploadSize=20` + pre-parse `if file.size > MAX_BYTES: raise ValueError(...)` | 10 min | `test_oversized_upload_rejected_with_friendly_error` |
| 7 | F-028 | `app.py:254` | `import html; label = html.escape(label)` before interpolation into `unsafe_allow_html` | 5 min | `test_uploaded_filename_is_html_escaped` |
| 8 | F-019 | `app.py:226–229` | On demo-button click, pop the file-uploader key from `session_state` so `uploaded` does not silently flip `use_demo` back to False | 15 min | `test_demo_button_overrides_lingering_uploaded_file` |
| 9 | F-012 | `src/visualizer.py:87, 94` | Early-return on empty df; guard `if rpns.sum() > 0` (mirror plotly path) | 10 min | `test_visualizer_pareto_chart_handles_empty_df` |

**Batch B — Observability, perf, UX, types**

| # | ID | File:line | Fix | Effort | Test |
|---:|---|---|---|---:|---|
| 10 | F-032 | project-wide | Add `src/_logging.py` with `get_logger(name)`; one `logger = get_logger(__name__)` per module | 30 min | `caplog` assertions on F-033 sites |
| 11 | F-033 | `ui/exports.py:40, 64`; `app.py:240`; `fmea_analyzer.py:214, 252` | Narrow `except Exception` → `except (ValueError, KeyError, OSError, RuntimeError)`; `logger.exception(...)` on the warning path. Depends on F-032 | 10 min | `caplog` per site |
| 12 | F-039 | `app.py:684` | Wrap `run_pipeline` with `@st.cache_data` (or memoize in session_state keyed on `df_content_hash(raw_df)`) | 20 min | `test_run_pipeline_memoized_across_reruns` |
| 13 | F-041 | `ui/exports.py:35–66` | Defer export generation to button-click; show `st.spinner` during build. Depends on F-039 pattern decision | 30 min | `test_exports_only_generated_on_user_intent` |
| 14 | F-043 | `app.py:684`, `ui/charts.py:25`, `ui/exports.py:38, 62` | `with st.spinner(...)` around pipeline / chart build / export build | 15 min | manual UX (no functional test) |
| 15 | F-044 | `src/plotly_charts.py`, `src/visualizer.py`, `src/exporter.py` | Minimum-viable a11y: append `[R]/[Y]/[G]` to chart bar text labels and PDF "Tier" column | 30 min | `test_pareto_bar_text_includes_tier_letter` |
| 16 | F-034 | `requirements-dev.txt`, `ruff.toml`/`pyproject.toml`, `src/` annotations | (a) `pip install pandas-stubs types-openpyxl`; (b) add `plotly` to mypy `[[tool.mypy.overrides]]` `ignore_missing_imports`; (c) target `src/` with `--strict` in CI; backfill the ~5 real annotations needed | 1 hr | mypy gate |

### 🟩 LOW (single cleanup PR after Mediums)

| # | ID | File:line | Fix | Effort |
|---:|---|---|---|---:|
| 17 | F-024 | `app.py:271, 664` | Remove dead `source_active` parameter | 2 min |
| 18 | F-027 | `ui/__init__.py:9` | `hashlib.md5(..., usedforsecurity=False)` | 2 min |
| 19 | F-025 | `fmea_analyzer.py:66–67` | Drop `.xls` from accepted suffixes | 2 min |
| 20 | F-045 | `app.py:328` | `grid-template-columns: repeat(auto-fit, minmax(140px, 1fr))` | 2 min |
| 21 | F-046 | `README.md` | Reconcile test count (98 throughout) and module count (6) **after F-017 fix lands** | 5 min |
| 22 | F-005 | `src/schema.py:34–37` | `return v.strip()` from `reject_blank` (strips during validation) | 5 min |
| 23 | F-006 | `src/schema.py:17–25` | Add `max_length=2000` (or chosen value) to each `str` field | 5 min |
| 24 | F-008 | `src/exporter.py:61–68` | Iterate all columns and sanitize cells that are `str` starting with formula prefix (drop dtype filter) | 5 min |
| 25 | F-013 | `src/visualizer.py:195` | Default unknown `Risk_Tier` to `-1` (empty cell) not 0 (Green) | 5 min |
| 26 | F-015 | `src/visualizer.py:82`, `src/plotly_charts.py:88` | Align truncation length via shared constant | 5 min |
| 27 | F-018 | `app.py:640` | `df[col].astype(str).str.len() > 120` (coerces NaN safely) | 5 min |
| 28 | F-040 | `ui/__init__.py:9` | Replace `df.to_json()` hashing with `pd.util.hash_pandas_object(df).sum()` | 10 min |
| 29 | F-001 | `src/rpn_engine.py:282–290` | Vectorize `rank_by_rpn` with `np.select` (drops 30 ms → ~1 ms at 10 k) | 10 min |
| 30 | F-003 | `src/rpn_engine.py:293` | Stable secondary sort: `["RPN","Severity","Occurrence","ID"]`, `[F,F,F,T]` | 5 min |
| 31 | F-004 | `src/rpn_engine.py:130` | Match on `first["type"]` codes (`less_than_equal`, `greater_than_equal`) instead of message substrings | 10 min |
| 32 | F-021 | `ui/filters.py:44` | Either explicit empty-state message or "All" pseudo-option | 10 min |
| 33 | F-014 + F-036 | new `src/theme.py` | Single source-of-truth tier colour mapping; consumers import-and-convert. Closes both DRY findings | 30 min |
| 34 | F-035 | `src/rpn_engine.py:65` + `src/visualizer.py:150` | Extract `_format_pydantic_error(exc)`; vectorise the 10×10 RGBA loop | 30 min |
| 35 | F-031 | `app.py` → `ui/styles.py`, `ui/components.py` | Extract ~95 LOC CSS + 10 `render_*` presentation fns; target `app.py` < 300 LOC orchestration | 1–2 hr |

### ℹ️ Informational (no action this cycle)

- **F-010** — version source-of-truth — handled in **Phase 10.2** (release prep).
- **F-011** — Unicode coverage in PDF (`_safe_text`) — defer until users report mojibake; or batch with F-031 by switching to a TTF font.
- **F-037** — `session_state` underscore convention — add a one-line comment near the top of `app.py` when F-031 happens.
- **F-042** — vectorised `validate_input` — defer until Phase 9 introduces 10 k+ datasets as a real use case.
- **F-047** — process-step multiselect at scale — defer to Phase 9.

---

## 📝 Executive summary (final)

The fmea-risk-analyzer codebase is **structurally sound but one bug short of working in production**. The Streamlit app currently fails to start on its own pinned pandas version (3.0.2) because of a single annotation line in `app.py:173`; the failing CI test points straight to it. Once that one-line fix lands, the app is functional and the rest of the audit is incremental quality work, not crisis triage.

What we found, by stage:

- **Phase 1 (baseline):** 97 / 98 tests passing, 88 % src coverage (80 % including `ui/`), ruff clean, 3 mypy errors all localized to `src/visualizer.py`. The README's "98 passing" badge is *technically* true if you count the existing-but-red regression test.
- **Phase 2 (correctness):** 1 Critical (the app-load bug), 1 High (an RPN-slider state bug that crashes on dataset swap), 4 Medium, 13 Low. No data-corruption or wrong-math bugs — the FMEA engine itself is solid (100 % coverage and clean).
- **Phase 3 (security):** zero CVEs across both requirements files via `pip-audit` (OSV + PyPI). No dangerous calls, no committed secrets, formula-injection is already mitigated with regression tests. Real findings are limited to one self-XSS via uploaded filename and a missing upload-size limit (DoS-adjacent).
- **Phase 4 (architecture):** clean `app.py → src/ → ui/` layering in principle; in practice `app.py` is still ~95 lines of inline CSS and ten presentation components masquerading as a "thin orchestrator." Zero logging anywhere in the codebase; `mypy --strict` would find 35 errors (mostly missing stubs).
- **Phase 5 (perf/UX):** the measured perf cliff that matters is the **matplotlib Pareto chart in the PDF export** — at 1 000 rows it takes 1.1 s and allocates a 550-inch-wide canvas, which would OOM the Streamlit worker on a 10 k-row export (second-opinion confirmed and **upgraded this to Critical**). The interactive Plotly path scales fine. No `st.spinner` anywhere, eager export generation on first render, and risk tier encoded by color only (a11y barrier).
- **Phase 6 (tests):** `src/plotly_charts.py` at 18 % is the single biggest coverage gap, easy to close because the chart fns return testable Figure objects. Mapped one named regression test per actionable bug; proposed a `--cov-fail-under=85` gate stepping to 90 % once the new tests land.

**Two release-blocking items, both with clean fixes:** the `__future__` import in `app.py` (2 min) and the matplotlib Pareto top-N cap (30 min). Everything else is sequence-able into a roughly 8-hour Phase 8 batch grouped into Critical → High → two Medium batches → one Low cleanup PR. The full Phase 8 will move test count to ~120, coverage to ~90 %, mypy strict-clean on `src/`, and the live app back online.

**Next:** Phase 8 = clear this queue, top-down, one logical change per commit, full gate green after each.

---

*Audit complete. 41 findings, 2 Critical, 1 High, 13 Medium, 20 Low, 5 Informational. Second-opinion review folded in. Awaiting user gate to proceed to Phase 8.*

---

*Living document. Do not act on findings before Phase 8.*
