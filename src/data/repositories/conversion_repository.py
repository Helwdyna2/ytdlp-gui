"""Repository for conversion job persistence."""

import logging
from datetime import datetime
from typing import List, Optional

from ..database import Database
from ..models import ConversionJob, ConversionStatus

logger = logging.getLogger(__name__)


class ConversionRepository:
    """Repository for managing conversion job records in the database."""

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize the repository.
        
        Args:
            db: Database instance (uses singleton if not provided)
        """
        self._db = db or Database()

    def create(self, job: ConversionJob) -> ConversionJob:
        """
        Create a new conversion job record.
        
        Args:
            job: ConversionJob to persist
            
        Returns:
            ConversionJob with assigned ID
        """
        cursor = self._db.execute(
            """
            INSERT INTO conversion_jobs (
                input_path, output_path, status, output_codec, crf_value,
                preset, hardware_encoder, progress_percent, error_message,
                input_size, output_size, duration, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.input_path,
                job.output_path,
                job.status.value,
                job.output_codec,
                job.crf_value,
                job.preset,
                job.hardware_encoder,
                job.progress_percent,
                job.error_message,
                job.input_size,
                job.output_size,
                job.duration,
                job.created_at.isoformat(),
                job.completed_at.isoformat() if job.completed_at else None,
            )
        )
        job.id = cursor.lastrowid
        logger.debug(f"Created conversion job {job.id}: {job.input_path}")
        return job

    def update(self, job: ConversionJob) -> None:
        """
        Update an existing conversion job.
        
        Args:
            job: ConversionJob with updated fields
        """
        if job.id is None:
            raise ValueError("Cannot update job without ID")

        self._db.execute(
            """
            UPDATE conversion_jobs SET
                status = ?,
                progress_percent = ?,
                error_message = ?,
                output_size = ?,
                completed_at = ?
            WHERE id = ?
            """,
            (
                job.status.value,
                job.progress_percent,
                job.error_message,
                job.output_size,
                job.completed_at.isoformat() if job.completed_at else None,
                job.id,
            )
        )
        logger.debug(f"Updated conversion job {job.id}: status={job.status.value}")

    def get_by_id(self, job_id: int) -> Optional[ConversionJob]:
        """
        Get a conversion job by ID.
        
        Args:
            job_id: Database ID
            
        Returns:
            ConversionJob if found, None otherwise
        """
        row = self._db.fetchone(
            "SELECT * FROM conversion_jobs WHERE id = ?",
            (job_id,)
        )
        if row:
            return ConversionJob.from_row(row)
        return None

    def get_all(self, limit: int = 100, offset: int = 0) -> List[ConversionJob]:
        """
        Get all conversion jobs, ordered by creation date (newest first).
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of ConversionJob objects
        """
        rows = self._db.fetchall(
            """
            SELECT * FROM conversion_jobs 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )
        return [ConversionJob.from_row(row) for row in rows]

    def get_by_status(self, status: ConversionStatus, limit: int = 100) -> List[ConversionJob]:
        """
        Get conversion jobs by status.
        
        Args:
            status: Status to filter by
            limit: Maximum number of results
            
        Returns:
            List of ConversionJob objects
        """
        rows = self._db.fetchall(
            """
            SELECT * FROM conversion_jobs 
            WHERE status = ? 
            ORDER BY created_at DESC 
            LIMIT ?
            """,
            (status.value, limit)
        )
        return [ConversionJob.from_row(row) for row in rows]

    def get_pending_jobs(self) -> List[ConversionJob]:
        """
        Get all pending conversion jobs.
        
        Returns:
            List of pending ConversionJob objects
        """
        return self.get_by_status(ConversionStatus.PENDING)

    def get_recent(self, days: int = 7, limit: int = 50) -> List[ConversionJob]:
        """
        Get recent conversion jobs.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of results
            
        Returns:
            List of ConversionJob objects
        """
        rows = self._db.fetchall(
            """
            SELECT * FROM conversion_jobs 
            WHERE created_at >= datetime('now', ?)
            ORDER BY created_at DESC 
            LIMIT ?
            """,
            (f"-{days} days", limit)
        )
        return [ConversionJob.from_row(row) for row in rows]

    def delete(self, job_id: int) -> bool:
        """
        Delete a conversion job.
        
        Args:
            job_id: Database ID
            
        Returns:
            True if deleted, False if not found
        """
        cursor = self._db.execute(
            "DELETE FROM conversion_jobs WHERE id = ?",
            (job_id,)
        )
        deleted = cursor.rowcount > 0
        if deleted:
            logger.debug(f"Deleted conversion job {job_id}")
        return deleted

    def delete_old(self, days: int = 30) -> int:
        """
        Delete conversion jobs older than specified days.
        
        Args:
            days: Delete jobs older than this many days
            
        Returns:
            Number of jobs deleted
        """
        cursor = self._db.execute(
            """
            DELETE FROM conversion_jobs 
            WHERE created_at < datetime('now', ?)
            """,
            (f"-{days} days",)
        )
        count = cursor.rowcount
        if count > 0:
            logger.info(f"Deleted {count} old conversion jobs")
        return count

    def count_by_status(self) -> dict:
        """
        Get count of jobs by status.
        
        Returns:
            Dict mapping status to count
        """
        rows = self._db.fetchall(
            """
            SELECT status, COUNT(*) as count 
            FROM conversion_jobs 
            GROUP BY status
            """
        )
        return {row['status']: row['count'] for row in rows}
