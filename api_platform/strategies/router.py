"""Strategies and Versions Router"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from infrastructure.database.connection import get_db
from infrastructure.database.models import User, Workspace
from api_platform.auth.dependencies import get_current_user, get_current_workspace
from api_platform.strategies import schemas, service

router = APIRouter(prefix="/strategies", tags=["Strategies"])


@router.post("/", response_model=schemas.StrategyResponse)
def create_strategy(
    payload: schemas.StrategyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
):
    strat = service.create_strategy(
        db=db,
        workspace_id=workspace.id,
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        strategy_type=payload.strategy_type,
        initial_parameters=payload.initial_parameters,
    )
    versions = service.list_strategy_versions(db, strat.id)
    latest_v = versions[0] if versions else None

    return schemas.StrategyResponse(
        id=strat.id,
        workspace_id=strat.workspace_id,
        user_id=strat.user_id,
        name=strat.name,
        description=strat.description,
        strategy_type=strat.strategy_type,
        is_live=strat.is_live,
        created_at=strat.created_at,
        latest_version=latest_v,
    )


@router.get("/", response_model=List[schemas.StrategyResponse])
def list_strategies(
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    strats = service.list_strategies(db, workspace.id)
    out = []
    for s in strats:
        versions = service.list_strategy_versions(db, s.id)
        latest_v = versions[0] if versions else None
        out.append(
            schemas.StrategyResponse(
                id=s.id,
                workspace_id=s.workspace_id,
                user_id=s.user_id,
                name=s.name,
                description=s.description,
                strategy_type=s.strategy_type,
                is_live=s.is_live,
                created_at=s.created_at,
                latest_version=latest_v,
            )
        )
    return out


@router.get("/{strategy_id}", response_model=schemas.StrategyResponse)
def get_strategy(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    s = service.get_strategy(db, strategy_id, workspace.id)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")

    versions = service.list_strategy_versions(db, s.id)
    latest_v = versions[0] if versions else None

    return schemas.StrategyResponse(
        id=s.id,
        workspace_id=s.workspace_id,
        user_id=s.user_id,
        name=s.name,
        description=s.description,
        strategy_type=s.strategy_type,
        is_live=s.is_live,
        created_at=s.created_at,
        latest_version=latest_v,
    )


@router.post("/{strategy_id}/versions", response_model=schemas.StrategyVersionResponse)
def create_version(
    strategy_id: UUID,
    payload: schemas.StrategyVersionCreate,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    s = service.get_strategy(db, strategy_id, workspace.id)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")

    return service.create_strategy_version(db, strategy_id, payload.parameters)


@router.get("/{strategy_id}/versions", response_model=List[schemas.StrategyVersionResponse])
def list_versions(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    s = service.get_strategy(db, strategy_id, workspace.id)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")

    return service.list_strategy_versions(db, strategy_id)
