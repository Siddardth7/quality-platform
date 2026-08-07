"""Script to verify README.md test count claims against collected pytest test cases."""

import pathlib
import re
import subprocess
import sys


def parse_readme_counts(content: str) -> tuple[int, int]:
    """Extract test counts from README badge and comment.

    Returns:
        tuple[int, int]: (badge_count, comment_count)

    Raises:
        ValueError: If badge or comment count cannot be parsed.
    """
    badge_match = re.search(r"https://img\.shields\.io/badge/tests-(\d+)%20passing", content)
    if not badge_match:
        raise ValueError("Could not parse test count badge from README.md")

    comment_match = re.search(r"#\s*(\d+)\s+tests\s+\+\s+coverage", content)
    if not comment_match:
        raise ValueError("Could not parse test count comment from README.md")

    badge_count = int(badge_match.group(1))
    comment_count = int(comment_match.group(1))
    return badge_count, comment_count


def get_collected_test_count() -> int:
    """Run pytest --collect-only to get total collected test case count.

    Returns:
        int: Collected test count.

    Raises:
        RuntimeError: If pytest collection fails or output cannot be parsed.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"pytest --collect-only failed with exit code {result.returncode}:\n{result.stderr or result.stdout}"
        )

    output = result.stdout
    match = re.search(r"(\d+)\s+tests?\s+collected", output)
    if not match:
        raise RuntimeError(f"Could not parse collected test count from pytest output:\n{output}")

    return int(match.group(1))


def check_readme_drift(readme_path: pathlib.Path | None = None) -> tuple[bool, str]:
    """Compare README test count claims against collected pytest count.

    Args:
        readme_path: Optional path to README file. Defaults to README.md in working dir.

    Returns:
        tuple[bool, str]: (is_matching, status_message)
    """
    if readme_path is None:
        readme_path = pathlib.Path("README.md")

    content = readme_path.read_text(encoding="utf-8")
    badge_count, comment_count = parse_readme_counts(content)
    collected_count = get_collected_test_count()

    if badge_count == collected_count and comment_count == collected_count:
        return True, f"README test counts match collected pytest total ({collected_count} tests)."

    msg = (
        f"README test count drift detected!\n"
        f"  Collected count: {collected_count}\n"
        f"  README badge count (line 14): {badge_count}\n"
        f"  README comment count (line 215): {comment_count}"
    )
    return False, msg


def main() -> int:
    """Main entrypoint for README test count drift check script."""
    try:
        success, msg = check_readme_drift()
        if success:
            print(msg)
            return 0
        print(msg, file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error checking README test count drift: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
