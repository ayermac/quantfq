"""Base class for screening strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..filters import Filter


@dataclass
class StrategyMeta:
    """Strategy metadata for UI display."""

    name: str
    label: str
    description: str
    conditions: List[str] = field(default_factory=list)
    default_params: Dict = field(default_factory=dict)


class ScreenStrategy(ABC):
    """Base class for stock screening strategies.

    Each strategy defines its filters, metadata, and parameter schema.
    Subclasses only need to implement `create_filters()` and `meta`.
    """

    @property
    @abstractmethod
    def meta(self) -> StrategyMeta:
        """Return strategy metadata for display."""
        pass

    @abstractmethod
    def create_filters(self, params: Optional[Dict] = None) -> List[Filter]:
        """Create filter chain from parameters.

        Args:
            params: User-provided parameters (overrides defaults).

        Returns:
            Ordered list of filters to apply.
        """
        pass

    def get_data_provider(self):
        """Return data provider instance. Override to customize."""
        from ..data_provider import AkshareDataProvider
        return AkshareDataProvider()
