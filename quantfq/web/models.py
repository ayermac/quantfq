"""Pydantic models for the web API."""

from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel
except ImportError:
    # Minimal fallback if pydantic not installed
    class BaseModel:
        pass


class BacktestRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    strategy: str = "sma_crossover"
    params: Dict[str, Any] = {}
    initial_capital: float = 1000000
    commission: float = 0.001


class ScreenerRequest(BaseModel):
    start_date: str
    end_date: str
    filters: List[Dict[str, Any]] = []
    exchanges: Optional[List[str]] = None
    max_workers: int = 4


class PortfolioRequest(BaseModel):
    symbols: List[str]
    start_date: str
    end_date: str
    strategy: str = "sma_crossover"
    params: Dict[str, Any] = {}
    initial_capital: float = 1000000
    allocation: str = "equal_weight"


class OptimizerRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    strategy: str = "sma_crossover"
    param_grid: Dict[str, List[Any]] = {}
    metric: str = "sharpe_ratio"
    method: str = "grid"  # grid, random, walk_forward
    n_iter: int = 100
