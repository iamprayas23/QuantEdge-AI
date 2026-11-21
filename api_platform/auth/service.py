"""User and Workspace Service Layer"""
import uuid
import re
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from infrastructure.database.models import User, Workspace, UserWorkspace
from .hashing import hash_password, verify_password


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", s)


def create_user_with_workspace(
    db: Session, email: str, password: str, workspace_name: Optional[str] = None
) -> Optional[Tuple[User, Workspace]]:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return None

    # Create user
    user = User(
        email=email,
        hashed_password=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.flush()

    # Create default workspace
    ws_name = workspace_name or f"{email.split('@')[0]}'s Workspace"
    base_slug = slugify(ws_name)
    slug = f"{base_slug}-{str(uuid.uuid4())[:8]}"

    workspace = Workspace(
        name=ws_name,
        slug=slug,
        owner_id=user.id,
    )
    db.add(workspace)
    db.flush()

    # Add membership as owner
    membership = UserWorkspace(
        user_id=user.id,
        workspace_id=workspace.id,
        role="owner",
    )
    db.add(membership)
    db.commit()
    db.refresh(user)
    db.refresh(workspace)

    return user, workspace


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_user_primary_workspace(db: Session, user_id: uuid.UUID) -> Optional[Workspace]:
    membership = (
        db.query(UserWorkspace)
        .filter(UserWorkspace.user_id == user_id)
        .order_by(UserWorkspace.created_at.asc())
        .first()
    )
    if membership:
        return db.query(Workspace).filter(Workspace.id == membership.workspace_id).first()

    return db.query(Workspace).filter(Workspace.owner_id == user_id).first()
