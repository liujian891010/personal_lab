from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    appkey: str


class AuthUserResponse(BaseModel):
    user_id: str
    user_name: str
    workspace_id: str
    workspace_name: str
    roles: list[str]
    appkey_status: str


class LoginResponse(BaseModel):
    user: AuthUserResponse


class LogoutResponse(BaseModel):
    status: str
