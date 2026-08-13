"""Tests for scripts/skill_lint.py (Issue #270, M2-1).

Covers the frontmatter parser, per-skill linting, the whole-tree walk, and the
main() entry point — plus a boundary test on the 1024-char description ceiling
and the prose-mention-vs-formula-assignment distinction. Mirrors the structure
of tests/test_readme_drift.py (root tests/, sys.path insert, script import).
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest  # noqa: E402

from scripts.skill_lint import (  # noqa: E402
    find_skill_dirs,
    lint_all,
    lint_skill,
    main,
    parse_frontmatter,
)

VALID_FRONTMATTER = """---
name: example-skill
description: Does a thing and says when to use it.
---

# Body
"""


def _write_skill(
    skill_dir: pathlib.Path,
    *,
    text: str,
    script: str | None = None,
    script_name: str = "call.py",
) -> pathlib.Path:
    """Create skill_dir/SKILL.md (and optionally scripts/<script_name>) and return the dir."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
    if script is not None:
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        (scripts_dir / script_name).write_text(script, encoding="utf-8")
    return skill_dir


# --------------------------------------------------------------------------- #
# parse_frontmatter                                                           #
# --------------------------------------------------------------------------- #


def test_parse_frontmatter_valid() -> None:
    """A well-formed block parses to a stripped key: value dict."""
    fm = parse_frontmatter(VALID_FRONTMATTER)
    assert fm["name"] == "example-skill"
    assert fm["description"] == "Does a thing and says when to use it."


def test_parse_frontmatter_no_leading_fence() -> None:
    """Text that does not open with '---' is rejected, not silently accepted."""
    with pytest.raises(ValueError, match="no frontmatter block"):
        parse_frontmatter("name: x\ndescription: y\n")


def test_parse_frontmatter_no_closing_fence() -> None:
    """An unterminated block raises rather than reading the whole file as frontmatter."""
    with pytest.raises(ValueError, match="unterminated frontmatter block"):
        parse_frontmatter("---\nname: example-skill\ndescription: y\n")


def test_parse_frontmatter_line_without_colon() -> None:
    """A line inside the block that is not 'key: value' raises, naming the offending line."""
    with pytest.raises(ValueError, match="malformed frontmatter line"):
        parse_frontmatter("---\nname: example-skill\nthis is not a pair\n---\n")


# --------------------------------------------------------------------------- #
# find_skill_dirs                                                             #
# --------------------------------------------------------------------------- #


def test_find_skill_dirs_missing_root(tmp_path: pathlib.Path) -> None:
    """A missing skills/ root returns [] — nothing to lint, no crash."""
    assert find_skill_dirs(tmp_path / "does-not-exist") == []


def test_find_skill_dirs_ignores_folder_without_skill_md(tmp_path: pathlib.Path) -> None:
    """A subdir with no SKILL.md is not treated as a skill; one with a SKILL.md is."""
    (tmp_path / "stray").mkdir()
    _write_skill(tmp_path / "real-skill", text=VALID_FRONTMATTER)
    found = find_skill_dirs(tmp_path)
    assert [p.name for p in found] == ["real-skill"]


# --------------------------------------------------------------------------- #
# lint_skill                                                                  #
# --------------------------------------------------------------------------- #


def test_lint_skill_valid(tmp_path: pathlib.Path) -> None:
    """A conforming skill folder produces no violations."""
    skill = _write_skill(tmp_path / "example-skill", text=VALID_FRONTMATTER)
    assert lint_skill(skill) == []


def test_lint_skill_missing_skill_md(tmp_path: pathlib.Path) -> None:
    """A folder with no SKILL.md fails with a message naming the folder."""
    (tmp_path / "example-skill").mkdir()
    violations = lint_skill(tmp_path / "example-skill")
    assert any("no SKILL.md" in v for v in violations)


def test_lint_skill_missing_name(tmp_path: pathlib.Path) -> None:
    """Frontmatter without a 'name' key fails."""
    text = "---\ndescription: has a description but no name\n---\n"
    skill = _write_skill(tmp_path / "example-skill", text=text)
    violations = lint_skill(skill)
    assert any("missing a 'name'" in v for v in violations)


def test_lint_skill_missing_description(tmp_path: pathlib.Path) -> None:
    """Frontmatter without a 'description' key fails."""
    text = "---\nname: example-skill\n---\n"
    skill = _write_skill(tmp_path / "example-skill", text=text)
    violations = lint_skill(skill)
    assert any("missing a non-empty 'description'" in v for v in violations)


def test_lint_skill_name_folder_mismatch(tmp_path: pathlib.Path) -> None:
    """A 'name' that differs from the folder name is a hard fail (the skill will not load)."""
    text = "---\nname: other-name\ndescription: valid.\n---\n"
    skill = _write_skill(tmp_path / "example-skill", text=text)
    violations = lint_skill(skill)
    assert any("does not match folder" in v and "will not load" in v for v in violations)


def test_lint_skill_description_exactly_1024_passes(tmp_path: pathlib.Path) -> None:
    """A description of exactly 1024 chars is at the ceiling and passes."""
    description = "a" * 1024
    text = f"---\nname: example-skill\ndescription: {description}\n---\n"
    skill = _write_skill(tmp_path / "example-skill", text=text)
    assert lint_skill(skill) == []


def test_lint_skill_description_1025_fails(tmp_path: pathlib.Path) -> None:
    """One char over the ceiling (1025) fails — off-by-one boundary."""
    description = "a" * 1025
    text = f"---\nname: example-skill\ndescription: {description}\n---\n"
    skill = _write_skill(tmp_path / "example-skill", text=text)
    violations = lint_skill(skill)
    assert any("1025 chars, over the 1024-char limit" in v for v in violations)


def test_lint_skill_formula_assignment_fails(tmp_path: pathlib.Path) -> None:
    """A formula-assignment line in the body is smuggled math — hard fail."""
    text = (
        "---\nname: example-skill\ndescription: valid.\n---\n\n"
        "RPN = severity * occurrence * detection\n"
    )
    skill = _write_skill(tmp_path / "example-skill", text=text)
    violations = lint_skill(skill)
    assert any("formula in SKILL.md body" in v for v in violations)


def test_lint_skill_msa_formula_assignment_fails(tmp_path: pathlib.Path) -> None:
    """The denylist covers MSA's metric tokens too (#273), including the `%GRR =` form."""
    text = (
        "---\nname: example-skill\ndescription: valid.\n---\n\n"
        "%GRR = sqrt(EV**2 + AV**2)\n"
    )
    skill = _write_skill(tmp_path / "example-skill", text=text)
    violations = lint_skill(skill)
    assert any("formula in SKILL.md body" in v for v in violations)


def test_lint_skill_prose_mention_passes(tmp_path: pathlib.Path) -> None:
    """A bare prose mention of a metric name must NOT false-positive."""
    text = (
        "---\nname: example-skill\ndescription: valid.\n---\n\n"
        "The skill reports the RPN and Action Priority returned by the tool.\n"
    )
    skill = _write_skill(tmp_path / "example-skill", text=text)
    assert lint_skill(skill) == []


def test_lint_skill_script_imports_engine_fails(tmp_path: pathlib.Path) -> None:
    """A scripts/*.py that imports a denylisted engine package fails, naming the package."""
    script = "from quality_core.scoring import rpn\n\nprint(rpn)\n"
    skill = _write_skill(tmp_path / "example-skill", text=VALID_FRONTMATTER, script=script)
    violations = lint_skill(skill)
    assert any("imports 'quality_core'" in v for v in violations)


def test_lint_skill_script_import_mcp_app_fails(tmp_path: pathlib.Path) -> None:
    """The denylist covers the aggregator package mcp_app too, not just quality_core."""
    script = "import mcp_app.server\n"
    skill = _write_skill(tmp_path / "example-skill", text=VALID_FRONTMATTER, script=script)
    violations = lint_skill(skill)
    assert any("imports 'mcp_app'" in v for v in violations)


def test_lint_skill_script_imports_allowed_package_passes(tmp_path: pathlib.Path) -> None:
    """A script importing fastmcp (the sanctioned client) is clean — denylist is not a blocklist-all."""
    script = "import fastmcp\n\nprint(fastmcp)\n"
    skill = _write_skill(tmp_path / "example-skill", text=VALID_FRONTMATTER, script=script)
    assert lint_skill(skill) == []


def test_lint_skill_malformed_frontmatter_names_file(tmp_path: pathlib.Path) -> None:
    """Malformed frontmatter fails with the SKILL.md path in the message, not a stack trace."""
    text = "---\nname: example-skill\nthis line has no colon\n---\n"
    skill = _write_skill(tmp_path / "example-skill", text=text)
    violations = lint_skill(skill)
    assert any("SKILL.md" in v and "malformed frontmatter line" in v for v in violations)


# --------------------------------------------------------------------------- #
# lint_all                                                                    #
# --------------------------------------------------------------------------- #


def test_lint_all_missing_root_is_clean(tmp_path: pathlib.Path) -> None:
    """A missing skills/ root is a clean pass with a '0 skill(s)' message, no crash."""
    clean, messages = lint_all(tmp_path / "nope")
    assert clean is True
    assert any("0 skill(s) clean" in m for m in messages)


def test_lint_all_reports_violations(tmp_path: pathlib.Path) -> None:
    """A tree with a broken skill returns (False, violations)."""
    _write_skill(tmp_path / "example-skill", text="---\ndescription: no name\n---\n")
    clean, messages = lint_all(tmp_path)
    assert clean is False
    assert messages  # non-empty violation list


def test_lint_all_real_example_skill_clean() -> None:
    """The real skills/example-skill/ folder lints clean end to end."""
    clean, messages = lint_all(_ROOT / "skills")
    assert clean is True, f"real skills/ tree is not clean: {messages}"


# --------------------------------------------------------------------------- #
# main                                                                        #
# --------------------------------------------------------------------------- #


def test_main_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() returns 0 when lint_all reports clean."""
    monkeypatch.setattr("scripts.skill_lint.lint_all", lambda: (True, ["ok"]))
    assert main() == 0


def test_main_violation(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() returns 1 when lint_all reports a violation."""
    monkeypatch.setattr("scripts.skill_lint.lint_all", lambda: (False, ["bad"]))
    assert main() == 1


def test_main_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() swallows an unexpected exception into exit code 1, never a traceback."""

    def _boom() -> tuple[bool, list[str]]:
        raise RuntimeError("kaboom")

    monkeypatch.setattr("scripts.skill_lint.lint_all", _boom)
    assert main() == 1


def test_skill_lint_script_success() -> None:
    """Running scripts/skill_lint.py directly against the repo exits 0."""
    result = subprocess.run(
        [sys.executable, "scripts/skill_lint.py"],
        capture_output=True,
        text=True,
        cwd=_ROOT,
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert "skill(s) clean" in result.stdout
