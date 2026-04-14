from __future__ import annotations

from contextvars import ContextVar, Token

from pydantic import BaseModel, Field


class UserContext(BaseModel):
    user_id: str
    user_name: str
    workspace_id: str
    workspace_name: str
    roles: list[str] = Field(default_factory=list)
    appkey_status: str = "active"


_current_user_context: ContextVar[UserContext | None] = ContextVar("current_user_context", default=None)


def set_current_user_context(user: UserContext | None) -> Token:
    return _current_user_context.set(user)


def reset_current_user_context(token: Token) -> None:
    _current_user_context.reset(token)


def get_current_user_context() -> UserContext | None:
    return _current_user_context.get()


def get_current_workspace_id() -> str | None:
    user = get_current_user_context()
    if user is None:
        return None
    return user.workspace_id
