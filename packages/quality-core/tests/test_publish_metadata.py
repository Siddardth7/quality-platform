"""
tests/test_publish_metadata.py
Publish-facing metadata for all eight distributions (#292, M6-1).

Two facts have to hold before anything is uploaded to a package index, and neither is
observable from any single app's test suite — which is why they live here, next to
test_packaging.py, the other test that reads distribution metadata rather than source:

1. **Distribution names are the `quality-*` namespace, import names are unchanged.**
   `uvx quality-mcp` (no `--from`) resolves the *distribution* named `quality-mcp` and
   runs the console script also named `quality-mcp` inside it; before #292 the
   distribution was `mcp-app`, so the command could not work. The import packages
   (`mcp_app`, `fmea_app`, …) deliberately did NOT change — every `import` in the repo
   is untouched, and this test pins both halves of that.

2. **Internal dependencies are pinned exactly to the workspace version.** The workspace
   ships as one version across all eight distributions (CLAUDE.md "## Version"), so a
   published `quality-mcp` must require `quality-core==<that version>`, never a bare
   name that would resolve against any published core. Before #292 the dependency
   strings were bare, so hatchling stamped a bare `Requires-Dist`.

Like test_packaging.py, these read the *installed* distribution metadata, so a
`pyproject.toml` edit is only visible after `uv sync` (or another re-install of the
editable package). A stale pass right after editing `pyproject.toml` means the
environment was not re-synced.

# ponytail: installed dist-info, not a freshly built wheel. hatchling stamps
# `Requires-Dist` from the same `[project] dependencies` strings for both, so building
# eight wheels in a test would shell out to `uv build` seven extra times per CI run
# (this directory is re-run by six per-surface coverage gates) to observe the same
# metadata. If a build-time rewriting step is ever added, switch this to `uv build` +
# zipfile/`email.message_from_string` on the wheel's METADATA.
"""

from __future__ import annotations

import importlib.util
import re
import tomllib
from importlib.metadata import entry_points, metadata, requires
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]

# Distribution name -> import package name. The keys are what PyPI serves and what
# `uvx`/`pip install` take; the values are what `import` takes. #292 renamed only the
# keys.
_DISTRIBUTIONS: dict[str, str] = {
    "quality-core": "quality_core",
    "quality-fmea": "fmea_app",
    "quality-spc": "spc_app",
    "quality-msa": "msa_app",
    "quality-controlplan": "controlplan_app",
    "quality-secom": "secom_app",
    "quality-database": "quality_database_app",
    "quality-mcp": "mcp_app",
}

# PEP 508 requirement strings ("quality-core==0.15.0", "streamlit>=1.56.0 ; extra == …").
# Split on the first version/marker/extras delimiter to get the bare name — same cheap,
# dependency-free approach test_packaging.py uses.
_NAME_DELIMITERS = re.compile(r"[<>=!~;[ ]")


def _workspace_version() -> str:
    """The one version every distribution is released at (root pyproject is the SSOT)."""
    data = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version: str = data["project"]["version"]
    return version


@pytest.mark.parametrize(("dist_name", "import_name"), sorted(_DISTRIBUTIONS.items()))
def test_distribution_is_installed_under_its_quality_name(
    dist_name: str, import_name: str
) -> None:
    """Each distribution is published as `quality-*` and still imports as before (#292).

    Raises PackageNotFoundError under the pre-#292 names (`mcp-app`, `fmea-app`, …) —
    that is exactly the regression this guards.
    """
    assert metadata(dist_name)["Name"] == dist_name
    assert importlib.util.find_spec(import_name) is not None, (
        f"{dist_name} no longer provides the import package {import_name}"
    )


def test_quality_mcp_console_script_is_the_uvx_entry_point() -> None:
    """`uvx quality-mcp` needs the script AND the distribution to be named `quality-mcp`.

    The two names are independent namespaces, so this is not a duplicate: it is the
    coincidence that lets `uvx quality-mcp` work without `--from` (#292).
    """
    scripts = entry_points(group="console_scripts", name="quality-mcp")
    assert [ep.value for ep in scripts] == ["mcp_app.server:main"]
    assert metadata("quality-mcp")["Name"] == "quality-mcp"


@pytest.mark.parametrize("dist_name", sorted(_DISTRIBUTIONS))
def test_internal_dependencies_are_pinned_to_the_workspace_version(dist_name: str) -> None:
    """Every internal dep ships as `==<workspace version>`, never bare or ranged (#292).

    A bare `Requires-Dist: quality-core` lets a published wheel resolve against any
    core, which the one-version-per-workspace release model does not support.
    """
    expected = f"=={_workspace_version()}"
    for requirement in requires(dist_name) or []:
        name = _NAME_DELIMITERS.split(requirement.strip(), maxsplit=1)[0]
        if name in _DISTRIBUTIONS:
            assert requirement.strip() == f"{name}{expected}", (
                f"{dist_name} declares an unpinned internal dependency: {requirement!r}"
            )
