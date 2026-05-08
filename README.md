# QuantFQ

[中文文档](README_CN.md)

A-share quantitative trading framework with backtesting, stock screening, portfolio management, parameter optimization, and web dashboard.

## Features

- **Data Fetching** — Yahoo Finance, miniQMT (xtquant), East Money API
- **Technical Indicators** — SMA, EMA, RSI, BOLL, MACD, KDJ, plus optional TA-Lib integration
- **Strategy Development** — BaseStrategy pattern with signal generation ({-1, 0, 1})
- **Backtesting** — Single-symbol and multi-symbol portfolio backtesting engine
- **Stock Screener** — Full A-share market scanning with technical/fundamental/price filters
- **Portfolio Management** — Multi-asset portfolio with equal-weight, market-cap, custom allocation and rebalancing
- **Parameter Optimization** — Grid search, random search, and walk-forward analysis
- **Live Trading** — miniQMT gateway for real-time trading
- **Web Dashboard** — FastAPI backend with Plotly.js visualization

## Installation

```bash
# Basic install
pip install -e .

# With TA-Lib support
pip install -e ".[talib]"

# With web dashboard
pip install -e ".[web]"

# Development
pip install -e ".[dev]"
```

## Quick Start

```python
from quantfq.data import DataFetcher
from quantfq.backtest import BacktestEngine

# Fetch data
fetcher = DataFetcher(source="yahoo")
data = fetcher.fetch_data("AAPL", "2023-01-01", "2024-01-01")

# Run backtest
engine = BacktestEngine(initial_capital=1000000)
engine.set_parameters("AAPL", "2023-01-01", "2024-01-01")
engine.load_data()
engine.add_strategy(your_strategy)
engine.run_backtest()
engine.show_report()
```

### Stock Screening

```python
from quantfq.screener import (
    AkshareUniverseProvider, PriceFilter, Screener,
)

universe = AkshareUniverseProvider()
filters = [PriceFilter(min_price=5, max_price=50)]
screener = Screener(universe_provider=universe, filters=filters)
result = screener.run(start_date="2024-01-01", end_date="2024-06-01")
print(result.summary())
```

### Parameter Optimization

```python
from quantfq.backtest.optimizer import GridSearchOptimizer, ParamGrid

param_grid = ParamGrid(params={"short_period": [5, 10], "long_period": [20, 60]})
optimizer = GridSearchOptimizer(
    engine_factory=lambda **p: BacktestEngine(),
    strategy_factory=lambda: YourStrategy(),
    param_grid=param_grid,
)
report = optimizer.run("AAPL", "2023-01-01", "2024-01-01")
print(report.summary())
```

### Web Dashboard

```bash
uvicorn quantfq.web.api:app --reload
# Open http://localhost:8000
```

## Project Structure

```
quantfq/
├── core/           # Base components, config, logger
├── data/           # Data fetching, cleaning, storage
├── indicators/     # Technical and fundamental indicators
├── strategy/       # Strategy base class and signals
├── backtest/       # Backtesting engines, metrics, optimizer/
├── screener/       # Stock screening (universe, filters, engine)
├── portfolio/      # Portfolio management, allocation, rebalancing
├── trader/         # Order and position management
├── live/           # Live trading engine and gateways
├── adapters/       # Data and trade gateway adapters
├── charts/         # Visualization (price, signals, performance)
└── web/            # FastAPI dashboard and API
```

## Examples

See `examples/` for 20+ usage examples covering data fetching, indicators, backtesting, live trading, and more.

## License

MIT
