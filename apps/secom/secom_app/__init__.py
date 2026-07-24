"""SECOM (semiconductor manufacturing) application package.

`__version__` is the single source of truth for the SECOM app version. It is read
by ``app.py`` (added by a later W09 issue) so the displayed/stamped version never
drifts. The app is ``package = false`` (not installed as a distribution), so
``importlib.metadata`` cannot resolve it — hence a plain constant here.

Keep this in sync with ``apps/secom/pyproject.toml`` at release (bump both together).
"""

__version__ = "0.7.0"
