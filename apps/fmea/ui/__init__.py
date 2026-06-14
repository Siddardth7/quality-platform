"""ui — FMEA Risk Analyzer UI module package."""
import pandas as pd


def df_content_hash(df: pd.DataFrame) -> str:
    """Return a stable hash of the DataFrame contents for cache keying."""
    row_hash = pd.util.hash_pandas_object(df.reset_index(drop=True), index=True).sum()
    return format(row_hash & 0xFFFFFFFFFFFFFFFF, "016x")
