"""Authentication & Workspace Dependencies"""
from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, Header
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from infrastructure.database.connection import get_db
from infrastructure.database.models import User, Workspace, UserWorkspace
from api_platform.auth.jwt import verify_token
from api_platform.auth.service import get_user_primary_workspace

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = verify_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        user_id = UUID(user_id_str)
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


def get_current_workspace(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
) -> Workspace:
    """
    Resolve workspace from X-Workspace-Id header if provided,
    otherwise fallback to user's primary/default workspace.
    """
    if x_workspace_id:
        try:
            ws_id = UUID(x_workspace_id)
            # Check user has access
            membership = (
                db.query(UserWorkspace)
                .filter(UserWorkspace.workspace_id == ws_id, UserWorkspace.user_id == current_user.id)
                .first()
            )
            if membership:
                ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
                if ws:
                    return ws
        except ValueError:
            pass

    # Fallback to primary workspace
    ws = get_user_primary_workspace(db, current_user.id)
    if not ws:
        raise HTTPException(status_code=404, detail="No active workspace found for user")
    return ws
