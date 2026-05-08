"""Portfolio management module for QuantFQ."""

# Lazy imports to avoid hard dependency on pandas at import time
def __getattr__(name: str):
    _portfolio_map = {
        "Portfolio": ".portfolio",
        "PortfolioPosition": ".portfolio",
    }
    _allocator_map = {
        "Allocator": ".allocator",
        "EqualWeightAllocator": ".allocator",
        "MarketCapAllocator": ".allocator",
        "CustomWeightAllocator": ".allocator",
    }
    _rebalancer_map = {
        "Rebalancer": ".rebalancer",
        "PeriodicRebalancer": ".rebalancer",
        "ThresholdRebalancer": ".rebalancer",
    }
    all_map = {**_portfolio_map, **_allocator_map, **_rebalancer_map}
    if name in all_map:
        import importlib
        mod = importlib.import_module(all_map[name], __name__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Portfolio",
    "PortfolioPosition",
    "Allocator",
    "EqualWeightAllocator",
    "MarketCapAllocator",
    "CustomWeightAllocator",
    "Rebalancer",
    "PeriodicRebalancer",
    "ThresholdRebalancer",
]
