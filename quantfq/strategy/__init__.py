"""
Strategy module for QuantFQ.
"""

from .base import BaseStrategy
from .signals import SignalGenerator

__all__ = [
    "BaseStrategy",
    "SignalGenerator"
]

