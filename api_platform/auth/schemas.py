"""Authentication & User Schemas"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", description="Valid email address")
    password: str = Field(..., min_length=6, max_length=72, description="Password between 6 and 72 characters")
    workspace_name: Optional[str] = Field("Default Workspace", description="Initial workspace name")


class UserLogin(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(..., max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    workspace_id: UUID


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    owner_id: UUID
    role: Optional[str] = "owner"
    created_at: datetime

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: UUID
    email: str
    is_active: bool
    is_verified: bool
    workspaces: List[WorkspaceResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True
