"""Capital allocation strategies for portfolio management."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class Allocator(ABC):
    """Abstract base class for capital allocation."""

    @abstractmethod
    def allocate(
        self,
        total_capital: float,
        symbols: List[str],
        current_prices: Dict[str, float],
    ) -> Dict[str, float]:
        """Return allocation amounts per symbol."""
        pass


class EqualWeightAllocator(Allocator):
    """Allocate equal capital to each symbol."""

    def allocate(
        self,
        total_capital: float,
        symbols: List[str],
        current_prices: Dict[str, float],
    ) -> Dict[str, float]:
        if not symbols:
            return {}
        per_symbol = total_capital / len(symbols)
        return {s: per_symbol for s in symbols}


class MarketCapAllocator(Allocator):
    """Allocate proportional to market capitalization."""

    def __init__(self, market_caps: Optional[Dict[str, float]] = None) -> None:
        self.market_caps = market_caps or {}

    def allocate(
        self,
        total_capital: float,
        symbols: List[str],
        current_prices: Dict[str, float],
    ) -> Dict[str, float]:
        caps = {s: self.market_caps.get(s, 0) for s in symbols if s in self.market_caps}
        if not caps or sum(caps.values()) == 0:
            # Fallback to equal weight
            return EqualWeightAllocator().allocate(total_capital, symbols, current_prices)

        total_cap = sum(caps.values())
        return {s: total_capital * (c / total_cap) for s, c in caps.items()}


class CustomWeightAllocator(Allocator):
    """Allocate based on user-defined weights."""

    def __init__(self, weights: Dict[str, float]) -> None:
        self.weights = weights

    def allocate(
        self,
        total_capital: float,
        symbols: List[str],
        current_prices: Dict[str, float],
    ) -> Dict[str, float]:
        relevant = {s: self.weights.get(s, 0) for s in symbols}
        total_weight = sum(relevant.values())
        if total_weight == 0:
            return EqualWeightAllocator().allocate(total_capital, symbols, current_prices)

        return {s: total_capital * (w / total_weight) for s, w in relevant.items()}
