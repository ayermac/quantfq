"""Screening filters for stock selection."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import pandas as pd

from ..indicators.technical import TechnicalIndicators


class Filter(ABC):
    """Abstract base class for screening filters."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def apply(self, data: pd.DataFrame) -> bool:
        """Return True if the stock passes the filter."""
        pass


class TechnicalFilter(Filter):
    """Filter based on technical indicators."""

    def __init__(
        self,
        indicator: str,
        condition: str,
        value: float,
        **kwargs: Any,
    ) -> None:
        self._name = f"tech_{indicator}_{condition}_{value}"
        self.indicator = indicator
        self.condition = condition
        self.value = value
        self.params = kwargs
        self._ti = TechnicalIndicators()

    @property
    def name(self) -> str:
        return self._name

    def apply(self, data: pd.DataFrame) -> bool:
        if data.empty or "Close" not in data.columns:
            return False

        close = data["Close"].astype(float)

        if self.indicator == "sma":
            period = self.params.get("period", 20)
            ma = self._ti.sma(close, period)
            return self._compare(ma.iloc[-1], close.iloc[-1])
        elif self.indicator == "rsi":
            period = self.params.get("period", 14)
            rsi = self._ti.rsi(close, period)
            return self._compare(rsi.iloc[-1], self.value)
        elif self.indicator == "boll":
            period = self.params.get("period", 20)
            std_dev = self.params.get("std_dev", 2)
            bands = self._ti.boll(close, period, std_dev)
            upper = bands["upper"].iloc[-1]
            lower = bands["lower"].iloc[-1]
            last_price = close.iloc[-1]
            if self.condition == "above_upper":
                return last_price > upper
            elif self.condition == "below_lower":
                return last_price < lower
            elif self.condition == "in_band":
                return lower <= last_price <= upper
        return False

    def _compare(self, actual: float, reference: float) -> bool:
        import math

        if math.isnan(actual) or math.isnan(reference):
            return False
        if self.condition == "gt":
            return actual > reference
        elif self.condition == "lt":
            return actual < reference
        elif self.condition == "gte":
            return actual >= reference
        elif self.condition == "lte":
            return actual <= reference
        elif self.condition == "cross_above":
            return actual > reference
        elif self.condition == "cross_below":
            return actual < reference
        return False


class FundamentalFilter(Filter):
    """Filter based on fundamental indicators."""

    def __init__(self, metric: str, condition: str, value: float) -> None:
        self._name = f"fund_{metric}_{condition}_{value}"
        self.metric = metric
        self.condition = condition
        self.value = value

    @property
    def name(self) -> str:
        return self._name

    def apply(self, data: pd.DataFrame) -> bool:
        # Fundamental data should be pre-loaded as extra columns
        if self.metric not in data.columns:
            return False

        val = pd.to_numeric(data[self.metric].iloc[-1], errors="coerce")
        if pd.isna(val):
            return False

        if self.condition == "gt":
            return val > self.value
        elif self.condition == "lt":
            return val < self.value
        elif self.condition == "gte":
            return val >= self.value
        elif self.condition == "lte":
            return val <= self.value
        elif self.condition == "eq":
            return abs(val - self.value) < 1e-6
        return False


class PriceFilter(Filter):
    """Filter based on price and volume conditions."""

    def __init__(
        self,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_volume: Optional[int] = None,
        max_volume: Optional[int] = None,
        min_change_pct: Optional[float] = None,
        max_change_pct: Optional[float] = None,
    ) -> None:
        self._name = "price_filter"
        self.min_price = min_price
        self.max_price = max_price
        self.min_volume = min_volume
        self.max_volume = max_volume
        self.min_change_pct = min_change_pct
        self.max_change_pct = max_change_pct

    @property
    def name(self) -> str:
        return self._name

    def apply(self, data: pd.DataFrame) -> bool:
        if data.empty:
            return False

        last = data.iloc[-1]
        close = float(last.get("Close", 0))
        volume = int(last.get("Volume", 0))

        if self.min_price is not None and close < self.min_price:
            return False
        if self.max_price is not None and close > self.max_price:
            return False
        if self.min_volume is not None and volume < self.min_volume:
            return False
        if self.max_volume is not None and volume > self.max_volume:
            return False

        if (self.min_change_pct is not None or self.max_change_pct is not None) and len(data) > 1:
            prev_close = float(data.iloc[-2]["Close"])
            if prev_close > 0:
                change_pct = (close - prev_close) / prev_close * 100
                if self.min_change_pct is not None and change_pct < self.min_change_pct:
                    return False
                if self.max_change_pct is not None and change_pct > self.max_change_pct:
                    return False

        return True


class AndFilter(Filter):
    """Logical AND组合多个筛选条件."""

    def __init__(self, *filters: Filter) -> None:
        self.filters = list(filters)

    @property
    def name(self) -> str:
        return " AND ".join(f.name for f in self.filters)

    def apply(self, data: pd.DataFrame) -> bool:
        return all(f.apply(data) for f in self.filters)


class OrFilter(Filter):
    """Logical OR组合多个筛选条件."""

    def __init__(self, *filters: Filter) -> None:
        self.filters = list(filters)

    @property
    def name(self) -> str:
        return " OR ".join(f.name for f in self.filters)

    def apply(self, data: pd.DataFrame) -> bool:
        return any(f.apply(data) for f in self.filters)
