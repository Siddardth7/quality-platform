"""
quality_core/io/validate.py
Shared validated-ingest boundary for Quality Platform apps — CSV / Excel.

App-agnostic by design: no FMEA/SPC domain knowledge lives here. Each app supplies
a :class:`TableSchema` (a Pydantic row model + the columns it requires, plus an
optional dataset-level model for cross-row rules); these helpers own the cross-cutting
concerns every app's upload path must get right:

  - reading CSV / Excel from raw bytes or a binary file-like (e.g. a Streamlit
    upload), with a *measured* byte ceiling, row/column caps, and a friendly
    error for unsupported file types or unparseable files (``read_table``)
  - the same, but from a trusted filesystem path (``read_table_from_path`` —
    the *only* place a path is accepted; see "Fail closed" below)
  - schema/type/range validation against the app's Pydantic model, turning the
    first failure into a clear, row-addressed message instead of a stack trace,
    and normalising empty cells to ``None`` so a blank never coerces to the
    literal text ``"nan"``; the frame comes back narrowed to the columns actually
    validated, so an undeclared column cannot reach an engine (``validate_table``)
  - ``load_table`` / ``load_table_from_path``, which read then validate — the
    *narrowing* replacement for a bare ``pd.read_csv(upload)``: same one call, but
    only the validated columns come back (#200)

Every friendly failure is raised as :class:`IngestError` — a ``ValueError`` subclass
so existing ``except ValueError`` paths keep working, and a distinct type so a
Streamlit caller can ``st.error(str(e))`` and trust the message is user-safe.

Fail closed (#199): ``read_table``/``load_table`` accept only raw bytes or a
binary file-like — never a ``str``/``PathLike`` — because pandas resolves a
``str`` source as a local path *or a URL*, which is an SSRF/LFI surface at a
request boundary. A filesystem path is only reachable via the separately named
``read_table_from_path``/``load_table_from_path``, which ``open()``s it directly
(no URL resolution). The byte ceiling is *measured* by seeking the stream, never
read off a caller-supplied ``.size`` attribute — an unmeasurable source (not
seekable, or missing ``tell``/``seek``) is rejected outright rather than let
through unmeasured. Row/column caps are a secondary, cell-count control; for
``.xlsx`` the byte ceiling remains the primary defense against a small zip
inflating hugely.

This is the platform's "validate ingest once, use it everywhere" surface: FMEA and
SPC both plug their own schema into the same machinery.
"""

from __future__ import annotations

import io
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

#: Default row ceiling. Every fixture checked into this repo today is orders of
#: magnitude smaller (thousands of rows at most); 1e6 rows is already far past
#: what the 20 MB byte ceiling allows for any plausible CSV, so this only bites
#: pathological input (SME sign-off, #199).
DEFAULT_MAX_ROWS = 1_000_000

#: Default column ceiling. The widest real quality table (Control Plan) has
#: ~15 columns; 1e3 columns bites only pathological input (SME sign-off, #199).
DEFAULT_MAX_COLUMNS = 1_000

#: Longest offending value echoed back in an error message before truncation.
_MAX_ECHO_LEN = 50

#: An API-safe source: a binary file-like (Streamlit ``UploadedFile``,
#: ``io.BytesIO``, an open file handle) or raw bytes. Deliberately NOT a
#: ``str``/``PathLike`` — pandas resolves a ``str`` as a local path or a URL, so
#: paths live behind :func:`read_table_from_path` only.
Source = Union[BinaryIO, bytes, bytearray]

#: A trusted filesystem path, accepted only by the ``*_from_path`` functions.
PathSource = Union[str, "os.PathLike[str]"]


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
    optional_columns:
        Columns that need not be present, but when they are, are validated by the
        same ``row_model`` and kept in the returned frame (#200). Every name must
        be a ``row_model`` field *with a default* — a file omitting the column
        would otherwise fail every row with a confusing "Field required".
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
    optional_columns: tuple[str, ...] = ()
    dataset_model: type[pydantic.BaseModel] | None = None
    template_hint: str | None = None

    def __post_init__(self) -> None:
        # Default required columns to the row model's declared fields.
        if not self.required_columns:
            object.__setattr__(
                self, "required_columns", tuple(self.row_model.model_fields)
            )
        # A bad optional_columns entry is a developer error at import time, not a
        # user-facing ingest failure — so plain ValueError, never IngestError.
        fields = self.row_model.model_fields
        bad = [
            col
            for col in self.optional_columns
            if col not in fields or fields[col].is_required()
        ]
        if bad:
            raise ValueError(
                f"{self.name}: optional_columns {bad} must be {self.row_model.__name__} "
                "fields with defaults."
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


def _resolve_filename(stream: BinaryIO, filename: str | None) -> str:
    """Best-effort name used only for extension dispatch and error messages."""
    if filename:
        return filename
    name = getattr(stream, "name", None)
    if isinstance(name, str) and name:
        return name
    raise IngestError(
        "Could not determine the file type: the upload has no file name. "
        "Pass filename=... or upload a .csv or .xlsx file."
    )


def _measured_size(stream: BinaryIO) -> int:
    """Measure a stream's length by seeking, never by trusting a ``.size`` attribute.

    A ``.size`` attribute is whatever the caller (or an attacker) set it to — it is
    not evidence of the stream's real length (#199 HIGH finding). The only
    authority is the stream's own position range, so this seeks to the end and
    back to the position found, leaving the stream exactly where a caller-driven
    rerun (e.g. Streamlit re-handing the same ``UploadedFile``) expects it, ready
    for ``pandas`` to read from that same position next.
    """
    try:
        pos = stream.tell()
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(pos)
    except (OSError, AttributeError) as exc:
        # OSError covers io.UnsupportedOperation (a subclass) for a non-seekable
        # stream; AttributeError covers a source missing tell/seek entirely.
        raise IngestError(
            "Upload could not be measured (the stream is not seekable). "
            "Re-upload the file or pass a seekable buffer."
        ) from exc
    return size


def read_table(
    source: Source,
    *,
    filename: str | None = None,
    max_bytes: int | None = DEFAULT_MAX_UPLOAD_BYTES,
    max_rows: int | None = DEFAULT_MAX_ROWS,
    max_columns: int | None = DEFAULT_MAX_COLUMNS,
) -> pd.DataFrame:
    """Read a ``.csv`` or ``.xlsx`` source into a DataFrame, friendly errors only.

    Parameters
    ----------
    source:
        Raw bytes or a binary file-like (e.g. a Streamlit upload). A filesystem
        path is deliberately NOT accepted here — see :func:`read_table_from_path`.
    filename:
        Overrides the name used to pick the reader; needed when ``source`` is a
        bare buffer/bytes with no ``.name``.
    max_bytes:
        Upload ceiling; ``None`` disables the check. Defaults to
        :data:`DEFAULT_MAX_UPLOAD_BYTES`. When enforced, the size is *measured*
        (stream seek), never read off a ``.size`` attribute, and an unmeasurable
        source is rejected rather than let through (fail closed).
    max_rows:
        Row ceiling; ``None`` disables the check. Defaults to
        :data:`DEFAULT_MAX_ROWS`. Enforced during the parse (one row past the
        cap is read so "too many" is distinguishable from "exactly at the cap"
        while keeping the parse bounded) — a secondary, cell-count control; the
        byte ceiling above is the primary defense, especially for ``.xlsx``
        (a small zip can inflate hugely).
    max_columns:
        Column ceiling; ``None`` disables the check. Defaults to
        :data:`DEFAULT_MAX_COLUMNS`, checked on the parsed frame.

    Raises
    ------
    IngestError
        On an unsupported extension, an unmeasurable or oversized source, a
        row/column cap violation, or an unparseable file. The file-type check
        runs first, then size, so each message names the more fundamental
        problem before the next.
    """
    if isinstance(source, (str, os.PathLike)):
        raise IngestError(
            "A file path is not accepted here. Upload the file, or use "
            "read_table_from_path() for a trusted local path."
        )
    stream: BinaryIO = io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else source
    name = _resolve_filename(stream, filename)
    lowered = name.lower()
    is_csv = lowered.endswith(".csv")
    is_excel = lowered.endswith((".xlsx", ".xlsm"))

    if not (is_csv or is_excel):
        raise IngestError(
            f"Unsupported file type: '{name}'. Please upload a .csv or .xlsx file."
        )

    if max_bytes is not None:
        size = _measured_size(stream)
        if size > max_bytes:
            mb = max_bytes // (1024 * 1024)
            raise IngestError(
                f"Uploaded file exceeds the {mb} MB limit. Files this large are "
                "unusual for a quality dataset; split it or load it from the CLI."
            )

    # One row past the cap, so "too many rows" is distinguishable from "exactly
    # at the cap" while keeping the parse itself bounded.
    nrows = max_rows + 1 if max_rows is not None else None

    try:
        df = pd.read_csv(stream, nrows=nrows) if is_csv else pd.read_excel(stream, nrows=nrows)
    except Exception as exc:  # message varies by reader; normalise to a friendly one
        raise IngestError(
            f"Could not read '{name}'. The file may be corrupt, empty, missing, or not a "
            f"valid {'CSV' if is_csv else 'Excel'} file."
        ) from exc

    if max_rows is not None and len(df) > max_rows:
        raise IngestError(
            f"'{name}' has more than {max_rows} rows, which exceeds the limit for a "
            "quality dataset. Split it into smaller files."
        )
    if max_columns is not None and df.shape[1] > max_columns:
        raise IngestError(
            f"'{name}' has more than {max_columns} columns, which exceeds the limit for "
            "a quality dataset. Check the file is not malformed."
        )

    return df


def read_table_from_path(
    path: PathSource,
    *,
    max_bytes: int | None = DEFAULT_MAX_UPLOAD_BYTES,
    max_rows: int | None = DEFAULT_MAX_ROWS,
    max_columns: int | None = DEFAULT_MAX_COLUMNS,
) -> pd.DataFrame:
    """Read a ``.csv``/``.xlsx`` file from a trusted filesystem path.

    The only place in this module a filesystem path is accepted (see the module
    docstring's "Fail closed"). Opens ``path`` directly in binary mode — never
    handed to pandas as a string — so a URL-shaped string (e.g.
    ``"http://169.254.169.254/..."``) is simply an unreadable local path, not a
    network request: the SSRF/LFI shape disappears without a URL blocklist.

    Raises
    ------
    IngestError
        The friendly "Could not read ..." message on a missing/unreadable path
        or a directory; otherwise the same failures as :func:`read_table`.
    """
    name = os.fspath(path)
    kind = "CSV" if name.lower().endswith(".csv") else "Excel"
    try:
        with open(name, "rb") as fh:
            return read_table(
                fh, filename=name, max_bytes=max_bytes, max_rows=max_rows, max_columns=max_columns
            )
    except OSError as exc:
        raise IngestError(
            f"Could not read '{name}'. The file may be corrupt, empty, missing, or not a "
            f"valid {kind} file."
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


_PYDANTIC_MSG_PREFIXES = ("Value error, ", "Assertion failed, ")


def clean_pydantic_message(msg: str) -> str:
    """Strip pydantic's raise/assert prefix so the surfaced text is the validator's own sentence.

    Pydantic prefixes model-validator messages with ``"Value error, "`` (raise) or
    ``"Assertion failed, "`` (assert); a message without either passes through
    unchanged, and a mid-sentence occurrence is left alone.
    """
    for prefix in _PYDANTIC_MSG_PREFIXES:
        msg = msg.removeprefix(prefix)
    return msg


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
    msg = clean_pydantic_message(first.get("msg", "invalid value"))
    # `exc.errors()` (default include_input=True) always carries the offending
    # value, so echo it unconditionally; `.get` stays crash-safe regardless.
    shown = repr(first.get("input"))
    if len(shown) > _MAX_ECHO_LEN:
        shown = shown[: _MAX_ECHO_LEN - 3] + "..."
    echo = f" (got {shown})"
    return f"{where}: {msg}{echo}.{schema._hint_suffix()}"


def _format_dataset_error(schema: TableSchema, exc: pydantic.ValidationError) -> str:
    """Turn a dataset-level (cross-row) Pydantic error into a clear message."""
    msg = clean_pydantic_message(exc.errors()[0].get("msg", "invalid dataset"))
    return f"{schema.name} dataset is invalid: {msg}.{schema._hint_suffix()}"


def validate_table(df: pd.DataFrame, schema: TableSchema) -> pd.DataFrame:
    """Validate ``df`` against ``schema``; return **only the validated columns** or raise.

    Checks, in order: at least one row; all ``required_columns`` present; each row
    valid per ``schema.row_model`` (empty cells normalised to ``None`` first); the
    dataset valid per ``schema.dataset_model`` (if any).

    Validation is reductive, not merely assertive (#200): the returned frame is a
    copy narrowed to ``required_columns`` plus any ``optional_columns`` actually
    present, in that order. A column the schema never looked at cannot reach an
    engine through this boundary — undeclared columns are dropped silently, which
    is normal for field data (``operator``, ``notes``, ``lot_id``) and not an error.

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

    # Required columns, then any declared optional column actually present. dict.fromkeys
    # dedupes (a name may appear in both) while preserving this deterministic order.
    present_optional = [col for col in schema.optional_columns if col in df.columns]
    columns = list(dict.fromkeys([*required, *present_optional]))

    rows: list[pydantic.BaseModel] = []
    records = df[columns].to_dict(orient="records")
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

    # Explicit .copy() pins the contract callers rely on: the returned frame is
    # independent of the input, so assigning into it (e.g. msa_app/gage_rr_engine.py:89
    # does `df["measurement"] = ...`) can never write through to the caller's frame.
    # Under the pinned pandas (Copy-on-Write always on) a list projection already
    # copies, so this is belt-and-braces — kept so the guarantee does not silently
    # depend on a pandas implementation detail.
    return df[columns].copy()


# ===========================================================================
# load_table — read + validate in one call
# ===========================================================================


def load_table(
    source: Source,
    schema: TableSchema,
    *,
    filename: str | None = None,
    max_bytes: int | None = DEFAULT_MAX_UPLOAD_BYTES,
    max_rows: int | None = DEFAULT_MAX_ROWS,
    max_columns: int | None = DEFAULT_MAX_COLUMNS,
) -> pd.DataFrame:
    """Read a ``.csv``/``.xlsx`` source and validate it against ``schema``.

    The one-call drop-in for ``pd.read_csv(upload)`` that fails with a friendly
    :class:`IngestError` instead of a stack trace — with one deliberate difference
    from ``pd.read_csv``: the frame comes back narrowed to the columns the schema
    validated (#200), so an undeclared column never reaches an engine. See
    :func:`read_table` and :func:`validate_table` for the individual steps.
    ``source`` is bytes/file-like only; for a trusted filesystem path use
    :func:`load_table_from_path`.
    """
    df = read_table(
        source, filename=filename, max_bytes=max_bytes, max_rows=max_rows, max_columns=max_columns
    )
    return validate_table(df, schema)


def load_table_from_path(
    path: PathSource,
    schema: TableSchema,
    *,
    max_bytes: int | None = DEFAULT_MAX_UPLOAD_BYTES,
    max_rows: int | None = DEFAULT_MAX_ROWS,
    max_columns: int | None = DEFAULT_MAX_COLUMNS,
) -> pd.DataFrame:
    """Read a ``.csv``/``.xlsx`` file from a trusted path and validate it against ``schema``.

    See :func:`read_table_from_path` and :func:`validate_table` for the individual
    steps.
    """
    df = read_table_from_path(path, max_bytes=max_bytes, max_rows=max_rows, max_columns=max_columns)
    return validate_table(df, schema)
