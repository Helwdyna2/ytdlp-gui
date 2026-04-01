"""Manager for video trim operations."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import QObject, QRecursiveMutex, QMutexLocker, pyqtSignal

from ..data.models import TrimConfig, TrimJob, TrimStatus
from .trim_worker import TrimWorker

logger = logging.getLogger(__name__)


class TrimManager(QObject):
    """
    Manages video trim operations.

    Orchestrates the trim queue and spawns TrimWorker threads.

    Signals:
        job_started: Emits (job_id) when a job starts
        job_progress: Emits (job_id, percent, speed, eta) for progress updates
        job_completed: Emits (job_id, success, output_path, error) when job completes
        queue_progress: Emits (completed, total, in_progress) for queue status
        all_completed: Emitted when all jobs are done
    """

    job_started = pyqtSignal(int)
    job_progress = pyqtSignal(int, float, str, str)  # job_id, percent, speed, eta
    job_completed = pyqtSignal(
        int, bool, str, str
    )  # job_id, success, output_path, error
    queue_progress = pyqtSignal(int, int, int)  # completed, total, in_progress
    all_completed = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize the trim manager."""
        super().__init__(parent)

        self._mutex = QRecursiveMutex()
        self._config: Optional[TrimConfig] = None
        self._jobs: Dict[int, TrimJob] = {}
        self._workers: Dict[int, TrimWorker] = {}
        self._job_id_counter = 0

        self._completed_count = 0
        self._failed_count = 0
        self._is_running = False

    def set_config(self, config: TrimConfig) -> None:
        """Set the trim configuration."""
        with QMutexLocker(self._mutex):
            self._config = config

    def add_job(
        self,
        input_path: str,
        start_time: float,
        end_time: float,
        original_duration: float,
        output_dir: Optional[str] = None,
        lossless: Optional[bool] = None,
        output_path_override: Optional[str] = None,
    ) -> TrimJob:
        """
        Add a trim job to the queue.

        Args:
            input_path: Path to input video file
            start_time: Start time in seconds
            end_time: End time in seconds
            original_duration: Original video duration in seconds
            output_dir: Optional custom output directory
            lossless: Optional override for lossless setting

        Returns:
            The created TrimJob
        """
        with QMutexLocker(self._mutex):
            self._job_id_counter += 1
            job_id = self._job_id_counter

            # Determine output path
            input_file = Path(input_path)
            suffix = self._config.suffix if self._config else "_trimmed"
            out_dir = output_dir or (self._config.output_dir if self._config else None)

            if output_path_override:
                output_path = Path(output_path_override)
            elif out_dir:
                output_path = (
                    Path(out_dir) / f"{input_file.stem}{suffix}{input_file.suffix}"
                )
            else:
                output_path = (
                    input_file.parent / f"{input_file.stem}{suffix}{input_file.suffix}"
                )

            # Determine lossless setting
            use_lossless = (
                lossless
                if lossless is not None
                else (self._config.lossless if self._config else True)
            )

            job = TrimJob(
                id=job_id,
                input_path=input_path,
                output_path=str(output_path),
                start_time=start_time,
                end_time=end_time,
                original_duration=original_duration,
                lossless=use_lossless,
                status=TrimStatus.PENDING,
            )

            self._jobs[job_id] = job
            logger.debug(f"Added trim job {job_id}: {input_path}")

            return job

    def add_jobs_batch(
        self,
        files: List[str],
        durations: Dict[str, float],
        start_offset: float = 0.0,
        end_offset: Optional[float] = None,
        output_dir: Optional[str] = None,
    ) -> List[TrimJob]:
        """
        Add multiple trim jobs with the same trim offsets.

        Args:
            files: List of input file paths
            durations: Dict mapping file paths to their durations
            start_offset: Time to remove from start (seconds)
            end_offset: Time to remove from end (seconds), or None
            output_dir: Optional custom output directory

        Returns:
            List of created TrimJob objects
        """
        jobs = []
        for file_path in files:
            duration = durations.get(file_path, 0.0)
            if duration <= 0:
                logger.warning(f"Skipping {file_path}: unknown duration")
                continue

            start_time = start_offset
            end_time = duration - (end_offset or 0.0)

            if start_time >= end_time:
                logger.warning(f"Skipping {file_path}: invalid trim range")
                continue

            job = self.add_job(
                input_path=file_path,
                start_time=start_time,
                end_time=end_time,
                original_duration=duration,
                output_dir=output_dir,
            )
            jobs.append(job)

        return jobs

    def start(self) -> None:
        """Start processing the trim queue."""
        with QMutexLocker(self._mutex):
            if self._is_running:
                return

            self._is_running = True
            self._completed_count = 0
            self._failed_count = 0

        self._process_next_job()

    def _process_next_job(self) -> None:
        """Process the next pending job in the queue."""
        with QMutexLocker(self._mutex):
            if not self._is_running:
                return

            # Find next pending job
            pending_job = None
            for job in self._jobs.values():
                if job.status == TrimStatus.PENDING:
                    pending_job = job
                    break

            if not pending_job:
                # No more jobs, check if all complete
                if not self._workers:
                    self._is_running = False
                    self.all_completed.emit()
                return

            # Start the job
            job_id = pending_job.id
            pending_job.status = TrimStatus.IN_PROGRESS

            worker = TrimWorker(
                input_path=pending_job.input_path,
                output_path=pending_job.output_path,
                start_time=pending_job.start_time,
                end_time=pending_job.end_time,
                lossless=pending_job.lossless,
                parent=self,
            )

            # Connect signals
            worker.progress.connect(
                lambda p, s, e, jid=job_id: self._on_job_progress(jid, p, s, e)
            )
            worker.completed.connect(
                lambda success, out, err, jid=job_id: self._on_job_completed(
                    jid, success, out, err
                )
            )

            self._workers[job_id] = worker
            worker.start()

            self.job_started.emit(job_id)
            self._emit_queue_progress()

    def _on_job_progress(
        self, job_id: int, percent: float, speed: str, eta: str
    ) -> None:
        """Handle progress update from a worker."""
        with QMutexLocker(self._mutex):
            if job_id in self._jobs:
                self._jobs[job_id].progress_percent = percent

        self.job_progress.emit(job_id, percent, speed, eta)

    def _on_job_completed(
        self, job_id: int, success: bool, output_path: str, error: str
    ) -> None:
        """Handle job completion."""
        with QMutexLocker(self._mutex):
            if job_id in self._jobs:
                job = self._jobs[job_id]
                job.completed_at = datetime.now()

                if success:
                    job.status = TrimStatus.COMPLETED
                    self._completed_count += 1
                elif "Cancelled" in error:
                    job.status = TrimStatus.CANCELLED
                else:
                    job.status = TrimStatus.FAILED
                    job.error_message = error
                    self._failed_count += 1

            # Clean up worker
            if job_id in self._workers:
                worker = self._workers.pop(job_id)
                worker.deleteLater()

        self.job_completed.emit(job_id, success, output_path, error)
        self._emit_queue_progress()

        # Process next job
        self._process_next_job()

    def _emit_queue_progress(self) -> None:
        """Emit queue progress signal."""
        with QMutexLocker(self._mutex):
            completed = sum(
                1
                for j in self._jobs.values()
                if j.status
                in (TrimStatus.COMPLETED, TrimStatus.FAILED, TrimStatus.CANCELLED)
            )
            total = len(self._jobs)
            in_progress = len(self._workers)

        self.queue_progress.emit(completed, total, in_progress)

    def cancel_all(self) -> None:
        """Cancel all pending and running jobs."""
        with QMutexLocker(self._mutex):
            self._is_running = False

            # Cancel pending jobs
            for job in self._jobs.values():
                if job.status == TrimStatus.PENDING:
                    job.status = TrimStatus.CANCELLED

            # Cancel running workers
            for worker in self._workers.values():
                worker.cancel()

    def get_job(self, job_id: int) -> Optional[TrimJob]:
        """Get a job by ID."""
        with QMutexLocker(self._mutex):
            return self._jobs.get(job_id)

    def get_all_jobs(self) -> List[TrimJob]:
        """Get all jobs."""
        with QMutexLocker(self._mutex):
            return list(self._jobs.values())

    def clear_jobs(self) -> None:
        """Clear all completed jobs from the queue."""
        with QMutexLocker(self._mutex):
            self._jobs = {
                k: v
                for k, v in self._jobs.items()
                if v.status == TrimStatus.IN_PROGRESS
            }

    def reset_counts(self) -> None:
        """Reset completed/failed counts."""
        with QMutexLocker(self._mutex):
            self._completed_count = 0
            self._failed_count = 0

    @property
    def is_running(self) -> bool:
        """Check if the manager is currently processing jobs."""
        with QMutexLocker(self._mutex):
            return self._is_running

    @property
    def completed_count(self) -> int:
        """Get the number of completed jobs."""
        with QMutexLocker(self._mutex):
            return self._completed_count

    @property
    def failed_count(self) -> int:
        """Get the number of failed jobs."""
        with QMutexLocker(self._mutex):
            return self._failed_count
