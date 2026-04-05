"""Saved task orchestration service."""

from typing import List, Optional

from ..data.models import SavedTask
from ..data.repositories.saved_task_repository import SavedTaskRepository


class SavedTaskService:
    """High-level access to saved task snapshots."""

    def __init__(self, saved_task_repository: SavedTaskRepository):
        self.repository = saved_task_repository

    def save_task(self, task: SavedTask) -> SavedTask:
        """Create or update a saved task snapshot."""
        if task.id is None:
            return self.repository.create(task)

        self.repository.update(task)
        return task

    def get_latest_recoverable_task(self) -> Optional[SavedTask]:
        """Return the newest unfinished task that can be recovered."""
        return self.repository.get_latest_unfinished()

    def list_unfinished_tasks(self) -> List[SavedTask]:
        """Return unfinished tasks ordered from newest to oldest."""
        return self.repository.list_unfinished()

    def delete_task(self, task_id: int) -> bool:
        """Mark a saved task as deleted."""
        return self.repository.mark_deleted(task_id)
