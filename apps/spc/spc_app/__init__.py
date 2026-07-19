"""SPC dashboard application package.

`__version__` is the single source of truth for the SPC app version. It is read
by ``app.py`` (and any future exporter) so the displayed/stamped version never
drifts. The app is ``package = false`` (not installed as a distribution), so
``importlib.metadata`` cannot resolve it — hence a plain constant here.

Keep this in sync with ``apps/spc/pyproject.toml`` at release (bump both together).
"""

__version__ = "0.6.0"
