"""Stock screening strategies."""

from .base import ScreenStrategy
from .momentum_breakout import MomentumBreakoutStrategy

STRATEGIES = {
    "momentum_breakout": MomentumBreakoutStrategy,
}

__all__ = ["ScreenStrategy", "MomentumBreakoutStrategy", "STRATEGIES"]
