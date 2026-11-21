"""Authentication & Workspace Router"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from infrastructure.database.connection import get_db
from infrastructure.database.models import User, Workspace, UserWorkspace
from api_platform.auth import schemas, service
from api_platform.auth.jwt import create_access_token
from api_platform.auth.dependencies import get_current_user, get_current_workspace

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=schemas.TokenResponse)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    res = service.create_user_with_workspace(
        db, email=payload.email, password=payload.password, workspace_name=payload.workspace_name
    )
    if not res:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    user, workspace = res
    token = create_access_token({"sub": str(user.id), "workspace_id": str(workspace.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "workspace_id": workspace.id,
    }


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = service.authenticate_user(db, email=payload.email, password=payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    workspace = service.get_user_primary_workspace(db, user.id)
    ws_id = workspace.id if workspace else None

    token = create_access_token({"sub": str(user.id), "workspace_id": str(ws_id) if ws_id else None})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "workspace_id": ws_id,
    }


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Gather memberships
    memberships = db.query(UserWorkspace).filter(UserWorkspace.user_id == current_user.id).all()
    workspaces = []
    for m in memberships:
        ws = db.query(Workspace).filter(Workspace.id == m.workspace_id).first()
        if ws:
            workspaces.append(
                schemas.WorkspaceResponse(
                    id=ws.id,
                    name=ws.name,
                    slug=ws.slug,
                    owner_id=ws.owner_id,
                    role=m.role,
                    created_at=ws.created_at,
                )
            )

    return schemas.UserResponse(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        workspaces=workspaces,
        created_at=current_user.created_at,
    )
