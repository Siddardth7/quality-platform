"""SECOM (semiconductor manufacturing) application package.

`__version__` is the single source of truth for the SECOM app version. It is read
by ``app.py`` (added by a later W09 issue) so the displayed/stamped version never
drifts. Since #204 the app is an installed (editable) workspace package, so
``importlib.metadata.version("secom-app")`` resolves too; this constant stays the
value ``pyproject.toml`` is kept in sync with.

Keep this in sync with ``apps/secom/pyproject.toml`` at release (bump both together).
"""

__version__ = "0.7.0"
