"""Manager for Extract URLs workflow."""

from typing import List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from ..data.models import ExtractUrlsConfig
from ..services.config_service import ConfigService
from ..utils.platform_utils import get_data_dir
from .extract_urls_worker import ExtractUrlsWorker


class ExtractUrlsManager(QObject):
    """
    Orchestrates URL extraction tasks.

    Signals:
        extract_started: (total: int) Extraction started
        extract_progress: (index: int, total: int, message: str) Progress update
        extract_result: (index: int, new_urls: list) New URLs found for a page
        extract_completed: (count: int, output_path: str) Extraction completed
        error: (message: str) Error occurred
    """

    extract_started = pyqtSignal(int)
    extract_progress = pyqtSignal(int, int, str)
    extract_result = pyqtSignal(int, list)
    extract_completed = pyqtSignal(int, str)
    error = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._config_service = ConfigService()
        self._config = self._load_config()
        self._worker: Optional[ExtractUrlsWorker] = None

    def get_config(self) -> ExtractUrlsConfig:
        """Get current Extract URLs configuration."""
        return self._config

    def update_config(self, config: ExtractUrlsConfig) -> None:
        """Update configuration and persist to config service."""
        self._config = config
        self._save_config(config)

    def start_extract(self, seed_urls: List[str], config: ExtractUrlsConfig) -> None:
        """
        Start extraction task.

        Args:
            seed_urls: List of URLs to visit
            config: ExtractUrlsConfig to use
        """
        if not seed_urls:
            self.error.emit("No URLs provided")
            return
        if self._worker and self._worker.isRunning():
            self.error.emit("Another task is already running")
            return

        self.update_config(config)

        self.extract_started.emit(len(seed_urls))

        self._worker = ExtractUrlsWorker(
            config=self._config,
            seed_urls=seed_urls,
            parent=self,
        )
        self._worker.progress.connect(self.extract_progress.emit)
        self._worker.result.connect(self.extract_result.emit)
        self._worker.completed.connect(self._on_extract_completed)
        self._worker.error.connect(self._on_worker_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def stop(self) -> None:
        """Stop the current task."""
        if self._worker:
            self._worker.cancel()

    def _load_config(self) -> ExtractUrlsConfig:
        """Load configuration from ConfigService and apply defaults."""
        section = self._config_service.get_section("extract_urls") or {}
        changed = False

        output_dir = section.get("output_dir", "")
        if not output_dir:
            output_dir = str(get_data_dir() / "extracted_urls")
            section["output_dir"] = output_dir
            changed = True

        auth_section = self._config_service.get_section("auth") or {}
        profile_dir = auth_section.get("profile_dir", "")
        if not profile_dir:
            profile_dir = str(get_data_dir() / "browser_profiles" / "global")
            auth_section["profile_dir"] = profile_dir
            self._config_service.set_section("auth", auth_section, save=True)

        if changed:
            self._config_service.set_section("extract_urls", section, save=True)

        return ExtractUrlsConfig(
            output_dir=output_dir,
            profile_dir=profile_dir,
            auto_scroll_enabled=section.get("auto_scroll_enabled", True),
            max_scrolls=section.get("max_scrolls", 200),
            idle_limit=section.get("idle_limit", 5),
            delay_ms=section.get("delay_ms", 800),
            max_bounce_attempts=section.get("max_bounce_attempts", 3),
        )

    def _save_config(self, config: ExtractUrlsConfig) -> None:
        """Persist configuration to ConfigService."""
        section = {
            "output_dir": config.output_dir,
            "auto_scroll_enabled": config.auto_scroll_enabled,
            "max_scrolls": config.max_scrolls,
            "idle_limit": config.idle_limit,
            "delay_ms": config.delay_ms,
            "max_bounce_attempts": config.max_bounce_attempts,
        }
        self._config_service.set_section("extract_urls", section, save=True)

    def _on_extract_completed(self, urls: List[str], output_path: str) -> None:
        """Handle extraction completion."""
        self.extract_completed.emit(len(urls), output_path)

    def _on_worker_error(self, message: str) -> None:
        """Handle worker error."""
        self.error.emit(message)

    def _on_worker_finished(self) -> None:
        """Clean up worker reference."""
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
