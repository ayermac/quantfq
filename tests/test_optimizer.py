"""Tests for the optimizer module."""

from quantfq.backtest.optimizer.base import ParamGrid, OptResult, OptReport


class TestParamGrid:
    def test_single_param(self):
        grid = ParamGrid(params={"period": [10, 20, 30]})
        combos = grid.combinations()
        assert len(combos) == 3
        assert combos[0] == {"period": 10}

    def test_multiple_params(self):
        grid = ParamGrid(params={"fast": [5, 10], "slow": [20, 30]})
        combos = grid.combinations()
        assert len(combos) == 4

    def test_empty_grid(self):
        grid = ParamGrid(params={})
        combos = grid.combinations()
        assert len(combos) == 1
        assert combos[0] == {}


class TestOptReport:
    def test_best(self):
        report = OptReport(metric_name="sharpe")
        report.results = [
            OptResult(params={"p": 1}, metrics={}, metric_value=0.5),
            OptResult(params={"p": 2}, metrics={}, metric_value=1.5),
            OptResult(params={"p": 3}, metrics={}, metric_value=1.0),
        ]
        assert report.best.params == {"p": 2}
        assert report.worst.params == {"p": 1}

    def test_top_n(self):
        report = OptReport(metric_name="sharpe")
        report.results = [
            OptResult(params={"p": i}, metrics={}, metric_value=float(i))
            for i in range(10)
        ]
        top3 = report.top_n(3)
        assert len(top3) == 3
        assert top3[0].metric_value == 9

    def test_empty_report(self):
        report = OptReport()
        assert report.best is None
        assert report.worst is None
        assert report.top_n(5) == []

    def test_to_dataframe(self):
        report = OptReport(metric_name="sharpe")
        report.results = [
            OptResult(params={"p": 1}, metrics={}, metric_value=0.5),
            OptResult(params={"p": 2}, metrics={}, metric_value=1.5),
        ]
        df = report.to_dataframe()
        assert len(df) == 2
        assert "sharpe" in df.columns
        assert "p" in df.columns
