"""Stock screener engine."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from ..data.fetcher import DataFetcher
from .filters import Filter
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
    ) -> None:
        self.universe = universe_provider
        self.filters = filters
        self.fetcher = data_fetcher or DataFetcher(source="yahoo")

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
                        filter_results[f.name] = f.apply(data)
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
