"""
quality_core/io/validate.py
Shared validated-ingest boundary for Quality Platform apps — CSV / Excel.

App-agnostic by design: no FMEA/SPC domain knowledge lives here. Each app supplies
a :class:`TableSchema` (a Pydantic row model + the columns it requires, plus an
optional dataset-level model for cross-row rules); these helpers own the cross-cutting
concerns every app's upload path must get right:

  - reading CSV / Excel from a path or Streamlit upload, with a size guard and a
    friendly error for unsupported file types or unparseable files
    (``read_table``)
  - schema/type/range validation against the app's Pydantic model, turning the
    first failure into a clear, row-addressed message instead of a stack trace,
    and normalising empty cells to ``None`` so a blank never coerces to the
    literal text ``"nan"`` (``validate_table``)
  - a single ``load_table`` that reads then validates, the drop-in replacement for
    a bare ``pd.read_csv(upload)``

Every friendly failure is raised as :class:`IngestError` — a ``ValueError`` subclass
so existing ``except ValueError`` paths keep working, and a distinct type so a
Streamlit caller can ``st.error(str(e))`` and trust the message is user-safe.

This is the platform's "validate ingest once, use it everywhere" surface: FMEA and
SPC both plug their own schema into the same machinery.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, BinaryIO, Union, cast

import pandas as pd
import pydantic

# ===========================================================================
# Public constants and types
# ===========================================================================

#: Default upload ceiling (20 MB). Apps may override per call. A spreadsheet
#: larger than this is unusual for any of the quality tools and is far more
#: likely to be a mistake or an attack than a real dataset.
DEFAULT_MAX_UPLOAD_BYTES = 20 * 1024 * 1024

#: Longest offending value echoed back in an error message before truncation.
_MAX_ECHO_LEN = 50

#: A readable source: a filesystem path or a binary file-like (e.g. a Streamlit
#: ``UploadedFile``, which is a ``BytesIO`` carrying ``.name`` and ``.size``).
Source = Union[str, "os.PathLike[str]", BinaryIO]


class IngestError(ValueError):
    """A user-facing ingest failure with a message safe to show as-is.

    Subclasses ``ValueError`` so callers that already catch ``ValueError`` (the
    interface FMEA's ``validate_input`` established) keep working, while the
    distinct type lets a Streamlit layer recognise "show this to the user" errors.
    """


@dataclass(frozen=True)
class TableSchema:
    """A per-tool ingest contract: how to validate one uploaded table.

    Parameters
    ----------
    name:
        Human label for the dataset (e.g. ``"FMEA"``), used in error messages.
    row_model:
        Pydantic model validating a single row. Its field names are matched
        against DataFrame columns.
    required_columns:
        Columns that must be present and are passed to ``row_model``. Defaults to
        the model's field names (the common case where columns == fields).
    dataset_model:
        Optional Pydantic model for cross-row rules (e.g. unique IDs). Constructed
        as ``dataset_model(rows=[...])`` over the validated row *instances*, so its
        ``rows`` field must accept ``row_model`` instances (not raw dicts).
    template_hint:
        Optional pointer appended to error messages, e.g.
        ``"data/fmea_input_template.csv"``.
    """

    name: str
    row_model: type[pydantic.BaseModel]
    required_columns: tuple[str, ...] = ()
    dataset_model: type[pydantic.BaseModel] | None = None
    template_hint: str | None = None

    def __post_init__(self) -> None:
        # Default required columns to the row model's declared fields.
        if not self.required_columns:
            object.__setattr__(
                self, "required_columns", tuple(self.row_model.model_fields)
            )

    def _hint_suffix(self) -> str:
        return (
            f" Check your data against the template at {self.template_hint}."
            if self.template_hint
            else ""
        )


# ===========================================================================
# read_table — bytes/path → DataFrame
# ===========================================================================


def _resolve_filename(source: Source, filename: str | None) -> str:
    """Best-effort name used only for extension dispatch and error messages."""
    if filename:
        return filename
    name = getattr(source, "name", None)
    if isinstance(name, str) and name:
        return name
    if isinstance(source, (str, os.PathLike)):
        return os.fspath(source)
    raise IngestError(
        "Could not determine the file type: the upload has no file name. "
        "Pass filename=... or upload a .csv or .xlsx file."
    )


def _source_size(source: Source) -> int | None:
    """Size in bytes if cheaply known (Streamlit upload .size, or a real path)."""
    size = getattr(source, "size", None)
    if isinstance(size, int):
        return size
    if isinstance(source, (str, os.PathLike)):
        try:
            return os.path.getsize(source)
        except OSError:
            return None
    return None


def read_table(
    source: Source,
    *,
    filename: str | None = None,
    max_bytes: int | None = DEFAULT_MAX_UPLOAD_BYTES,
) -> pd.DataFrame:
    """Read a ``.csv`` or ``.xlsx`` source into a DataFrame, friendly errors only.

    Parameters
    ----------
    source:
        A filesystem path or a binary file-like (e.g. a Streamlit upload).
    filename:
        Overrides the name used to pick the reader; needed when ``source`` is a
        bare buffer with no ``.name``.
    max_bytes:
        Upload ceiling; ``None`` disables the check. Defaults to
        :data:`DEFAULT_MAX_UPLOAD_BYTES`.

    Raises
    ------
    IngestError
        On an unsupported extension, an oversized file, or an unparseable file.
        The file-type check runs first, so the message names the more fundamental
        problem (wrong type) before complaining about size.
    """
    name = _resolve_filename(source, filename)
    lowered = name.lower()
    is_csv = lowered.endswith(".csv")
    is_excel = lowered.endswith((".xlsx", ".xlsm"))

    if not (is_csv or is_excel):
        raise IngestError(
            f"Unsupported file type: '{name}'. Please upload a .csv or .xlsx file."
        )

    if max_bytes is not None:
        size = _source_size(source)
        if size is not None and size > max_bytes:
            mb = max_bytes // (1024 * 1024)
            raise IngestError(
                f"Uploaded file exceeds the {mb} MB limit. Files this large are "
                "unusual for a quality dataset; split it or load it from the CLI."
            )

    try:
        return pd.read_csv(source) if is_csv else pd.read_excel(source)
    except Exception as exc:  # message varies by reader; normalise to a friendly one
        raise IngestError(
            f"Could not read '{name}'. The file may be corrupt, empty, missing, or not a "
            f"valid {'CSV' if is_csv else 'Excel'} file."
        ) from exc


# ===========================================================================
# validate_table — DataFrame → DataFrame (or raise IngestError)
# ===========================================================================


def _na_to_none(value: Any) -> Any:
    """Map a pandas missing value (NaN/NaT/NA) to ``None``; pass everything else.

    Keeps an empty cell from reaching a non-strict model as the float ``nan``,
    which would silently coerce to the literal string ``"nan"``.
    """
    try:
        return None if pd.isna(value) else value
    except (TypeError, ValueError):
        # pd.isna on an array-like cell returns an array; treat as present.
        return value


def _format_row_error(row_number: int, schema: TableSchema, exc: pydantic.ValidationError) -> str:
    """Turn the first row-level Pydantic error into a clear, addressed message.

    One uniform shape for every failure kind (type, range, custom validator):
    ``Row N, column 'X': <pydantic message> (got <value>)``. Pydantic's own
    message is already specific ("Input should be less than or equal to 10"),
    so no per-error-type special-casing is needed here.
    """
    first = exc.errors()[0]
    column = ".".join(str(part) for part in first.get("loc", ()))
    where = f"Row {row_number}" + (f", column '{column}'" if column else "")
    msg = first.get("msg", "invalid value")
    echo = ""
    if "input" in first:
        shown = repr(first["input"])
        if len(shown) > _MAX_ECHO_LEN:
            shown = shown[: _MAX_ECHO_LEN - 3] + "..."
        echo = f" (got {shown})"
    return f"{where}: {msg}{echo}.{schema._hint_suffix()}"


def _format_dataset_error(schema: TableSchema, exc: pydantic.ValidationError) -> str:
    """Turn a dataset-level (cross-row) Pydantic error into a clear message."""
    msg = exc.errors()[0].get("msg", "invalid dataset")
    # Pydantic prefixes model-validator messages with "Value error, " (raise) or
    # "Assertion failed, " (assert); drop either so the surfaced text is the
    # validator's own sentence.
    for prefix in ("Value error, ", "Assertion failed, "):
        msg = msg.removeprefix(prefix)
    return f"{schema.name} dataset is invalid: {msg}.{schema._hint_suffix()}"


def validate_table(df: pd.DataFrame, schema: TableSchema) -> pd.DataFrame:
    """Validate ``df`` against ``schema``; return it unchanged or raise.

    Checks, in order: at least one row; all ``required_columns`` present; each row
    valid per ``schema.row_model`` (empty cells normalised to ``None`` first); the
    dataset valid per ``schema.dataset_model`` (if any). The DataFrame is returned
    untouched so this slots in where a bare ``pd.read_csv`` result was used.

    Raises
    ------
    IngestError
        With a row-addressed, user-safe message on the first failure found.
    """
    if df.empty:
        raise IngestError(
            f"No data rows found. A {schema.name} file must contain at least one "
            f"row below the header.{schema._hint_suffix()}"
        )

    required: Sequence[str] = schema.required_columns
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise IngestError(
            f"Missing required column(s): {missing}. "
            f"Expected columns: {list(required)}.{schema._hint_suffix()}"
        )

    rows: list[pydantic.BaseModel] = []
    records = df[list(required)].to_dict(orient="records")
    for offset, record in enumerate(records):
        clean = {key: _na_to_none(value) for key, value in record.items()}
        try:
            rows.append(schema.row_model(**cast("dict[str, Any]", clean)))
        except pydantic.ValidationError as exc:
            # Row numbers are 1-based with the header as row 1, so the number
            # matches what the user sees in a spreadsheet (first data row = 2).
            raise IngestError(_format_row_error(offset + 2, schema, exc)) from exc

    if schema.dataset_model is not None:
        try:
            schema.dataset_model(rows=rows)
        except pydantic.ValidationError as exc:
            raise IngestError(_format_dataset_error(schema, exc)) from exc

    return df


# ===========================================================================
# load_table — read + validate in one call
# ===========================================================================


def load_table(
    source: Source,
    schema: TableSchema,
    *,
    filename: str | None = None,
    max_bytes: int | None = DEFAULT_MAX_UPLOAD_BYTES,
) -> pd.DataFrame:
    """Read a ``.csv``/``.xlsx`` source and validate it against ``schema``.

    The one-call drop-in for ``pd.read_csv(upload)`` that fails with a friendly
    :class:`IngestError` instead of a stack trace. See :func:`read_table` and
    :func:`validate_table` for the individual steps.
    """
    df = read_table(source, filename=filename, max_bytes=max_bytes)
    return validate_table(df, schema)
