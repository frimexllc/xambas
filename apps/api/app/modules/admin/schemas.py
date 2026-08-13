from typing import Literal

from pydantic import BaseModel, Field

AdminRole = Literal["super_admin", "editor"]


class AdminBootstrapRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=200)


class AdminCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=200)
    role: AdminRole = "editor"


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminSummary(BaseModel):
    id: str
    name: str
    email: str
    role: AdminRole
    created_at: str


class AdminSessionSummary(BaseModel):
    session_id: str
    token: str
    expires_at: str
    admin_id: str


class AdminLoginResponse(BaseModel):
    module: str
    status: str
    admin: AdminSummary
    session: AdminSessionSummary


class AdminListResponse(BaseModel):
    module: str
    total: int
    items: list[AdminSummary]


class AdminStatusResponse(BaseModel):
    module: str
    status: str
    has_admins: bool
