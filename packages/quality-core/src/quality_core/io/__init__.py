"""Shared I/O for Quality Platform apps.

`export` holds app-agnostic export primitives (CSV / Excel / PDF) so FMEA, SPC,
and the future Control Plan write export *config* (columns, colors, layout) and
reuse the cross-cutting machinery — formula-injection escaping, openpyxl styling,
Latin-1 PDF text, repeating table headers with page breaks.

`validate` holds the mirror-image *ingest* boundary: each app supplies a
`TableSchema` (its Pydantic row model + required columns), and `load_table`
reads a CSV/Excel upload and validates it, raising a user-safe `IngestError`
instead of a stack trace.
"""

from quality_core.io.export import (
    FORMULA_PREFIXES,
    add_image_page,
    export_csv,
    pdf_subheader,
    pdf_summary_cells,
    pdf_title,
    render_table,
    safe_text,
    sanitize_cell,
    sanitize_for_export,
    write_keyvalue_sheet,
    write_table_sheet,
)
from quality_core.io.validate import (
    DEFAULT_MAX_UPLOAD_BYTES,
    IngestError,
    TableSchema,
    load_table,
    read_table,
    validate_table,
)

__all__ = [
    # export
    "FORMULA_PREFIXES",
    "sanitize_cell",
    "sanitize_for_export",
    "export_csv",
    "safe_text",
    "write_table_sheet",
    "write_keyvalue_sheet",
    "render_table",
    "add_image_page",
    "pdf_title",
    "pdf_subheader",
    "pdf_summary_cells",
    # validate
    "IngestError",
    "TableSchema",
    "DEFAULT_MAX_UPLOAD_BYTES",
    "read_table",
    "validate_table",
    "load_table",
]
