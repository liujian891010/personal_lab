"""
One-time migration: recalculate report_count for all report_folders.
Run from the backend/ directory:
    python migrate_folder_counts.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db import db_manager

db_manager.initialize()

with db_manager.session() as conn:
    conn.execute("""
        UPDATE report_folders
        SET report_count = (
            SELECT COUNT(*) FROM reports
            WHERE reports.folder_id_ref = report_folders.folder_id
        ),
        updated_at = datetime('now')
    """)
    rows = conn.execute("SELECT folder_id, folder_name, report_count FROM report_folders").fetchall()

print("Migration complete. Folder counts:")
for row in rows:
    print(f"  {row['folder_name']}: {row['report_count']}")
