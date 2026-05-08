"""Stock screener engine."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from ..data.fetcher import DataFetcher
from .filters import BoardFilter, Filter, STFilter
from .universe import UniverseProvider

logger = logging.getLogger(__name__)


@dataclass
class ScreenerResult:
    """Result of a screening run."""

    candidates: pd.DataFrame
    details: Dict[str, Dict[str, bool]] = field(default_factory=dict)

    @property
    def symbols(self) -> List[str]:
        return self.candidates["symbol"].tolist() if not self.candidates.empty else []

    def summary(self) -> str:
        lines = [f"Screener found {len(self.candidates)} candidates:"]
        for _, row in self.candidates.iterrows():
            sym = row["symbol"]
            name = row.get("name", "")
            passed = self.details.get(sym, {})
            filters_str = ", ".join(k for k, v in passed.items() if v)
            lines.append(f"  {sym} ({name}) — passed: {filters_str}")
        return "\n".join(lines)


class Screener:
    """Scan a stock universe and filter by technical/fundamental conditions."""

    def __init__(
        self,
        universe_provider: UniverseProvider,
        filters: List[Filter],
        data_fetcher: Optional[DataFetcher] = None,
        data_provider=None,
    ) -> None:
        self.universe = universe_provider
        self.filters = filters
        self.fetcher = data_fetcher or DataFetcher(source="yahoo")
        self.provider = data_provider

    def run(
        self,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        max_workers: int = 4,
        max_stocks: int = 0,
        exchanges: Optional[List[str]] = None,
        industries: Optional[List[str]] = None,
    ) -> ScreenerResult:
        """Run the screener across the universe."""
        has_board_filter = any(isinstance(f, BoardFilter) for f in self.filters)
        has_st_filter = any(isinstance(f, STFilter) for f in self.filters)
        need_money_flow = any(
            hasattr(f, "days") and hasattr(f, "min_total") for f in self.filters
        )

        if self.provider and (has_board_filter or has_st_filter):
            return self._run_with_snapshot(
                start_date, end_date, max_workers, max_stocks, need_money_flow
            )

        return self._run_legacy(
            start_date, end_date, interval, max_workers, max_stocks,
            exchanges, industries,
        )

    def _run_with_snapshot(
        self,
        start_date: str,
        end_date: str,
        max_workers: int,
        max_stocks: int,
        need_money_flow: bool,
    ) -> ScreenerResult:
        """Fast path: use akshare snapshot for pre-filtering."""
        from datetime import datetime, timedelta

        logger.info("Using snapshot-based fast screening")

        # Auto-extend start_date for OHLCV to ensure enough lookback data
        max_lookback = 0
        for f in self.filters:
            if hasattr(f, "lookback_days"):
                max_lookback = max(max_lookback, f.lookback_days)
            if hasattr(f, "params") and isinstance(f.params, dict):
                max_lookback = max(max_lookback, f.params.get("period", 0))

        if max_lookback > 0:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                data_start = end_dt - timedelta(days=int(max_lookback * 2.5))
                data_start_str = data_start.strftime("%Y-%m-%d")
                logger.info(f"Extended OHLCV start to {data_start_str} for {max_lookback}-day lookback")
            except ValueError:
                data_start_str = start_date
        else:
            data_start_str = start_date
        snapshot = self.provider.get_snapshot()
        if snapshot.empty:
            logger.warning("Snapshot is empty")
            return ScreenerResult(candidates=pd.DataFrame())

        pre_filters = [f for f in self.filters if isinstance(f, (BoardFilter, STFilter))]
        post_filters = [f for f in self.filters if not isinstance(f, (BoardFilter, STFilter))]

        mask = pd.Series(True, index=snapshot.index)
        for f in pre_filters:
            for i, row in snapshot.iterrows():
                sym = str(row.get("symbol", ""))
                nm = str(row.get("name", ""))
                if not f.apply(pd.DataFrame(), symbol=sym, name=nm):
                    mask.iloc[i] = False

        filtered = snapshot[mask].reset_index(drop=True)
        if max_stocks > 0:
            filtered = filtered.head(max_stocks)
        logger.info(f"Pre-filter: {len(filtered)} stocks from {len(snapshot)} total")

        candidates: List[Dict] = []
        details: Dict[str, Dict[str, bool]] = {}

        def _check_symbol(symbol: str, name: str) -> Optional[Dict]:
            try:
                data = self.provider.get_ohlcv(symbol, data_start_str, end_date)
                if data.empty:
                    return None

                money_flow = None
                if need_money_flow:
                    money_flow = self.provider.get_money_flow(symbol)

                filter_results = {}
                for f in pre_filters:
                    filter_results[f.name] = True

                for f in post_filters:
                    try:
                        filter_results[f.name] = f.apply(
                            data, symbol=symbol, name=name, money_flow=money_flow,
                        )
                    except Exception:
                        filter_results[f.name] = False

                if all(filter_results.values()):
                    return {
                        "symbol": symbol,
                        "name": name,
                        "filter_results": filter_results,
                    }
            except Exception as e:
                logger.debug(f"Failed to screen {symbol}: {e}")
            return None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _check_symbol, str(row.get("symbol", "")), str(row.get("name", ""))
                ): str(row.get("symbol", ""))
                for _, row in filtered.iterrows()
            }
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    sym = result["symbol"]
                    candidates.append({"symbol": sym, "name": result["name"]})
                    details[sym] = result["filter_results"]
                    logger.info(f"Candidate found: {sym} ({result['name']})")

        result_df = pd.DataFrame(candidates)
        logger.info(f"Screening complete: {len(result_df)} candidates")
        return ScreenerResult(candidates=result_df, details=details)

    def _run_legacy(
        self,
        start_date: str,
        end_date: str,
        interval: str,
        max_workers: int,
        max_stocks: int,
        exchanges: Optional[List[str]],
        industries: Optional[List[str]],
    ) -> ScreenerResult:
        """Legacy path: use universe provider + data fetcher."""
        universe_df = self.universe.get_symbols(
            exchanges=exchanges, industries=industries
        )
        if universe_df.empty:
            logger.warning("Universe is empty, nothing to screen")
            return ScreenerResult(candidates=pd.DataFrame())

        if max_stocks > 0:
            universe_df = universe_df.head(max_stocks)
            logger.info(f"Limiting scan to {max_stocks} stocks")

        symbols = universe_df["symbol"].tolist()
        logger.info(f"Screening {len(symbols)} symbols with {len(self.filters)} filters")

        candidates: List[Dict] = []
        details: Dict[str, Dict[str, bool]] = {}

        def _check_symbol(symbol: str, name: str) -> Optional[Dict]:
            try:
                data = self.fetcher.fetch_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    interval=interval,
                    clean=True,
                )
                if data.empty:
                    return None

                filter_results = {}
                for f in self.filters:
                    try:
                        filter_results[f.name] = f.apply(
                            data, symbol=symbol, name=name,
                        )
                    except Exception:
                        filter_results[f.name] = False

                if all(filter_results.values()):
                    return {
                        "symbol": symbol,
                        "name": name,
                        "filter_results": filter_results,
                    }
            except Exception as e:
                logger.debug(f"Failed to screen {symbol}: {e}")
            return None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_check_symbol, row["symbol"], row["name"]): row["symbol"]
                for _, row in universe_df.iterrows()
            }
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    sym = result["symbol"]
                    candidates.append({"symbol": sym, "name": result["name"]})
                    details[sym] = result["filter_results"]
                    logger.info(f"Candidate found: {sym} ({result['name']})")

        result_df = pd.DataFrame(candidates)
        logger.info(f"Screening complete: {len(result_df)} candidates from {len(symbols)} symbols")
        return ScreenerResult(candidates=result_df, details=details)
