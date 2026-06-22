"""Shared I/O for Quality Platform apps.

`export` holds app-agnostic export primitives (CSV / Excel / PDF) so FMEA, SPC,
and the future Control Plan write export *config* (columns, colors, layout) and
reuse the cross-cutting machinery — formula-injection escaping, openpyxl styling,
Latin-1 PDF text, repeating table headers with page breaks.
"""

from quality_core.io.export import (
    FORMULA_PREFIXES,
    add_image_page,
    export_csv,
    render_table,
    safe_text,
    sanitize_for_export,
    write_keyvalue_sheet,
    write_table_sheet,
)

__all__ = [
    "FORMULA_PREFIXES",
    "sanitize_for_export",
    "export_csv",
    "safe_text",
    "write_table_sheet",
    "write_keyvalue_sheet",
    "render_table",
    "add_image_page",
]
