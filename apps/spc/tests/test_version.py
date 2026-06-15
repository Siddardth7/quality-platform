"""Guard the SPC version single-source-of-truth against drift."""

import tomllib
from pathlib import Path

from spc_app import __version__


def test_version_ssot_matches_pyproject():
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    assert __version__ == data["project"]["version"]
