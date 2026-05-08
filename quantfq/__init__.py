"""
QuantFQ - A comprehensive Python quantitative finance library.

This library provides tools for strategy development, backtesting,
paper trading, live trading, stock screening, portfolio management,
parameter optimization, and a web dashboard.
"""

from pathlib import Path

# Read version from VERSION file
_version_file = Path(__file__).parent.parent / "VERSION"
if _version_file.exists():
    __version__ = _version_file.read_text().strip()
else:
    __version__ = "2.0.0"

__author__ = "QuantF"

# Lazy imports — allow `import quantfq` even when heavy deps (pandas, numpy) are missing
_available = {}

for _mod_name in (
    "core", "data", "strategy", "backtest", "indicators",
    "trader", "live", "screener", "portfolio", "charts", "adapters", "web",
):
    try:
        mod = __import__(f"quantfq.{_mod_name}", fromlist=[_mod_name])
        _available[_mod_name] = mod
    except ImportError:
        pass

# Re-export available modules at package level
globals().update(_available)

__all__ = [
    "core",
    "data",
    "strategy",
    "backtest",
    "indicators",
    "trader",
    "live",
    "screener",
    "portfolio",
    "charts",
    "adapters",
    "web",
]

