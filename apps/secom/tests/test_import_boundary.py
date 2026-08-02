"""Prove secom_app imports outside pytest, with no conftest.py sys.path help (#204).

``secom_app.capability`` imports ``spc_app.spc_engine.capability`` — the sole remaining
``spc_app`` consumer in this app, since #205 PR 2 moved ``charts.py``'s SPC math to
``quality_core.spc``. Before #204, that import only worked under pytest because
``apps/secom/conftest.py`` path-hacked ``spc_app`` onto ``sys.path``.

This test runs a clean, non-pytest interpreter (which never loads ``conftest.py``) to
prove the import resolves via the installed (editable) ``spc-app`` / ``secom-app``
workspace packages, not the hack.

**For #205 PR 3:** when ``capability.py`` is promoted, the last ``spc_app`` import goes
with it — but do NOT delete this test. Retarget it at ``quality_core``: the property it
proves (``secom_app`` imports outside pytest, with no ``sys.path`` help) is what #204
bought, and is independent of *which* package supplies the engine.
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
