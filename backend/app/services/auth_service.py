from __future__ import annotations

import json
from dataclasses import dataclass
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..config import settings
from ..workspace import UserContext


class AuthenticationError(ValueError):
    """Raised when APPKEY authentication fails."""


@dataclass(frozen=True)
class AuthResult:
    user: UserContext


class AuthService:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, UserContext]] = {}
        self._cache_ttl_sec = 300.0

    def resolve_user_from_appkey(self, appkey: str) -> AuthResult:
        normalized_appkey = appkey.strip()
        if not normalized_appkey:
            raise AuthenticationError("appkey is required")

        cached = self._cache.get(normalized_appkey)
        now = monotonic()
        if cached is not None and cached[0] > now:
            return AuthResult(user=cached[1])

        payload = self._fetch_user_payload(normalized_appkey)
        user = self._build_user_context(payload)
        self._cache[normalized_appkey] = (now + self._cache_ttl_sec, user)
        return AuthResult(user=user)

    def login_with_appkey(self, appkey: str) -> AuthResult:
        return self.resolve_user_from_appkey(appkey)

    def _fetch_user_payload(self, appkey: str) -> dict:
        query = urlencode(
            {
                settings.appkey_query_param: appkey,
                "appCode": settings.appkey_app_code,
            }
        )
        request = Request(
            url=f"{settings.appkey_login_url}?{query}",
            method="GET",
            headers={"Accept": "application/json"},
        )
        try:
            with urlopen(request, timeout=settings.auth_http_timeout_sec) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            raise AuthenticationError(f"appkey login failed: upstream returned {exc.code}") from exc
        except URLError as exc:
            raise AuthenticationError("appkey login failed: upstream unavailable") from exc

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise AuthenticationError("appkey login failed: invalid upstream payload") from exc

        return data

    def _build_user_context(self, payload: dict) -> UserContext:
        user_payload = self._extract_candidate_user_payload(payload)
        user_id = self._pick_first_string(
            user_payload,
            "user_id",
            "userId",
            "userid",
            "uid",
            "id",
        )
        if user_id is None:
            raise AuthenticationError("appkey login failed: missing user_id")

        user_name = self._pick_first_string(
            user_payload,
            "user_name",
            "userName",
            "username",
            "name",
            "nickname",
            "displayName",
            "realName",
        ) or user_id

        workspace_id = self._pick_first_string(
            user_payload,
            "workspace_id",
            "workspaceId",
            "workspaceid",
            "tenant_id",
            "tenantId",
            "tenantid",
            "org_id",
            "orgId",
            "orgid",
            "space_id",
            "spaceId",
            "spaceid",
        ) or user_id
        workspace_name = self._pick_first_string(
            user_payload,
            "workspace_name",
            "workspaceName",
            "workspacename",
            "tenant_name",
            "tenantName",
            "tenantname",
            "org_name",
            "orgName",
            "orgname",
            "space_name",
            "spaceName",
            "spacename",
        ) or user_name

        roles = self._extract_roles(user_payload)
        appkey_status = self._pick_first_string(user_payload, "appkey_status", "appkeyStatus", "status") or "active"

        return UserContext(
            user_id=user_id,
            user_name=user_name,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            roles=roles,
            appkey_status=appkey_status,
        )

    def _extract_candidate_user_payload(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            raise AuthenticationError("appkey login failed: unexpected upstream payload")

        success_value = payload.get("success")
        if success_value is False:
            message = self._pick_first_string(payload, "message", "msg", "error") or "invalid appkey"
            raise AuthenticationError(message)

        for key in ("data", "result", "user", "payload"):
            value = payload.get(key)
            if isinstance(value, dict):
                return value

        return payload

    def _extract_roles(self, payload: dict) -> list[str]:
        raw_roles = payload.get("roles")
        if isinstance(raw_roles, list):
            roles = [str(item).strip() for item in raw_roles if str(item).strip()]
            if roles:
                return roles
        role = self._pick_first_string(payload, "role")
        return [role] if role else ["user"]

    def _pick_first_string(self, payload: dict, *keys: str) -> str | None:
        for key in keys:
            value = payload.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None


auth_service = AuthService()
