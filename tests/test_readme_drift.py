"""Tests for scripts/check_readme_test_count.py (Issue #210).

Verifies README count parsing, pytest collection count parsing, drift detection,
and script execution.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
from unittest.mock import MagicMock

_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from scripts.check_readme_test_count import (  # noqa: E402
    check_readme_drift,
    get_collected_test_count,
    main,
    parse_readme_counts,
)

SAMPLE_README_MATCHING = """
[![Tests](https://img.shields.io/badge/tests-1641%20passing-2ea043)](#-the-quality-gate)

```bash
uv run pytest --cov     # 1641 tests + coverage across core + apps
```
"""

SAMPLE_README_BADGE_MISMATCH = """
[![Tests](https://img.shields.io/badge/tests-999%20passing-2ea043)](#-the-quality-gate)

```bash
uv run pytest --cov     # 1641 tests + coverage across core + apps
```
"""

SAMPLE_README_COMMENT_MISMATCH = """
[![Tests](https://img.shields.io/badge/tests-1641%20passing-2ea043)](#-the-quality-gate)

```bash
uv run pytest --cov     # 999 tests + coverage across core + apps
```
"""


def test_parse_readme_counts() -> None:
    """Assert regex correctly extracts badge count (line 14) and comment count (line 215)."""
    # 1. Valid sample parsing
    badge, comment = parse_readme_counts(SAMPLE_README_MATCHING)
    assert badge == 1641
    assert comment == 1641

    # 2. Actual README.md parsing. Assert the two claims agree with each other rather
    #    than pinning a literal: a hardcoded count here goes stale on every PR that adds
    #    a test — the exact drift this module exists to catch. The absolute number is
    #    already enforced against pytest by the CI step itself.
    readme_path = pathlib.Path("README.md")
    assert readme_path.exists()
    actual_badge, actual_comment = parse_readme_counts(readme_path.read_text(encoding="utf-8"))
    assert actual_badge > 0
    assert actual_badge == actual_comment

    # 3. Missing badge raises ValueError
    with pytest.raises(ValueError, match="Could not parse test count badge from README.md"):
        parse_readme_counts("uv run pytest --cov     # 1641 tests + coverage")

    # 4. Missing comment raises ValueError
    with pytest.raises(ValueError, match="Could not parse test count comment from README.md"):
        parse_readme_counts("[![Tests](https://img.shields.io/badge/tests-1641%20passing-2ea043)]")


def test_collect_test_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert pytest collection parser accurately extracts total collected test count."""
    # 1. Standard output parsing
    mock_run = MagicMock()
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="1641 tests collected in 0.45s\n", stderr=""
    )
    monkeypatch.setattr(subprocess, "run", mock_run)
    assert get_collected_test_count() == 1641

    # 2. Singular test count parsing
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="1 test collected in 0.01s\n", stderr=""
    )
    assert get_collected_test_count() == 1

    # 3. Subprocess failure raises RuntimeError
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="pytest error"
    )
    with pytest.raises(RuntimeError, match="pytest --collect-only failed with exit code 1"):
        get_collected_test_count()

    # 4. Unparseable output raises RuntimeError
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="no tests\n", stderr=""
    )
    with pytest.raises(RuntimeError, match="Could not parse collected test count"):
        get_collected_test_count()


def test_readme_test_count_script_success() -> None:
    """Run scripts/check_readme_test_count.py directly against repository and assert exit code 0."""
    result = subprocess.run(
        [sys.executable, "scripts/check_readme_test_count.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Script failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    # No literal count: the exit code already proves README and pytest agree, and
    # pinning today's number here would break on every PR that adds a test.
    assert "README test counts match collected pytest total" in result.stdout


def test_readme_test_count_script_failure_negative_control(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run check_readme_drift with mutated README text (badge or comment altered to 999)."""
    # 1. Badge mismatch
    readme_badge = tmp_path / "README_badge.md"
    readme_badge.write_text(SAMPLE_README_BADGE_MISMATCH, encoding="utf-8")
    monkeypatch.setattr("scripts.check_readme_test_count.get_collected_test_count", lambda: 1641)

    matching, msg = check_readme_drift(readme_badge)
    assert matching is False
    assert "README test count drift detected!" in msg
    assert "Collected count: 1641" in msg
    assert "README badge count (line 14): 999" in msg
    assert "README comment count (line 215): 1641" in msg

    # 2. Comment mismatch
    readme_comment = tmp_path / "README_comment.md"
    readme_comment.write_text(SAMPLE_README_COMMENT_MISMATCH, encoding="utf-8")
    matching, msg = check_readme_drift(readme_comment)
    assert matching is False
    assert "README test count drift detected!" in msg
    assert "Collected count: 1641" in msg
    assert "README badge count (line 14): 1641" in msg
    assert "README comment count (line 215): 999" in msg

    # 3. Entrypoint main() return codes
    monkeypatch.setattr(
        "scripts.check_readme_test_count.check_readme_drift",
        lambda: (True, "OK"),
    )
    assert main() == 0

    monkeypatch.setattr(
        "scripts.check_readme_test_count.check_readme_drift",
        lambda: (False, "Drift!"),
    )
    assert main() == 1

    def _raise_exc() -> tuple[bool, str]:
        raise ValueError("Bad README format")

    monkeypatch.setattr("scripts.check_readme_test_count.check_readme_drift", _raise_exc)
    assert main() == 1


def test_check_readme_drift_default_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify check_readme_drift defaults to README.md in working directory."""
    # Derive the count from the real README instead of pinning it. This test is about
    # the default-path behaviour, not about today's total, and a literal would go stale
    # on every PR that adds a test.
    expected, _comment = parse_readme_counts(
        pathlib.Path("README.md").read_text(encoding="utf-8")
    )
    monkeypatch.setattr(
        "scripts.check_readme_test_count.get_collected_test_count",
        lambda: expected,
    )
    matching, msg = check_readme_drift(None)
    assert matching is True
    assert f"README test counts match collected pytest total ({expected} tests)." in msg
