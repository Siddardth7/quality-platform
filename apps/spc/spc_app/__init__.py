"""SPC dashboard application package.

`__version__` is the single source of truth for the SPC app version. It is read
by ``app.py`` (and any future exporter) so the displayed/stamped version never
drifts. Since #204 the app is an installed (editable) workspace package, so
``importlib.metadata.version("spc-app")`` resolves too; this constant stays the
value ``pyproject.toml`` is kept in sync with.

Keep this in sync with ``apps/spc/pyproject.toml`` at release (bump both together).
"""

__version__ = "0.13.0"
