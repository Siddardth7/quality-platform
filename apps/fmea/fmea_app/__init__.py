"""FMEA Risk Analyzer application package.

``__version__`` is the single source of truth for the FMEA app version. It is
read by ``app.py`` (sidebar) and ``fmea_app/exporter.py`` (Excel/PDF metadata)
so the displayed and stamped version never drift. The app is ``package = false``
(not installed as a distribution), so ``importlib.metadata`` cannot resolve it —
hence a plain constant here.

Keep this in sync with ``apps/fmea/pyproject.toml`` at release (bump both
together); ``tests/test_version.py`` guards against drift.
"""

__version__ = "0.8.0"
