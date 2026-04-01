"""Repository for saved task persistence."""

import json
import logging
from datetime import datetime
from typing import List, Optional

from ..database import Database
from ..models import SavedTask, SavedTaskStatus

logger = logging.getLogger(__name__)


class SavedTaskRepository:
    """Repository for saved task snapshots."""

    _UNFINISHED_STATUSES = (
        SavedTaskStatus.ACTIVE,
        SavedTaskStatus.PAUSED,
        SavedTaskStatus.FAILED,
    )

    def __init__(self, database: Database):
        self.db = database

    def create(self, task: SavedTask) -> SavedTask:
        """Insert a new saved task and return it with its assigned ID."""
        cursor = self.db.execute(
            """
            INSERT INTO saved_tasks (
                task_type, title, status, summary_json, payload_json,
                created_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.task_type,
                task.title,
                task.status.value,
                json.dumps(task.summary),
                json.dumps(task.payload),
                task.created_at.isoformat(),
                task.updated_at.isoformat(),
                task.deleted_at.isoformat() if task.deleted_at else None,
            ),
        )
        task.id = cursor.lastrowid
        return task

    def update(self, task: SavedTask) -> None:
        """Update an existing saved task."""
        if task.id is None:
            raise ValueError("Cannot update saved task without ID")

        task.updated_at = datetime.now()
        self.db.execute(
            """
            UPDATE saved_tasks
            SET task_type = ?, title = ?, status = ?,
                summary_json = ?, payload_json = ?, updated_at = ?, deleted_at = ?
            WHERE id = ?
            """,
            (
                task.task_type,
                task.title,
                task.status.value,
                json.dumps(task.summary),
                json.dumps(task.payload),
                task.updated_at.isoformat(),
                task.deleted_at.isoformat() if task.deleted_at else None,
                task.id,
            ),
        )

    def get_by_id(self, task_id: int) -> Optional[SavedTask]:
        """Get a saved task by ID."""
        row = self.db.fetchone(
            "SELECT * FROM saved_tasks WHERE id = ?",
            (task_id,),
        )
        if row:
            return SavedTask.from_row(row)
        return None

    def get_latest_unfinished(self) -> Optional[SavedTask]:
        """Get the most recently updated unfinished task."""
        row = self.db.fetchone(
            """
            SELECT * FROM saved_tasks
            WHERE deleted_at IS NULL AND status IN (?, ?, ?)
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
            """,
            tuple(status.value for status in self._UNFINISHED_STATUSES),
        )
        if row:
            return SavedTask.from_row(row)
        return None

    def list_unfinished(self) -> List[SavedTask]:
        """List unfinished tasks, newest first."""
        rows = self.db.fetchall(
            """
            SELECT * FROM saved_tasks
            WHERE deleted_at IS NULL AND status IN (?, ?, ?)
            ORDER BY updated_at DESC, id DESC
            """,
            tuple(status.value for status in self._UNFINISHED_STATUSES),
        )
        return [SavedTask.from_row(row) for row in rows]

    def mark_deleted(self, task_id: int) -> bool:
        """Soft-delete a saved task."""
        now = datetime.now().isoformat()
        cursor = self.db.execute(
            """
            UPDATE saved_tasks
            SET status = ?, deleted_at = ?, updated_at = ?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (SavedTaskStatus.DELETED.value, now, now, task_id),
        )
        return cursor.rowcount > 0
