"""skill-lint: validate every Agent Skill under `skills/` against the house conventions (#270).

Checks, per skill folder (`skills/<name>/`):

- `SKILL.md` exists.
- Its frontmatter parses as a flat `key: value` block between two `---` fences.
- `name` is present, lowercase-hyphen (`^[a-z0-9]+(-[a-z0-9]+)*$`), <=64 chars, and equals
  the folder name — a mismatch makes the skill fail to *load* in a host, so lint catches it first.
- `description` is present, non-empty, <=1024 chars, and contains no `<`/`>` (prompt-injection
  footgun; frontmatter is loaded verbatim at discovery).
- No math in the SKILL.md body: no `RPN =`-style formula assignment (the denylisted symbols are
  `RPN`, `AP`, `Cp`, `Cpk`, `Pp`, `Ppk`, `GRR`, `EV`, `AV`, `PV`, `ndc`), and no ```python block
  carrying `import numpy|pandas|scipy` or `def compute`. Engine decides, skill orchestrates.
- No `scripts/*.py` under the skill imports an engine package directly (`quality_core`,
  `fmea_app`, `spc_app`, `msa_app`, `controlplan_app`, `secom_app`, `mcp_app`) — a skill talks
  to the MCP tool surface, never to the engines.

Run locally: `uv run python scripts/skill_lint.py`. Exits 1 on any violation. Wired into the
CI `gate` job as its own step, mirroring `scripts/check_readme_test_count.py` — a plain script,
not a pytest test. See `skills/CONVENTIONS.md` for the prose version of these rules.

Stdlib only, deliberately: SKILL.md frontmatter is flat `key: value`, and the only PyYAML in
this workspace is a transitive dependency of `fastmcp`. Importing it here would be a hidden,
un-pinned coupling to another package's dependency tree.
"""

from __future__ import annotations

import pathlib
import re
import sys

MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024

NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Keyed on an `=` assignment, not a bare mention: a skill may legitimately say "reports the
# RPN and Action Priority" — it may not say "RPN = severity * occurrence * detection". The MSA
# tokens (GRR/EV/AV/PV/ndc) were added with the msa skill (#273); the leading `\b` keeps
# `%GRR =` caught (the boundary sits between `%` and `G`), and the match is case-sensitive, so
# a skill may still write `ndc` prose but not `ndc = 1.41 * PV / GRR`.
FORMULA_PATTERN = re.compile(r"\b(RPN|AP|Cpk|Cp|Ppk|Pp|GRR|EV|AV|PV|ndc)\s*=")

CODE_SMELLS = ("import numpy", "import pandas", "import scipy", "def compute")

ENGINE_PACKAGES = (
    "quality_core",
    "fmea_app",
    "spc_app",
    "msa_app",
    "controlplan_app",
    "secom_app",
    "mcp_app",
)

# ponytail: source-text scan, not an `ast` walk — same regex approach as
# check_readme_test_count.py. It sees `import x` / `from x import y` at any indent and misses
# `importlib.import_module("quality_core")`. Documented limitation in CONVENTIONS.md; upgrade
# to `ast.parse` only if a skill is ever caught smuggling an engine in dynamically.
ENGINE_IMPORT_PATTERN = re.compile(
    r"^\s*(?:from|import)\s+(" + "|".join(ENGINE_PACKAGES) + r")\b",
    re.MULTILINE,
)


def find_skill_dirs(skills_root: pathlib.Path) -> list[pathlib.Path]:
    """Every immediate subdirectory of skills_root that contains a SKILL.md.

    A missing skills_root returns [] — "nothing to lint" is a pass, so the CI step can land
    before any real skill exists. A subdirectory without a SKILL.md is not a skill.
    """
    if not skills_root.is_dir():
        return []
    return sorted(
        path for path in skills_root.iterdir() if path.is_dir() and (path / "SKILL.md").is_file()
    )


def parse_frontmatter(skill_md_text: str) -> dict[str, str]:
    """Parse the flat `key: value` frontmatter block between the two `---` fences.

    Returns:
        dict[str, str]: the frontmatter keys, values stripped.

    Raises:
        ValueError: if there is no frontmatter block, no closing fence, or a line inside the
            block is not `key: value`.
    """
    lines = skill_md_text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("no frontmatter block: the file must start with a '---' line")

    closing = next((i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)
    if closing is None:
        raise ValueError("unterminated frontmatter block: no closing '---' line")

    frontmatter: dict[str, str] = {}
    for line in lines[1:closing]:
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        if not separator or not key.strip():
            raise ValueError(f"malformed frontmatter line (expected 'key: value'): {line!r}")
        frontmatter[key.strip()] = value.strip()
    return frontmatter


def _body(skill_md_text: str) -> str:
    """The SKILL.md text with its frontmatter block removed (whole text if it has none)."""
    lines = skill_md_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return skill_md_text
    closing = next((i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)
    if closing is None:
        return skill_md_text
    return "\n".join(lines[closing + 1 :])


def _check_math(skill_md_path: pathlib.Path, body: str) -> list[str]:
    """Violations for formula assignments and compute-flavoured python blocks in the body."""
    violations: list[str] = []
    in_python_block = False
    in_fence = False
    for number, line in enumerate(body.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            in_python_block = in_fence and stripped[3:].strip().lower() == "python"
            continue
        if FORMULA_PATTERN.search(line):
            violations.append(
                f"{skill_md_path}:{number}: formula in SKILL.md body — the engine computes this, "
                f"the skill calls an MCP tool for it: {stripped!r}"
            )
        if in_python_block and any(smell in line for smell in CODE_SMELLS):
            violations.append(
                f"{skill_md_path}:{number}: compute code in a SKILL.md python block — "
                f"skills orchestrate, engines compute: {stripped!r}"
            )
    return violations


def lint_skill(skill_dir: pathlib.Path) -> list[str]:
    """Run every check against one skill folder; returns violation strings (empty = clean)."""
    violations: list[str] = []
    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.is_file():
        return [f"{skill_dir}: no SKILL.md — every skill folder needs one"]

    text = skill_md_path.read_text(encoding="utf-8")
    try:
        frontmatter = parse_frontmatter(text)
    except ValueError as exc:
        violations.append(f"{skill_md_path}: {exc}")
        frontmatter = {}

    name = frontmatter.get("name", "")
    if not name:
        violations.append(f"{skill_md_path}: frontmatter is missing a 'name'")
    else:
        if not NAME_PATTERN.match(name):
            violations.append(
                f"{skill_md_path}: name {name!r} must be lowercase letters/digits separated by "
                f"single hyphens"
            )
        if len(name) > MAX_NAME_LENGTH:
            violations.append(
                f"{skill_md_path}: name is {len(name)} chars, over the {MAX_NAME_LENGTH}-char limit"
            )
        if name != skill_dir.name:
            violations.append(
                f"{skill_md_path}: name {name!r} does not match folder {skill_dir.name!r} — "
                f"the skill will not load"
            )

    description = frontmatter.get("description", "")
    if not description:
        violations.append(f"{skill_md_path}: frontmatter is missing a non-empty 'description'")
    else:
        if len(description) > MAX_DESCRIPTION_LENGTH:
            violations.append(
                f"{skill_md_path}: description is {len(description)} chars, over the "
                f"{MAX_DESCRIPTION_LENGTH}-char limit"
            )
        if "<" in description or ">" in description:
            violations.append(
                f"{skill_md_path}: description must not contain '<' or '>' "
                f"(prompt-injection footgun)"
            )

    violations.extend(_check_math(skill_md_path, _body(text)))

    for script in sorted((skill_dir / "scripts").glob("*.py")):
        match = ENGINE_IMPORT_PATTERN.search(script.read_text(encoding="utf-8"))
        if match:
            violations.append(
                f"{script}: imports {match.group(1)!r} — a skill calls MCP tools, never an "
                f"engine package directly"
            )

    return violations


def lint_all(skills_root: pathlib.Path | None = None) -> tuple[bool, list[str]]:
    """Lint every skill under skills_root (default: `skills`). Returns (all_clean, messages)."""
    if skills_root is None:
        skills_root = pathlib.Path("skills")

    skill_dirs = find_skill_dirs(skills_root)
    violations = [violation for skill_dir in skill_dirs for violation in lint_skill(skill_dir)]
    if violations:
        return False, violations
    return True, [f"skill-lint: {len(skill_dirs)} skill(s) clean under {skills_root}."]


def main() -> int:
    """Entry point: print messages, return 0 if all_clean else 1."""
    try:
        all_clean, messages = lint_all()
        for message in messages:
            print(message, file=sys.stdout if all_clean else sys.stderr)
        return 0 if all_clean else 1
    except Exception as exc:
        print(f"Error running skill-lint: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
