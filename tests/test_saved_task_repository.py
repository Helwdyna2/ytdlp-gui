"""Tests for saved task persistence."""

from datetime import datetime, timedelta

import pytest

from src.data.database import Database
from src.data.models import SavedTask, SavedTaskStatus
from src.data.repositories import SavedTaskRepository


@pytest.fixture(autouse=True)
def reset_database():
    """Keep the singleton database isolated per test."""
    Database.reset_instance()
    yield
    Database.reset_instance()


def _build_repository(tmp_path):
    db = Database(db_path=str(tmp_path / "saved_tasks.sqlite3"))
    return SavedTaskRepository(db)


def test_saved_task_round_trips_payload_and_summary(tmp_path):
    repo = _build_repository(tmp_path)
    task = SavedTask(
        status=SavedTaskStatus.PENDING,
        payload={"url": "https://example.com/video", "items": [1, 2]},
        summary={"title": "Example", "count": 2},
    )

    created = repo.create(task)
    fetched = repo.get_by_id(created.id)

    assert fetched is not None
    assert fetched.status == SavedTaskStatus.PENDING
    assert fetched.payload == task.payload
    assert fetched.summary == task.summary

    fetched.payload = {"url": "https://example.com/video-2", "items": [3]}
    fetched.summary = {"title": "Updated", "count": 1}
    fetched.status = SavedTaskStatus.IN_PROGRESS

    repo.update(fetched)

    updated = repo.get_by_id(created.id)
    assert updated is not None
    assert updated.status == SavedTaskStatus.IN_PROGRESS
    assert updated.payload == fetched.payload
    assert updated.summary == fetched.summary

    assert repo.mark_deleted(created.id) is True

    deleted = repo.get_by_id(created.id)
    assert deleted is not None
    assert deleted.status == SavedTaskStatus.DELETED
    assert deleted.deleted_at is not None
    assert repo.get_latest_unfinished() is None
    assert repo.list_unfinished() == []


def test_saved_task_latest_unfinished_prefers_most_recent_active_task(tmp_path):
    repo = _build_repository(tmp_path)
    base_time = datetime(2024, 1, 1, 12, 0, 0)

    repo.create(
        SavedTask(
            status=SavedTaskStatus.PENDING,
            payload={"id": "old"},
            summary={"title": "old"},
            created_at=base_time,
            updated_at=base_time,
        )
    )
    repo.create(
        SavedTask(
            status=SavedTaskStatus.COMPLETED,
            payload={"id": "done"},
            summary={"title": "done"},
            created_at=base_time + timedelta(minutes=1),
            updated_at=base_time + timedelta(minutes=1),
        )
    )
    repo.create(
        SavedTask(
            status=SavedTaskStatus.IN_PROGRESS,
            payload={"id": "newer"},
            summary={"title": "newer"},
            created_at=base_time + timedelta(minutes=2),
            updated_at=base_time + timedelta(minutes=2),
        )
    )

    latest = repo.get_latest_unfinished()
    unfinished = repo.list_unfinished()

    assert latest is not None
    assert latest.summary == {"title": "newer"}
    assert [task.summary["title"] for task in unfinished] == ["newer", "old"]
