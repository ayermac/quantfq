"""动量突破选股策略。

条件：
1. 沪深主板个股
2. 非 ST 个股
3. 近 10 日内有涨停
4. 非连板（最后一次涨停后已回调）
5. 近 3 日连续大单净流入 > 3000 万
6. 位于 5 日均线之上
7. 当前非涨停
"""

from typing import Dict, List, Optional

from ..filters import (
    BoardFilter,
    Filter,
    LimitUpFilter,
    MoneyFlowFilter,
    STFilter,
    TechnicalFilter,
)
from .base import ScreenStrategy, StrategyMeta


class MomentumBreakoutStrategy(ScreenStrategy):

    @property
    def meta(self) -> StrategyMeta:
        return StrategyMeta(
            name="momentum_breakout",
            label="动量突破选股",
            description="筛选近期涨停后回调、资金持续流入、站上均线的主板个股",
            conditions=[
                "沪深主板个股",
                "非 ST 个股",
                "近 10 日内有涨停",
                "非连板（涨停后已回调）",
                "近 3 日大单净流入 > 3000 万",
                "位于 5 日均线之上",
                "当前非涨停",
            ],
            default_params={
                "lookback_days": 10,
                "money_flow_days": 3,
                "min_money_flow": 3000,
                "sma_period": 5,
                "limit_pct": 9.8,
            },
        )

    def create_filters(self, params: Optional[Dict] = None) -> List[Filter]:
        p = {**self.meta.default_params, **(params or {})}
        return [
            BoardFilter(boards=("沪主板", "深主板")),
            STFilter(),
            LimitUpFilter(
                lookback_days=p["lookback_days"],
                require_in_period=True,
                exclude_consecutive=True,
                exclude_current=True,
                limit_pct=p["limit_pct"],
            ),
            MoneyFlowFilter(
                days=p["money_flow_days"],
                min_total=p["min_money_flow"],
            ),
            TechnicalFilter(
                indicator="sma",
                condition="gt",
                value=0,
                period=p["sma_period"],
            ),
        ]
