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
    def apply(self, data: pd.DataFrame, **kwargs) -> bool:
        """Return True if the stock passes the filter.

        Args:
            data: OHLCV DataFrame
            **kwargs: Optional context - symbol, name, money_flow, etc.
        """
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

    def apply(self, data: pd.DataFrame, **kwargs) -> bool:
        if data.empty or "Close" not in data.columns:
            return False

        close = data["Close"].astype(float)

        if self.indicator == "sma":
            period = self.params.get("period", 20)
            ma = self._ti.sma(close, period)
            return self._compare(close.iloc[-1], ma.iloc[-1])
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

    def apply(self, data: pd.DataFrame, **kwargs) -> bool:
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

    def apply(self, data: pd.DataFrame, **kwargs) -> bool:
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

    def apply(self, data: pd.DataFrame, **kwargs) -> bool:
        return all(f.apply(data, **kwargs) for f in self.filters)


class OrFilter(Filter):
    """Logical OR组合多个筛选条件."""

    def __init__(self, *filters: Filter) -> None:
        self.filters = list(filters)

    @property
    def name(self) -> str:
        return " OR ".join(f.name for f in self.filters)

    def apply(self, data: pd.DataFrame, **kwargs) -> bool:
        return any(f.apply(data, **kwargs) for f in self.filters)


class BoardFilter(Filter):
    """Filter for main board stocks only (exclude ChiNext 300, STAR 688, BSE 8xx)."""

    def __init__(self, boards=("沪主板", "深主板")) -> None:
        self._name = f"board_{'_'.join(boards)}"
        self.boards = boards

    @property
    def name(self) -> str:
        return self._name

    def apply(self, data: pd.DataFrame, **kwargs) -> bool:
        symbol = kwargs.get("symbol", "")
        if "沪主板" in self.boards and symbol.startswith("60"):
            return True
        if "深主板" in self.boards and symbol.startswith("00"):
            return True
        return False


class STFilter(Filter):
    """Exclude ST, ST*, and delisted stocks."""

    @property
    def name(self) -> str:
        return "non_st"

    def apply(self, data: pd.DataFrame, **kwargs) -> bool:
        name = kwargs.get("name", "")
        upper = name.upper()
        return "ST" not in upper and "退" not in name


class LimitUpFilter(Filter):
    """Detect limit-up related conditions.

    Args:
        lookback_days: Number of days to look back (default 10)
        require_in_period: Require at least one limit-up in period (default True)
        exclude_consecutive: Exclude consecutive limit-up days (default True)
        exclude_current: Exclude stocks currently at limit-up (default True)
        limit_pct: Limit-up threshold percentage (default 9.8 for 10% board)
    """

    def __init__(
        self,
        lookback_days: int = 10,
        require_in_period: bool = True,
        exclude_consecutive: bool = True,
        exclude_current: bool = True,
        limit_pct: float = 9.8,
    ) -> None:
        self._name = (
            f"limit_up_{lookback_days}d"
            f"{'_req' if require_in_period else ''}"
            f"{'_no_consec' if exclude_consecutive else ''}"
            f"{'_no_current' if exclude_current else ''}"
        )
        self.lookback_days = lookback_days
        self.require_in_period = require_in_period
        self.exclude_consecutive = exclude_consecutive
        self.exclude_current = exclude_current
        self.limit_pct = limit_pct

    @property
    def name(self) -> str:
        return self._name

    def apply(self, data: pd.DataFrame, **kwargs) -> bool:
        if data.empty or len(data) < 2 or "Close" not in data.columns:
            return False

        close = data["Close"].astype(float)
        change_pct = close.pct_change() * 100

        # Look at last N days (excluding today for lookback, today for current check)
        lookback = change_pct.iloc[-self.lookback_days - 1:-1] if len(change_pct) > self.lookback_days else change_pct.iloc[:-1]
        is_limit_up = lookback >= self.limit_pct

        # Condition 3: Must have at least one limit-up in lookback period
        if self.require_in_period and not is_limit_up.any():
            return False

        # Condition 4: Exclude if the last limit-up is still in a consecutive streak
        # (i.e. the most recent limit-up was NOT followed by a pullback day)
        if self.exclude_consecutive and self.require_in_period:
            limit_indices = is_limit_up[is_limit_up].index
            if len(limit_indices) > 0:
                last_limit_idx = limit_indices[-1]
                pos = lookback.index.get_loc(last_limit_idx)
                if pos + 1 < len(lookback) and lookback.iloc[pos + 1] >= self.limit_pct:
                    return False

        # Condition 7: Exclude current limit-up
        if self.exclude_current:
            current_change = change_pct.iloc[-1]
            if pd.notna(current_change) and current_change >= self.limit_pct:
                return False

        return True


class MoneyFlowFilter(Filter):
    """Filter for consecutive days of net large-order capital inflow.

    Args:
        days: Number of consecutive days with net inflow (default 3)
        min_total: Minimum cumulative net inflow in wan yuan (default 3000)
    """

    def __init__(self, days: int = 3, min_total: float = 3000) -> None:
        self._name = f"money_flow_{days}d_{min_total}w"
        self.days = days
        self.min_total = min_total

    @property
    def name(self) -> str:
        return self._name

    def apply(self, data: pd.DataFrame, **kwargs) -> bool:
        money_flow = kwargs.get("money_flow")
        if money_flow is None or money_flow.empty:
            return False

        # Calculate total large-order net flow (super_large + large)
        has_super = "super_large_net" in money_flow.columns
        has_large = "large_net" in money_flow.columns

        if not has_super and not has_large:
            return False

        if has_super and has_large:
            total_net = money_flow["super_large_net"].fillna(0) + money_flow["large_net"].fillna(0)
        elif has_super:
            total_net = money_flow["super_large_net"].fillna(0)
        else:
            total_net = money_flow["large_net"].fillna(0)

        # Check last N days all positive
        recent = total_net.tail(self.days)
        if len(recent) < self.days:
            return False

        if not (recent > 0).all():
            return False

        # Check cumulative total exceeds threshold
        cumulative = recent.sum()
        return cumulative >= self.min_total * 10000
