"""Main application window."""

import logging
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QMessageBox,
    QApplication,
    QLineEdit,
    QPlainTextEdit,
    QTextEdit,
    QComboBox,
    QToolTip,
)
from PyQt6.QtCore import Qt, QTimer, QEvent, QObject, QRect
from PyQt6.QtGui import QAction, QCloseEvent, QCursor, QShortcut, QKeySequence

from .widgets.url_input_widget import UrlInputWidget
from .widgets.file_picker_widget import FilePickerWidget
from .widgets.output_config_widget import OutputConfigWidget
from .widgets.progress_widget import ProgressWidget
from .widgets.queue_progress_widget import QueueProgressWidget
from .widgets.download_log_widget import DownloadLogWidget
from .widgets.auth_status_widget import AuthStatusWidget
from .pages.add_urls_page import AddUrlsPage
from .pages.extract_urls_page import ExtractUrlsPage
from .pages.convert_page import ConvertPage
from .pages.trim_page import TrimPage
from .pages.metadata_page import MetadataPage
from .pages.sort_page import SortPage
from .pages.rename_page import RenamePage
from .pages.match_page import MatchPage
from .pages.settings_page import SettingsPage
from .playwright_install_prompt import (
    is_playwright_setup_message,
    show_playwright_install_prompt,
)
from .shell import Shell

from ..core.download_manager import DownloadManager
from ..core.auth_manager import AuthManager
from ..core.auth_types import AuthResult
from ..core.site_auth import get_handler_for_host
from ..core.url_domains import extract_hostnames
from ..core.netscape_cookies import cookiefile_has_domain_suffix
from ..services.config_service import ConfigService
from ..services.session_service import SessionService
from ..data.database import Database
from ..data.models import OutputConfig, Session
from ..data.repositories.download_repository import DownloadRepository
from ..utils.constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
    SUPPORTED_VIDEO_EXTENSIONS,
)
from ..utils.platform_utils import quick_look_file, get_platform, Platform
from ..utils.url_redaction import redact_url


class QuickLookEventFilter(QObject):
    """
    Event filter for spacebar Quick Look shortcut.

    Triggers macOS Quick Look preview when spacebar is pressed
    and a video file is selected in a file list widget.
    Only activates when:
    - Focus is on a file list widget (not text inputs, buttons, etc.)
    - A file is actually selected in the list
    """

    def __init__(self, get_file_callback, is_file_list_focused_callback, parent=None):
        super().__init__(parent)
        self._get_file_callback = get_file_callback
        self._is_file_list_focused_callback = is_file_list_focused_callback

    def eventFilter(self, obj, event):
        """Filter key events to intercept spacebar for Quick Look."""
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Space:
                # Only trigger if focus is on a file list widget
                if not self._is_file_list_focused_callback():
                    return False  # Let normal handling occur

                # Try to get selected file and trigger Quick Look
                file_path = self._get_file_callback()
                if file_path:
                    return self._trigger_quick_look(file_path)

        return False  # Pass event to other filters

    def _is_text_input(self, widget) -> bool:
        """Check if the widget is a text input that needs spacebar."""
        if widget is None:
            return False
        if isinstance(widget, (QLineEdit, QPlainTextEdit, QTextEdit)):
            return True
        if isinstance(widget, QComboBox) and widget.isEditable():
            return True
        return False

    def _trigger_quick_look(self, file_path: str) -> bool:
        """Trigger Quick Look for the file, return True if event consumed."""
        from pathlib import Path

        # Only for video files
        if Path(file_path).suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
            return False

        if get_platform() == Platform.MACOS:
            quick_look_file(file_path)
            return True
        else:
            # Show tooltip for non-macOS platforms
            QToolTip.showText(
                QCursor.pos(),
                "Quick Look is only available on macOS",
                None,
                QRect(),
                2000,  # 2 seconds
            )
            return True  # Still consume the event


class MainWindow(QMainWindow):
    """
    Main application window.

    Orchestrates all UI components and connects them to the download manager.
    """

    def __init__(
        self, database: Database, session_service: SessionService, parent=None
    ):
        super().__init__(parent)
        self.database = database
        self.session_service = session_service

        # Initialize repositories
        self.download_repo = DownloadRepository(database)

        # Initialize download manager
        self.download_manager = DownloadManager(self.download_repo)
        self.auth_manager = AuthManager(self)
        self._config = ConfigService()

        # Current URLs
        self._current_urls: List[str] = []
        self._pending_download_config: Optional[OutputConfig] = None
        self._pending_download_urls: List[str] = []
        self._pending_auth_domain: Optional[str] = None

        # Setup UI
        self._setup_ui()
        self._setup_menu_bar()
        self._setup_shortcuts()
        self._connect_signals()
        self._setup_quick_look_shortcut()

        # Set window properties
        self.setWindowTitle(APP_NAME)
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        self.setMinimumSize(1000, 650)

    def _setup_ui(self):
        """Setup the main UI layout."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Shell layout
        self.shell = Shell()
        main_layout.addWidget(self.shell)

        # Shared workflow widgets
        self.auth_status_widget = AuthStatusWidget()
        self.url_input_widget = UrlInputWidget()
        self.file_picker_widget = FilePickerWidget()
        self.output_config_widget = OutputConfigWidget()
        self.queue_progress_widget = QueueProgressWidget()
        self.progress_widget = ProgressWidget()
        self.download_log_widget = DownloadLogWidget()

        # Create page widgets and register them with the shell
        self.add_urls_page = AddUrlsPage(
            url_input=self.url_input_widget,
            auth_status=self.auth_status_widget,
            output_config=self.output_config_widget,
            queue_progress=self.queue_progress_widget,
            progress=self.progress_widget,
            download_log=self.download_log_widget,
        )
        self.shell.register_tool("add_urls", self.add_urls_page)

        self.extract_urls_page = ExtractUrlsPage()
        self.shell.register_tool("extract_urls", self.extract_urls_page)

        self.convert_page = ConvertPage()
        self.shell.register_tool("convert", self.convert_page)

        self.trim_page = TrimPage()
        self.shell.register_tool("trim", self.trim_page)

        self.metadata_page = MetadataPage()
        self.shell.register_tool("metadata", self.metadata_page)

        self.sort_page = SortPage()
        self.shell.register_tool("sort", self.sort_page)

        self.rename_page = RenamePage()
        self.shell.register_tool("rename", self.rename_page)

        self.match_page = MatchPage()
        self.shell.register_tool("match", self.match_page)

        self.settings_page = SettingsPage(
            config_service=self._config,
            auth_manager=self.auth_manager,
        )
        self.shell.register_tool("settings", self.settings_page)

        # Update footer bar with dependency status
        self._update_footer_bar()

    def _setup_menu_bar(self):
        """Setup the menu bar."""
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")

        clear_history_action = QAction("Clear Download History", self)
        clear_history_action.triggered.connect(self._clear_history)
        file_menu.addAction(clear_history_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menu_bar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts for common actions."""
        # Ctrl+Return: Start Download
        start_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        start_shortcut.activated.connect(self._start_downloads)

        # Escape: Cancel downloads (only when running)
        cancel_shortcut = QShortcut(QKeySequence("Escape"), self)
        cancel_shortcut.activated.connect(self._cancel_downloads_if_running)

        # Ctrl+L: Focus URL input
        focus_url_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        focus_url_shortcut.activated.connect(self._focus_url_input)

        # Ctrl+Shift+C: Clear download log
        clear_log_shortcut = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
        clear_log_shortcut.activated.connect(self._clear_log)

        # Tab order: URL input → Start → Cancel → Output config → Auth status
        QWidget.setTabOrder(
            self.url_input_widget.text_edit,
            self.queue_progress_widget.start_btn,
        )
        QWidget.setTabOrder(
            self.queue_progress_widget.start_btn,
            self.queue_progress_widget.cancel_btn,
        )
        QWidget.setTabOrder(
            self.queue_progress_widget.cancel_btn,
            self.output_config_widget,
        )

    def _focus_url_input(self):
        """Focus the URL input and switch to the Add URLs page."""
        self.shell.switch_to_tool("add_urls")
        self.url_input_widget.focus_input()

    def _cancel_downloads_if_running(self):
        """Cancel downloads only when downloads are active."""
        if self.download_manager.is_running:
            self._cancel_downloads()

    def _clear_log(self):
        """Clear the download log."""
        self.download_log_widget.clear()

    def _connect_signals(self):
        """Connect all signals and slots."""
        # AddUrlsPage signals
        self.add_urls_page.start_download.connect(self._start_downloads)
        self.add_urls_page.cancel_download.connect(self._cancel_downloads)
        self.add_urls_page.load_from_file.connect(self._on_load_from_file)

        # URL input signals
        self.url_input_widget.urls_changed.connect(self._on_urls_changed)
        self.file_picker_widget.urls_loaded.connect(self._on_urls_loaded)
        self.auth_status_widget.authenticate_requested.connect(
            self._on_authenticate_domain
        )

        # Queue progress signals
        self.queue_progress_widget.start_clicked.connect(self._start_downloads)
        self.queue_progress_widget.cancel_clicked.connect(self._cancel_downloads)
        self.queue_progress_widget.clear_history_clicked.connect(self._clear_history)

        # Download manager signals
        self.download_manager.download_started.connect(self._on_download_started)
        self.download_manager.download_progress.connect(self._on_download_progress)
        self.download_manager.download_completed.connect(self._on_download_completed)
        self.download_manager.download_title_found.connect(self._on_title_found)
        self.download_manager.queue_progress.connect(self._on_queue_progress)
        self.download_manager.aggregate_speed.connect(self._on_aggregate_speed)
        self.download_manager.log_message.connect(self._on_log_message)
        self.download_manager.all_completed.connect(self._on_all_completed)
        self.download_manager.downloads_started.connect(self._on_downloads_started)
        self.download_manager.download_cancelling.connect(self._on_download_cancelling)
        self.download_manager.download_force_terminated.connect(
            self._on_download_force_terminated
        )

        # Auth manager signals
        self.auth_manager.login_finished.connect(self._on_auth_login_finished)
        self.auth_manager.cookies_export_started.connect(
            self._on_cookies_export_started
        )
        self.auth_manager.cookies_exported.connect(self._on_cookies_exported)
        self.auth_manager.error.connect(self._on_auth_error)

    def _on_load_from_file(self):
        """Trigger file picker to load URLs from file."""
        self.file_picker_widget._browse_url_file()

    def _setup_quick_look_shortcut(self):
        """Setup spacebar shortcut for Quick Look preview."""
        self._quick_look_filter = QuickLookEventFilter(
            self._get_selected_file_for_preview, self._is_file_list_focused, parent=self
        )
        app = QApplication.instance()
        if app:
            app.installEventFilter(self._quick_look_filter)

    def _get_selected_file_for_preview(self) -> Optional[str]:
        """Get the currently selected file path for Quick Look preview."""
        current_widget = self.shell.content_stack.currentWidget()
        if hasattr(current_widget, "get_selected_preview_file"):
            return current_widget.get_selected_preview_file()

        return None

    def _is_file_list_focused(self) -> bool:
        """Check if focus is on a file list widget that supports Quick Look."""
        focus_widget = QApplication.focusWidget()
        if focus_widget is None:
            return False

        # Check if focus is on a QListWidget (file list)
        from PyQt6.QtWidgets import QListWidget, QTableWidget, QTreeWidget

        if isinstance(focus_widget, (QListWidget, QTableWidget, QTreeWidget)):
            return True

        # Check if focus is within a file list widget (e.g., on a child item)
        # by walking up the parent hierarchy
        parent = focus_widget.parent()
        while parent is not None:
            if isinstance(parent, (QListWidget, QTableWidget, QTreeWidget)):
                return True
            parent = parent.parent()

        return False

    def _on_urls_changed(self, urls: List[str]):
        """Handle URL list changes."""
        self._current_urls = urls
        self.auth_status_widget.set_urls(urls)
        self.queue_progress_widget.set_url_count(len(urls))
        # Update badge on sidebar
        self.shell.set_badge("add_urls", len(urls) if urls else 0)

    def _on_urls_loaded(self, urls: List[str]):
        """Handle URLs loaded from file."""
        self.url_input_widget.add_urls(urls)
        self.download_log_widget.add_info(f"Loaded {len(urls)} URLs from file")

    def _start_downloads(self):
        """Start downloading URLs."""
        if not self._current_urls:
            return

        # Get output config
        config = self.output_config_widget.get_config()
        config.output_dir = self.output_config_widget.output_dir
        config.force_overwrite = self._config.get(
            "download.force_overwrite", config.force_overwrite
        )
        config.video_only = self._config.get("download.video_only", config.video_only)

        if not config.output_dir:
            QMessageBox.warning(
                self,
                "Missing Output Directory",
                "Please select an output directory before starting downloads.",
            )
            return

        if not self._ensure_output_dir(config):
            return

        missing_auth = self._get_missing_auth_domains(self._current_urls)
        if missing_auth:
            hostname, display_name = missing_auth[0]
            prompt = QMessageBox(self)
            prompt.setWindowTitle("Authentication Required")
            prompt.setText(f"Authenticate for {display_name} first?")
            authenticate_button = prompt.addButton(
                "Authenticate now", QMessageBox.ButtonRole.AcceptRole
            )
            prompt.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            prompt.setDefaultButton(authenticate_button)
            prompt.exec()
            if prompt.clickedButton() == authenticate_button:
                self._pending_download_urls = list(self._current_urls)
                self._pending_download_config = config
                self._pending_auth_domain = hostname
                self._on_authenticate_domain(hostname)
            return

        self._queue_downloads_with_cookies(self._current_urls, config)

    def _queue_downloads_with_cookies(
        self, urls: List[str], config: OutputConfig
    ) -> None:
        """Export cookies, then start downloads."""
        self._pending_download_urls = list(urls)
        self._pending_download_config = config
        self.download_log_widget.add_info(
            "Exporting cookies from Playwright profile..."
        )
        self.auth_manager.export_cookies()

    def _on_cookies_export_started(self) -> None:
        """Handle cookies export started."""
        pass

    def _on_cookies_exported(self, path: str) -> None:
        """Handle cookies exported; start pending downloads."""
        self.auth_status_widget.refresh_status()
        if not self._pending_download_config:
            return

        self._pending_download_config.cookies_path = path or None

        # Create session using SessionService
        session = self.session_service.create_session(
            self._pending_download_urls, self._pending_download_config
        )

        # Start downloads
        self.download_log_widget.add_info(
            f"Starting download of {len(self._pending_download_urls)} URLs"
        )
        self.download_manager.start_downloads(
            self._pending_download_urls, self._pending_download_config
        )

        self._pending_download_urls = []
        self._pending_download_config = None

    def _on_auth_error(self, message: str) -> None:
        """Handle authentication-related errors."""
        if self._pending_download_config:
            if is_playwright_setup_message(message):
                show_playwright_install_prompt(
                    self, message, self.auth_manager, title="Authentication Error"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Authentication Error",
                    f"{message}\n\nAuthenticate in the Add URLs tab (Auth Status panel) and try again.",
                )
            self._pending_download_urls = []
            self._pending_download_config = None
            self._pending_auth_domain = None
        else:
            show_playwright_install_prompt(
                self, message, self.auth_manager, title="Authentication Error"
            )

    def _cancel_downloads(self):
        """Cancel all downloads."""
        result = QMessageBox.question(
            self,
            "Cancel Downloads",
            "Are you sure you want to cancel all downloads?\n\n"
            "Completed downloads will be preserved.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if result == QMessageBox.StandardButton.Yes:
            self.download_manager.cancel_all()

    def _on_downloads_started(self):
        """Handle downloads started."""
        self.queue_progress_widget.set_running(True)
        self._set_input_enabled(False)
        self.add_urls_page.set_download_mode(True)

    def _on_download_started(self, url: str, title: str):
        """Handle individual download started."""
        self.progress_widget.add_download(url)

    def _on_download_progress(self, url: str, progress: dict):
        """Handle download progress update."""
        self.progress_widget.update_progress(url, progress)

    def _on_title_found(self, url: str, title: str):
        """Handle title discovery."""
        self.progress_widget.set_title(url, title)

    def _on_download_completed(self, url: str, success: bool, message: str):
        """Handle download completion."""
        cancelled = not success and "Cancelled" in message
        self.progress_widget.set_completed(url, success, message, cancelled=cancelled)

        # Update session using SessionService
        if self.session_service.has_active_session:
            remaining = self.download_manager.get_remaining_urls()
            self.session_service.update_pending_urls(remaining)

    def _on_download_cancelling(self, url: str):
        """Handle download being cancelled - update UI immediately."""
        self.progress_widget.set_cancelling(url)

    def _on_download_force_terminated(self, url: str):
        """Handle download worker being force-terminated."""
        # The download will be marked as completed with failure via the normal flow
        # This is mainly for logging/debugging purposes
        logger.warning("Download force-terminated: %s", redact_url(url))

    def _on_queue_progress(
        self, completed: int, failed: int, cancelled: int, total: int
    ):
        """Handle queue progress update."""
        self.queue_progress_widget.update_progress(completed, failed, cancelled, total)

        active = total - completed - failed - cancelled
        # Update badge with active download count
        self.shell.set_badge("add_urls", active if active > 0 else 0)
        self.add_urls_page.set_queue_stats(
            queued=total - completed - failed - cancelled,
            active=active,
            done=completed,
            elapsed="",
        )

    def _on_aggregate_speed(self, speed: float):
        """Handle aggregate download speed update."""
        self.queue_progress_widget.update_speed(speed)

    def _on_log_message(self, level: str, message: str):
        """Handle log message from download manager."""
        self.download_log_widget.add_entry(level, message)

    def _on_all_completed(self):
        """Handle all downloads completed."""
        self.queue_progress_widget.set_running(False)
        self._set_input_enabled(True)
        self.add_urls_page.set_download_mode(False)

        # Clear completed from progress widget after a delay
        QTimer.singleShot(2000, self.progress_widget.clear_completed)

        # Mark session inactive using SessionService
        if self.session_service.has_active_session:
            self.session_service.complete_session()

        # Clear badge
        self.shell.set_badge("add_urls", 0)

    def _set_input_enabled(self, enabled: bool):
        """Enable or disable input widgets."""
        self.url_input_widget.set_enabled(enabled)
        self.file_picker_widget.set_enabled(enabled)
        self.output_config_widget.set_enabled(enabled)
        self.auth_status_widget.setEnabled(enabled)

    def _ensure_output_dir(self, config: OutputConfig) -> bool:
        """Ensure output directory exists."""
        try:
            Path(config.output_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Could not create output directory: {e}"
            )
            return False
        return True

    def _get_missing_auth_domains(self, urls: List[str]) -> List[tuple[str, str]]:
        """Return hostnames that require auth but are missing cookies."""
        hostnames = extract_hostnames(urls)
        cookies_path = self.auth_manager.get_cookies_file_path()
        missing: List[tuple[str, str]] = []

        for hostname in hostnames:
            handler = get_handler_for_host(hostname)
            if not handler:
                continue
            has_cookies = any(
                cookiefile_has_domain_suffix(cookies_path, suffix)
                for suffix in handler.cookie_domain_suffixes
            )
            if not has_cookies:
                missing.append((hostname, handler.display_name))

        return missing

    def _on_authenticate_domain(self, hostname: str) -> None:
        """Start authentication flow for a hostname."""
        handler = get_handler_for_host(hostname)
        if handler:
            start_url = handler.start_url
            suffixes = handler.cookie_domain_suffixes
        else:
            start_url = f"https://{hostname}/"
            suffixes = [hostname]

        QMessageBox.information(
            self,
            "Authenticate",
            "A browser window will open.\nLog in and close the window when finished.",
        )
        self.auth_manager.open_login(start_url, target_cookie_suffixes=suffixes)

    def _on_auth_login_finished(self, result: str, message: str) -> None:
        """Handle auth completion."""
        self.auth_status_widget.refresh_status()

        if result == AuthResult.SUCCESS.value:
            if (
                self._pending_auth_domain
                and self._pending_download_config
                and self._pending_download_urls
            ):
                pending_urls = list(self._pending_download_urls)
                pending_config = self._pending_download_config
                self._pending_download_urls = []
                self._pending_download_config = None
                self._pending_auth_domain = None
                if not self._ensure_output_dir(pending_config):
                    return
                self._queue_downloads_with_cookies(pending_urls, pending_config)
            QMessageBox.information(
                self, "Authentication", message or "Authentication complete."
            )
            return

        if result == AuthResult.CANCELLED_NO_COOKIES.value:
            QMessageBox.warning(self, "Authentication", message or "Please try again.")
        elif result == AuthResult.ERROR_PLAYWRIGHT_SETUP.value:
            show_playwright_install_prompt(
                self, message, self.auth_manager, title="Authentication Error"
            )
        elif result == AuthResult.ERROR_FATAL.value:
            QMessageBox.critical(
                self, "Authentication Error", message or "Authentication failed."
            )

        self._pending_download_urls = []
        self._pending_download_config = None
        self._pending_auth_domain = None

    def _clear_history(self):
        """Clear download history."""
        if self.download_manager.is_running:
            QMessageBox.warning(
                self,
                "Cannot Clear History",
                "Please wait for downloads to complete or cancel them first.",
            )
            return

        result = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear all download history?\n\n"
            "This will allow previously downloaded URLs to be downloaded again.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if result == QMessageBox.StandardButton.Yes:
            count = self.download_repo.delete_all()
            self.download_log_widget.add_info(
                f"Cleared {count} entries from download history"
            )

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"{APP_NAME} v{APP_VERSION}\n\n"
            "A cross-platform GUI for yt-dlp.\n\n"
            "Download videos from YouTube and other sites with\n"
            "queue management, progress tracking, and session persistence.",
        )

    def _update_footer_bar(self):
        """Update footer bar with dependency status."""
        import shutil

        ytdlp = shutil.which("yt-dlp")
        ffmpeg = shutil.which("ffmpeg")
        # Footer bar has been removed from the new shell; log dependency status instead
        if not ytdlp:
            logger.warning("yt-dlp not found in PATH")
        if not ffmpeg:
            logger.warning("ffmpeg not found in PATH")

    def restore_session(self, session: Session):
        """Restore a previous session."""
        # Set URLs
        self.url_input_widget.set_urls(session.pending_urls)

        # Set config
        self.output_config_widget.set_config(
            {
                "output_dir": session.output_dir,
                "concurrent_limit": session.concurrent_limit,
                "force_overwrite": session.force_overwrite,
                "video_only": session.video_only,
            }
        )
        self.settings_page.reload_settings()

        # Recreate session in SessionService for tracking
        from ..data.models import OutputConfig

        config = OutputConfig(
            output_dir=session.output_dir,
            concurrent_limit=session.concurrent_limit,
            force_overwrite=session.force_overwrite,
            video_only=session.video_only,
            cookies_path=session.cookies_path,
        )
        self.session_service.create_session(session.pending_urls, config)

        self.download_log_widget.add_info(
            f"Restored session with {len(session.pending_urls)} pending URLs"
        )

    def closeEvent(self, event: QCloseEvent):
        """Handle window close event."""
        if self.download_manager.is_running:
            result = QMessageBox.question(
                self,
                "Confirm Exit",
                "Downloads are still in progress.\n\n"
                "Are you sure you want to exit?\n"
                "Your progress will be saved for next time.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if result == QMessageBox.StandardButton.No:
                event.ignore()
                return

            # Cancel downloads gracefully
            self.download_manager.cancel_all()

        # Stop auto-save and save any pending changes via SessionService
        self.session_service.stop_auto_save()

        event.accept()
