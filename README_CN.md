# QuantFQ

**A 股量化交易框架**

[English](README.md) | 中文

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Plotly](https://img.shields.io/badge/Plotly-5.0-3F4F75?logo=plotly&logoColor=white)](https://plotly.com/python/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

模块化 A 股量化交易框架 — 回测、股票筛选、组合管理、参数优化和 Web 仪表盘，一站式集成。

[快速开始](#快速开始) | [架构](#架构) | [模块](#模块) | [Web 仪表盘](#web-仪表盘) | [示例](#示例)

---

## 功能特性

- **数据获取** — Yahoo Finance、miniQMT (xtquant)、东方财富 API，自动清洗和缓存
- **技术指标** — SMA、EMA、RSI、BOLL、MACD、KDJ，可选 TA-Lib 扩展
- **策略开发** — BaseStrategy 模式，信号生成 (`{-1, 0, 1}`)
- **回测引擎** — 单标的和多标的组合回测，详细绩效指标
- **股票筛选** — 全市场扫描，20+ 可配置过滤器（技术面、基本面、价格）
- **组合管理** — 等权、市值加权、自定义权重分配，定期和阈值再平衡
- **参数优化** — 网格搜索、随机搜索、滚动前推验证
- **实盘交易** — miniQMT 网关实时下单
- **Web 仪表盘** — FastAPI 后端 + Plotly.js 交互式可视化

## 架构

```
                         ┌──────────────────────┐
                         │   Web 仪表盘         │
                         │   FastAPI + Plotly.js │
                         └──────────┬───────────┘
                                    │
          ┌─────────────┬───────────┼───────────┬─────────────┐
          ▼             ▼           ▼           ▼             ▼
   ┌────────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐
   │  筛选引擎  │ │ 回测引擎 │ │组合管理 │ │ 交易员  │ │ 实盘交易 │
   └─────┬──────┘ └────┬─────┘ └────┬────┘ └────┬────┘ └────┬─────┘
         │             │            │            │            │
         └─────────────┴────────────┴────────────┴────────────┘
                                    │
                         ┌──────────┴───────────┐
                         │      核心层          │
                         │  数据 │ 技术指标     │
                         │  配置 │ 策略基类     │
                         └──────────────────────┘
```

| 层级 | 组件 | 用途 |
|------|------|------|
| 数据 | `DataFetcher`、`cleaners`、适配器 | Yahoo、miniQMT、东方财富 API |
| 指标 | `SMA`、`EMA`、`RSI`、`BOLL`、`MACD`、`KDJ` | 技术分析（可选 TA-Lib） |
| 策略 | `BaseStrategy`、信号 | 信号生成 (`{-1, 0, 1}`) |
| 回测 | `BacktestEngine`、`optimizer/` | 单标的和组合回测 |
| 筛选 | `Screener`、`filters`、策略 | A 股市场扫描 |
| 组合 | `PortfolioManager`、再平衡 | 多资产配置 |
| 实盘 | `LiveEngine`、miniQMT 网关 | 实时交易 |
| Web | FastAPI API + Plotly.js 仪表盘 | 交互式可视化 |

## 快速开始

### 环境要求

- Python 3.9+
- pip

### 安装

```bash
# 克隆仓库
git clone git@github.com:ayermac/quantfq.git
cd quantfq

# 基础安装
pip install -e .

# 支持 TA-Lib
pip install -e ".[talib]"

# Web 仪表盘
pip install -e ".[web]"

# 开发环境（代码检查、测试、文档）
pip install -e ".[dev]"
```

### 运行回测

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

### 运行股票筛选

```python
from quantfq.screener import AkshareUniverseProvider, PriceFilter, Screener

universe = AkshareUniverseProvider()
filters = [PriceFilter(min_price=5, max_price=50)]
screener = Screener(universe_provider=universe, filters=filters)
result = screener.run(start_date="2024-01-01", end_date="2024-06-01")
print(result.summary())
```

## 模块

### 数据获取

```python
from quantfq.data import DataFetcher

fetcher = DataFetcher(source="yahoo")       # 或 "miniqmt", "eastmoney"
df = fetcher.fetch_data("600519.SH", "2023-01-01", "2024-01-01")
```

### 技术指标

```python
from quantfq.indicators import SMA, RSI, MACD

sma_20 = SMA(df, period=20)
rsi_14 = RSI(df, period=14)
macd_line, signal_line, histogram = MACD(df)
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

### 组合管理

```python
from quantfq.portfolio import PortfolioManager

pm = PortfolioManager(
    symbols=["600519.SH", "000858.SZ", "601318.SH"],
    weights=[0.4, 0.3, 0.3],
    rebalance="monthly",
)
pm.run(start_date="2023-01-01", end_date="2024-01-01")
```

## Web 仪表盘

```bash
uvicorn quantfq.web.api:app --reload
# 浏览器打开 http://localhost:8000
```

| 端点 | 说明 |
|------|------|
| `GET /` | 交互式仪表盘 |
| `POST /api/backtest/run` | 通过 API 运行回测 |
| `POST /api/screener/run` | 通过 API 运行股票筛选 |
| `GET /api/strategies` | 列出可用策略 |

## 项目结构

```
quantfq/
├── core/           # 基础组件、配置、日志
├── data/           # 数据获取、清洗、存储
│   └── fetcher.py  #   Yahoo / miniQMT / 东方财富适配器
├── indicators/     # 技术指标和基本面指标
├── strategy/       # 策略基类和信号
├── backtest/       # 回测引擎、指标计算
│   └── optimizer/  #   网格搜索、随机搜索、滚动前推
├── screener/       # 股票筛选
│   ├── filters.py  #   价格、成交量、技术面过滤器
│   └── strategies/ #   可插拔筛选策略
├── portfolio/      # 组合管理、资金分配、再平衡
├── trader/         # 订单和持仓管理
├── live/           # 实盘交易引擎和网关
├── adapters/       # 数据和交易网关适配器
├── charts/         # 可视化（价格、信号、绩效）
├── web/            # FastAPI 仪表盘和 API
└── examples/       # 20+ 使用示例
```

## 示例

参见 `examples/` 目录，包含 20+ 个使用示例，涵盖数据获取、指标计算、回测、实盘交易等。

```bash
# 运行指定示例
python examples/basic_backtest.py
```

## 贡献

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v

# 代码检查
ruff check .

# 格式化
black .
```

## 许可证

[MIT](LICENSE)
