"""Strategy Registry"""
from typing import Dict, Type, Any
from core.backtesting.strategies.base import BaseStrategy
from core.backtesting.strategies.rsi import RSIStrategy
from core.backtesting.strategies.divergence import DivergenceStrategy

STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {
    "rsi": RSIStrategy,
    "rsi_mean_reversion": RSIStrategy,
    "divergence": DivergenceStrategy,
    "divergence_strategy": DivergenceStrategy,
}


def get_strategy_class(strategy_type: str) -> Type[BaseStrategy]:
    clean_type = strategy_type.strip().lower()
    if clean_type not in STRATEGY_REGISTRY:
        available = list(STRATEGY_REGISTRY.keys())
        raise ValueError(f"Unknown strategy type '{strategy_type}'. Available: {available}")
    return STRATEGY_REGISTRY[clean_type]
