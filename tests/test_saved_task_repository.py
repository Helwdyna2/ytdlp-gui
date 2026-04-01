"""Tests for saved task persistence."""

import sqlite3
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


def _seed_legacy_v4_saved_tasks_db(db_path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE saved_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL DEFAULT 'pending',
                payload TEXT NOT NULL DEFAULT '{}',
                summary TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                CONSTRAINT chk_saved_task_status CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'deleted'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO schema_version (version, description) VALUES (?, ?)",
            (4, "Legacy saved_tasks schema"),
        )
        conn.execute(
            """
            INSERT INTO saved_tasks (status, payload, summary, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "pending",
                '{"job":"legacy","task_type":"download"}',
                '{"title":"Legacy task"}',
                "2024-01-01T12:00:00",
                "2024-01-01T12:00:00",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def test_saved_task_round_trips_payload_and_summary(tmp_path):
    repo = _build_repository(tmp_path)
    task = SavedTask(
        task_type="export",
        title="Export clip",
        status=SavedTaskStatus.ACTIVE,
        payload={"url": "https://example.com/video", "items": [1, 2]},
        summary={"title": "Example", "count": 2},
    )

    created = repo.create(task)
    fetched = repo.get_by_id(created.id)

    assert fetched is not None
    assert fetched.task_type == "export"
    assert fetched.title == "Export clip"
    assert fetched.status == SavedTaskStatus.ACTIVE
    assert fetched.payload == task.payload
    assert fetched.summary == task.summary

    fetched.task_type = "download"
    fetched.title = "Updated export"
    fetched.payload = {"url": "https://example.com/video-2", "items": [3]}
    fetched.summary = {"title": "Updated", "count": 1}
    fetched.status = SavedTaskStatus.PAUSED

    repo.update(fetched)

    updated = repo.get_by_id(created.id)
    assert updated is not None
    assert updated.task_type == "download"
    assert updated.title == "Updated export"
    assert updated.status == SavedTaskStatus.PAUSED
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
            task_type="download",
            title="Old task",
            status=SavedTaskStatus.ACTIVE,
            payload={"id": "old"},
            summary={"title": "old"},
            created_at=base_time,
            updated_at=base_time,
        )
    )
    repo.create(
        SavedTask(
            task_type="download",
            title="Done task",
            status=SavedTaskStatus.COMPLETED,
            payload={"id": "done"},
            summary={"title": "done"},
            created_at=base_time + timedelta(minutes=1),
            updated_at=base_time + timedelta(minutes=1),
        )
    )
    repo.create(
        SavedTask(
            task_type="download",
            title="Newest task",
            status=SavedTaskStatus.PAUSED,
            payload={"id": "newer"},
            summary={"title": "newer"},
            created_at=base_time + timedelta(minutes=2),
            updated_at=base_time + timedelta(minutes=2),
        )
    )

    latest = repo.get_latest_unfinished()
    unfinished = repo.list_unfinished()

    assert latest is not None
    assert latest.task_type == "download"
    assert latest.title == "Newest task"
    assert latest.summary == {"title": "newer"}
    assert [task.summary["title"] for task in unfinished] == ["newer", "old"]


def test_database_repairs_legacy_v4_saved_tasks_schema(tmp_path):
    db_path = str(tmp_path / "saved_tasks.sqlite3")
    _seed_legacy_v4_saved_tasks_db(db_path)

    database = Database(db_path=db_path)
    repo = SavedTaskRepository(database)

    restored = repo.get_by_id(1)
    assert restored is not None
    assert restored.task_type == "download"
    assert restored.title == "Legacy task"
    assert restored.status == SavedTaskStatus.ACTIVE
    assert restored.payload == {"job": "legacy", "task_type": "download"}
    assert restored.summary == {"title": "Legacy task"}

    created = repo.create(
        SavedTask(
            task_type="trim",
            title="Trim task",
            status=SavedTaskStatus.PAUSED,
            payload={"clip": "a"},
            summary={"title": "Trim task"},
        )
    )
    created.title = "Trim task updated"
    created.summary = {"title": "Trim task updated"}
    repo.update(created)

    updated = repo.get_by_id(created.id)
    assert updated is not None
    assert updated.title == "Trim task updated"
    assert updated.status == SavedTaskStatus.PAUSED
    assert repo.get_latest_unfinished() is not None
