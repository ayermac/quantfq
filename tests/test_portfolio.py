"""Tests for the portfolio module."""

import pytest
from quantfq.portfolio.portfolio import Portfolio, PortfolioPosition
from quantfq.portfolio.allocator import EqualWeightAllocator, CustomWeightAllocator
from quantfq.portfolio.rebalancer import PeriodicRebalancer, ThresholdRebalancer


class TestPortfolio:
    def test_initial_state(self):
        p = Portfolio(initial_cash=100000)
        assert p.cash == 100000
        assert p.total_value == 100000
        assert p.total_pnl == 0
        assert len(p.positions) == 0

    def test_buy(self):
        p = Portfolio(initial_cash=100000, commission_rate=0)
        trade = p.buy("AAPL", 10, 150.0)
        assert trade.symbol == "AAPL"
        assert trade.quantity == 10
        assert "AAPL" in p.positions
        assert p.positions["AAPL"].quantity == 10
        assert p.cash == 100000 - 1500

    def test_sell(self):
        p = Portfolio(initial_cash=100000, commission_rate=0)
        p.buy("AAPL", 10, 150.0)
        p.sell("AAPL", 10, 160.0)
        assert "AAPL" not in p.positions
        assert p.cash == 100000 - 1500 + 1600

    def test_insufficient_cash(self):
        p = Portfolio(initial_cash=100, commission_rate=0)
        with pytest.raises(ValueError):
            p.buy("AAPL", 10, 150.0)

    def test_insufficient_position(self):
        p = Portfolio(initial_cash=100000, commission_rate=0)
        with pytest.raises(ValueError):
            p.sell("AAPL", 10, 150.0)

    def test_update_prices(self):
        p = Portfolio(initial_cash=100000, commission_rate=0)
        p.buy("AAPL", 10, 150.0)
        p.update_prices({"AAPL": 160.0})
        assert p.positions["AAPL"].market_value == 1600
        assert p.positions["AAPL"].unrealized_pnl == 100

    def test_snapshot(self):
        p = Portfolio(initial_cash=100000)
        snap = p.snapshot()
        assert "cash" in snap
        assert "total_value" in snap
        assert len(p.equity_history) == 1


class TestAllocator:
    def test_equal_weight(self):
        alloc = EqualWeightAllocator()
        result = alloc.allocate(100000, ["A", "B", "C"], {})
        assert result == {"A": 100000 / 3, "B": 100000 / 3, "C": 100000 / 3}

    def test_custom_weight(self):
        alloc = CustomWeightAllocator({"A": 3, "B": 1})
        result = alloc.allocate(100000, ["A", "B"], {})
        assert result["A"] == 75000
        assert result["B"] == 25000


class TestRebalancer:
    def test_periodic_rebalance(self):
        from datetime import datetime
        r = PeriodicRebalancer(frequency="monthly")
        p = Portfolio(initial_cash=100000)
        assert r.should_rebalance(datetime(2024, 1, 1), p) is True

    def test_threshold_rebalance(self):
        r = ThresholdRebalancer(threshold=0.05)
        p = Portfolio(initial_cash=100000)
        # No positions, should not trigger
        changes = r.compute_trades(p, {"A": 0.5, "B": 0.5}, {"A": 100, "B": 100})
        assert len(changes) > 0  # Initial allocation needed
