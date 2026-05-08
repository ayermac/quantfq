"""FastAPI web application for QuantFQ dashboard."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

if HAS_FASTAPI:
    app = FastAPI(
        title="QuantFQ Dashboard",
        description="Quantitative trading framework dashboard",
        version="2.0.0",
    )

    _results_cache: Dict[str, Any] = {}

    # ==================== Static ====================

    @app.get("/", response_class=HTMLResponse)
    async def index():
        import os
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r") as f:
                return HTMLResponse(content=f.read())
        return HTMLResponse(content="<h1>QuantFQ Dashboard</h1><p>Static files not found.</p>")

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "2.0.0"}

    # ==================== Backtest ====================

    @app.post("/api/backtest/run")
    async def run_backtest(request: Dict[str, Any]):
        try:
            from ..backtest.engine import BacktestEngine
            from ..strategy.base import BaseStrategy
            import pandas as pd

            symbol = request.get("symbol", "000001.SZ")
            start_date = request.get("start_date", "2024-01-01")
            end_date = request.get("end_date", "2024-12-31")
            initial_capital = request.get("initial_capital", 1000000)
            commission = request.get("commission", 0.001)
            slippage = request.get("slippage", 0.0)
            source = request.get("source", "yahoo")
            strategy_name = request.get("strategy", "sma")
            params = request.get("params", {})
            fast_period = params.get("fast_period", 10)
            slow_period = params.get("slow_period", 30)

            engine = BacktestEngine(
                initial_capital=initial_capital,
                commission=commission,
                slippage=slippage,
                data_source=source,
            )
            engine.set_parameters(symbol, start_date, end_date)
            engine.load_data()

            if strategy_name == "rsi":
                rsi_period = fast_period
                class DynamicStrategy(BaseStrategy):
                    def generate_signals(self, data):
                        close = data["Close"].astype(float)
                        delta = close.diff()
                        gain = delta.where(delta > 0, 0.0).rolling(rsi_period).mean()
                        loss = (-delta.where(delta < 0, 0.0)).rolling(rsi_period).mean()
                        rs = gain / loss.replace(0, 1e-10)
                        rsi = 100 - 100 / (1 + rs)
                        signals = pd.Series(0, index=close.index)
                        signals[rsi < 30] = 1
                        signals[rsi > 70] = -1
                        return signals
            elif strategy_name == "bollinger":
                class DynamicStrategy(BaseStrategy):
                    def generate_signals(self, data):
                        close = data["Close"].astype(float)
                        mid = close.rolling(slow_period).mean()
                        std = close.rolling(slow_period).std()
                        upper = mid + 2 * std
                        lower = mid - 2 * std
                        signals = pd.Series(0, index=close.index)
                        signals[close < lower] = 1
                        signals[close > upper] = -1
                        return signals
            else:  # sma
                class DynamicStrategy(BaseStrategy):
                    def generate_signals(self, data):
                        close = data["Close"].astype(float)
                        fast = close.rolling(fast_period).mean()
                        slow = close.rolling(slow_period).mean()
                        signals = pd.Series(0, index=close.index)
                        signals[fast > slow] = 1
                        signals[fast < slow] = -1
                        return signals

            engine.add_strategy(DynamicStrategy(name=strategy_name))
            engine.run_backtest()
            values_df, metrics = engine.calculate_metrics()

            result = {
                "symbol": symbol,
                "metrics": metrics,
                "equity_curve": values_df.to_dict() if values_df is not None else {},
            }
            _results_cache[f"backtest_{symbol}"] = result
            return result
        except Exception as e:
            logger.exception("Backtest failed")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/backtest/results")
    async def get_backtest_results():
        return _results_cache

    # ==================== Screener ====================

    @app.post("/api/screener/run")
    async def run_screener(request: Dict[str, Any]):
        try:
            from ..screener import AkshareUniverseProvider, PriceFilter, Screener

            start_date = request.get("start_date", "2024-01-01")
            end_date = request.get("end_date", "2024-06-01")
            min_price = request.get("min_price", 5)
            max_price = request.get("max_price", 50)

            filters = [PriceFilter(min_price=min_price, max_price=max_price)]

            max_pe = request.get("max_pe", 100)
            min_roe = request.get("min_roe", 0)
            if max_pe < 100 or min_roe > 0:
                from ..screener import FundamentalFilter
                if max_pe < 100:
                    filters.append(FundamentalFilter(metric="pe", condition="lt", value=max_pe))
                if min_roe > 0:
                    filters.append(FundamentalFilter(metric="roe", condition="gt", value=min_roe))

            universe = AkshareUniverseProvider()
            screener = Screener(universe_provider=universe, filters=filters)
            result = screener.run(start_date=start_date, end_date=end_date)

            candidates = []
            if not result.candidates.empty:
                for _, row in result.candidates.iterrows():
                    candidates.append({
                        "symbol": row.get("symbol", ""),
                        "name": row.get("name", ""),
                        "price": row.get("price", 0),
                        "volume": row.get("volume", 0),
                    })

            response = {
                "candidates": candidates,
                "summary": result.summary(),
                "total": len(candidates),
            }
            _results_cache["screener"] = response
            return response
        except ImportError as e:
            logger.warning(f"Screener dependency missing: {e}")
            raise HTTPException(status_code=501, detail=f"Screener requires akshare: {e}")
        except Exception as e:
            logger.exception("Screener failed")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/screener/results")
    async def get_screener_results():
        return _results_cache.get("screener", {})

    # ==================== Portfolio ====================

    @app.post("/api/portfolio/run")
    async def run_portfolio(request: Dict[str, Any]):
        try:
            from ..backtest.engine import BacktestEngine
            from ..strategy.base import BaseStrategy
            import pandas as pd

            symbols = request.get("symbols", ["000001.SZ", "600519.SH"])
            start_date = request.get("start_date", "2024-01-01")
            end_date = request.get("end_date", "2024-12-31")
            initial_capital = request.get("initial_capital", 1000000)
            capital_per_symbol = initial_capital / len(symbols)

            allocation = {sym: 1.0 / len(symbols) for sym in symbols}
            positions = []
            total_return = 0.0

            class SmaStrategy(BaseStrategy):
                def generate_signals(self, data):
                    close = data["Close"].astype(float)
                    fast = close.rolling(10).mean()
                    slow = close.rolling(30).mean()
                    signals = pd.Series(0, index=close.index)
                    signals[fast > slow] = 1
                    signals[fast < slow] = -1
                    return signals

            for sym in symbols:
                try:
                    engine = BacktestEngine(
                        initial_capital=capital_per_symbol,
                        commission=0.001,
                    )
                    engine.set_parameters(sym, start_date, end_date)
                    engine.load_data()
                    engine.add_strategy(SmaStrategy(name=f"SMA_{sym}"))
                    engine.run_backtest()
                    _, metrics = engine.calculate_metrics()
                    ret = metrics.get("total_return", 0.0)
                    total_return += ret * allocation[sym]
                    positions.append({
                        "symbol": sym,
                        "weight": f"{allocation[sym] * 100:.1f}%",
                        "return": f"{ret * 100:.2f}%",
                        "status": "ok",
                    })
                except Exception as e:
                    positions.append({
                        "symbol": sym,
                        "weight": f"{allocation[sym] * 100:.1f}%",
                        "return": "N/A",
                        "status": f"error: {str(e)[:50]}",
                    })

            response = {
                "symbols": symbols,
                "metrics": {
                    "total_return": total_return,
                    "sharpe_ratio": 0.0,
                },
                "equity_curve": {},
                "allocation": allocation,
                "positions": positions,
            }
            _results_cache["portfolio"] = response
            return response
        except Exception as e:
            logger.exception("Portfolio backtest failed")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/portfolio/positions")
    async def get_positions():
        return _results_cache.get("portfolio", {})

    # ==================== Optimizer ====================

    @app.post("/api/optimizer/run")
    async def run_optimizer(request: Dict[str, Any]):
        try:
            from ..backtest.engine import BacktestEngine
            from ..backtest.optimizer import GridSearchOptimizer, RandomSearchOptimizer, ParamGrid
            from ..strategy.base import BaseStrategy
            import pandas as pd

            symbol = request.get("symbol", "000001.SZ")
            start_date = request.get("start_date", "2024-01-01")
            end_date = request.get("end_date", "2024-12-31")
            method = request.get("method", "grid")
            param_grid_dict = request.get("param_grid", {})
            metric = request.get("metric", "sharpe_ratio")
            n_iter = request.get("n_iter", 50)

            fast_periods = param_grid_dict.get("fast_period", [5, 10, 20])
            slow_periods = param_grid_dict.get("slow_period", [30, 60, 120])

            param_grid = ParamGrid(params={
                "fast_period": fast_periods,
                "slow_period": slow_periods,
            })

            def engine_factory(**kwargs):
                return BacktestEngine(
                    initial_capital=1000000,
                    commission=0.001,
                )

            def strategy_factory():
                return _create_sma_strategy(10, 30)

            if method == "random":
                optimizer = RandomSearchOptimizer(
                    engine_factory=engine_factory,
                    strategy_factory=strategy_factory,
                    param_distributions=param_grid,
                    n_iter=n_iter,
                    metric=metric,
                )
            else:
                optimizer = GridSearchOptimizer(
                    engine_factory=engine_factory,
                    strategy_factory=strategy_factory,
                    param_grid=param_grid,
                    metric=metric,
                )

            report = optimizer.run(symbol, start_date, end_date)

            results_list = []
            for r in report.results:
                results_list.append({
                    "params": r.params,
                    "metric_value": r.metric_value,
                    **{k: v for k, v in r.metrics.items() if not k.startswith('_')},
                })

            best = {}
            if report.best:
                best = {
                    "params": report.best.params,
                    metric: report.best.metric_value,
                    **report.best.metrics,
                }

            heatmap = _build_heatmap(results_list, fast_periods, slow_periods, metric)

            response = {
                "symbol": symbol,
                "method": method,
                "metric": metric,
                "total_runs": len(results_list),
                "best": best,
                "results": results_list,
                "heatmap": heatmap,
            }
            _results_cache["optimizer"] = response
            return response
        except Exception as e:
            logger.exception("Optimizer failed")
            raise HTTPException(status_code=500, detail=str(e))

    def _create_sma_strategy(fast_period: int, slow_period: int):
        from ..strategy.base import BaseStrategy
        import pandas as pd
        class SmaStrategy(BaseStrategy):
            def generate_signals(self, data):
                close = data["Close"].astype(float)
                fast = close.rolling(fast_period).mean()
                slow_ma = close.rolling(slow_period).mean()
                signals = pd.Series(0, index=close.index)
                signals[fast > slow_ma] = 1
                signals[fast < slow_ma] = -1
                return signals
        return SmaStrategy(name=f"SMA_{fast_period}_{slow_period}")

    def _build_heatmap(results: List[Dict], fast_periods: List, slow_periods: List, metric: str) -> Dict[str, Any]:
        if not results:
            return {}
        lookup = {}
        for r in results:
            p = r.get("params", {})
            key = (p.get("fast_period"), p.get("slow_period"))
            lookup[key] = r.get("metric_value", 0)
        fast_sorted = sorted(set(fast_periods))
        slow_sorted = sorted(set(slow_periods))
        z = []
        for f in fast_sorted:
            row = []
            for s in slow_sorted:
                row.append(lookup.get((f, s), 0))
            z.append(row)
        return {
            "z": z,
            "x": [str(s) for s in slow_sorted],
            "y": [str(f) for f in fast_sorted],
            "x_label": "Slow Period",
            "y_label": "Fast Period",
        }

    @app.get("/api/optimizer/results")
    async def get_optimizer_results():
        return _results_cache.get("optimizer", {})

else:
    app = None
    logger.warning("FastAPI not installed. Run: pip install fastapi uvicorn")


def create_app():
    """Create and return the FastAPI app."""
    if not HAS_FASTAPI:
        raise ImportError("fastapi is required. Install with: pip install fastapi uvicorn")
    return app
