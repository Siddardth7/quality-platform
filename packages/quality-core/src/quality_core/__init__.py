"""Quality Platform shared core.

Home for cross-app primitives — schema, IO (validation + export), and the shared
theme/palette — consumed by the FMEA, SPC, and Control Plan apps. Concrete modules
are introduced in later Week-01 issues (W01-6 theme, W04 io/schema); this package is
established here so the uv workspace resolves into one dependency graph.
"""

__version__ = "0.6.0"

__all__ = ["__version__"]
