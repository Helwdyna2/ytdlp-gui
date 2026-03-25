"""Download manager orchestrating multiple download workers."""

from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, Set
import logging

from PyQt6.QtCore import QObject, pyqtSignal, QMutex, QMutexLocker, QTimer

from .download_worker import DownloadWorker, clear_dir_listing_cache
from ..data.models import OutputConfig, Download, DownloadStatus
from ..data.repositories.download_repository import DownloadRepository
from ..utils.url_redaction import redact_url

logger = logging.getLogger(__name__)

# Force-terminate timeout for unresponsive workers (milliseconds)
FORCE_TERMINATE_TIMEOUT_MS = 5000  # 5 seconds


class DownloadManager(QObject):
    """
    Orchestrates download operations.

    Manages download queue, spawns worker threads, respects concurrent limits,
    aggregates progress statistics, and handles cancellation.
    """

    # Signals for UI updates
    download_started = pyqtSignal(str, str)  # url, title
    download_progress = pyqtSignal(str, dict)  # url, progress_dict
    download_completed = pyqtSignal(str, bool, str)  # url, success, message
    download_title_found = pyqtSignal(str, str)  # url, title
    queue_progress = pyqtSignal(int, int, int, int)  # completed, failed, cancelled, total
    aggregate_speed = pyqtSignal(float)  # total bytes/sec
    log_message = pyqtSignal(str, str)  # level, message
    all_completed = pyqtSignal()
    downloads_started = pyqtSignal()  # Emitted when downloads begin
    download_cancelling = pyqtSignal(str)  # url - emitted when download is being cancelled
    download_force_terminated = pyqtSignal(str)  # url - emitted when worker is force-terminated

    def __init__(
        self,
        download_repository: DownloadRepository,
        parent=None
    ):
        super().__init__(parent)
        self.download_repo = download_repository

        self._queue: deque = deque()
        self._active_workers: Dict[str, DownloadWorker] = {}
        self._worker_speeds: Dict[str, float] = {}  # URL -> current speed
        self._mutex = QMutex()

        self._max_concurrent = 3
        self._total_count = 0
        self._completed_count = 0
        self._failed_count = 0
        self._cancelled_count = 0
        self._is_cancelled = False
        self._is_running = False
        self._config: Optional[OutputConfig] = None
        self._skipped_urls: Set[str] = set()
        
        # Track workers being cancelled for force-terminate timeout
        self._cancelling_workers: Dict[str, QTimer] = {}

    @property
    def is_running(self) -> bool:
        """Check if downloads are currently in progress."""
        return self._is_running

    @property
    def pending_urls(self) -> List[str]:
        """Get list of URLs still in queue."""
        with QMutexLocker(self._mutex):
            return list(self._queue)

    @property
    def active_urls(self) -> List[str]:
        """Get list of URLs currently downloading."""
        with QMutexLocker(self._mutex):
            return list(self._active_workers.keys())

    def start_downloads(self, urls: List[str], config: OutputConfig):
        """
        Start downloading URLs.

        Args:
            urls: List of URLs to download.
            config: Download configuration.
        """
        logger.info(f"Starting downloads for {len(urls)} URLs")

        # Clear directory listing cache to invalidate stale entries
        clear_dir_listing_cache()

        with QMutexLocker(self._mutex):
            self._config = config
            self._max_concurrent = config.concurrent_limit
            self._is_cancelled = False
            self._is_running = True
            self._completed_count = 0
            self._failed_count = 0
            self._cancelled_count = 0
            self._worker_speeds.clear()
            self._cancelling_workers.clear()

            # Filter out already downloaded URLs
            already_downloaded = self.download_repo.get_downloaded_urls(urls)
            new_urls = [u for u in urls if u not in already_downloaded]
            self._skipped_urls = already_downloaded

            skipped = len(already_downloaded)
            if skipped:
                self.log_message.emit('info', f"Skipping {skipped} already downloaded URLs")

            if not new_urls:
                self.log_message.emit('info', "All URLs already downloaded")
                self._is_running = False
                self.all_completed.emit()
                return

            self._queue = deque(new_urls)
            self._total_count = len(new_urls)

        self.queue_progress.emit(0, 0, 0, self._total_count)
        self.downloads_started.emit()

        # Spawn initial workers
        self._spawn_workers()

    def cancel_all(self):
        """Cancel all downloads gracefully with force-terminate timeout."""
        logger.info("Cancellation requested")

        with QMutexLocker(self._mutex):
            self._is_cancelled = True
            remaining = len(self._queue)
            self._cancelled_count += remaining
            self._queue.clear()

            # Signal cancellation to all active workers and set up force-terminate timers
            for url, worker in list(self._active_workers.items()):
                worker.cancel()
                self.download_cancelling.emit(url)
                # Set up force-terminate timeout
                self._setup_force_terminate_timer(url)

        self.log_message.emit('info', f"Cancelling... ({remaining} URLs removed from queue)")
        self.queue_progress.emit(
            self._completed_count,
            self._failed_count,
            self._cancelled_count,
            self._total_count
        )

    def _setup_force_terminate_timer(self, url: str):
        """Set up a timer to force-terminate a worker if it doesn't respond to cancellation."""
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._force_terminate_worker(url))
        timer.start(FORCE_TERMINATE_TIMEOUT_MS)
        self._cancelling_workers[url] = timer
        logger.debug(f"Force-terminate timer started for {url} ({FORCE_TERMINATE_TIMEOUT_MS}ms)")

    def _force_terminate_worker(self, url: str):
        """Force-terminate a worker that hasn't responded to cancellation."""
        worker = None
        was_running = False
        with QMutexLocker(self._mutex):
            if url in self._active_workers:
                worker = self._active_workers.pop(url)
                was_running = worker.isRunning()
            self._cancelling_workers.pop(url, None)

        if worker and was_running:
            redacted_url = redact_url(url)
            logger.warning("Force-terminating unresponsive worker for: %s", redacted_url)
            worker.terminate()
            worker.wait(1000)  # Wait for cleanup
            self.download_force_terminated.emit(url)
            self.log_message.emit("warning", f"Force-stopped: {redacted_url}")
        if worker:
            worker.deleteLater()

    def cancel_download(self, url: str) -> bool:
        """
        Cancel a specific download.

        Args:
            url: URL of the download to cancel.

        Returns:
            True if the download was found and cancelled.
        """
        with QMutexLocker(self._mutex):
            # Check if in queue
            if url in self._queue:
                self._queue.remove(url)
                self._cancelled_count += 1
                self.log_message.emit("info", f"Removed from queue: {redact_url(url)}")
                self.queue_progress.emit(
                    self._completed_count,
                    self._failed_count,
                    self._cancelled_count,
                    self._total_count
                )
                return True

            # Check if active
            if url in self._active_workers:
                worker = self._active_workers[url]
                worker.cancel()
                self.download_cancelling.emit(url)
                self._setup_force_terminate_timer(url)
                return True

        return False

    def get_remaining_urls(self) -> List[str]:
        """Get all remaining URLs (queued + active)."""
        with QMutexLocker(self._mutex):
            remaining = list(self._queue)
            remaining.extend(self._active_workers.keys())
            return remaining

    def _spawn_workers(self):
        """Spawn workers up to concurrent limit."""
        with QMutexLocker(self._mutex):
            while (
                len(self._active_workers) < self._max_concurrent
                and self._queue
                and not self._is_cancelled
            ):
                url = self._queue.popleft()
                self._spawn_single_worker(url)

    def _spawn_single_worker(self, url: str):
        """Create and start a worker for a URL."""
        if self._config is None:
            logger.error("Cannot spawn worker: no config set")
            return

        worker = DownloadWorker(url, self._config)

        # Connect signals
        worker.progress.connect(lambda p, u=url: self._on_progress(u, p))
        worker.completed.connect(lambda s, m, d, u=url: self._on_completed(u, s, m, d))
        worker.log.connect(self.log_message.emit)
        worker.title_found.connect(lambda t, u=url: self._on_title_found(u, t))
        worker.finished.connect(lambda u=url: self._on_worker_finished(u))

        self._active_workers[url] = worker
        worker.start()

        self.download_started.emit(url, url)

        # Create pending download record
        download = Download(
            url=url,
            status=DownloadStatus.IN_PROGRESS,
            created_at=datetime.now()
        )
        self.download_repo.save(download)

    def _on_progress(self, url: str, progress: dict):
        """Handle progress update from worker."""
        # Track speed for aggregate calculation
        speed = progress.get('speed', 0) or 0
        self._worker_speeds[url] = speed

        self.download_progress.emit(url, progress)
        self._emit_aggregate_speed()

    def _on_title_found(self, url: str, title: str):
        """Handle title discovery from worker."""
        self.download_title_found.emit(url, title)

    def _on_completed(self, url: str, success: bool, message: str, metadata: dict):
        """Handle download completion."""
        with QMutexLocker(self._mutex):
            # Remove from speed tracking
            self._worker_speeds.pop(url, None)

            # Cancel force-terminate timer if present
            if url in self._cancelling_workers:
                timer = self._cancelling_workers.pop(url)
                timer.stop()
                timer.deleteLater()

            if success:
                self._completed_count += 1
                # Update download record
                self.download_repo.mark_completed(
                    url=url,
                    title=metadata.get('title'),
                    output_path=metadata.get('filename'),
                    file_size=metadata.get('total_bytes')
                )
            else:
                if "Cancelled" in message:
                    self._cancelled_count += 1
                else:
                    self._failed_count += 1
                    # Update status to failed
                    self.download_repo.update_status(
                        url=url,
                        status=DownloadStatus.FAILED,
                        error_message=message
                    )

        self.download_completed.emit(url, success, message)
        self.queue_progress.emit(
            self._completed_count,
            self._failed_count,
            self._cancelled_count,
            self._total_count
        )

    def _on_worker_finished(self, url: str):
        """Handle worker thread completion."""
        with QMutexLocker(self._mutex):
            # Cancel force-terminate timer if present
            if url in self._cancelling_workers:
                timer = self._cancelling_workers.pop(url)
                timer.stop()
                timer.deleteLater()

            if url in self._active_workers:
                # Clean up worker reference
                worker = self._active_workers.pop(url)
                worker.deleteLater()

        # Spawn next worker if queue not empty
        self._spawn_workers()

        # Check if all done
        all_done = False
        completed = 0
        failed = 0
        cancelled = 0
        total = 0
        with QMutexLocker(self._mutex):
            if not self._active_workers and not self._queue:
                self._is_running = False
                all_done = True
                completed = self._completed_count
                failed = self._failed_count
                cancelled = self._cancelled_count
                total = self._total_count

        # Emit outside lock
        if all_done:
            parts = [f"{completed} completed"]
            if failed:
                parts.append(f"{failed} failed")
            if cancelled:
                parts.append(f"{cancelled} cancelled")
            self.log_message.emit(
                'info',
                f"Finished: {', '.join(parts)} out of {total}"
            )
            self.all_completed.emit()

    def _emit_aggregate_speed(self):
        """Calculate and emit total download speed."""
        total_speed = sum(self._worker_speeds.values())
        self.aggregate_speed.emit(total_speed)

    def update_concurrent_limit(self, limit: int):
        """Update the concurrent download limit."""
        with QMutexLocker(self._mutex):
            self._max_concurrent = limit

        # If increased, try to spawn more workers
        if self._is_running:
            self._spawn_workers()

    def get_stats(self) -> dict:
        """Get current download statistics."""
        with QMutexLocker(self._mutex):
            return {
                'total': self._total_count,
                'completed': self._completed_count,
                'failed': self._failed_count,
                'cancelled': self._cancelled_count,
                'queued': len(self._queue),
                'active': len(self._active_workers),
                'skipped': len(self._skipped_urls),
                'is_running': self._is_running,
            }
