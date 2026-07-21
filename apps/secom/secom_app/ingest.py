"""
secom_app/ingest.py
SECOM semiconductor manufacturing dataset — honest, NaN-preserving ingest.

SECOM's defining trait is heavy, honest missingness across ~590 sensor columns
(UCI ML Repository, dataset 179). The platform's shared validated-ingest boundary
(`quality_core.io.load_table`) is the WRONG tool here: it validates one Pydantic
row model per row and normalises NaN -> None, so a required `float` field with
`allow_inf_nan=False` *rejects* any row with a missing cell. That is correct for
a tidy CSV upload (Gage R&R, Control Plan, SPC) but would silently discard most
of SECOM's rows. This module reuses only `quality_core.io.IngestError` — the
friendly, user-safe failure type — and validates *structure*, not cell presence:
a missing sensor reading is data, not an error. NaN is never imputed or dropped;
downstream missingness/selection screening happens in `selection.py`.

Failure modes that DO raise `IngestError` (structural, not cell-level):
  - the two raw files disagree on row count
  - a label value falls outside the SECOM domain {-1, +1}
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from quality_core.io import IngestError

__all__ = [
    "SecomDataset",
    "load_secom",
    "secom_missingness",
    "IngestError",
    "PASS",
    "FAIL",
    "SECOM_DATA_PATH",
    "SECOM_LABELS_PATH",
]

# Vendored defaults, resolved relative to this file (mirrors the other apps' data/).
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SECOM_DATA_PATH = DATA_DIR / "secom.data"
SECOM_LABELS_PATH = DATA_DIR / "secom_labels.data"

#: SECOM label encoding (UCI): -1 = pass, +1 = fail.
PASS, FAIL = -1, 1

#: Fixed timestamp format used by `secom_labels.data` (UCI, verified).
_TIMESTAMP_FORMAT = "%d/%m/%Y %H:%M:%S"


@dataclass(frozen=True)
class SecomDataset:
    """A loaded, row-aligned SECOM study.

    ``features`` preserves every NaN exactly as read — no imputation, no row or
    column drop. ``labels`` and ``timestamps`` share the same index as ``features``.
    """

    features: pd.DataFrame  # n_rows x n_sensors float; NaN preserved
    labels: pd.Series  # int, values in {PASS, FAIL}, index-aligned to features
    timestamps: pd.Series  # datetime64, index-aligned; NaT if a stamp is unparseable


def load_secom(
    data_path: str | Path = SECOM_DATA_PATH,
    labels_path: str | Path = SECOM_LABELS_PATH,
) -> SecomDataset:
    """Read the vendored SECOM raw files into an aligned, NaN-preserving dataset.

    Both files are space-separated with no header. Feature columns are named
    deterministically (``sensor_000``, ``sensor_001``, ...) from the column count
    actually found in ``data_path`` — the count is never hardcoded (UCI's own
    metadata and raw file disagree, 591 vs 590). Raises :class:`IngestError`
    (a ``ValueError`` subclass, user-safe) if the two files' row counts disagree
    or a label falls outside {-1, +1}. NaNs in the feature matrix are left as-is.
    """
    try:
        features = pd.read_csv(data_path, sep=r"\s+", header=None)
    except (OSError, pd.errors.ParserError) as exc:
        raise IngestError(f"Could not read SECOM data file: {exc}") from exc
    features.columns = [f"sensor_{i:03d}" for i in range(features.shape[1])]

    try:
        raw_labels = pd.read_csv(
            labels_path, sep=r"\s+", header=None, names=["label", "timestamp"]
        )
    except (OSError, pd.errors.ParserError) as exc:
        raise IngestError(f"Could not read SECOM labels file: {exc}") from exc

    if len(features) != len(raw_labels):
        raise IngestError(
            f"SECOM data/labels row-count mismatch: "
            f"{len(features)} feature rows vs {len(raw_labels)} label rows."
        )

    labels = raw_labels["label"].astype(int)
    bad = ~labels.isin([PASS, FAIL])
    if bad.any():
        bad_values = sorted(set(labels[bad]))
        raise IngestError(
            f"SECOM labels must be in {{{PASS}, {FAIL}}}; found out-of-domain "
            f"value(s): {bad_values}"
        )

    timestamps = pd.to_datetime(
        raw_labels["timestamp"].str.strip('"'), format=_TIMESTAMP_FORMAT, errors="coerce"
    )

    return SecomDataset(features=features, labels=labels, timestamps=timestamps)


def secom_missingness(features: pd.DataFrame) -> pd.DataFrame:
    """Per-signal missingness, one row per signal.

    Pure: surfaces missingness without changing the input. Columns:
    ``[signal, n_present, n_missing, missing_frac]``.
    """
    n_rows = len(features)
    n_present = features.notna().sum()
    n_missing = features.isna().sum()
    missing_frac = n_missing / n_rows if n_rows else n_missing.astype(float)
    return pd.DataFrame(
        {
            "signal": features.columns,
            "n_present": n_present.to_numpy(),
            "n_missing": n_missing.to_numpy(),
            "missing_frac": missing_frac.to_numpy(),
        }
    )
