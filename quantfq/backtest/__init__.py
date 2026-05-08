"""
Backtesting module for QuantFQ.
"""

# Lazy imports to avoid hard dependency on pandas at import time
def __getattr__(name: str):
    if name == "BacktestEngine":
        from .engine import BacktestEngine
        return BacktestEngine
    if name == "PortfolioBacktestEngine":
        from .portfolio_engine import PortfolioBacktestEngine
        return PortfolioBacktestEngine
    if name == "PortfolioBacktestResult":
        from .portfolio_engine import PortfolioBacktestResult
        return PortfolioBacktestResult
    if name == "PerformanceReporter":
        from .performance import PerformanceReporter
        return PerformanceReporter
    # metrics functions
    _metrics = {
        "calculate_annualized_return", "calculate_calmar_ratio",
        "calculate_max_drawdown", "calculate_returns", "calculate_sharpe_ratio",
        "calculate_total_return", "calculate_volatility",
        "compute_cumulative_returns", "compute_drawdown_series",
    }
    if name in _metrics:
        from . import metrics
        return getattr(metrics, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BacktestEngine",
    "PortfolioBacktestEngine",
    "PortfolioBacktestResult",
    "PerformanceReporter",
    "calculate_returns",
    "compute_cumulative_returns",
    "compute_drawdown_series",
    "calculate_total_return",
    "calculate_annualized_return",
    "calculate_volatility",
    "calculate_sharpe_ratio",
    "calculate_max_drawdown",
    "calculate_calmar_ratio",
]

