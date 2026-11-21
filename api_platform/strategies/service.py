"""Strategy & Version Service Layer"""
import json
import hashlib
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func

from infrastructure.database.models import Strategy, StrategyVersion


def compute_config_hash(strategy_type: str, parameters: Dict[str, Any]) -> str:
    """
    Compute a deterministic canonical SHA-256 hash of strategy type and parameters.
    Guarantees 100% reproducible snapshot identification.
    """
    canonical_payload = {
        "strategy_type": strategy_type.strip().lower(),
        "parameters": parameters,
    }
    canonical_str = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


def create_strategy(
    db: Session,
    workspace_id: UUID,
    user_id: UUID,
    name: str,
    description: Optional[str] = None,
    strategy_type: str = "rsi",
    initial_parameters: Optional[Dict[str, Any]] = None,
) -> Strategy:
    strategy = Strategy(
        workspace_id=workspace_id,
        user_id=user_id,
        name=name,
        description=description,
        strategy_type=strategy_type.lower(),
        is_live=False,
    )
    db.add(strategy)
    db.flush()

    # Create version 1
    params = initial_parameters or {}
    if not params:
        if strategy.strategy_type == "rsi":
            params = {
                "rsi_period": 14,
                "oversold": 30.0,
                "overbought": 70.0,
                "risk_per_trade_pct": 0.01,
                "risk_reward_ratio": 2.0,
                "atr_period": 14,
                "sl_atr_mult": 1.5,
                "max_bars_held": 48,
            }
        else:
            params = {
                "rsi_period": 14,
                "swing_window": 5,
                "entry_mode": "early_candlestick",
                "risk_per_trade_pct": 0.01,
                "risk_reward_ratio": 2.0,
                "atr_period": 14,
                "sl_buffer_atr": 0.2,
                "oversold_threshold": 35.0,
                "overbought_threshold": 65.0,
                "max_bars_held": 72,
            }

    code_hash = compute_config_hash(strategy.strategy_type, params)
    v1 = StrategyVersion(
        strategy_id=strategy.id,
        version_number=1,
        parameters=params,
        code_hash=code_hash,
        is_locked=True,
    )
    db.add(v1)
    db.commit()
    db.refresh(strategy)
    return strategy


def create_strategy_version(
    db: Session,
    strategy_id: UUID,
    parameters: Dict[str, Any],
) -> StrategyVersion:
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise ValueError("Strategy not found")

    # Determine next version number
    max_ver = (
        db.query(func.max(StrategyVersion.version_number))
        .filter(StrategyVersion.strategy_id == strategy_id)
        .scalar()
    )
    next_ver = 1 if max_ver is None else max_ver + 1

    code_hash = compute_config_hash(strategy.strategy_type, parameters)

    version = StrategyVersion(
        strategy_id=strategy_id,
        version_number=next_ver,
        parameters=parameters,
        code_hash=code_hash,
        is_locked=True,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def list_strategies(db: Session, workspace_id: UUID) -> List[Strategy]:
    return (
        db.query(Strategy)
        .filter(Strategy.workspace_id == workspace_id)
        .order_by(Strategy.created_at.desc())
        .all()
    )


def get_strategy(db: Session, strategy_id: UUID, workspace_id: UUID) -> Optional[Strategy]:
    return (
        db.query(Strategy)
        .filter(Strategy.id == strategy_id, Strategy.workspace_id == workspace_id)
        .first()
    )


def list_strategy_versions(db: Session, strategy_id: UUID) -> List[StrategyVersion]:
    return (
        db.query(StrategyVersion)
        .filter(StrategyVersion.strategy_id == strategy_id)
        .order_by(StrategyVersion.version_number.desc())
        .all()
    )


def get_strategy_version(db: Session, version_id: UUID) -> Optional[StrategyVersion]:
    return db.query(StrategyVersion).filter(StrategyVersion.id == version_id).first()
