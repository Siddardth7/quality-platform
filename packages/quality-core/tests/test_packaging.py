"""
tests/test_packaging.py
Tests for quality-core's *packaging metadata* — the dependency contract itself (#202).

The shared core is imported by every app and by the API, so its hard dependency set is
part of its public contract: a UI framework in it ships Streamlit's whole transitive
chain (gitpython, tornado, protobuf, pyarrow, pydeck, …) to every consumer. Nothing in
the test suite imports streamlit *through* ``quality_core``, so removing the dependency
passes vacuously — these tests assert the metadata directly instead.

These read the *installed* distribution metadata, so a `pyproject.toml` edit is only
visible after `uv sync` (or another re-install of the editable package). A stale pass
right after editing `pyproject.toml` means the environment was not re-synced.
"""

from __future__ import annotations

import re
from importlib.metadata import requires

# `requires()` returns PEP 508 strings: "pandas>=3.0.2", "streamlit>=1.56.0 ; extra == 'streamlit'".
# Split on the first version/marker/extras delimiter to get the bare distribution name —
# cheaper and dependency-free compared with pulling in a PEP 508 parser.
_NAME_DELIMITERS = re.compile(r"[<>=!~;[ ]")


def _bare_name(requirement: str) -> str:
    return _NAME_DELIMITERS.split(requirement.strip(), maxsplit=1)[0]


def _hard_requirements() -> set[str]:
    """Distribution names quality-core requires with no extra (i.e. on a base install)."""
    return {
        _bare_name(req)
        for req in requires("quality-core") or []
        if "extra ==" not in req
    }


def test_core_hard_dependencies_are_only_the_data_path() -> None:
    """A base quality-core install pulls the data path and nothing else.

    Exact equality, not membership: this must fail both when a UI dependency creeps
    back in *and* when `defusedxml` is dropped as "unused" (it is never imported by
    our code — see test_validate.test_xlsx_ingest_has_xml_bomb_hardening_enabled).

    `numpy` is hard because `quality_core.spc.control_charts` imports it at module
    level (#205 PR 2); it was already resolved transitively via pandas, so declaring
    it is honesty about a real import, not a new install.

    `scipy` is hard because `quality_core.spc.capability` imports it at module level
    (#205 PR 3); it was already in the workspace lock via `spc-app`/`secom-app`, so
    declaring it is likewise honesty about a real import, not a new install.
    """
    assert _hard_requirements() == {
        "pandas",
        "pydantic",
        "openpyxl",
        "defusedxml",
        "numpy",
        "scipy",
    }


def test_streamlit_is_optional_not_required() -> None:
    """Streamlit is still available, but only via the `streamlit` extra (#202, Option A).

    `quality_core.theme.style` still exists and still imports streamlit; it is reachable
    through the lazy `__getattr__` shim in `quality_core.theme`, which is what keeps a
    base install able to import the pure-data tokens.
    """
    declared = requires("quality-core") or []
    assert any(_bare_name(req) == "streamlit" for req in declared)
    assert "streamlit" not in _hard_requirements()
