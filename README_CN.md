# QuantFQ

A 股量化交易框架，支持回测、股票筛选、组合管理、参数优化和 Web 仪表盘。

## 功能特性

- **数据获取** — Yahoo Finance、miniQMT (xtquant)、东方财富 API
- **技术指标** — SMA、EMA、RSI、BOLL、MACD、KDJ，可选 TA-Lib 扩展
- **策略开发** — BaseStrategy 模式，信号生成 ({-1, 0, 1})
- **回测引擎** — 单标的和多标的组合回测
- **股票筛选** — 全市场扫描，支持技术面/基本面/价格条件过滤
- **组合管理** — 多资产组合，等权/市值加权/自定义权重分配，定期/阈值再平衡
- **参数优化** — 网格搜索、随机搜索、滚动前推验证
- **实盘交易** — miniQMT 网关实时交易
- **Web 仪表盘** — FastAPI 后端 + Plotly.js 可视化

## 安装

```bash
# 基础安装
pip install -e .

# 支持 TA-Lib
pip install -e ".[talib]"

# Web 仪表盘
pip install -e ".[web]"

# 开发环境
pip install -e ".[dev]"
```

## 快速开始

```python
from quantfq.data import DataFetcher
from quantfq.backtest import BacktestEngine

# 获取数据
fetcher = DataFetcher(source="yahoo")
data = fetcher.fetch_data("AAPL", "2023-01-01", "2024-01-01")

# 运行回测
engine = BacktestEngine(initial_capital=1000000)
engine.set_parameters("AAPL", "2023-01-01", "2024-01-01")
engine.load_data()
engine.add_strategy(your_strategy)
engine.run_backtest()
engine.show_report()
```

### 股票筛选

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

### 参数优化

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

### Web 仪表盘

```bash
uvicorn quantfq.web.api:app --reload
# 浏览器打开 http://localhost:8000
```

## 项目结构

```
quantfq/
├── core/           # 基础组件、配置、日志
├── data/           # 数据获取、清洗、存储
├── indicators/     # 技术指标和基本面指标
├── strategy/       # 策略基类和信号
├── backtest/       # 回测引擎、指标计算、参数优化器
├── screener/       # 股票筛选（股票池、过滤器、筛选引擎）
├── portfolio/      # 组合管理、资金分配、再平衡
├── trader/         # 订单和持仓管理
├── live/           # 实盘交易引擎和网关
├── adapters/       # 数据和交易网关适配器
├── charts/         # 可视化（价格、信号、绩效）
└── web/            # FastAPI 仪表盘和 API
```

## 示例

参见 `examples/` 目录，包含 20+ 个使用示例，涵盖数据获取、指标计算、回测、实盘交易等。

## 许可证

MIT
