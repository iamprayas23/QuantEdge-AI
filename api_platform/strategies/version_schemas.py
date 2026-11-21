from pydantic import BaseModel
from typing import Dict, Any
from uuid import UUID


class StrategyVersionCreate(BaseModel):
    parameters: Dict[str, Any]
    code_hash: str


class StrategyVersionResponse(BaseModel):
    id: UUID
    strategy_id: UUID
    version_number: int
    parameters: Dict[str, Any]
    code_hash: str

    class Config:
        from_attributes = True