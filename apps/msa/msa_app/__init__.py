"""MSA (Measurement System Analysis) application package.

`__version__` is the single source of truth for the MSA app version. It is read
by ``app.py`` so the displayed/stamped version never drifts. Since #231 the app is an
installed (editable) workspace package, so ``importlib.metadata.version("msa-app")``
resolves too; this constant stays the value ``pyproject.toml`` is kept in sync with.

Keep this in sync with ``apps/msa/pyproject.toml`` at release (bump both together).
"""

__version__ = "0.13.0"
