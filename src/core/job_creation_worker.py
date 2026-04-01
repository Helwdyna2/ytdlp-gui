"""Worker for creating conversion jobs in background thread."""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from ..core.conversion_paths import build_conversion_output_path
from ..data.models import ConversionConfig, ConversionJob, ConversionStatus
from ..data.repositories.conversion_repository import ConversionRepository
from ..utils.file_validation import cleanup_zero_byte_files

logger = logging.getLogger(__name__)


class JobCreationWorker(QThread):
    """
    QThread worker for creating conversion jobs without blocking the UI.

    This worker performs file I/O (stat) and database operations in a background
    thread to keep the UI responsive when adding many files for conversion.

    Signals:
        progress: Emits (current, total) for progress tracking
        completed: Emits list of created ConversionJob objects
        error: Emits error message if creation fails
        files_deleted: Emits (count, paths) when zero-byte files are trashed
    """

    progress = pyqtSignal(int, int)  # current, total
    completed = pyqtSignal(list)  # List[ConversionJob]
    error = pyqtSignal(str)
    files_deleted = pyqtSignal(int, list)  # count, paths

    def __init__(
        self,
        input_paths: List[str],
        output_dir: str,
        output_paths: Optional[Dict[str, str]],
        config: ConversionConfig,
        repository: ConversionRepository,
        parent=None,
    ):
        """
        Initialize the job creation worker.

        Args:
            input_paths: List of input video file paths
            output_dir: Output directory for converted files
            config: Conversion configuration
            repository: Repository for persisting jobs
            parent: Parent QObject
        """
        super().__init__(parent)
        self._input_paths = input_paths
        self._output_dir = output_dir
        self._output_paths = output_paths or {}
        self._config = config
        self._repository = repository
        self._cancelled = False

    def cancel(self) -> None:
        """Request cancellation of job creation."""
        self._cancelled = True

    def run(self) -> None:
        """Execute job creation in background thread."""
        try:
            # Filter out zero-byte files before creating jobs
            valid_paths, trashed_paths = cleanup_zero_byte_files(self._input_paths)
            self._input_paths = valid_paths

            if trashed_paths:
                logger.info(
                    f"Moved {len(trashed_paths)} zero-byte files to trash before conversion"
                )
                self.files_deleted.emit(len(trashed_paths), trashed_paths)

            jobs = []
            total = len(self._input_paths)
            last_progress_time = time.time()

            logger.info(f"JobCreationWorker: Starting creation of {total} jobs...")
            logger.debug(f"JobCreationWorker thread started for {total} files")

            for i, input_path in enumerate(self._input_paths):
                if self._cancelled:
                    logger.info("Job creation cancelled")
                    return

                # Create job (includes file stat and DB write)
                job = self._create_job(input_path)
                jobs.append(job)

                # Emit progress only every 5 files or every 500ms to avoid flooding UI
                current_time = time.time()
                if (
                    (i + 1) % 5 == 0
                    or (current_time - last_progress_time) >= 0.5
                    or i == total - 1
                ):
                    self.progress.emit(i + 1, total)
                    last_progress_time = current_time
                    # Give UI a moment to process
                    self.msleep(10)

            logger.info(f"Successfully created {len(jobs)} jobs")
            self.completed.emit(jobs)

        except Exception as e:
            error_msg = f"Failed to create jobs: {e}"
            logger.exception(error_msg)
            self.error.emit(error_msg)

    def _create_job(self, input_path: str) -> ConversionJob:
        """
        Create a single conversion job.

        Args:
            input_path: Path to input video file

        Returns:
            Created ConversionJob with database ID
        """
        # Generate output filename
        input_file = Path(input_path)
        output_path = self._output_paths.get(input_path) or build_conversion_output_path(
            input_path, output_dir=self._output_dir
        )

        # Get input file size (blocking I/O - that's why we're in a thread)
        input_size = 0
        try:
            if input_file.exists():
                input_size = input_file.stat().st_size
        except Exception as e:
            logger.warning(f"Could not get file size for {input_path}: {e}")

        # Create job object
        job = ConversionJob(
            input_path=input_path,
            output_path=output_path,
            status=ConversionStatus.PENDING,
            output_codec=self._config.output_codec,
            crf_value=self._config.crf_value,
            preset=self._config.preset,
            hardware_encoder=self._config.hardware_encoder
            if self._config.use_hardware_accel
            else None,
            input_size=input_size,
        )

        # Persist to database (blocking DB write - that's why we're in a thread)
        job = self._repository.create(job)
        logger.debug(f"Created conversion job {job.id}: {input_path}")

        return job
