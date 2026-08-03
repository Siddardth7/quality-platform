"""Prove secom_app and msa_app import outside pytest, with no sys.path help (#204,
retargeted by #205 PR 3, extended by #231).

``secom_app.capability`` and ``secom_app.charts`` now take their engine math from
``quality_core.spc``; no ``spc_app`` import survives anywhere in this app (#205). Before
#204, the engine import only worked under pytest because ``apps/secom/conftest.py``
path-hacked the engine onto ``sys.path`` — which is why this test exists at all. That
conftest survived only to path-hack ``apps/msa``; #231 made ``msa-app`` installable and
deleted it, so ``apps/secom`` now has **no ``conftest.py`` at all**.

These tests run a clean, non-pytest interpreter to prove the imports resolve via the
installed (editable) ``quality-core`` / ``secom-app`` / ``msa-app`` workspace packages,
not the hack.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_SECOM_APP_DIR = Path(__file__).resolve().parents[1]


def test_secom_app_imports_without_conftest() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import secom_app.charts, secom_app.capability; print('IMPORT OK')",
        ],
        cwd=_SECOM_APP_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"clean-interpreter import failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )


def test_secom_app_has_no_spc_app_import() -> None:
    """The audit A12 (#205) acceptance criterion, asserted as an executable fact.

    A fresh interpreter is what makes the ``sys.modules`` check honest: in a
    full-workspace pytest run the SPC app's own tests have already imported
    ``spc_app``, so an in-process assertion would be order-dependent.

    Every ``secom_app`` submodule is walked, not a hand-listed pair, so a cross-app
    import re-introduced into *any* module fails this test — the docstring's claim
    and the assertion cover the same ground.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import importlib, pkgutil, sys; import secom_app; "
            "[importlib.import_module(m.name) for m in "
            "pkgutil.walk_packages(secom_app.__path__, secom_app.__name__ + '.')]; "
            "leaked = [m for m in sys.modules "
            "if m == 'spc_app' or m.startswith('spc_app.')]; "
            "assert not leaked, leaked; print('NO SPC_APP')",
        ],
        cwd=_SECOM_APP_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"secom_app still pulls in spc_app:\nstdout={result.stdout}\nstderr={result.stderr}"
    )


def test_secom_app_is_an_installed_distribution() -> None:
    """secom-app must be installed (editable), not just importable via cwd (#204, OQ2).

    Runs from the workspace root (not ``apps/secom``) so ``secom_app`` can only
    resolve through the editable install, never through a cwd sys.path[0] hack.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import importlib.util; assert importlib.util.find_spec('secom_app'); "
            "print('IMPORT OK')",
        ],
        cwd=_SECOM_APP_DIR.parent.parent,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"secom_app is not an installed distribution:\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )


def test_msa_app_is_an_installed_distribution() -> None:
    """msa-app must be installed (editable), not reachable via a conftest sys.path hack (#231).

    tests/test_msa.py imports ``msa_app.gage_rr_engine`` (#68); until #231 that only
    worked because ``apps/secom/conftest.py`` inserted ``apps/msa`` onto ``sys.path`` —
    a hack invisible to every gate. Runs from the workspace root so ``msa_app`` cannot
    resolve through cwd, and imports ``msa_app.pages`` so a wheel that silently drops
    the subpackage fails here.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import importlib.util; import msa_app.gage_rr_engine, msa_app.pages; "
            "assert importlib.util.find_spec('msa_app'); print('IMPORT OK')",
        ],
        cwd=_SECOM_APP_DIR.parent.parent,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"msa_app is not an installed distribution:\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
