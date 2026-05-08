"""Portfolio-level backtesting engine."""

import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..data.fetcher import DataFetcher
from ..portfolio.allocator import Allocator, EqualWeightAllocator
from ..portfolio.portfolio import Portfolio
from ..portfolio.rebalancer import Rebalancer
from ..strategy.base import BaseStrategy

logger = logging.getLogger(__name__)


@dataclass
class PortfolioBacktestResult:
    """Results from a portfolio backtest."""

    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)
    trades: pd.DataFrame = field(default_factory=pd.DataFrame)
    per_symbol_metrics: Dict[str, Dict] = field(default_factory=dict)
    portfolio_metrics: Dict[str, float] = field(default_factory=dict)
    correlation_matrix: Optional[pd.DataFrame] = None


class PortfolioBacktestEngine:
    """Run strategies across multiple symbols with portfolio-level tracking."""

    def __init__(
        self,
        initial_capital: float = 1000000.0,
        commission: float = 0.001,
        slippage: float = 0.001,
        data_source: str = "yahoo",
        allocator: Optional[Allocator] = None,
        rebalancer: Optional[Rebalancer] = None,
    ) -> None:
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.fetcher = DataFetcher(source=data_source)
        self.allocator = allocator or EqualWeightAllocator()
        self.rebalancer = rebalancer
        self._strategies: Dict[str, BaseStrategy] = {}
        self._symbols: List[str] = []

    def add_strategy(self, strategy: BaseStrategy, symbols: List[str]) -> None:
        """Bind a strategy to a list of symbols."""
        for sym in symbols:
            self._strategies[sym] = strategy
            if sym not in self._symbols:
                self._symbols.append(sym)

    def run_backtest(
        self,
        start_date: str,
        end_date: str,
        interval: str = "1d",
    ) -> PortfolioBacktestResult:
        """Execute the portfolio backtest."""
        logger.info(
            f"Portfolio backtest: {len(self._symbols)} symbols, "
            f"capital={self.initial_capital:,.0f}"
        )

        # Fetch all data
        all_data: Dict[str, pd.DataFrame] = {}
        for symbol in self._symbols:
            try:
                data = self.fetcher.fetch_data(
                    symbol=symbol, start_date=start_date, end_date=end_date,
                    interval=interval, clean=True
                )
                if not data.empty:
                    all_data[symbol] = data
            except Exception as e:
                logger.warning(f"Failed to fetch {symbol}: {e}")

        if not all_data:
            logger.error("No data fetched for any symbol")
            return PortfolioBacktestResult()

        # Generate signals for each symbol
        all_signals: Dict[str, pd.Series] = {}
        for symbol, data in all_data.items():
            strategy = self._strategies.get(symbol)
            if strategy:
                try:
                    result = strategy.run(data)
                    all_signals[symbol] = result["signals"]
                except Exception as e:
                    logger.warning(f"Strategy failed for {symbol}: {e}")

        # Align all data to common dates
        common_dates = None
        for symbol in all_signals:
            dates = all_data[symbol].index
            common_dates = dates if common_dates is None else common_dates.intersection(dates)

        if common_dates is None or len(common_dates) == 0:
            return PortfolioBacktestResult()

        # Run simulation
        portfolio = Portfolio(
            initial_cash=self.initial_capital, commission_rate=self.commission
        )
        equity_records = []
        all_trades = []

        for date in common_dates:
            # Get current prices
            prices: Dict[str, float] = {}
            for symbol in all_data:
                if date in all_data[symbol].index:
                    prices[symbol] = float(all_data[symbol].loc[date, "Close"])

            # Check signals and execute trades
            for symbol, signals in all_signals.items():
                if date in signals.index:
                    signal = int(signals.loc[date])
                    price = prices.get(symbol, 0)
                    if price <= 0:
                        continue

                    # Apply slippage
                    if signal == 1:
                        price *= (1 + self.slippage)
                    elif signal == -1:
                        price *= (1 - self.slippage)

                    if signal == 1 and symbol not in portfolio.positions:
                        # Buy: allocate capital
                        allocation = self.allocator.allocate(
                            portfolio.cash, [symbol], prices
                        )
                        buy_amount = allocation.get(symbol, 0)
                        qty = int(buy_amount / price)
                        if qty > 0:
                            try:
                                trade = portfolio.buy(symbol, qty, price)
                                all_trades.append({
                                    "date": date, "symbol": symbol,
                                    "side": "buy", "quantity": qty,
                                    "price": price, "commission": trade.commission,
                                })
                            except ValueError:
                                pass

                    elif signal == -1 and symbol in portfolio.positions:
                        qty = portfolio.positions[symbol].quantity
                        if qty > 0:
                            try:
                                trade = portfolio.sell(symbol, qty, price)
                                all_trades.append({
                                    "date": date, "symbol": symbol,
                                    "side": "sell", "quantity": qty,
                                    "price": price, "commission": trade.commission,
                                })
                            except ValueError:
                                pass

            # Rebalance check
            if self.rebalancer and self.rebalancer.should_rebalance(date, portfolio):
                weights = {s: 1.0 / len(self._symbols) for s in self._symbols}
                changes = self.rebalancer.compute_trades(portfolio, weights, prices)
                for symbol, delta_shares in changes.items():
                    price = prices.get(symbol, 0)
                    if price <= 0:
                        continue
                    qty = int(abs(delta_shares))
                    if qty <= 0:
                        continue
                    try:
                        if delta_shares > 0:
                            portfolio.buy(symbol, qty, price * (1 + self.slippage))
                        elif delta_shares < 0 and symbol in portfolio.positions:
                            portfolio.sell(symbol, qty, price * (1 - self.slippage))
                    except ValueError:
                        pass

            # Update prices and record
            portfolio.update_prices(prices)
            snap = portfolio.snapshot()
            snap["date"] = date
            equity_records.append(snap)

        # Build results
        equity_df = pd.DataFrame(equity_records)
        if "date" in equity_df.columns:
            equity_df = equity_df.set_index("date")

        trades_df = pd.DataFrame(all_trades)

        # Per-symbol metrics
        per_symbol: Dict[str, Dict] = {}
        for symbol in all_signals:
            sym_trades = trades_df[trades_df["symbol"] == symbol] if not trades_df.empty else pd.DataFrame()
            buys = sym_trades[sym_trades["side"] == "buy"] if not sym_trades.empty else pd.DataFrame()
            sells = sym_trades[sym_trades["side"] == "sell"] if not sym_trades.empty else pd.DataFrame()
            per_symbol[symbol] = {
                "num_buys": len(buys),
                "num_sells": len(sells),
                "total_commission": sym_trades["commission"].sum() if not sym_trades.empty else 0,
            }

        # Portfolio-level metrics
        if not equity_df.empty and "total_value" in equity_df.columns:
            total_return = (equity_df["total_value"].iloc[-1] / self.initial_capital) - 1
            daily_returns = equity_df["total_value"].pct_change().dropna()
            sharpe = (
                daily_returns.mean() / daily_returns.std() * (252 ** 0.5)
                if len(daily_returns) > 1 and daily_returns.std() > 0
                else 0
            )
            cummax = equity_df["total_value"].cummax()
            drawdown = (equity_df["total_value"] - cummax) / cummax
            max_dd = drawdown.min()

            portfolio_metrics = {
                "total_return": total_return,
                "sharpe_ratio": sharpe,
                "max_drawdown": max_dd,
                "total_trades": len(trades_df),
                "final_value": equity_df["total_value"].iloc[-1],
            }
        else:
            portfolio_metrics = {}

        # Correlation matrix
        corr_matrix = None
        if len(all_data) > 1:
            returns_df = pd.DataFrame({
                sym: data["Close"].pct_change()
                for sym, data in all_data.items()
            }).dropna()
            if not returns_df.empty:
                corr_matrix = returns_df.corr()

        return PortfolioBacktestResult(
            equity_curve=equity_df,
            trades=trades_df,
            per_symbol_metrics=per_symbol,
            portfolio_metrics=portfolio_metrics,
            correlation_matrix=corr_matrix,
        )
