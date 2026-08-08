"""Shared SPC frame helpers.

Promoted verbatim out of `spc_app.spc_engine.utils` (audit A12, #205);
`spc_app.spc_engine.utils` re-exports it.
"""

from __future__ import annotations

import pandas as pd


def subgroup_rows(frame: pd.DataFrame) -> list[list[float]]:
    return frame.groupby("subgroup", sort=True)["value"].apply(list).tolist()
