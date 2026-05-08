"""Tests for the screener module."""

import pandas as pd
import pytest
from quantfq.screener.filters import PriceFilter, AndFilter, OrFilter, FundamentalFilter


class TestPriceFilter:
    def _make_data(self, close=100, volume=1000000):
        return pd.DataFrame({"Close": [close], "Volume": [volume]})

    def test_min_price_pass(self):
        f = PriceFilter(min_price=50)
        assert f.apply(self._make_data(close=100)) is True

    def test_min_price_fail(self):
        f = PriceFilter(min_price=150)
        assert f.apply(self._make_data(close=100)) is False

    def test_max_price_pass(self):
        f = PriceFilter(max_price=200)
        assert f.apply(self._make_data(close=100)) is True

    def test_max_price_fail(self):
        f = PriceFilter(max_price=50)
        assert f.apply(self._make_data(close=100)) is False

    def test_min_volume(self):
        f = PriceFilter(min_volume=500000)
        assert f.apply(self._make_data(volume=1000000)) is True
        assert f.apply(self._make_data(volume=100)) is False

    def test_empty_data(self):
        f = PriceFilter(min_price=50)
        assert f.apply(pd.DataFrame()) is False


class TestCombinationFilters:
    def test_and_filter(self):
        f1 = PriceFilter(min_price=50)
        f2 = PriceFilter(max_price=200)
        data = pd.DataFrame({"Close": [100], "Volume": [1000000]})
        assert AndFilter(f1, f2).apply(data) is True

    def test_and_filter_fail(self):
        f1 = PriceFilter(min_price=50)
        f2 = PriceFilter(max_price=80)
        data = pd.DataFrame({"Close": [100], "Volume": [1000000]})
        assert AndFilter(f1, f2).apply(data) is False

    def test_or_filter(self):
        f1 = PriceFilter(min_price=200)
        f2 = PriceFilter(max_price=200)
        data = pd.DataFrame({"Close": [100], "Volume": [1000000]})
        assert OrFilter(f1, f2).apply(data) is True


class TestFundamentalFilter:
    def test_pass(self):
        f = FundamentalFilter(metric="pe", condition="lt", value=20)
        data = pd.DataFrame({"pe": [15]})
        assert f.apply(data) == True  # noqa: E712

    def test_fail(self):
        f = FundamentalFilter(metric="pe", condition="lt", value=10)
        data = pd.DataFrame({"pe": [15]})
        assert f.apply(data) == False  # noqa: E712

    def test_missing_column(self):
        f = FundamentalFilter(metric="pe", condition="lt", value=10)
        data = pd.DataFrame({"price": [100]})
        assert f.apply(data) is False
