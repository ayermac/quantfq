"""Walk-forward optimization to prevent overfitting."""

import logging
from typing import Any, Callable, Dict, List

import pandas as pd

from .base import OptReport, OptResult, Optimizer, ParamGrid

logger = logging.getLogger(__name__)


class WalkForwardOptimizer(Optimizer):
    """Walk-forward analysis: optimize on in-sample, validate on out-of-sample."""

    def __init__(
        self,
        engine_factory: Callable[..., Any],
        strategy_factory: Callable[..., Any],
        param_grid: ParamGrid,
        metric: str = "sharpe_ratio",
        in_sample_ratio: float = 0.7,
        n_splits: int = 3,
    ) -> None:
        super().__init__(engine_factory, strategy_factory, metric)
        self.param_grid = param_grid
        self.in_sample_ratio = in_sample_ratio
        self.n_splits = n_splits

    def run(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> OptReport:
        """Run walk-forward optimization."""
        all_dates = pd.date_range(start=start_date, end=end_date, freq="B")
        if len(all_dates) < 10:
            logger.error("Date range too short for walk-forward analysis")
            return OptReport(metric_name=self.metric)

        # Create expanding window splits
        split_size = len(all_dates) // (self.n_splits + 1)
        combos = self.param_grid.combinations()
        logger.info(
            f"Walk-forward: {self.n_splits} splits, {len(combos)} param combos"
        )

        report = OptReport(metric_name=self.metric)
        oos_results: List[Dict[str, Any]] = []

        for split_idx in range(self.n_splits):
            # Define in-sample and out-of-sample windows
            is_end_idx = split_size * (split_idx + 1)
            oos_end_idx = min(is_end_idx + split_size, len(all_dates))

            is_start = all_dates[0].strftime("%Y-%m-%d")
            is_end = all_dates[is_end_idx].strftime("%Y-%m-%d")
            oos_start = all_dates[is_end_idx].strftime("%Y-%m-%d")
            oos_end = all_dates[oos_end_idx - 1].strftime("%Y-%m-%d")

            logger.info(f"  Split {split_idx+1}: IS=[{is_start}, {is_end}], OOS=[{oos_start}, {oos_end}]")

            # Optimize on in-sample
            best_params = None
            best_metric = float("-inf")

            for params in combos:
                try:
                    engine = self.engine_factory(**params)
                    engine.set_parameters(symbol, is_start, is_end)
                    engine.load_data()
                    engine.add_strategy(self.strategy_factory())
                    engine.run_backtest()
                    _, metrics = engine.calculate_metrics()
                    value = self._extract_metric(metrics)
                    if value > best_metric:
                        best_metric = value
                        best_params = params
                except Exception:
                    continue

            if best_params is None:
                logger.warning(f"  Split {split_idx+1}: no valid params found")
                continue

            # Validate on out-of-sample
            try:
                engine = self.engine_factory(**best_params)
                engine.set_parameters(symbol, oos_start, oos_end)
                engine.load_data()
                engine.add_strategy(self.strategy_factory())
                engine.run_backtest()
                _, oos_metrics = engine.calculate_metrics()
                oos_value = self._extract_metric(oos_metrics)

                result = OptResult(
                    params={**best_params, "_split": split_idx + 1, "_is_metric": best_metric},
                    metrics=oos_metrics,
                    metric_value=oos_value,
                )
                report.results.append(result)
                logger.info(
                    f"  Split {split_idx+1}: best IS={best_metric:.4f}, OOS={oos_value:.4f}, params={best_params}"
                )
            except Exception as e:
                logger.warning(f"  Split {split_idx+1}: OOS validation failed: {e}")

        logger.info(f"Walk-forward complete: {len(report.results)} splits validated")
        return report
