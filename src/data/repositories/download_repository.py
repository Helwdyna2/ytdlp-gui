"""Repository for download history CRUD operations."""

from datetime import datetime
from typing import Optional, List, Set
import logging

from ..database import Database
from ..models import Download, DownloadStatus

logger = logging.getLogger(__name__)


class DownloadRepository:
    """
    CRUD operations for download history.

    Tracks all downloaded URLs to enable skip-on-future-runs.
    """

    def __init__(self, database: Database):
        self.db = database

    def save(self, download: Download) -> int:
        """
        Save or update a download record.

        Returns the download ID.
        """
        cursor = self.db.execute(
            """
            INSERT OR REPLACE INTO downloads
            (url, title, output_path, file_size, status, error_message, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                download.url,
                download.title,
                download.output_path,
                download.file_size,
                download.status.value,
                download.error_message,
                download.created_at.isoformat(),
                download.completed_at.isoformat() if download.completed_at else None
            )
        )
        return cursor.lastrowid

    def get_by_url(self, url: str) -> Optional[Download]:
        """Get download record by URL."""
        row = self.db.fetchone(
            "SELECT * FROM downloads WHERE url = ?",
            (url,)
        )
        if row:
            return Download.from_row(row)
        return None

    def get_by_id(self, download_id: int) -> Optional[Download]:
        """Get download record by ID."""
        row = self.db.fetchone(
            "SELECT * FROM downloads WHERE id = ?",
            (download_id,)
        )
        if row:
            return Download.from_row(row)
        return None

    def is_downloaded(self, url: str) -> bool:
        """Check if URL was already downloaded successfully."""
        row = self.db.fetchone(
            """
            SELECT 1 FROM downloads
            WHERE url = ? AND status = 'completed'
            LIMIT 1
            """,
            (url,)
        )
        return row is not None

    def get_downloaded_urls(self, urls: List[str]) -> Set[str]:
        """
        Get set of URLs that have already been downloaded successfully.

        Efficiently checks multiple URLs in a single query.
        """
        if not urls:
            return set()

        placeholders = ','.join('?' * len(urls))
        rows = self.db.fetchall(
            f"""
            SELECT url FROM downloads
            WHERE url IN ({placeholders}) AND status = 'completed'
            """,
            tuple(urls)
        )
        return {row['url'] for row in rows}

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Download]:
        """Get all downloads with pagination."""
        rows = self.db.fetchall(
            """
            SELECT * FROM downloads
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )
        return [Download.from_row(row) for row in rows]

    def get_by_status(self, status: DownloadStatus, limit: int = 100) -> List[Download]:
        """Get downloads by status."""
        rows = self.db.fetchall(
            """
            SELECT * FROM downloads
            WHERE status = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (status.value, limit)
        )
        return [Download.from_row(row) for row in rows]

    def get_count(self) -> int:
        """Get total number of downloads."""
        row = self.db.fetchone("SELECT COUNT(*) as count FROM downloads")
        return row['count'] if row else 0

    def get_count_by_status(self, status: DownloadStatus) -> int:
        """Get count of downloads by status."""
        row = self.db.fetchone(
            "SELECT COUNT(*) as count FROM downloads WHERE status = ?",
            (status.value,)
        )
        return row['count'] if row else 0

    def delete_by_id(self, download_id: int) -> bool:
        """Delete a download by ID."""
        cursor = self.db.execute(
            "DELETE FROM downloads WHERE id = ?",
            (download_id,)
        )
        return cursor.rowcount > 0

    def delete_by_url(self, url: str) -> bool:
        """Delete a download by URL."""
        cursor = self.db.execute(
            "DELETE FROM downloads WHERE url = ?",
            (url,)
        )
        return cursor.rowcount > 0

    def delete_all(self) -> int:
        """Delete all download records. Returns count of deleted records."""
        cursor = self.db.execute("DELETE FROM downloads")
        logger.info(f"Cleared {cursor.rowcount} download records")
        return cursor.rowcount

    def update_status(self, url: str, status: DownloadStatus, error_message: Optional[str] = None) -> bool:
        """Update the status of a download."""
        cursor = self.db.execute(
            """
            UPDATE downloads
            SET status = ?, error_message = ?, updated_at = ?
            WHERE url = ?
            """,
            (status.value, error_message, datetime.now().isoformat(), url)
        )
        return cursor.rowcount > 0

    def mark_completed(self, url: str, title: Optional[str] = None,
                       output_path: Optional[str] = None, file_size: Optional[int] = None) -> bool:
        """Mark a download as completed with metadata."""
        cursor = self.db.execute(
            """
            UPDATE downloads
            SET status = 'completed', title = COALESCE(?, title),
                output_path = COALESCE(?, output_path),
                file_size = COALESCE(?, file_size),
                completed_at = ?
            WHERE url = ?
            """,
            (title, output_path, file_size, datetime.now().isoformat(), url)
        )
        return cursor.rowcount > 0
