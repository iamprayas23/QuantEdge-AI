"""Strategy & Immutable Version Schemas"""
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class StrategyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    strategy_type: str = Field("rsi", description="'rsi' or 'divergence'")
    initial_parameters: Optional[Dict[str, Any]] = None


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_live: Optional[bool] = None


class StrategyVersionResponse(BaseModel):
    id: UUID
    strategy_id: UUID
    version_number: int
    parameters: Dict[str, Any]
    code_hash: str
    is_locked: bool
    created_at: datetime

    class Config:
        from_attributes = True


class StrategyResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    strategy_type: str
    is_live: bool
    created_at: datetime
    latest_version: Optional[StrategyVersionResponse] = None

    class Config:
        from_attributes = True


class StrategyVersionCreate(BaseModel):
    parameters: Dict[str, Any] = Field(..., description="Exact strategy parameters to snapshot into a new version")
