"""Load-bearing checks on the M6-3 registry manifests (#294).

These are static files consumed only by external tooling (mcp-publisher, Smithery,
Glama). Nothing else in CI catches a syntax error or an identity/version mismatch, and
`mcp-publisher publish` fails silently-until-attempted on a marker/name divergence — so
this module pins the invariants that would otherwise only surface at submission time.
No fixtures, no per-field schema validation (that is mcp-publisher's job).
"""

import json
import re
import tomllib
from pathlib import Path

import yaml

_MCP = Path(__file__).resolve().parents[1]
_ROOT = _MCP.parents[1]

_SERVER_JSON = json.loads((_MCP / "server.json").read_text(encoding="utf-8"))
_GLAMA_JSON = json.loads((_ROOT / "glama.json").read_text(encoding="utf-8"))
_SMITHERY = yaml.safe_load((_MCP / "smithery.yaml").read_text(encoding="utf-8"))
_PYPROJECT = tomllib.loads((_MCP / "pyproject.toml").read_text(encoding="utf-8"))["project"]
_README = (_MCP / "README.md").read_text(encoding="utf-8")


def test_manifests_are_parseable():
    # json.loads / yaml.safe_load above would already raise; assert the shapes are objects.
    assert isinstance(_SERVER_JSON, dict)
    assert isinstance(_GLAMA_JSON, dict)
    assert isinstance(_SMITHERY, dict)


def test_server_name_matches_readme_ownership_marker():
    # The exact string mcp-publisher greps in the PyPI long_description to prove ownership.
    marker = re.search(r"<!--\s*mcp-name:\s*(\S+)\s*-->", _README)
    assert marker is not None, "README is missing the <!-- mcp-name: ... --> marker"
    assert marker.group(1) == _SERVER_JSON["name"]


def test_server_package_matches_pyproject():
    pkg = _SERVER_JSON["packages"][0]
    assert pkg["identifier"] == _PYPROJECT["name"]  # quality-mcp
    assert pkg["version"] == _PYPROJECT["version"]  # 0.15.0
    assert _SERVER_JSON["version"] == _PYPROJECT["version"]
    assert _SERVER_JSON["description"] == _PYPROJECT["description"]


def test_smithery_command_matches_documented_invocation():
    sc = _SMITHERY["startCommand"]
    assert sc["type"] == "stdio"
    # commandFunction is a JS arrow fn string; pull command + args out of the single-quoted
    # tokens and reconstruct the invocation the README documents (README.md line 67).
    tokens = re.findall(r"'([^']*)'", sc["commandFunction"])
    assert " ".join(tokens) == "uv run python -m mcp_app.server"
