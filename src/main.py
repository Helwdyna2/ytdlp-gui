"""Application entry point."""

import locale
import sys
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox, QCheckBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication, QSurfaceFormat
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from .utils.platform_utils import ensure_dirs, get_log_dir
from .utils.constants import APP_NAME, APP_VERSION
from .utils.ffmpeg_utils import check_ffmpeg_available, get_ffmpeg_version
from .data.database import Database
from .data.repositories.session_repository import SessionRepository
from .services.crash_recovery_service import CrashRecoveryService
from .services.config_service import ConfigService
from .services.session_service import SessionService
from .ui.main_window import MainWindow
from .ui.theme.theme_engine import ThemeEngine


class SingleApplication(QApplication):
    """
    Single-instance application wrapper using Qt Local Sockets.

    Ensures only one instance of the application can run at a time.
    Uses QLocalServer/QLocalSocket for cross-platform instance detection.
    """

    def __init__(self, argv, key="ytdlp-gui-single-instance"):
        super().__init__(argv)
        self._key = key
        self._server = None
        self._is_primary = False

        # Try to connect to existing instance
        socket = QLocalSocket()
        socket.connectToServer(key)

        if socket.waitForConnected(500):
            # Another instance is running
            socket.disconnectFromServer()
            self._is_primary = False
            return

        # We're the primary instance - start server
        self._server = QLocalServer()
        # Remove any stale socket file (Unix) or named pipe (Windows)
        self._server.removeServer(key)

        if self._server.listen(key):
            self._is_primary = True
            logging.getLogger(__name__).debug(
                "SingleApplication: Acquired primary instance lock"
            )
        else:
            # Failed to listen - another instance might have started in the meantime
            self._is_primary = False
            logging.getLogger(__name__).warning(
                "SingleApplication: Failed to acquire lock"
            )

    def is_primary(self) -> bool:
        """Check if this is the primary (first) application instance."""
        return self._is_primary

    def cleanup(self):
        """Clean up the local server on shutdown."""
        if self._server:
            self._server.close()
            self._server = None
            logging.getLogger(__name__).debug(
                "SingleApplication: Released primary instance lock"
            )


def setup_logging():
    """Setup application logging."""
    ensure_dirs()
    log_file = get_log_dir() / "ytdlp_gui.log"

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Reduce noise from other libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("yt_dlp").setLevel(logging.WARNING)

    logging.info(f"Starting {APP_NAME} v{APP_VERSION}")


def check_crash_recovery(crash_service: CrashRecoveryService) -> bool:
    """
    Check for crash and offer recovery.

    Returns True if user wants to recover, False otherwise.
    """
    if not crash_service.check_crash():
        return False

    session = crash_service.get_recoverable_session()
    if not session:
        return False

    # Show recovery dialog
    result = QMessageBox.question(
        None,
        "Recover Previous Session",
        f"The application did not shut down cleanly.\n\n"
        f"Found {len(session.pending_urls)} URLs that were not downloaded.\n\n"
        "Would you like to restore them?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )

    if result == QMessageBox.StandardButton.Yes:
        crash_service.mark_recovered(session)
        return True
    else:
        crash_service.discard_session(session)
        return False


def check_ffmpeg_installation(logger: logging.Logger) -> None:
    """
    Check if FFmpeg/ffprobe are available and warn if not.

    This is a non-blocking warning - the app still runs but Sort/Convert
    tabs will not work without FFmpeg.
    """
    ffmpeg_available, ffprobe_available = check_ffmpeg_available()

    if ffmpeg_available and ffprobe_available:
        version = get_ffmpeg_version()
        logger.info(f"FFmpeg detected: {version}")
        return

    missing = []
    if not ffmpeg_available:
        missing.append("FFmpeg")
    if not ffprobe_available:
        missing.append("ffprobe")

    missing_str = " and ".join(missing)
    logger.warning(f"{missing_str} not found in PATH")

    # Check if user has dismissed this warning
    config = ConfigService()
    if config.get("ffmpeg.warning_dismissed"):
        logger.info("FFmpeg warning dismissed by user")
        return

    # Show warning dialog with "Don't show again" checkbox
    msg = QMessageBox()
    msg.setWindowTitle("FFmpeg Not Found")
    msg.setText(
        f"{missing_str} could not be found on your system.\n\n"
        "The Sort and Convert tabs require FFmpeg to work.\n\n"
        "To install FFmpeg:\n"
        "• macOS: brew install ffmpeg\n"
        "• Windows: Download from ffmpeg.org\n"
        "• Linux: sudo apt install ffmpeg\n\n"
        "The Download tab will work normally without FFmpeg."
    )
    msg.setIcon(QMessageBox.Icon.Warning)

    # Add "Don't show again" checkbox
    checkbox = QCheckBox("Don't show this warning again")
    msg.setCheckBox(checkbox)

    msg.exec()

    # Save preference if checkbox is checked
    if checkbox.isChecked():
        config.set("ffmpeg.warning_dismissed", True)
        config.save()
        logger.info("FFmpeg warning dismissed permanently by user")


def check_single_instance() -> bool:
    """
    Check if another instance is already running.

    Shows a warning dialog if another instance is detected.
    Returns True if this is the primary instance, False otherwise.
    """
    # Create a temporary socket to check for existing instance
    socket = QLocalSocket()
    socket.connectToServer("ytdlp-gui-single-instance")

    if socket.waitForConnected(500):
        # Another instance is running
        socket.disconnectFromServer()
        QMessageBox.warning(
            None,
            "Already Running",
            f"{APP_NAME} is already running.\n\n"
            "Only one instance can run at a time to prevent data conflicts.",
        )
        return False

    return True


def configure_process_locale(logger: logging.Logger) -> None:
    """Keep numeric formatting compatible with libmpv and FFmpeg parsing."""

    current = locale.setlocale(locale.LC_NUMERIC, None)
    if current == "C":
        return

    try:
        locale.setlocale(locale.LC_NUMERIC, "C")
    except locale.Error:
        logger.warning(
            "Unable to force LC_NUMERIC='C' at startup; current locale is %r.",
            current,
        )
        return

    logger.info("Adjusted LC_NUMERIC from %r to 'C' during startup.", current)


def main():
    """Main application entry point."""
    # Setup logging first
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        configure_process_locale(logger)

        surface_format = QSurfaceFormat()
        surface_format.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
        surface_format.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
        surface_format.setDepthBufferSize(24)
        surface_format.setStencilBufferSize(8)
        surface_format.setVersion(3, 2)
        surface_format.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        QSurfaceFormat.setDefaultFormat(surface_format)
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        # Create Qt application with single-instance support
        app = SingleApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)

        # Apply the Signal Deck theme
        theme_engine = ThemeEngine()
        theme_engine.apply_theme(app)

        # Check if this is the primary instance
        if not app.is_primary():
            logger.warning("Another instance is already running")
            QMessageBox.warning(
                None,
                "Already Running",
                f"{APP_NAME} is already running.\n\n"
                "Only one instance can run at a time to prevent data conflicts.",
            )
            return 0

        # Initialize database
        logger.info("Initializing database...")
        database = Database()

        # Initialize services
        config_service = ConfigService()
        session_repo = SessionRepository(database)
        crash_service = CrashRecoveryService(session_repo)
        session_service = SessionService(session_repo)

        # Check for crash recovery
        session_to_restore = None
        if check_crash_recovery(crash_service):
            session_to_restore = crash_service.get_recoverable_session()

        # Check FFmpeg availability (non-blocking warning)
        check_ffmpeg_installation(logger)

        # Acquire lock
        crash_service.acquire_lock()

        # Create main window
        logger.info("Creating main window...")
        main_window = MainWindow(database, session_service)

        # Start auto-save
        session_service.start_auto_save()

        # Restore session if available
        if session_to_restore:
            main_window.restore_session(session_to_restore)

        # Apply saved window geometry
        window_config = config_service.get_section("window")
        if window_config.get("x") is not None and window_config.get("y") is not None:
            main_window.move(window_config["x"], window_config["y"])
        if window_config.get("width") and window_config.get("height"):
            main_window.resize(window_config["width"], window_config["height"])
        if window_config.get("maximized"):
            main_window.showMaximized()
        else:
            main_window.show()

        # Run application
        logger.info("Application started")
        exit_code = app.exec()

        # Save window geometry
        if not main_window.isMaximized():
            config_service.set("window.x", main_window.x(), save=False)
            config_service.set("window.y", main_window.y(), save=False)
            config_service.set("window.width", main_window.width(), save=False)
            config_service.set("window.height", main_window.height(), save=False)
        config_service.set("window.maximized", main_window.isMaximized())

        # Clean shutdown
        session_service.stop_auto_save()
        if config_service.get("behavior.clear_transient_data_on_exit"):
            platform_utils.clear_transient_data()
        crash_service.release_lock()
        app.cleanup()
        database.close()

        logger.info("Application closed")
        return exit_code

    except Exception as e:
        logger.exception("Fatal error in main")
        QMessageBox.critical(
            None,
            "Fatal Error",
            f"An unexpected error occurred:\n\n{str(e)}\n\n"
            "Please check the log file for details.",
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
