from __future__ import annotations
import pandas as pd


def subgroup_rows(frame: pd.DataFrame) -> list[list[float]]:
    return frame.groupby("subgroup", sort=True)["value"].apply(list).tolist()
