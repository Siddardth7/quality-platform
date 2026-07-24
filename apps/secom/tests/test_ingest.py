"""Tests for secom_app/ingest.py — honest, NaN-preserving SECOM loader (W09-1).

Drives load_secom() and secom_missingness() with:
- A reference/scorecard test against the real vendored UCI files (shape, label
  split, dynamic column count, timestamp parsing).
- The core correctness point: NaN is preserved, not imputed or dropped.
- Structural failure modes -> IngestError (row-count mismatch, out-of-domain
  label, unreadable/missing file, malformed file).
- secom_missingness() reconciliation.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from secom_app.ingest import (
    FAIL,
    PASS,
    SECOM_DATA_PATH,
    SECOM_LABELS_PATH,
    IngestError,
    load_secom,
    secom_missingness,
)

# --- Reference test against the real vendored data ---------------------------


def test_load_secom_reference_shape_and_labels():
    """Real vendored files: 1567 rows x 590 signals; label split 1463/104."""
    dataset = load_secom()

    # Column count must come from the file, not a hardcoded 590/591 literal.
    raw_features = pd.read_csv(SECOM_DATA_PATH, sep=r"\s+", header=None)
    assert dataset.features.shape == raw_features.shape
    assert dataset.features.shape == (1567, 590)
    assert len(dataset.labels) == 1567
    assert len(dataset.timestamps) == 1567

    assert set(dataset.labels.unique()) <= {PASS, FAIL}
    assert (dataset.labels == PASS).sum() == 1463
    assert (dataset.labels == FAIL).sum() == 104

    assert pd.api.types.is_datetime64_any_dtype(dataset.timestamps)
    assert dataset.timestamps.notna().all()


def test_load_secom_column_names_derived_dynamically(tmp_path: Path):
    """Feature columns are named from the file's actual width, not a constant.

    A synthetic 4-column file must yield exactly sensor_000..sensor_003 — proof
    the loader doesn't hardcode 590/591.
    """
    data_path = tmp_path / "secom.data"
    labels_path = tmp_path / "secom_labels.data"
    data_path.write_text("1 2 3 4\n5 6 7 8\n")
    labels_path.write_text('-1 "19/07/2008 11:55:00"\n1 "19/07/2008 12:32:00"\n')

    dataset = load_secom(data_path, labels_path)

    assert list(dataset.features.columns) == [
        "sensor_000",
        "sensor_001",
        "sensor_002",
        "sensor_003",
    ]


def test_load_secom_preserves_nan_no_imputation_no_row_drop():
    """The core correctness point: a known-missing cell stays NaN; no rows lost."""
    dataset = load_secom()

    assert len(dataset.features) == 1567
    # Row 0 / sensor_072 is a known-missing cell in the vendored file.
    assert pd.isna(dataset.features.loc[0, "sensor_072"])
    # And the matrix genuinely has missingness to preserve (not silently filled).
    assert dataset.features.isna().to_numpy().sum() > 0


# --- Structural failure modes --------------------------------------------------


def test_load_secom_row_count_mismatch_raises_ingest_error(tmp_path: Path):
    data_path = tmp_path / "secom.data"
    labels_path = tmp_path / "secom_labels.data"
    data_path.write_text("1 2\n3 4\n5 6\n")  # 3 rows
    labels_path.write_text('-1 "19/07/2008 11:55:00"\n1 "19/07/2008 12:32:00"\n')  # 2 rows

    with pytest.raises(IngestError, match="row-count mismatch"):
        load_secom(data_path, labels_path)


@pytest.mark.parametrize("bad_label", ["0", "2", "-2"])
def test_load_secom_out_of_domain_label_raises_ingest_error(
    tmp_path: Path, bad_label: str
):
    data_path = tmp_path / "secom.data"
    labels_path = tmp_path / "secom_labels.data"
    data_path.write_text("1 2\n3 4\n")
    labels_path.write_text(
        f'-1 "19/07/2008 11:55:00"\n{bad_label} "19/07/2008 12:32:00"\n'
    )

    with pytest.raises(IngestError, match="out-of-domain"):
        load_secom(data_path, labels_path)


def test_load_secom_missing_data_file_raises_ingest_error(tmp_path: Path):
    with pytest.raises(IngestError, match="Could not read SECOM data file"):
        load_secom(tmp_path / "does_not_exist.data", SECOM_LABELS_PATH)


def test_load_secom_missing_labels_file_raises_ingest_error(tmp_path: Path):
    data_path = tmp_path / "secom.data"
    data_path.write_text("1 2\n3 4\n")

    with pytest.raises(IngestError, match="Could not read SECOM labels file"):
        load_secom(data_path, tmp_path / "does_not_exist.data")


def test_load_secom_malformed_data_file_raises_ingest_error(tmp_path: Path):
    """An unterminated quote trips pandas' ParserError -> wrapped as IngestError."""
    data_path = tmp_path / "secom.data"
    labels_path = tmp_path / "secom_labels.data"
    data_path.write_text('1 "2\n4 5\n')
    labels_path.write_text('-1 "19/07/2008 11:55:00"\n1 "19/07/2008 12:32:00"\n')

    with pytest.raises(IngestError, match="Could not read SECOM data file"):
        load_secom(data_path, labels_path)


def test_load_secom_malformed_labels_file_raises_ingest_error(tmp_path: Path):
    data_path = tmp_path / "secom.data"
    labels_path = tmp_path / "secom_labels.data"
    data_path.write_text("1 2\n3 4\n")
    labels_path.write_text('-1 "19/07/2008 11:55:00\n1 19/07/2008 12:32:00\n')

    with pytest.raises(IngestError, match="Could not read SECOM labels file"):
        load_secom(data_path, labels_path)


def test_load_secom_unparseable_timestamp_becomes_nat(tmp_path: Path):
    """A garbled timestamp is coerced to NaT, not a hard failure (per docstring)."""
    data_path = tmp_path / "secom.data"
    labels_path = tmp_path / "secom_labels.data"
    data_path.write_text("1 2\n3 4\n")
    labels_path.write_text('-1 "not-a-timestamp"\n1 "19/07/2008 12:32:00"\n')

    dataset = load_secom(data_path, labels_path)

    assert pd.isna(dataset.timestamps.iloc[0])
    assert pd.notna(dataset.timestamps.iloc[1])


# --- secom_missingness() -------------------------------------------------------


def test_secom_missingness_reconciles_on_synthetic_frame():
    features = pd.DataFrame(
        {
            "sensor_000": [1.0, 2.0, None, 4.0],
            "sensor_001": [None, None, None, None],
            "sensor_002": [1.0, 2.0, 3.0, 4.0],
        }
    )

    report = secom_missingness(features)

    assert list(report["signal"]) == ["sensor_000", "sensor_001", "sensor_002"]
    assert len(report) == features.shape[1]
    for _, row in report.iterrows():
        assert row["n_present"] + row["n_missing"] == len(features)
        assert 0.0 <= row["missing_frac"] <= 1.0

    row0 = report[report["signal"] == "sensor_000"].iloc[0]
    assert row0["n_present"] == 3
    assert row0["n_missing"] == 1
    assert row0["missing_frac"] == pytest.approx(0.25)

    row1 = report[report["signal"] == "sensor_001"].iloc[0]
    assert row1["n_present"] == 0
    assert row1["missing_frac"] == pytest.approx(1.0)


def test_secom_missingness_on_real_vendored_data_reconciles():
    dataset = load_secom()
    report = secom_missingness(dataset.features)

    assert len(report) == dataset.features.shape[1]
    n_rows = len(dataset.features)
    assert (report["n_present"] + report["n_missing"] == n_rows).all()
    assert (report["missing_frac"] >= 0.0).all()
    assert (report["missing_frac"] <= 1.0).all()


def test_secom_missingness_empty_dataframe():
    """Zero-row input: division-by-n_rows guard, no crash."""
    features = pd.DataFrame({"sensor_000": [], "sensor_001": []}, dtype=float)

    report = secom_missingness(features)

    assert len(report) == 2
    assert (report["n_present"] == 0).all()
    assert (report["n_missing"] == 0).all()
