"""Guard against reintroducing the phantom "AIAG FMEA 5th Edition" (#197).

There is no AIAG FMEA 5th Edition. The 2019 document is the **AIAG & VDA FMEA Handbook,
1st Edition** — a joint AIAG/VDA publication that restarted the edition count. The phantom
edition had spread to `ASSUMPTIONS_LOG.md` and to four live code files, two of which print
it onto exported Excel and PDF reports: in an IATF 16949 core-tools context, a report citing
a nonexistent standard edition is itself an audit finding.

Prose regresses silently — no assertion fails when a docstring or a caption drifts back.
This is that assertion. It is a plain grep, deliberately: a citation defect needs a check a
reviewer can verify at a glance, not a framework.

The check is textual, so the corrected prose must not spell the phantom token either, even
to disown it. `ASSUMPTIONS_LOG.md` therefore says "a fifth edition of the AIAG FMEA manual"
where it records what was wrong. That is a real constraint on the wording, and it is the
price of a guard with no exception list to rot.

Scope is the *live* surfaces. Dated planning records under `docs/plans/` and
`docs/superpowers/plans/` still contain the old text and are deliberately excluded: they are
historical artifacts of past work, and editing them would be rewriting history rather than
fixing documentation.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_APP_ROOT = Path(__file__).resolve().parents[1]

# The stable token, matching "5th Ed", "5th Ed.", "5th Edition" in any case.
PHANTOM_EDITION = re.compile(r"5th\s+(?:ed\.?|edition)", re.IGNORECASE)

GUARDED_FILES = [
    "docs/ASSUMPTIONS_LOG.md",
    "app.py",
    "fmea_analyzer.py",
    "fmea_app/rpn_engine.py",
    "fmea_app/exporter.py",
]


@pytest.mark.parametrize("relative_path", GUARDED_FILES)
def test_no_phantom_aiag_fmea_5th_edition(relative_path: str) -> None:
    """No live FMEA doc or app-code file may cite an "AIAG FMEA 5th Edition" (#197)."""
    path = _APP_ROOT / relative_path
    assert path.exists(), f"guarded file {relative_path} no longer exists — fix this list"

    hits = [
        f"  {relative_path}:{number}: {line.strip()[:120]}"
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if PHANTOM_EDITION.search(line)
    ]
    assert not hits, (
        "phantom edition citation reintroduced — there is no AIAG FMEA 5th Edition; the "
        "2019 document is the AIAG & VDA FMEA Handbook, 1st Edition (#197):\n"
        + "\n".join(hits)
    )
