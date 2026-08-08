"""Pytest path setup for the MSA app.

Since #231 this insert is **inert**, and the honest thing is to say so rather than invent a
job for it.

``msa_app`` is an installed (editable) package, so it needs no help. Neither does ``app``,
the top-level Streamlit module that is deliberately outside the wheel: the editable install
is a plain-path ``.pth`` pointing at this very directory, which puts ``apps/msa`` on
``sys.path`` for every ``.venv`` process — so ``app`` already resolves without this file.
Coverage attribution is unaffected for the same reason; ``--cov=msa_app.*`` measures this
tree either way.

Verified, not assumed: with this file removed, the MSA gate still passes at 100% line +
branch with byte-identical coverage paths, standalone (``pytest`` from ``apps/msa``) and
under the unified root run alike. No MSA test imports ``app`` by any route.

It stays only to match ``apps/spc/conftest.py``, which carries the identical seam from #204.
Delete both together or neither — and if you do, delete them for being no-ops, not because
this docstring found a use for them.
"""

from __future__ import annotations

import sys
from pathlib import Path

_APP_DIR = str(Path(__file__).parent)
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)
