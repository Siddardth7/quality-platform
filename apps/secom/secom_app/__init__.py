"""SECOM (semiconductor manufacturing) analysis engine.

**Engine-only by decision (#206).** SECOM ships as a tested library — consumed by
its own suite and, from P3 onward, by the API — and is deliberately *not* mounted
in the Streamlit shell (``app.py``); there is no entry script under ``apps/secom/``.

`__version__` is the single source of truth for the SECOM app version. Since #204
the app is an installed (editable) workspace package, so
``importlib.metadata.version("secom-app")`` resolves too; this constant stays the
value ``pyproject.toml`` is kept in sync with.

Keep this in sync with ``apps/secom/pyproject.toml`` at release (bump both together).
"""

__version__ = "0.13.0"
