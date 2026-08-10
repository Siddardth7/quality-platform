"""The aggregator exception to "apps never import each other", asserted as fact (#262).

Root ``CLAUDE.md`` says imports go downward only and apps never import each other.
``mcp_app`` is the ONE intentional exception (SME sign-off, #262): its whole job is
exposing the domain-app engines as MCP tools, so it imports ``fmea_app`` deliberately.
Peer apps (FMEA/SPC/MSA/SECOM) are unaffected — they still never import each other, which
``apps/secom/tests/test_import_boundary.py`` enforces on its own side.

The exception has a limit, and that limit is what these tests pin down:

1. the dependency must resolve as an installed (editable) workspace distribution, not
   through a ``sys.path``/cwd accident — so ``uvx --from . quality-mcp`` works; and
2. no Streamlit chain may leak in. ``fmea-app`` depends on Streamlit for its UI, so
   importing an FMEA *engine* module could quietly drag a UI runtime into a stdio server
   process. The engine modules must stay UI-free, in the spirit of the audit A11 core
   dependency contract.

Each check runs a clean, non-pytest interpreter: in a full-workspace pytest run other
apps' tests have already imported Streamlit, so an in-process ``sys.modules`` assertion
would be order-dependent and vacuous.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]


def _run(code: str) -> subprocess.CompletedProcess[str]:
    """Run one snippet in a clean interpreter from the workspace root.

    The workspace root (not ``apps/mcp``) is the cwd on purpose: ``mcp_app`` then cannot
    resolve through ``sys.path[0]``, only through the editable install.
    """
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=_WORKSPACE_ROOT,
        capture_output=True,
        text=True,
    )


def test_mcp_app_dependencies_are_installed_distributions() -> None:
    """mcp_app, fmea_app, msa_app and quality_core resolve as installed distributions."""
    result = _run(
        "import importlib.util; import mcp_app.server; "
        "assert all(importlib.util.find_spec(m) for m in "
        "('mcp_app', 'fmea_app', 'msa_app', 'quality_core')); print('IMPORT OK')"
    )
    assert result.returncode == 0, (
        f"mcp_app cannot resolve its engine dependencies:\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )


def test_mcp_app_actually_imports_the_fmea_engine() -> None:
    """The documented exception is real, not aspirational: fmea_app is in sys.modules.

    Asserted positively so that if the FMEA tools were ever quietly rewritten to
    reimplement RPN/AP locally, this file's premise would fail rather than silently rot.
    """
    result = _run(
        "import sys, mcp_app.server; "
        "assert 'fmea_app.rpn_engine' in sys.modules, sorted(sys.modules); "
        "assert 'quality_core.scoring' in sys.modules, sorted(sys.modules); "
        "print('ENGINES IMPORTED')"
    )
    assert result.returncode == 0, (
        f"mcp_app no longer imports the FMEA engine:\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )


def test_mcp_app_actually_imports_the_msa_engine() -> None:
    """The MSA Gage R&R tool wraps the real engine: msa_app.gage_rr_engine is loaded.

    Sibling to the FMEA check (not a rename): if msa_gage_rr were ever rewritten to
    reimplement the AIAG math locally, this file's aggregator premise would fail loudly.
    """
    result = _run(
        "import sys, mcp_app.server; "
        "assert 'msa_app.gage_rr_engine' in sys.modules, sorted(sys.modules); "
        "print('MSA ENGINE IMPORTED')"
    )
    assert result.returncode == 0, (
        f"mcp_app no longer imports the MSA engine:\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )


def test_mcp_app_pulls_in_no_streamlit_chain() -> None:
    """Importing the server must not drag Streamlit into a stdio server process.

    Every ``mcp_app`` submodule is walked rather than a hand-listed pair, so a UI import
    re-introduced into *any* module fails here.
    """
    result = _run(
        "import importlib, pkgutil, sys; import mcp_app; "
        "[importlib.import_module(m.name) for m in "
        "pkgutil.walk_packages(mcp_app.__path__, mcp_app.__name__ + '.')]; "
        "leaked = [m for m in sys.modules "
        "if m == 'streamlit' or m.startswith('streamlit.')]; "
        "assert not leaked, leaked; print('NO STREAMLIT')"
    )
    assert result.returncode == 0, (
        f"mcp_app pulls in a Streamlit chain:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
