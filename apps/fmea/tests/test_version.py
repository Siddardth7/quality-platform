"""Guard the FMEA version single-source-of-truth against drift (W03-5)."""

import tomllib
from pathlib import Path

from fmea_app import __version__
from fmea_app.exporter import _TOOL_VERSION


def test_version_ssot_matches_pyproject():
    """fmea_app.__version__ must equal the version in pyproject.toml."""
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    assert __version__ == data["project"]["version"]


def test_exporter_reads_version_from_ssot():
    """The exporter must stamp the SSOT version, not a hardcoded string."""
    assert _TOOL_VERSION == __version__


def test_exporter_has_no_hardcoded_version_literal():
    """The legacy hardcoded '1.0.0' string must be gone from the exporter."""
    src = (Path(__file__).resolve().parents[1] / "fmea_app" / "exporter.py").read_text(
        encoding="utf-8"
    )
    assert '"1.0.0"' not in src
