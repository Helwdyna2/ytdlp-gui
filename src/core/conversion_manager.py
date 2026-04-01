"""Manager for batch video conversion operations."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import QObject, pyqtSignal, QMutexLocker, QRecursiveMutex

from ..core.conversion_paths import build_conversion_output_path
from ..core.ffmpeg_worker import FFmpegWorker
from ..core.job_creation_worker import JobCreationWorker
from ..data.models import ConversionConfig, ConversionJob, ConversionStatus
from ..data.repositories.conversion_repository import ConversionRepository

logger = logging.getLogger(__name__)


class ConversionManager(QObject):
    """
    Manager for batch video conversion operations.

    Signals:
        job_started: Emits job_id when a conversion starts
        job_progress: Emits (job_id, percent, speed, eta)
        job_completed: Emits (job_id, success, output_path, error_message)
        queue_progress: Emits (completed, total, in_progress)
        all_completed: Emits when all jobs are done
        job_creation_progress: Emits (current, total) during async job creation
        jobs_created: Emits list of created jobs after async creation
        log: Emits (level, message) for logging
    """

    job_started = pyqtSignal(int)  # job_id
    job_progress = pyqtSignal(int, float, str, str)  # job_id, percent, speed, eta
    job_completed = pyqtSignal(
        int, bool, str, str
    )  # job_id, success, output_path, error_message
    queue_progress = pyqtSignal(int, int, int)  # completed, total, in_progress
    all_completed = pyqtSignal()
    job_creation_progress = pyqtSignal(int, int)  # current, total
    jobs_created = pyqtSignal(list)  # List[ConversionJob]
    log = pyqtSignal(str, str)  # level, message
    files_deleted = pyqtSignal(int, list)  # count, paths

    def __init__(self, repository: Optional[ConversionRepository] = None, parent=None):
        """
        Initialize the conversion manager.

        Args:
            repository: Repository for persisting jobs (creates new if None)
            parent: Parent QObject
        """
        super().__init__(parent)
        self._repository = repository or ConversionRepository()
        self._mutex = QRecursiveMutex()

        # Job tracking
        self._pending_jobs: List[ConversionJob] = []
        self._active_workers: Dict[int, FFmpegWorker] = {}  # job_id -> worker
        self._completed_count = 0
        self._failed_count = 0
        self._last_saved_progress_bucket: Dict[int, int] = {}

        # Job creation worker
        self._job_creation_worker: Optional[JobCreationWorker] = None

        # Configuration
        self._max_concurrent = 1  # Only one conversion at a time by default
        self._config: Optional[ConversionConfig] = None

    @property
    def is_running(self) -> bool:
        """Check if any conversions are in progress."""
        with QMutexLocker(self._mutex):
            return len(self._active_workers) > 0

    @property
    def pending_count(self) -> int:
        """Get number of pending jobs."""
        with QMutexLocker(self._mutex):
            return len(self._pending_jobs)

    @property
    def active_count(self) -> int:
        """Get number of active conversions."""
        with QMutexLocker(self._mutex):
            return len(self._active_workers)

    def set_config(self, config: ConversionConfig) -> None:
        """
        Set the conversion configuration.

        Args:
            config: ConversionConfig to use for all jobs
        """
        self._config = config

    def add_files(
        self,
        input_paths: List[str],
        output_dir: Optional[str] = None,
        output_paths: Optional[Dict[str, str]] = None,
    ) -> List[ConversionJob]:
        """
        Add files to the conversion queue.

        Args:
            input_paths: List of input video file paths
            output_dir: Output directory (uses config if None)

        Returns:
            List of created ConversionJob objects
        """
        if not self._config:
            self._config = ConversionConfig()

        output_directory = output_dir or self._config.output_dir
        if not output_directory:
            output_directory = str(Path(input_paths[0]).parent) if input_paths else "."

        jobs = []
        for input_path in input_paths:
            job = self._create_job(
                input_path,
                output_directory,
                output_path=output_paths.get(input_path) if output_paths else None,
            )
            jobs.append(job)

            with QMutexLocker(self._mutex):
                self._pending_jobs.append(job)

        self._emit_queue_progress()
        return jobs

    def add_files_async(
        self,
        input_paths: List[str],
        output_dir: Optional[str] = None,
        output_paths: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Add files to the conversion queue asynchronously (non-blocking).

        This method creates jobs in a background thread to avoid blocking the UI
        when processing many files. Progress is emitted via job_creation_progress
        signal, and completion is signaled via jobs_created.

        Args:
            input_paths: List of input video file paths
            output_dir: Output directory (uses config if None)
        """
        if not self._config:
            self._config = ConversionConfig()

        output_directory = output_dir or self._config.output_dir
        if not output_directory:
            output_directory = str(Path(input_paths[0]).parent) if input_paths else "."

        # Create worker for background job creation
        self._job_creation_worker = JobCreationWorker(
            input_paths=input_paths,
            output_dir=output_directory,
            output_paths=output_paths,
            config=self._config,
            repository=self._repository,
            parent=self,
        )

        # Connect signals
        self._job_creation_worker.progress.connect(self._on_job_creation_progress)
        self._job_creation_worker.completed.connect(self._on_jobs_created)
        self._job_creation_worker.error.connect(self._on_job_creation_error)
        self._job_creation_worker.files_deleted.connect(
            self._on_job_creation_files_deleted
        )

        # Start worker
        self._job_creation_worker.start()
        logger.info(f"Started async job creation for {len(input_paths)} files")

    def _on_job_creation_progress(self, current: int, total: int) -> None:
        """Handle progress update from job creation worker."""
        self.job_creation_progress.emit(current, total)

    def _on_jobs_created(self, jobs: List[ConversionJob]) -> None:
        """Handle completion of async job creation."""
        # Add jobs to pending queue
        with QMutexLocker(self._mutex):
            self._pending_jobs.extend(jobs)

        # Emit signals
        self._emit_queue_progress()
        self.jobs_created.emit(jobs)

        # Clean up worker
        if self._job_creation_worker:
            self._job_creation_worker.deleteLater()
            self._job_creation_worker = None

        logger.info(f"Async job creation completed: {len(jobs)} jobs created")

    def _on_job_creation_error(self, error: str) -> None:
        """Handle error from job creation worker."""
        self.log.emit("error", f"Job creation failed: {error}")

        # Clean up worker
        if self._job_creation_worker:
            self._job_creation_worker.deleteLater()
            self._job_creation_worker = None

    def _on_job_creation_files_deleted(self, count: int, paths: List[str]) -> None:
        """Forward files_deleted signal from job creation worker."""
        self.files_deleted.emit(count, paths)

    def _create_job(
        self,
        input_path: str,
        output_dir: str,
        output_path: Optional[str] = None,
    ) -> ConversionJob:
        """
        Create a conversion job.

        Args:
            input_path: Path to input video
            output_dir: Output directory

        Returns:
            Created ConversionJob
        """
        config = self._config or ConversionConfig()

        # Generate output filename
        input_file = Path(input_path)
        resolved_output_path = output_path or build_conversion_output_path(
            input_path, output_dir=output_dir
        )

        # Get input file size
        input_size = input_file.stat().st_size if input_file.exists() else 0

        job = ConversionJob(
            input_path=input_path,
            output_path=resolved_output_path,
            status=ConversionStatus.PENDING,
            output_codec=config.output_codec,
            crf_value=config.crf_value,
            preset=config.preset,
            hardware_encoder=config.hardware_encoder
            if config.use_hardware_accel
            else None,
            input_size=input_size,
        )

        # Persist to database
        job = self._repository.create(job)
        logger.info(f"Created conversion job {job.id}: {input_path}")

        return job

    def start(self) -> None:
        """Start processing the conversion queue."""
        self._process_queue()

    def cancel_all(self) -> None:
        """Cancel all pending and active conversions."""
        with QMutexLocker(self._mutex):
            # Cancel active workers
            for job_id, worker in list(self._active_workers.items()):
                worker.cancel()

            # Mark pending jobs as cancelled
            for job in self._pending_jobs:
                job.status = ConversionStatus.CANCELLED
                self._repository.update(job)

            self._pending_jobs.clear()

        self.log.emit("info", "All conversions cancelled")

    def cancel_job(self, job_id: int) -> bool:
        """
        Cancel a specific job.

        Args:
            job_id: ID of job to cancel

        Returns:
            True if job was found and cancelled
        """
        with QMutexLocker(self._mutex):
            # Check if it's an active job
            if job_id in self._active_workers:
                self._active_workers[job_id].cancel()
                return True

            # Check if it's pending
            for i, job in enumerate(self._pending_jobs):
                if job.id == job_id:
                    job.status = ConversionStatus.CANCELLED
                    self._repository.update(job)
                    self._pending_jobs.pop(i)
                    return True

        return False

    def _process_queue(self) -> None:
        """Process pending jobs if capacity available."""
        while True:
            job: Optional[ConversionJob] = None
            with QMutexLocker(self._mutex):
                if len(self._active_workers) >= self._max_concurrent:
                    return
                if not self._pending_jobs:
                    return
                job = self._pending_jobs.pop(0)

            if job is not None:
                self._start_job(job)

    def _start_job(self, job: ConversionJob) -> None:
        """
        Start a conversion job.

        Args:
            job: ConversionJob to start
        """
        config = self._config or ConversionConfig()

        # Create worker
        worker = FFmpegWorker(
            input_path=job.input_path, output_path=job.output_path, config=config
        )

        # Connect signals - job.id is guaranteed to be set after create()
        job_id = job.id
        if job_id is None:
            logger.error("Job ID is None, cannot start conversion")
            return

        worker.progress.connect(
            lambda p, s, e, c, t, jid=job_id: self._on_progress(jid, p, s, e)
        )
        worker.completed.connect(
            lambda success, path, err, jid=job_id: self._on_completed(
                jid, success, path, err
            )
        )
        worker.log.connect(self.log.emit)

        # Update job status
        job.status = ConversionStatus.IN_PROGRESS
        self._repository.update(job)

        # Track worker
        with QMutexLocker(self._mutex):
            self._active_workers[job_id] = worker
            self._last_saved_progress_bucket[job_id] = -1

        # Emit signals
        self.job_started.emit(job_id)
        self._emit_queue_progress()

        # Start the worker
        worker.start()
        logger.info(f"Started conversion job {job_id}")

    def _on_progress(self, job_id: int, percent: float, speed: str, eta: str) -> None:
        """Handle progress update from worker."""
        self.job_progress.emit(job_id, percent, speed, eta)

        # Update job in database periodically (every 5%) without flooding.
        progress_bucket = int(percent) // 5  # 0..20
        last_bucket = self._last_saved_progress_bucket.get(job_id, -1)
        if progress_bucket <= last_bucket or progress_bucket == 0:
            return

        job = self._repository.get_by_id(job_id)
        if job:
            job.progress_percent = percent
            self._repository.update(job)
            self._last_saved_progress_bucket[job_id] = progress_bucket

    def _on_completed(
        self, job_id: int, success: bool, output_path: str, error_message: str
    ) -> None:
        """Handle completion of a conversion job."""
        all_done = False
        with QMutexLocker(self._mutex):
            # Remove worker from active list
            worker = self._active_workers.pop(job_id, None)
            self._last_saved_progress_bucket.pop(job_id, None)
            if worker:
                worker.deleteLater()

            if success:
                self._completed_count += 1
            else:
                self._failed_count += 1

            all_done = len(self._active_workers) == 0 and len(self._pending_jobs) == 0

        # Update job in database
        job = self._repository.get_by_id(job_id)
        if job:
            if success:
                job.status = ConversionStatus.COMPLETED
                job.progress_percent = 100.0
                job.completed_at = datetime.now()

                # Get output file size
                output_file = Path(output_path)
                if output_file.exists():
                    job.output_size = output_file.stat().st_size
            else:
                if "Cancelled" in error_message:
                    job.status = ConversionStatus.CANCELLED
                else:
                    job.status = ConversionStatus.FAILED
                job.error_message = error_message

            self._repository.update(job)

        # Emit signals
        self.job_completed.emit(job_id, success, output_path, error_message)
        self._emit_queue_progress()

        # Process next job
        self._process_queue()

        if all_done:
            self.all_completed.emit()
            self.log.emit(
                "info",
                f"All conversions complete. "
                f"Success: {self._completed_count}, Failed: {self._failed_count}",
            )

    def _emit_queue_progress(self) -> None:
        """Emit queue progress signal."""
        with QMutexLocker(self._mutex):
            completed = self._completed_count + self._failed_count
            total = completed + len(self._pending_jobs) + len(self._active_workers)
            in_progress = len(self._active_workers)

        self.queue_progress.emit(completed, total, in_progress)

    def get_job(self, job_id: int) -> Optional[ConversionJob]:
        """
        Get a job by ID.

        Args:
            job_id: Job ID

        Returns:
            ConversionJob if found
        """
        return self._repository.get_by_id(job_id)

    def get_history(self, limit: int = 50) -> List[ConversionJob]:
        """
        Get conversion history.

        Args:
            limit: Maximum number of results

        Returns:
            List of ConversionJob objects
        """
        return self._repository.get_all(limit=limit)

    def clear_history(self, days: int = 30) -> int:
        """
        Clear old conversion history.

        Args:
            days: Delete jobs older than this many days

        Returns:
            Number of jobs deleted
        """
        return self._repository.delete_old(days=days)

    def reset_counts(self) -> None:
        """Reset completion counters."""
        with QMutexLocker(self._mutex):
            self._completed_count = 0
            self._failed_count = 0

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
