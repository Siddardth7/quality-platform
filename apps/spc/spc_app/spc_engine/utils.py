"""Shared SPC frame helpers.

``subgroup_rows`` now lives in ``quality_core.spc.utils`` (audit A12, #205); this
module re-exports it so existing ``from spc_app.spc_engine.utils import ...``
callers keep working unchanged.
"""

from __future__ import annotations

from quality_core.spc.utils import subgroup_rows

__all__ = ["subgroup_rows"]
