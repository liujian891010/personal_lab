from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ..config import settings


class ReportShareTokenError(ValueError):
    pass


class ReportShareTokenExpiredError(ReportShareTokenError):
    pass


@dataclass(frozen=True, slots=True)
class ReportShareTokenPayload:
    report_id: str
    workspace_id: str
    expires_at: str


@dataclass(frozen=True, slots=True)
class ReportShareLink:
    report_id: str
    share_token: str
    expires_at: str


class ReportShareService:
    def create_share_link(
        self,
        *,
        report_id: str,
        workspace_id: str,
        expires_in_hours: int = 168,
    ) -> ReportShareLink:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=max(expires_in_hours, 1))
        payload = {
            "v": 1,
            "report_id": report_id,
            "workspace_id": workspace_id,
            "exp": int(expires_at.timestamp()),
        }
        payload_segment = self._encode_segment(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signature_segment = self._sign(payload_segment)
        return ReportShareLink(
            report_id=report_id,
            share_token=f"{payload_segment}.{signature_segment}",
            expires_at=expires_at.isoformat(),
        )

    def verify_share_token(self, share_token: str, *, report_id: str) -> ReportShareTokenPayload:
        try:
            payload_segment, signature_segment = share_token.split(".", 1)
        except ValueError as exc:
            raise ReportShareTokenError("invalid share token") from exc

        expected_signature = self._sign(payload_segment)
        if not hmac.compare_digest(signature_segment, expected_signature):
            raise ReportShareTokenError("invalid share token")

        try:
            payload = json.loads(self._decode_segment(payload_segment))
        except Exception as exc:  # noqa: BLE001
            raise ReportShareTokenError("invalid share token") from exc

        token_report_id = str(payload.get("report_id") or "").strip()
        workspace_id = str(payload.get("workspace_id") or "").strip()
        exp = int(payload.get("exp") or 0)
        if not token_report_id or not workspace_id or exp <= 0:
            raise ReportShareTokenError("invalid share token")
        if token_report_id != report_id:
            raise ReportShareTokenError("invalid share token")

        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            raise ReportShareTokenExpiredError("share token expired")

        return ReportShareTokenPayload(
            report_id=token_report_id,
            workspace_id=workspace_id,
            expires_at=expires_at.isoformat(),
        )

    def _sign(self, payload_segment: str) -> str:
        digest = hmac.new(
            settings.session_secret.encode("utf-8"),
            payload_segment.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return self._encode_segment(digest)

    def _encode_segment(self, value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")

    def _decode_segment(self, value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(f"{value}{padding}")


report_share_service = ReportShareService()
