"""Grid search parameter optimizer."""

import logging
from typing import Any, Callable

from .base import OptReport, OptResult, Optimizer, ParamGrid

logger = logging.getLogger(__name__)


class GridSearchOptimizer(Optimizer):
    """Exhaustive grid search over all parameter combinations."""

    def __init__(
        self,
        engine_factory: Callable[..., Any],
        strategy_factory: Callable[..., Any],
        param_grid: ParamGrid,
        metric: str = "sharpe_ratio",
    ) -> None:
        super().__init__(engine_factory, strategy_factory, metric)
        self.param_grid = param_grid

    def run(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> OptReport:
        """Run grid search optimization."""
        combos = self.param_grid.combinations()
        logger.info(f"Grid search: {len(combos)} combinations for {symbol}")

        report = OptReport(metric_name=self.metric)

        for i, params in enumerate(combos):
            try:
                engine = self.engine_factory(**params)
                engine.set_parameters(symbol, start_date, end_date)
                engine.load_data()
                engine.add_strategy(self.strategy_factory())
                engine.run_backtest()
                _, metrics = engine.calculate_metrics()

                value = self._extract_metric(metrics)
                result = OptResult(params=params, metrics=metrics, metric_value=value)
                report.results.append(result)
                logger.debug(f"  [{i+1}/{len(combos)}] {params} -> {self.metric}={value:.4f}")
            except Exception as e:
                logger.warning(f"  [{i+1}/{len(combos)}] Failed with {params}: {e}")

        logger.info(f"Grid search complete: {len(report.results)} successful runs")
        return report
