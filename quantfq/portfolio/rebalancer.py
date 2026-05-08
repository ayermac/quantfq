"""Portfolio rebalancing strategies."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional

from .portfolio import Portfolio


class Rebalancer(ABC):
    """Abstract base class for rebalancing strategies."""

    @abstractmethod
    def should_rebalance(self, current_date: datetime, portfolio: Portfolio) -> bool:
        """Check if rebalancing should be triggered."""
        pass

    @abstractmethod
    def compute_trades(
        self,
        portfolio: Portfolio,
        target_weights: Dict[str, float],
        current_prices: Dict[str, float],
    ) -> Dict[str, float]:
        """Compute required position changes to reach target weights."""
        pass


class PeriodicRebalancer(Rebalancer):
    """Rebalance at fixed intervals (weekly, monthly, quarterly)."""

    def __init__(self, frequency: str = "monthly") -> None:
        self.frequency = frequency
        self._last_rebalance: Optional[datetime] = None

    def should_rebalance(self, current_date: datetime, portfolio: Portfolio) -> bool:
        if self._last_rebalance is None:
            return True

        delta = current_date - self._last_rebalance
        if self.frequency == "weekly":
            return delta.days >= 7
        elif self.frequency == "monthly":
            return delta.days >= 30
        elif self.frequency == "quarterly":
            return delta.days >= 90
        return False

    def compute_trades(
        self,
        portfolio: Portfolio,
        target_weights: Dict[str, float],
        current_prices: Dict[str, float],
    ) -> Dict[str, float]:
        total_value = portfolio.total_value
        changes: Dict[str, float] = {}

        for symbol, weight in target_weights.items():
            target_value = total_value * weight
            current_value = portfolio.positions.get(symbol, None)
            current_val = current_value.market_value if current_value else 0
            price = current_prices.get(symbol, 0)
            if price > 0:
                shares_to_trade = (target_value - current_val) / price
                if abs(shares_to_trade) > 0:
                    changes[symbol] = shares_to_trade

        self._last_rebalance = datetime.now()
        return changes


class ThresholdRebalancer(Rebalancer):
    """Rebalance when any position drifts beyond a threshold."""

    def __init__(self, threshold: float = 0.05) -> None:
        self.threshold = threshold  # e.g., 0.05 = 5% drift

    def should_rebalance(self, current_date: datetime, portfolio: Portfolio) -> bool:
        # Always check — the threshold logic is in compute_trades
        return True

    def compute_trades(
        self,
        portfolio: Portfolio,
        target_weights: Dict[str, float],
        current_prices: Dict[str, float],
    ) -> Dict[str, float]:
        total_value = portfolio.total_value
        if total_value == 0:
            return {}

        needs_rebalance = False
        for symbol, weight in target_weights.items():
            pos = portfolio.positions.get(symbol)
            current_weight = (pos.market_value / total_value) if pos else 0
            if abs(current_weight - weight) > self.threshold:
                needs_rebalance = True
                break

        if not needs_rebalance:
            return {}

        changes: Dict[str, float] = {}
        for symbol, weight in target_weights.items():
            target_value = total_value * weight
            pos = portfolio.positions.get(symbol)
            current_val = pos.market_value if pos else 0
            price = current_prices.get(symbol, 0)
            if price > 0:
                shares_to_trade = (target_value - current_val) / price
                if abs(shares_to_trade) > 0:
                    changes[symbol] = shares_to_trade

        return changes
