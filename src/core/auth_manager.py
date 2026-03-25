"""Authentication manager for global Playwright profile."""

from typing import Optional, List

from PyQt6.QtCore import QObject, pyqtSignal

from ..services.config_service import ConfigService
from .auth_worker import AuthWorker


class AuthManager(QObject):
    """
    Manages global authentication and cookie export.

    Signals:
        login_started: (url: str)
        login_finished: (result: str, message: str)
        cookies_export_started: ()
        cookies_exported: (path: str)
        install_started: ()
        install_progress: (message: str)
        install_output: (line: str) - Real-time output from install process
        install_completed: ()
        install_failed: (error_message: str)
        error: (message: str)
    """

    login_started = pyqtSignal(str)
    login_finished = pyqtSignal(str, str)
    cookies_export_started = pyqtSignal()
    cookies_exported = pyqtSignal(str)
    install_started = pyqtSignal()
    install_progress = pyqtSignal(str)
    install_output = pyqtSignal(str)  # Real-time streaming output
    install_completed = pyqtSignal()
    install_failed = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._config = ConfigService()
        self._worker: Optional[AuthWorker] = None
        self._current_login_url: str = ""

    def get_profile_dir(self) -> str:
        """Get the global Playwright profile directory."""
        return self._config.get("auth.profile_dir", "")

    def get_cookies_file_path(self) -> str:
        """Get the cookies.txt output path."""
        return self._config.get("auth.cookies_file_path", "")

    def get_playwright_browser(self) -> str:
        """Get the configured Playwright browser."""
        return self._config.get("playwright.browser", "chromium")

    def set_playwright_browser(self, browser: str) -> None:
        """Set the configured Playwright browser."""
        self._config.set("playwright.browser", browser, save=True)

    def open_login(
        self, start_url: str, target_cookie_suffixes: Optional[List[str]] = None
    ) -> None:
        """Open a visible browser for login."""
        if self._worker and self._worker.isRunning():
            self.error.emit("Authentication task already running")
            return

        self.login_started.emit(start_url)
        self._current_login_url = start_url
        self._worker = AuthWorker(
            profile_dir=self.get_profile_dir(),
            cookies_file_path=self.get_cookies_file_path(),
            task="login",
            start_url=start_url,
            target_cookie_suffixes=target_cookie_suffixes,
            browser=self.get_playwright_browser(),
            parent=self,
        )
        self._worker.login_finished.connect(self._on_login_finished)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def export_cookies(self) -> None:
        """Export cookies to a Netscape cookies.txt file."""
        if self._worker and self._worker.isRunning():
            self.error.emit("Authentication task already running")
            return

        self.cookies_export_started.emit()
        self._worker = AuthWorker(
            profile_dir=self.get_profile_dir(),
            cookies_file_path=self.get_cookies_file_path(),
            task="export_cookies",
            browser=self.get_playwright_browser(),
            parent=self,
        )
        self._worker.cookies_exported.connect(self._on_cookies_exported)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def install_chromium(self) -> None:
        """Install Playwright Chromium browser binaries."""
        self.install_browsers(["chromium"], force=False)

    def install_browsers(self, browsers: List[str], force: bool = False) -> None:
        """Install Playwright browsers."""
        if self._worker and self._worker.isRunning():
            self.error.emit("Authentication task already running")
            return

        self.install_started.emit()
        self._worker = AuthWorker(
            profile_dir=self.get_profile_dir(),
            cookies_file_path=self.get_cookies_file_path(),
            task="install_browsers",
            install_browsers=browsers,
            install_force=force,
            browser=self.get_playwright_browser(),
            parent=self,
        )
        self._worker.progress.connect(self.install_progress.emit)
        self._worker.output_received.connect(self.install_output.emit)
        self._worker.install_completed.connect(self.install_completed.emit)
        self._worker.install_failed.connect(self.install_failed.emit)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def cancel(self) -> None:
        """Cancel the current auth task."""
        if self._worker:
            self._worker.cancel()

    def _on_login_finished(self, result: str, message: str, _path: str) -> None:
        """Handle login completion."""
        if self._current_login_url:
            self._config.set(
                "auth.last_login_url", self._current_login_url, save=True
            )
            self._current_login_url = ""
        self.login_finished.emit(result, message)

    def _on_cookies_exported(self, path: str) -> None:
        """Handle cookies export."""
        self.cookies_exported.emit(path)

    def _on_error(self, message: str) -> None:
        """Handle worker error."""
        self.error.emit(message)

    def _on_worker_finished(self) -> None:
        """Clean up worker reference."""
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
