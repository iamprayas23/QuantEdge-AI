"""Billing and Usage Router"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from infrastructure.database.connection import get_db
from infrastructure.database.models import Workspace
from api_platform.auth.dependencies import get_current_workspace
from api_platform.billing import service

router = APIRouter(prefix="/billing", tags=["Billing & Usage"])


@router.get("/usage")
def get_usage(
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    return service.get_workspace_usage_summary(db, workspace.id)
