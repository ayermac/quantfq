"""Universe providers for stock screening."""

from abc import ABC, abstractmethod
from typing import List, Optional

import pandas as pd


class UniverseProvider(ABC):
    """Abstract base class for stock universe providers."""

    @abstractmethod
    def get_symbols(
        self,
        exchanges: Optional[List[str]] = None,
        industries: Optional[List[str]] = None,
        min_market_cap: Optional[float] = None,
        max_market_cap: Optional[float] = None,
    ) -> pd.DataFrame:
        """Return a DataFrame with at least 'symbol' and 'name' columns."""
        pass


class AkshareUniverseProvider(UniverseProvider):
    """Fetch A-share stock universe via akshare."""

    def get_symbols(
        self,
        exchanges: Optional[List[str]] = None,
        industries: Optional[List[str]] = None,
        min_market_cap: Optional[float] = None,
        max_market_cap: Optional[float] = None,
    ) -> pd.DataFrame:
        import akshare as ak

        frames: List[pd.DataFrame] = []
        exchanges = exchanges or ["沪深A股"]

        for exchange in exchanges:
            try:
                df = ak.stock_zh_a_spot_em()
                if df is not None and not df.empty:
                    frames.append(df)
            except Exception:
                continue

        if not frames:
            return pd.DataFrame(columns=["symbol", "name"])

        result = pd.concat(frames, ignore_index=True)

        # Normalize column names
        col_map = {}
        for col in result.columns:
            if "代码" in col:
                col_map[col] = "symbol"
            elif "名称" in col:
                col_map[col] = "name"
            elif "总市值" in col:
                col_map[col] = "market_cap"
            elif "行业" in col or "板块" in col:
                col_map[col] = "industry"
        result = result.rename(columns=col_map)

        if "symbol" not in result.columns or "name" not in result.columns:
            return pd.DataFrame(columns=["symbol", "name"])

        # Apply filters
        if industries and "industry" in result.columns:
            result = result[result["industry"].isin(industries)]

        if "market_cap" in result.columns:
            result["market_cap"] = pd.to_numeric(result["market_cap"], errors="coerce")
            if min_market_cap is not None:
                result = result[result["market_cap"] >= min_market_cap]
            if max_market_cap is not None:
                result = result[result["market_cap"] <= max_market_cap]

        return result[["symbol", "name"]].reset_index(drop=True)
