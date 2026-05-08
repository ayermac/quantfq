# Changelog

## v2.0.0 (2026-05-08)

### Breaking Changes
- Renamed project from `deltafq` to `quantfq` — all imports, package name, and references updated

### New Modules
- **Screener** (`quantfq.screener`) — Full A-share market screening with `AkshareUniverseProvider`, `PriceFilter`, `TechnicalFilter`, `FundamentalFilter`, `AndFilter`/`OrFilter`
- **Portfolio** (`quantfq.portfolio`) — Multi-asset portfolio with `EqualWeightAllocator`, `MarketCapAllocator`, `CustomWeightAllocator`, `PeriodicRebalancer`, `ThresholdRebalancer`
- **Portfolio Backtest** (`quantfq.backtest.PortfolioBacktestEngine`) — Multi-symbol backtesting with portfolio-level tracking
- **Optimizer** (`quantfq.backtest.optimizer`) — `GridSearchOptimizer`, `RandomSearchOptimizer`, `WalkForwardOptimizer`
- **Web Dashboard** (`quantfq.web`) — FastAPI backend with Plotly.js frontend

### Improvements
- Lazy imports throughout — `import quantfq` works even without pandas/numpy/talib installed
- `indicators` subpackage gracefully degrades when TA-Lib is not installed
- `data.fetcher` lazy-imports `yfinance` and `requests` only when needed
- Added `charts`, `adapters`, `web` to top-level module exports
- 30+ unit tests for screener, portfolio, and optimizer modules

### Bug Fixes
- Fixed optimizer modules calling `engine.add_strategy(engine.strategy)` (circular reference)
- Removed stale fallback version `0.9.1`

---

## v1.0.2

- DataGateway interface completion

## v1.0.1

- miniQMT bid/ask based order placement

## v1.0.0

- miniQMT live trading and LiveEngine

## v0.9.1

- Fix backtest engine data source switching bug
