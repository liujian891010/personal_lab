from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from ..db import db_manager, row_to_dict


class FolderNotFoundError(Exception):
    pass


class FolderConflictError(Exception):
    pass


class FolderNotEmptyError(Exception):
    pass


def _slugify(name: str) -> str:
    slug = name.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FolderService:
    def list_folders(self) -> dict[str, Any]:
        with db_manager.session() as conn:
            rows = conn.execute(
                "SELECT folder_id, folder_name, folder_slug, description, sort_order, report_count, created_at, updated_at "
                "FROM report_folders ORDER BY sort_order, folder_name"
            ).fetchall()
            items = [row_to_dict(r) for r in rows]
            return {"items": items, "total": len(items)}

    def get_folder(self, folder_id: str) -> dict[str, Any]:
        with db_manager.session() as conn:
            row = conn.execute(
                "SELECT folder_id, folder_name, folder_slug, description, sort_order, report_count, created_at, updated_at "
                "FROM report_folders WHERE folder_id = ?",
                (folder_id,),
            ).fetchone()
            if row is None:
                raise FolderNotFoundError(f"folder not found: {folder_id}")
            return row_to_dict(row)

    def create_folder(self, *, folder_name: str, description: str | None, sort_order: int) -> dict[str, Any]:
        slug = _slugify(folder_name)
        folder_id = str(uuid.uuid4())
        now = _now()
        with db_manager.session() as conn:
            existing = conn.execute(
                "SELECT 1 FROM report_folders WHERE folder_name = ? COLLATE NOCASE OR folder_slug = ?",
                (folder_name, slug),
            ).fetchone()
            if existing:
                raise FolderConflictError(f"folder name already exists: {folder_name}")
            conn.execute(
                "INSERT INTO report_folders (folder_id, folder_name, folder_slug, description, sort_order, report_count, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 0, ?, ?)",
                (folder_id, folder_name, slug, description, sort_order, now, now),
            )
            return {
                "folder_id": folder_id,
                "folder_name": folder_name,
                "folder_slug": slug,
                "description": description,
                "sort_order": sort_order,
                "report_count": 0,
                "created_at": now,
                "updated_at": now,
            }

    def update_folder(self, folder_id: str, *, folder_name: str | None, description: str | None, sort_order: int | None) -> dict[str, Any]:
        with db_manager.session() as conn:
            row = conn.execute("SELECT * FROM report_folders WHERE folder_id = ?", (folder_id,)).fetchone()
            if row is None:
                raise FolderNotFoundError(f"folder not found: {folder_id}")
            updates: list[str] = []
            params: list[Any] = []
            if folder_name is not None:
                conflict = conn.execute(
                    "SELECT 1 FROM report_folders WHERE folder_name = ? COLLATE NOCASE AND folder_id != ?",
                    (folder_name, folder_id),
                ).fetchone()
                if conflict:
                    raise FolderConflictError(f"folder name already exists: {folder_name}")
                updates += ["folder_name = ?", "folder_slug = ?"]
                params += [folder_name, _slugify(folder_name)]
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if sort_order is not None:
                updates.append("sort_order = ?")
                params.append(sort_order)
            if updates:
                updates.append("updated_at = ?")
                params += [_now(), folder_id]
                conn.execute(f"UPDATE report_folders SET {', '.join(updates)} WHERE folder_id = ?", params)
            return self.get_folder(folder_id)

    def delete_folder(self, folder_id: str) -> None:
        with db_manager.session() as conn:
            row = conn.execute("SELECT report_count FROM report_folders WHERE folder_id = ?", (folder_id,)).fetchone()
            if row is None:
                raise FolderNotFoundError(f"folder not found: {folder_id}")
            if row["report_count"] > 0:
                raise FolderNotEmptyError("folder is not empty; move or remove reports first")
            conn.execute("DELETE FROM report_folders WHERE folder_id = ?", (folder_id,))

    def move_report(self, report_id: str, folder_id: str | None) -> None:
        with db_manager.session() as conn:
            row = conn.execute("SELECT folder_id_ref FROM reports WHERE report_id = ?", (report_id,)).fetchone()
            if row is None:
                raise ValueError(f"report not found: {report_id}")
            old_folder = row["folder_id_ref"]
            if folder_id is not None:
                exists = conn.execute("SELECT 1 FROM report_folders WHERE folder_id = ?", (folder_id,)).fetchone()
                if not exists:
                    raise FolderNotFoundError(f"folder not found: {folder_id}")
            conn.execute(
                "UPDATE reports SET folder_id_ref = ?, updated_at = ? WHERE report_id = ?",
                (folder_id, _now(), report_id),
            )
            if old_folder:
                conn.execute(
                    "UPDATE report_folders SET report_count = MAX(0, report_count - 1), updated_at = ? WHERE folder_id = ?",
                    (_now(), old_folder),
                )
            if folder_id:
                conn.execute(
                    "UPDATE report_folders SET report_count = report_count + 1, updated_at = ? WHERE folder_id = ?",
                    (_now(), folder_id),
                )


folder_service = FolderService()
