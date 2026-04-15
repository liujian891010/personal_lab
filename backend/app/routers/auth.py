from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, HTTPException, status

from ..config import ensure_workspace_dirs, get_workspace_sqlite_path
from ..db import db_manager
from ..schemas.auth import AuthUserResponse, LogoutResponse
from ..services.auth_service import AuthenticationError, auth_service
from ..workspace import UserContext, reset_current_user_context, set_current_user_context


router = APIRouter(prefix="/api/auth", tags=["auth"])


async def _bind_user_context_from_appkey(appkey: str | None, *, required: bool) -> AsyncIterator[UserContext | None]:
    normalized_appkey = (appkey or "").strip()
    if not normalized_appkey:
        if required:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
        yield None
        return
    try:
        result = auth_service.resolve_user_from_appkey(normalized_appkey)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    ensure_workspace_dirs(result.user.workspace_id)
    db_manager.initialize(db_path=get_workspace_sqlite_path(result.user.workspace_id))
    token = set_current_user_context(result.user)
    try:
        yield result.user
    finally:
        reset_current_user_context(token)


async def bind_optional_user_context(
    x_appkey: str | None = Header(default=None, alias="X-Appkey"),
) -> AsyncIterator[UserContext | None]:
    async for user in _bind_user_context_from_appkey(x_appkey, required=False):
        yield user


async def require_user(x_appkey: str | None = Header(default=None, alias="X-Appkey")) -> AsyncIterator[UserContext]:
    async for user in _bind_user_context_from_appkey(x_appkey, required=True):
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
        yield user


@router.get("/me", response_model=AuthUserResponse)
def get_me(current_user: UserContext = Depends(require_user)) -> AuthUserResponse:
    return AuthUserResponse(**current_user.model_dump())


@router.post("/logout", response_model=LogoutResponse)
def logout() -> LogoutResponse:
    return LogoutResponse(status="ok")
