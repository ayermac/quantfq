"""Random search parameter optimizer."""

import logging
import random
from typing import Any, Callable, Dict, List, Optional

from .base import OptReport, OptResult, Optimizer

logger = logging.getLogger(__name__)


class RandomSearchOptimizer(Optimizer):
    """Random search over parameter distributions."""

    def __init__(
        self,
        engine_factory: Callable[..., Any],
        strategy_factory: Callable[..., Any],
        param_distributions: Dict[str, List[Any]],
        n_iter: int = 100,
        metric: str = "sharpe_ratio",
        seed: Optional[int] = None,
    ) -> None:
        super().__init__(engine_factory, strategy_factory, metric)
        self.param_distributions = param_distributions
        self.n_iter = n_iter
        self.seed = seed

    def _sample_params(self) -> Dict[str, Any]:
        """Sample one parameter combination from distributions."""
        params = {}
        for key, values in self.param_distributions.items():
            if isinstance(values, list):
                params[key] = random.choice(values)
            else:
                params[key] = values
        return params

    def run(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> OptReport:
        """Run random search optimization."""
        if self.seed is not None:
            random.seed(self.seed)

        logger.info(f"Random search: {self.n_iter} iterations for {symbol}")

        report = OptReport(metric_name=self.metric)

        for i in range(self.n_iter):
            params = self._sample_params()
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
                logger.debug(f"  [{i+1}/{self.n_iter}] {params} -> {self.metric}={value:.4f}")
            except Exception as e:
                logger.warning(f"  [{i+1}/{self.n_iter}] Failed with {params}: {e}")

        logger.info(f"Random search complete: {len(report.results)} successful runs")
        return report
