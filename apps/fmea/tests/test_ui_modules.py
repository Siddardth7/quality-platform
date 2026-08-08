"""
tests/test_ui_modules.py
Unit tests for pure (non-Streamlit) functions in the ui/ package.
"""
from types import SimpleNamespace

import pandas as pd

from ui import df_content_hash
from ui.exports import _export_cache_key
from ui.filters import apply_filters

# ---------------------------------------------------------------------------
# df_content_hash
# ---------------------------------------------------------------------------

def test_df_content_hash_stable():
    """Same DataFrame produces the same hash on repeated calls."""
    df = pd.DataFrame([{"A": 1, "B": 2}])
    assert df_content_hash(df) == df_content_hash(df)


def test_df_content_hash_differs_on_different_data():
    """Different DataFrames produce different hashes."""
    df1 = pd.DataFrame([{"A": 1}])
    df2 = pd.DataFrame([{"A": 2}])
    assert df_content_hash(df1) != df_content_hash(df2)


def test_df_content_hash_index_insensitive():
    """Hash is the same regardless of DataFrame index values."""
    df1 = pd.DataFrame([{"A": 1}], index=[0])
    df2 = pd.DataFrame([{"A": 1}], index=[99])
    assert df_content_hash(df1) == df_content_hash(df2)


# ---------------------------------------------------------------------------
# apply_filters
# ---------------------------------------------------------------------------

def _make_df() -> pd.DataFrame:
    return pd.DataFrame([
        {"RPN": 200, "Severity": 9, "Process_Step": "Layup",    "Risk_Tier": "Red"},
        {"RPN": 80,  "Severity": 6, "Process_Step": "Bagging",  "Risk_Tier": "Yellow"},
        {"RPN": 20,  "Severity": 3, "Process_Step": "Autoclave","Risk_Tier": "Green"},
    ])


def test_apply_filters_rpn_min():
    df = _make_df()
    result = apply_filters(df, rpn_min=100, sev9_only=False, process_steps=["Layup", "Bagging", "Autoclave"])
    assert len(result) == 1
    assert result.iloc[0]["RPN"] == 200


def test_apply_filters_sev9_only():
    df = _make_df()
    result = apply_filters(df, rpn_min=0, sev9_only=True, process_steps=["Layup", "Bagging", "Autoclave"])
    assert len(result) == 1
    assert result.iloc[0]["Severity"] == 9


def test_apply_filters_process_steps():
    df = _make_df()
    result = apply_filters(df, rpn_min=0, sev9_only=False, process_steps=["Layup"])
    assert len(result) == 1
    assert result.iloc[0]["Process_Step"] == "Layup"


def test_apply_filters_no_filters():
    df = _make_df()
    result = apply_filters(df, rpn_min=0, sev9_only=False, process_steps=["Layup", "Bagging", "Autoclave"])
    assert len(result) == 3


def test_apply_filters_combined():
    df = _make_df()
    result = apply_filters(df, rpn_min=50, sev9_only=True, process_steps=["Layup", "Bagging"])
    assert len(result) == 1
    assert result.iloc[0]["RPN"] == 200


# ---------------------------------------------------------------------------
# _export_cache_key
# ---------------------------------------------------------------------------

def test_export_cache_key_same_inputs_same_key():
    df = pd.DataFrame([{"A": 1}])
    key1 = _export_cache_key(df, 0, False, ["Layup"], "excel")
    key2 = _export_cache_key(df, 0, False, ["Layup"], "excel")
    assert key1 == key2


def test_export_cache_key_different_data_different_key():
    df1 = pd.DataFrame([{"A": 1}])
    df2 = pd.DataFrame([{"A": 2}])
    key1 = _export_cache_key(df1, 0, False, ["Layup"], "excel")
    key2 = _export_cache_key(df2, 0, False, ["Layup"], "excel")
    assert key1 != key2


def test_export_cache_key_different_type_different_key():
    df = pd.DataFrame([{"A": 1}])
    key_xl  = _export_cache_key(df, 0, False, ["Layup"], "excel")
    key_pdf = _export_cache_key(df, 0, False, ["Layup"], "pdf")
    assert key_xl != key_pdf


# ---------------------------------------------------------------------------
# render_rating_scale_selector — 3-way branch routing (#256)
#
# render_rating_scale_selector() reads one st.sidebar.selectbox choice and must
# route to the matching loader. We fake `st` (sidebar with the widget calls the
# function uses) rather than stand up Streamlit's runtime — the routing is pure
# once the choice is fixed.
# ---------------------------------------------------------------------------

class _FakeSidebar:
    """Minimal st.sidebar stub: selectbox/file_uploader return canned values;
    error/caption record their calls so branch selection is observable."""

    def __init__(self, choice: str, upload: object | None = None):
        self._choice = choice
        self._upload = upload
        self.errors: list[str] = []
        self.captions: list[str] = []

    def selectbox(self, *_args, **_kwargs) -> str:
        return self._choice

    def file_uploader(self, *_args, **_kwargs) -> object | None:
        return self._upload

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def caption(self, msg: str) -> None:
        self.captions.append(msg)


def _patch_selector(monkeypatch, choice, upload=None):
    """Point ui.filters.st at a fake carrying `choice`/`upload`; return the sidebar."""
    from ui import filters

    sidebar = _FakeSidebar(choice, upload)
    monkeypatch.setattr(filters, "st", SimpleNamespace(sidebar=sidebar))
    return sidebar


def test_selector_labels_match_loader_names():
    """Label≈name coupling: each selectbox label must equal the `name` its loader
    returns. This is load-bearing because `_build`'s setdefault makes the JSON
    file — not the loader arg — the source of `name`, so a label/JSON drift is
    silent otherwise (see changes.md Deviation)."""
    from fmea_app.rating_scales import load_default_scales, load_legacy_fmea4_scales
    from ui.filters import _SCALE_2019, _SCALE_FMEA4

    assert _SCALE_2019 == load_default_scales().name
    assert _SCALE_FMEA4 == load_legacy_fmea4_scales().name


def test_selector_2019_choice_routes_to_default_loader(monkeypatch):
    from ui import filters

    _patch_selector(monkeypatch, filters._SCALE_2019)
    monkeypatch.setattr(filters, "load_default_scales", lambda: "DEFAULT")
    monkeypatch.setattr(filters, "load_legacy_fmea4_scales", lambda: "LEGACY")
    assert filters.render_rating_scale_selector() == "DEFAULT"


def test_selector_fmea4_choice_routes_to_legacy_loader(monkeypatch):
    from ui import filters

    _patch_selector(monkeypatch, filters._SCALE_FMEA4)
    monkeypatch.setattr(filters, "load_default_scales", lambda: "DEFAULT")
    monkeypatch.setattr(filters, "load_legacy_fmea4_scales", lambda: "LEGACY")
    assert filters.render_rating_scale_selector() == "LEGACY"


def test_selector_custom_valid_upload_routes_to_json_loader(monkeypatch):
    from ui import filters

    upload = SimpleNamespace(getvalue=lambda: b"{}")
    _patch_selector(monkeypatch, filters._SCALE_CUSTOM, upload=upload)
    monkeypatch.setattr(filters, "load_scales_from_json", lambda data: "CUSTOM")
    assert filters.render_rating_scale_selector() == "CUSTOM"


def test_selector_custom_no_upload_falls_back_to_default(monkeypatch):
    from ui import filters

    sidebar = _patch_selector(monkeypatch, filters._SCALE_CUSTOM, upload=None)
    monkeypatch.setattr(filters, "load_default_scales", lambda: "DEFAULT")
    assert filters.render_rating_scale_selector() == "DEFAULT"
    assert sidebar.captions  # caption prompting for an upload was shown


def test_selector_custom_invalid_upload_errors_and_falls_back(monkeypatch):
    from ui import filters

    def _boom(_data):
        raise ValueError("bad scale")

    upload = SimpleNamespace(getvalue=lambda: b"{bad")
    sidebar = _patch_selector(monkeypatch, filters._SCALE_CUSTOM, upload=upload)
    monkeypatch.setattr(filters, "load_scales_from_json", _boom)
    monkeypatch.setattr(filters, "load_default_scales", lambda: "DEFAULT")
    assert filters.render_rating_scale_selector() == "DEFAULT"
    assert any("bad scale" in e for e in sidebar.errors)
