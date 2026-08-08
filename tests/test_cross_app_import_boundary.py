"""Repo-wide cross-app import guard (#233).

Imports go downward only: apps import ``quality_core``, apps never import each other.
``apps/secom/tests/test_import_boundary.py`` has asserted that for SECOM -> SPC since
#204/#205; this generalises the same mechanism to every app pair.

Two parts:

1. **Production walk** — one fresh, non-pytest interpreter per app that imports the app's
   package, walks every submodule, and then inspects ``sys.modules`` for any of the other
   four app packages. The subprocess is what makes the ``sys.modules`` check honest: in a
   full-workspace pytest run the other apps' own suites have already imported their
   packages, so an in-process assertion would be import-order-dependent.
2. **Test scan** — an ``ast`` walk over every ``apps/*/tests/**/*.py`` looking for imports
   of another app. Anything not in ``_ALLOWED_TEST_ONLY_CROSS_APP_IMPORTS`` fails, so a
   third test-only cross-app import is a conscious edit to that constant rather than a
   silent gap (OQ-1, SME decision).
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Module name -> the directory the guard subprocess runs in, relative to _REPO_ROOT.
# The cwd must be the app's *own* directory: `fmea-app` and `controlplan-app` set
# `package = false`, so they are never built as wheels and resolve only through the
# implicit `sys.path[0] = cwd` that `python -c` inserts. A shared repo-root cwd would
# fail them with ModuleNotFoundError before the guard logic ran.
_APPS: dict[str, Path] = {
    "fmea_app": Path("apps/fmea"),
    "spc_app": Path("apps/spc"),
    "msa_app": Path("apps/msa"),
    "controlplan_app": Path("apps/controlplan"),
    "secom_app": Path("apps/secom"),
}

# Deliberate test-only cross-app imports (#231, W07-4/#90). The production walk never
# sees these — it only inspects each app's *_app package, never its tests/ directory —
# but the test scan below does, and fails on any pair not listed here.
_ALLOWED_TEST_ONLY_CROSS_APP_IMPORTS: set[tuple[str, str]] = {
    ("apps/secom/tests/test_msa.py", "msa_app"),
    ("apps/spc/tests/test_loop_integration.py", "controlplan_app"),
    ("apps/spc/tests/test_loop_integration.py", "fmea_app"),
}

# Call forms that import by string name and so are invisible to an ast.Import walk.
_STRING_IMPORT_CALLS = frozenset({"importorskip", "import_module"})


@pytest.mark.parametrize("app_module", sorted(_APPS))
def test_no_cross_app_import_in_production_code(app_module: str) -> None:
    """No app's production package may pull in another app's package.

    Every submodule is walked rather than a hand-listed set, so a cross-app import
    re-introduced into *any* module fails. ``walk_packages`` deliberately gets no
    ``onerror`` handler: a genuinely broken import must surface as a raw traceback,
    distinguishable from the ``AssertionError: [...]`` a real leak produces.
    """
    others = sorted(name for name in _APPS if name != app_module)
    leak_predicate = " or ".join(f"m == {o!r} or m.startswith({o!r} + '.')" for o in others)
    script = (
        f"import importlib, pkgutil, sys; import {app_module}; "
        f"walked = [importlib.import_module(m.name) for m in "
        f"pkgutil.walk_packages({app_module}.__path__, {app_module}.__name__ + '.')]; "
        f"assert walked, 'walked no submodules of {app_module}'; "
        f"leaked = sorted(m for m in sys.modules if {leak_predicate}); "
        f"assert not leaked, leaked; "
        f"print('NO CROSS-APP IMPORT', len(walked))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=_REPO_ROOT / _APPS[app_module],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"{app_module} pulls in another app (or failed to walk):\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )


def _referenced_modules(tree: ast.Module) -> set[str]:
    """Top-level package names this module imports, by any of the three forms.

    ``ast`` rather than a regex: hand-written grep patterns have under-matched in this
    repo before (#235), and a walk is immune to line wrapping, parenthesised import
    lists and aliases. ``pytest.importorskip("fmea_app")`` is an ``ast.Call``, not an
    import node, so it is matched separately — missing it would make this scan pass for
    the wrong reason on two of the three known allowlist entries.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module is not None:
                names.add(node.module)
        elif isinstance(node, ast.Call) and node.args:
            func = node.func
            called = func.attr if isinstance(func, ast.Attribute) else None
            if called is None and isinstance(func, ast.Name):
                called = func.id
            first = node.args[0]
            if (
                called in _STRING_IMPORT_CALLS
                and isinstance(first, ast.Constant)
                and isinstance(first.value, str)
            ):
                names.add(first.value)
    return {name.split(".")[0] for name in names}


def _scan_test_cross_app_imports() -> set[tuple[str, str]]:
    """Every ``(repo-relative posix path, other app package)`` pair under apps/*/tests/."""
    found: set[tuple[str, str]] = set()
    for app_module, app_dir in _APPS.items():
        for path in sorted((_REPO_ROOT / app_dir / "tests").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            relpath = path.relative_to(_REPO_ROOT).as_posix()
            for name in _referenced_modules(tree):
                if name in _APPS and name != app_module:
                    found.add((relpath, name))
    return found


def test_no_unlisted_cross_app_import_in_tests() -> None:
    """Test-only cross-app imports must be named individually, not glob-exempted.

    Stale entries are deliberately not a failure: an allowlist entry whose import has
    been removed permits something that no longer exists, and failing on it would
    punish cleanup. Only *unlisted* imports fail.
    """
    unlisted = sorted(_scan_test_cross_app_imports() - _ALLOWED_TEST_ONLY_CROSS_APP_IMPORTS)
    assert not unlisted, (
        f"Unlisted test-only cross-app import(s): {unlisted}. If deliberate, add each pair "
        f"to _ALLOWED_TEST_ONLY_CROSS_APP_IMPORTS in {__file__} — that edit is the "
        f"conscious act."
    )
