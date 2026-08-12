"""
tests/test_api_surface.py
Parity between each published module's ``__all__`` and the manifest in ``API.md`` (#261).

``API.md`` carries one ``<!-- STABLE SYMBOLS: <module> -->`` block per module. The block is
the machine-checkable copy of that module's ``__all__``; this test asserts set equality in
both directions, so drift fails whichever way it happens — a symbol added to ``__all__``
without a doc update, or a doc entry for a symbol that no longer exists.

A typo'd ``__all__`` entry fails earlier still: importing the module and reading
``__all__`` is enough for the name to be reported, and the parity assertion then shows it
as documented-but-absent.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

API_MD = Path(__file__).resolve().parents[1] / "API.md"

MODULES = [
    "msa_app.gage_rr_engine",
]


# ponytail: this parser is duplicated verbatim in each package's tests/test_api_surface.py.
# A shared helper module cannot be imported across packages under --import-mode=importlib
# (the `tests` basename collides); consolidate if a real test-support package ever exists.
def parse_manifest(text: str, module: str) -> set[str]:
    """Return the symbol set declared in ``module``'s STABLE SYMBOLS block.

    Formatting-tolerant: leading/trailing whitespace, blank lines, and ``- ``/``* ``
    list markers are ignored. A missing block is an error, never a skip — the
    ``API.md`` files are checked into this repo, so their absence is always a failure.
    """
    match = re.search(
        rf"<!-- STABLE SYMBOLS: {re.escape(module)} -->(.*?)<!-- END STABLE SYMBOLS -->",
        text,
        re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"{API_MD} has no STABLE SYMBOLS block for {module!r}.")
    symbols = set()
    for line in match.group(1).splitlines():
        name = line.strip().removeprefix("- ").removeprefix("* ").strip()
        if name:
            symbols.add(name)
    return symbols


@pytest.mark.parametrize("module", MODULES)
def test_all_matches_api_md(module: str) -> None:
    """``module.__all__`` and its API.md manifest declare exactly the same symbols."""
    declared = set(importlib.import_module(module).__all__)
    documented = parse_manifest(API_MD.read_text(encoding="utf-8"), module)
    assert declared == documented, (
        f"{module}: in __all__ but missing from API.md: {sorted(declared - documented)}; "
        f"in API.md but missing from __all__: {sorted(documented - declared)}"
    )


def test_parser_self_check() -> None:
    """The parser itself: tolerant on formatting, loud on a missing block.

    Runs against a fixture string, never the real ``API.md``, so exercising the failure
    branch cannot depend on (or corrupt) the checked-in docs.
    """
    fixture = (
        "<!-- STABLE SYMBOLS: demo.module -->\n"
        "alpha\n"
        "\n"
        "  - beta\n"
        "* gamma\n"
        "<!-- END STABLE SYMBOLS -->\n"
    )
    assert parse_manifest(fixture, "demo.module") == {"alpha", "beta", "gamma"}
    with pytest.raises(AssertionError, match="no STABLE SYMBOLS block"):
        parse_manifest(fixture, "demo.absent")
