"""Repository for session state persistence."""

import json
from datetime import datetime
from typing import Optional, List
import logging

from ..database import Database
from ..models import Session

logger = logging.getLogger(__name__)


class SessionRepository:
    """
    Session state persistence.

    Handles save/restore of session state for crash recovery.
    """

    def __init__(self, database: Database):
        self.db = database

    def save(self, session: Session) -> int:
        """
        Save a new session or update existing one.

        Returns the session ID.
        """
        if session.id:
            # Update existing
            self.db.execute(
                """
                UPDATE sessions
                SET pending_urls = ?, completed_urls = ?, output_dir = ?,
                    concurrent_limit = ?, force_overwrite = ?, video_only = ?,
                    cookies_path = ?, is_active = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    json.dumps(session.pending_urls),
                    json.dumps(session.completed_urls),
                    session.output_dir,
                    session.concurrent_limit,
                    int(session.force_overwrite),
                    int(session.video_only),
                    session.cookies_path,
                    int(session.is_active),
                    datetime.now().isoformat(),
                    session.id
                )
            )
            return session.id
        else:
            # Insert new
            cursor = self.db.execute(
                """
                INSERT INTO sessions
                (pending_urls, completed_urls, output_dir, concurrent_limit,
                 force_overwrite, video_only, cookies_path, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    json.dumps(session.pending_urls),
                    json.dumps(session.completed_urls),
                    session.output_dir,
                    session.concurrent_limit,
                    int(session.force_overwrite),
                    int(session.video_only),
                    session.cookies_path,
                    int(session.is_active),
                    session.created_at.isoformat(),
                    datetime.now().isoformat()
                )
            )
            return cursor.lastrowid

    def get_latest(self) -> Optional[Session]:
        """Get the most recent session."""
        row = self.db.fetchone(
            """
            SELECT * FROM sessions
            ORDER BY updated_at DESC
            LIMIT 1
            """
        )
        if row:
            return Session.from_row(row)
        return None

    def get_active(self) -> Optional[Session]:
        """Get the active session if one exists."""
        row = self.db.fetchone(
            """
            SELECT * FROM sessions
            WHERE is_active = 1
            ORDER BY updated_at DESC
            LIMIT 1
            """
        )
        if row:
            return Session.from_row(row)
        return None

    def get_by_id(self, session_id: int) -> Optional[Session]:
        """Get session by ID."""
        row = self.db.fetchone(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,)
        )
        if row:
            return Session.from_row(row)
        return None

    def update_pending_urls(self, session_id: int, pending_urls: List[str]) -> bool:
        """Update the pending URLs for a session."""
        cursor = self.db.execute(
            """
            UPDATE sessions
            SET pending_urls = ?, updated_at = ?
            WHERE id = ?
            """,
            (json.dumps(pending_urls), datetime.now().isoformat(), session_id)
        )
        return cursor.rowcount > 0

    def add_completed_url(self, session_id: int, url: str) -> bool:
        """Add a URL to the completed list."""
        session = self.get_by_id(session_id)
        if not session:
            return False

        completed = session.completed_urls
        if url not in completed:
            completed.append(url)

        cursor = self.db.execute(
            """
            UPDATE sessions
            SET completed_urls = ?, updated_at = ?
            WHERE id = ?
            """,
            (json.dumps(completed), datetime.now().isoformat(), session_id)
        )
        return cursor.rowcount > 0

    def mark_inactive(self, session_id: int) -> bool:
        """Mark a session as inactive (completed or cancelled)."""
        cursor = self.db.execute(
            """
            UPDATE sessions
            SET is_active = 0, updated_at = ?
            WHERE id = ?
            """,
            (datetime.now().isoformat(), session_id)
        )
        return cursor.rowcount > 0

    def delete(self, session_id: int) -> bool:
        """Delete a session."""
        cursor = self.db.execute(
            "DELETE FROM sessions WHERE id = ?",
            (session_id,)
        )
        return cursor.rowcount > 0

    def delete_all(self) -> int:
        """Delete all sessions. Returns count of deleted records."""
        cursor = self.db.execute("DELETE FROM sessions")
        logger.info(f"Cleared {cursor.rowcount} session records")
        return cursor.rowcount

    def delete_inactive(self) -> int:
        """Delete all inactive sessions."""
        cursor = self.db.execute(
            "DELETE FROM sessions WHERE is_active = 0"
        )
        return cursor.rowcount
