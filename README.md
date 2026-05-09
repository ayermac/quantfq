# QuantFQ

**A-Share Quantitative Trading Framework**

English | [中文](README_CN.md)

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Plotly](https://img.shields.io/badge/Plotly-5.0-3F4F75?logo=plotly&logoColor=white)](https://plotly.com/python/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A modular framework for A-share quantitative trading — backtesting, stock screening, portfolio management, parameter optimization, and a web dashboard, all in one package.

[Quick Start](#quick-start) | [Architecture](#architecture) | [Modules](#modules) | [Web Dashboard](#web-dashboard) | [Examples](#examples)

---

## Features

- **Data Fetching** — Yahoo Finance, miniQMT (xtquant), East Money API with automatic cleaning and caching
- **Technical Indicators** — SMA, EMA, RSI, BOLL, MACD, KDJ, plus optional TA-Lib integration
- **Strategy Development** — BaseStrategy pattern with signal generation (`{-1, 0, 1}`)
- **Backtesting Engine** — Single-symbol and multi-symbol portfolio backtesting with detailed metrics
- **Stock Screener** — Full A-share market scanning with 20+ configurable filters (technical, fundamental, price)
- **Portfolio Management** — Equal-weight, market-cap, custom allocation with periodic and threshold-based rebalancing
- **Parameter Optimization** — Grid search, random search, and walk-forward analysis
- **Live Trading** — miniQMT gateway for real-time order execution
- **Web Dashboard** — FastAPI backend with Plotly.js interactive visualization

## Architecture

```
                         ┌──────────────────────┐
                         │   Web Dashboard      │
                         │   FastAPI + Plotly.js │
                         └──────────┬───────────┘
                                    │
          ┌─────────────┬───────────┼───────────┬─────────────┐
          ▼             ▼           ▼           ▼             ▼
   ┌────────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐
   │  Screener  │ │ Backtest │ │Portfolio│ │ Trader  │ │  Live    │
   │  Engine    │ │  Engine  │ │ Manager │ │ Orders  │ │ Trading  │
   └─────┬──────┘ └────┬─────┘ └────┬────┘ └────┬────┘ └────┬─────┘
         │             │            │            │            │
         └─────────────┴────────────┴────────────┴────────────┘
                                    │
                         ┌──────────┴───────────┐
                         │    Core Layer        │
                         │  Data │ Indicators   │
                         │  Config │ Strategy   │
                         └──────────────────────┘
```

| Layer | Components | Purpose |
|-------|-----------|---------|
| Data | `DataFetcher`, `cleaners`, adapters | Yahoo, miniQMT, East Money APIs |
| Indicators | `SMA`, `EMA`, `RSI`, `BOLL`, `MACD`, `KDJ` | Technical analysis (TA-Lib optional) |
| Strategy | `BaseStrategy`, signals | Signal generation (`{-1, 0, 1}`) |
| Backtest | `BacktestEngine`, `optimizer/` | Single & portfolio backtesting |
| Screener | `Screener`, `filters`, strategies | A-share market scanning |
| Portfolio | `PortfolioManager`, rebalancing | Multi-asset allocation |
| Live | `LiveEngine`, miniQMT gateway | Real-time trading |
| Web | FastAPI API + Plotly.js dashboard | Interactive visualization |

## Quick Start

### Prerequisites

- Python 3.9+
- pip

### Installation

```bash
# Clone the repository
git clone git@github.com:ayermac/quantfq.git
cd quantfq

# Basic install
pip install -e .

# With TA-Lib support
pip install -e ".[talib]"

# With web dashboard
pip install -e ".[web]"

# Development (linters, test runner, docs)
pip install -e ".[dev]"
```

### Run Backtest

```python
from quantfq.data import DataFetcher
from quantfq.backtest import BacktestEngine

fetcher = DataFetcher(source="yahoo")
data = fetcher.fetch_data("AAPL", "2023-01-01", "2024-01-01")

engine = BacktestEngine(initial_capital=1_000_000)
engine.set_parameters("AAPL", "2023-01-01", "2024-01-01")
engine.load_data()
engine.add_strategy(your_strategy)
engine.run_backtest()
engine.show_report()
```

### Run Stock Screener

```python
from quantfq.screener import AkshareUniverseProvider, PriceFilter, Screener

universe = AkshareUniverseProvider()
filters = [PriceFilter(min_price=5, max_price=50)]
screener = Screener(universe_provider=universe, filters=filters)
result = screener.run(start_date="2024-01-01", end_date="2024-06-01")
print(result.summary())
```

## Modules

### Data

```python
from quantfq.data import DataFetcher

fetcher = DataFetcher(source="yahoo")       # or "miniqmt", "eastmoney"
df = fetcher.fetch_data("600519.SH", "2023-01-01", "2024-01-01")
```

### Technical Indicators

```python
from quantfq.indicators import SMA, RSI, MACD

sma_20 = SMA(df, period=20)
rsi_14 = RSI(df, period=14)
macd_line, signal_line, histogram = MACD(df)
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

### Portfolio Management

```python
from quantfq.portfolio import PortfolioManager

pm = PortfolioManager(
    symbols=["600519.SH", "000858.SZ", "601318.SH"],
    weights=[0.4, 0.3, 0.3],
    rebalance="monthly",
)
pm.run(start_date="2023-01-01", end_date="2024-01-01")
```

## Web Dashboard

```bash
uvicorn quantfq.web.api:app --reload
# Open http://localhost:8000
```

| Endpoint | Description |
|----------|------------|
| `GET /` | Interactive dashboard |
| `POST /api/backtest/run` | Run backtest via API |
| `POST /api/screener/run` | Run stock screener via API |
| `GET /api/strategies` | List available strategies |

## Project Structure

```
quantfq/
├── core/           # Base components, config, logger
├── data/           # Data fetching, cleaning, storage
│   └── fetcher.py  #   Yahoo / miniQMT / East Money adapters
├── indicators/     # Technical and fundamental indicators
├── strategy/       # Strategy base class and signals
├── backtest/       # Backtesting engines, metrics
│   └── optimizer/  #   Grid search, random search, walk-forward
├── screener/       # Stock screening
│   ├── filters.py  #   Price, volume, technical filters
│   └── strategies/ #   Pluggable screener strategies
├── portfolio/      # Portfolio management, allocation, rebalancing
├── trader/         # Order and position management
├── live/           # Live trading engine and gateways
├── adapters/       # Data and trade gateway adapters
├── charts/         # Visualization (price, signals, performance)
├── web/            # FastAPI dashboard and API
└── examples/       # 20+ usage examples
```

## Examples

See `examples/` for 20+ usage examples covering data fetching, indicators, backtesting, live trading, and more.

```bash
# Run a specific example
python examples/basic_backtest.py
```

## Contributing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check .

# Format
black .
```

## License

[MIT](LICENSE)
