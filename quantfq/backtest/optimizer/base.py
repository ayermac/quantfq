"""Base classes for parameter optimization."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from itertools import product
from typing import Any, Callable, Dict, List, Optional

import pandas as pd


@dataclass
class ParamGrid:
    """Define a parameter grid for optimization."""

    params: Dict[str, List[Any]]

    def combinations(self) -> List[Dict[str, Any]]:
        """Generate all parameter combinations."""
        if not self.params:
            return [{}]
        keys = list(self.params.keys())
        values = list(self.params.values())
        return [dict(zip(keys, combo)) for combo in product(*values)]


@dataclass
class OptResult:
    """Result of a single optimization run."""

    params: Dict[str, Any]
    metrics: Dict[str, float]
    metric_value: float

    def __repr__(self) -> str:
        return f"OptResult(params={self.params}, metric={self.metric_value:.4f})"


@dataclass
class OptReport:
    """Aggregated optimization results."""

    results: List[OptResult] = field(default_factory=list)
    metric_name: str = "sharpe_ratio"

    @property
    def best(self) -> Optional[OptResult]:
        if not self.results:
            return None
        return max(self.results, key=lambda r: r.metric_value)

    @property
    def worst(self) -> Optional[OptResult]:
        if not self.results:
            return None
        return min(self.results, key=lambda r: r.metric_value)

    def top_n(self, n: int = 10) -> List[OptResult]:
        return sorted(self.results, key=lambda r: r.metric_value, reverse=True)[:n]

    def to_dataframe(self) -> pd.DataFrame:
        rows = []
        for r in self.results:
            row = {**r.params, self.metric_name: r.metric_value}
            rows.append(row)
        return pd.DataFrame(rows).sort_values(self.metric_name, ascending=False)

    def summary(self) -> str:
        lines = [
            f"Optimization Report ({len(self.results)} runs, metric={self.metric_name}):",
        ]
        if self.best:
            lines.append(f"  Best: {self.best}")
        if self.worst:
            lines.append(f"  Worst: {self.worst}")
        for i, r in enumerate(self.top_n(5)):
            lines.append(f"  #{i+1}: {r}")
        return "\n".join(lines)


class Optimizer(ABC):
    """Abstract base class for parameter optimizers."""

    def __init__(
        self,
        engine_factory: Callable[..., Any],
        strategy_factory: Callable[..., Any],
        metric: str = "sharpe_ratio",
    ) -> None:
        self.engine_factory = engine_factory
        self.strategy_factory = strategy_factory
        self.metric = metric

    @abstractmethod
    def run(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> OptReport:
        """Run optimization and return report."""
        pass

    def _extract_metric(self, metrics: Dict[str, float]) -> float:
        """Extract the target metric, return -inf if missing."""
        return metrics.get(self.metric, float("-inf"))
