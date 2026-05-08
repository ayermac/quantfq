"""Tests for quantfq.backtest.metrics — pure math functions."""

import numpy as np
import pandas as pd
import pytest

from quantfq.backtest.metrics import (
    calculate_annualized_return,
    calculate_calmar_ratio,
    calculate_max_drawdown,
    calculate_returns,
    calculate_sharpe_ratio,
    calculate_total_return,
    calculate_volatility,
    compute_cumulative_returns,
    compute_drawdown_series,
)


@pytest.fixture
def equity() -> pd.Series:
    """Simple equity curve: 100 → 110 → 105 → 115."""
    return pd.Series([100.0, 110.0, 105.0, 115.0], index=pd.date_range("2024-01-01", periods=4))


@pytest.fixture
def flat_equity() -> pd.Series:
    """Flat equity — no returns."""
    return pd.Series([100.0] * 5, index=pd.date_range("2024-01-01", periods=5))


class TestCalculateReturns:
    def test_returns_shape(self, equity: pd.Series) -> None:
        result = calculate_returns(equity)
        assert len(result) == len(equity)

    def test_first_return_is_zero(self, equity: pd.Series) -> None:
        result = calculate_returns(equity)
        assert result.iloc[0] == 0.0

    def test_known_values(self, equity: pd.Series) -> None:
        result = calculate_returns(equity)
        assert result.iloc[1] == pytest.approx(0.1)  # 110/100 - 1
        assert result.iloc[2] == pytest.approx(-5 / 110)  # 105/110 - 1

    def test_flat_equity(self, flat_equity: pd.Series) -> None:
        result = calculate_returns(flat_equity)
        assert (result == 0.0).all()


class TestComputeCumulativeReturns:
    def test_cumulative_from_zero(self, equity: pd.Series) -> None:
        returns = calculate_returns(equity)
        cum = compute_cumulative_returns(returns)
        assert cum.iloc[0] == pytest.approx(0.0)

    def test_cumulative_final(self, equity: pd.Series) -> None:
        returns = calculate_returns(equity)
        cum = compute_cumulative_returns(returns)
        assert cum.iloc[-1] == pytest.approx(0.15)  # 115/100 - 1


class TestComputeDrawdownSeries:
    def test_drawdown_non_positive(self, equity: pd.Series) -> None:
        returns = calculate_returns(equity)
        dd = compute_drawdown_series(returns)
        assert (dd <= 0.0).all()

    def test_drawdown_at_peak_is_zero(self, equity: pd.Series) -> None:
        returns = calculate_returns(equity)
        dd = compute_drawdown_series(returns)
        assert dd.iloc[0] == pytest.approx(0.0)
        assert dd.iloc[1] == pytest.approx(0.0)


class TestCalculateTotalReturn:
    def test_known_total_return(self, equity: pd.Series) -> None:
        assert calculate_total_return(equity) == pytest.approx(0.15)

    def test_flat(self, flat_equity: pd.Series) -> None:
        assert calculate_total_return(flat_equity) == pytest.approx(0.0)


class TestCalculateAnnualizedReturn:
    def test_positive_returns(self) -> None:
        returns = pd.Series([0.01] * 252)
        result = calculate_annualized_return(returns)
        assert result > 0

    def test_zero_mean(self) -> None:
        returns = pd.Series([0.0] * 252)
        result = calculate_annualized_return(returns)
        assert result == pytest.approx(0.0)


class TestCalculateVolatility:
    def test_positive(self, equity: pd.Series) -> None:
        returns = calculate_returns(equity)
        vol = calculate_volatility(returns)
        assert vol >= 0

    def test_flat_is_zero(self, flat_equity: pd.Series) -> None:
        returns = calculate_returns(flat_equity)
        vol = calculate_volatility(returns)
        assert vol == pytest.approx(0.0)


class TestCalculateSharpeRatio:
    def test_positive_sharpe(self) -> None:
        returns = pd.Series([0.001] * 252)
        sharpe = calculate_sharpe_ratio(returns)
        assert sharpe > 0

    def test_zero_std(self, flat_equity: pd.Series) -> None:
        returns = calculate_returns(flat_equity)
        sharpe = calculate_sharpe_ratio(returns)
        assert sharpe == 0.0


class TestCalculateMaxDrawdown:
    def test_known_drawdown(self) -> None:
        equity = pd.Series([100, 110, 90, 95])
        mdd = calculate_max_drawdown(equity)
        assert mdd == pytest.approx(-20 / 110)  # (90-110)/110

    def test_no_drawdown(self, flat_equity: pd.Series) -> None:
        mdd = calculate_max_drawdown(flat_equity)
        assert mdd == pytest.approx(0.0)


class TestCalculateCalmarRatio:
    def test_positive(self) -> None:
        ratio = calculate_calmar_ratio(0.15, -0.10)
        assert ratio == pytest.approx(1.5)

    def test_zero_drawdown_positive_return(self) -> None:
        ratio = calculate_calmar_ratio(0.10, 0.0)
        assert ratio == float("inf")

    def test_zero_drawdown_zero_return(self) -> None:
        ratio = calculate_calmar_ratio(0.0, 0.0)
        assert ratio == 0.0
