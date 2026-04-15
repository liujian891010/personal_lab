from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..config import sanitize_workspace_id, settings


class StorageError(RuntimeError):
    """Raised when storage operations fail."""


@dataclass(frozen=True, slots=True)
class StoragePointer:
    storage_provider: str
    storage_bucket: str
    object_key: str
    storage_status: str = "ready"


def storage_pointer_from_mapping(mapping: object | None) -> StoragePointer | None:
    if mapping is None:
        return None
    try:
        provider = str(mapping["storage_provider"] or "").strip()
        bucket = str(mapping["storage_bucket"] or "").strip()
        object_key = str(mapping["object_key"] or "").strip()
        status = str(mapping["storage_status"] or "ready").strip()
    except Exception:
        return None
    if not provider or not bucket or not object_key:
        return None
    return StoragePointer(
        storage_provider=provider,
        storage_bucket=bucket,
        object_key=object_key,
        storage_status=status or "ready",
    )


class StorageService:
    def __init__(self) -> None:
        self.provider = settings.object_storage_provider
        self.bucket = settings.object_storage_bucket
        self.root = settings.object_storage_root

    def write_workspace_bytes(self, *, workspace_id: str, namespace: str, relative_path: str, data: bytes) -> StoragePointer:
        object_key = self._workspace_object_key(workspace_id=workspace_id, namespace=namespace, relative_path=relative_path)
        self._write_bytes(bucket=self.bucket, object_key=object_key, data=data)
        return StoragePointer(
            storage_provider=self.provider,
            storage_bucket=self.bucket,
            object_key=object_key,
            storage_status="ready",
        )

    def write_workspace_text(
        self,
        *,
        workspace_id: str,
        namespace: str,
        relative_path: str,
        text: str,
        encoding: str = "utf-8",
    ) -> StoragePointer:
        return self.write_workspace_bytes(
            workspace_id=workspace_id,
            namespace=namespace,
            relative_path=relative_path,
            data=text.encode(encoding),
        )

    def read_bytes(self, pointer: StoragePointer) -> bytes:
        if pointer.storage_provider != "local":
            raise StorageError(f"unsupported storage provider: {pointer.storage_provider}")
        return self._resolve_local_path(pointer.storage_bucket, pointer.object_key).read_bytes()

    def read_text(self, pointer: StoragePointer, *, encoding: str = "utf-8") -> str:
        return self.read_bytes(pointer).decode(encoding)

    def delete(self, pointer: StoragePointer) -> None:
        if pointer.storage_provider != "local":
            raise StorageError(f"unsupported storage provider: {pointer.storage_provider}")
        path = self._resolve_local_path(pointer.storage_bucket, pointer.object_key)
        path.unlink(missing_ok=True)
        self._prune_empty_parents(path.parent, stop_at=(self.root / pointer.storage_bucket).resolve())

    def _workspace_object_key(self, *, workspace_id: str, namespace: str, relative_path: str) -> str:
        normalized_workspace = sanitize_workspace_id(workspace_id)
        normalized_namespace = namespace.replace("\\", "/").strip("/")
        normalized_relative = relative_path.replace("\\", "/").lstrip("/")
        return f"workspaces/{normalized_workspace}/{normalized_namespace}/{normalized_relative}"

    def _write_bytes(self, *, bucket: str, object_key: str, data: bytes) -> None:
        if self.provider != "local":
            raise StorageError(f"unsupported storage provider: {self.provider}")
        path = self._resolve_local_path(bucket, object_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def _resolve_local_path(self, bucket: str, object_key: str) -> Path:
        normalized_key = object_key.replace("\\", "/").lstrip("/")
        root = (self.root / bucket).resolve()
        candidate = (root / normalized_key).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise StorageError(f"object key escapes bucket root: {object_key}") from exc
        return candidate

    def _prune_empty_parents(self, path: Path, *, stop_at: Path) -> None:
        current = path.resolve()
        while current != stop_at:
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent


storage_service = StorageService()
