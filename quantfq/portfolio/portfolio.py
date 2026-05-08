"""Portfolio management for multi-asset tracking."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd


@dataclass
class PortfolioPosition:
    """Track a single position in the portfolio."""

    symbol: str
    quantity: int = 0
    avg_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0

    def update_market_value(self, current_price: float) -> None:
        self.market_value = self.quantity * current_price
        if self.quantity > 0:
            self.unrealized_pnl = (current_price - self.avg_price) * self.quantity


@dataclass
class PortfolioTrade:
    """Record of a portfolio trade."""

    symbol: str
    side: str  # "buy" or "sell"
    quantity: int
    price: float
    timestamp: datetime = field(default_factory=datetime.now)
    commission: float = 0.0


class Portfolio:
    """Multi-asset portfolio manager."""

    def __init__(self, initial_cash: float = 1000000.0, commission_rate: float = 0.001) -> None:
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.commission_rate = commission_rate
        self.positions: Dict[str, PortfolioPosition] = {}
        self.trades: List[PortfolioTrade] = []
        self.equity_history: List[Dict] = []

    def buy(self, symbol: str, quantity: int, price: float) -> PortfolioTrade:
        """Execute a buy order."""
        cost = quantity * price
        commission = cost * self.commission_rate
        total_cost = cost + commission

        if total_cost > self.cash:
            raise ValueError(
                f"Insufficient cash: need {total_cost:.2f}, have {self.cash:.2f}"
            )

        self.cash -= total_cost

        if symbol in self.positions:
            pos = self.positions[symbol]
            total_qty = pos.quantity + quantity
            pos.avg_price = (pos.avg_price * pos.quantity + price * quantity) / total_qty
            pos.quantity = total_qty
        else:
            self.positions[symbol] = PortfolioPosition(
                symbol=symbol, quantity=quantity, avg_price=price
            )

        trade = PortfolioTrade(
            symbol=symbol, side="buy", quantity=quantity, price=price, commission=commission
        )
        self.trades.append(trade)
        return trade

    def sell(self, symbol: str, quantity: int, price: float) -> PortfolioTrade:
        """Execute a sell order."""
        if symbol not in self.positions or self.positions[symbol].quantity < quantity:
            available = self.positions.get(symbol, PortfolioPosition(symbol)).quantity
            raise ValueError(
                f"Insufficient position: need {quantity}, have {available}"
            )

        proceeds = quantity * price
        commission = proceeds * self.commission_rate
        self.cash += proceeds - commission

        pos = self.positions[symbol]
        pos.quantity -= quantity
        if pos.quantity == 0:
            del self.positions[symbol]

        trade = PortfolioTrade(
            symbol=symbol, side="sell", quantity=quantity, price=price, commission=commission
        )
        self.trades.append(trade)
        return trade

    def update_prices(self, prices: Dict[str, float]) -> None:
        """Update market values for all positions."""
        for symbol, pos in self.positions.items():
            if symbol in prices:
                pos.update_market_value(prices[symbol])

    @property
    def total_value(self) -> float:
        """Total portfolio value (cash + positions)."""
        return self.cash + sum(p.market_value for p in self.positions.values())

    @property
    def total_pnl(self) -> float:
        return self.total_value - self.initial_cash

    @property
    def total_return(self) -> float:
        if self.initial_cash == 0:
            return 0.0
        return self.total_pnl / self.initial_cash

    def snapshot(self) -> Dict:
        """Record current equity state."""
        record = {
            "cash": self.cash,
            "positions_value": sum(p.market_value for p in self.positions.values()),
            "total_value": self.total_value,
            "num_positions": len(self.positions),
        }
        self.equity_history.append(record)
        return record

    def get_equity_df(self) -> pd.DataFrame:
        """Return equity history as DataFrame."""
        return pd.DataFrame(self.equity_history)

    def summary(self) -> str:
        """Human-readable portfolio summary."""
        lines = [
            f"Portfolio Summary:",
            f"  Cash: {self.cash:,.2f}",
            f"  Positions: {len(self.positions)}",
            f"  Total Value: {self.total_value:,.2f}",
            f"  Total PnL: {self.total_pnl:,.2f} ({self.total_return:.2%})",
            f"  Trades: {len(self.trades)}",
        ]
        for sym, pos in self.positions.items():
            lines.append(
                f"    {sym}: {pos.quantity} shares @ {pos.avg_price:.2f} "
                f"(value={pos.market_value:,.2f}, pnl={pos.unrealized_pnl:,.2f})"
            )
        return "\n".join(lines)
