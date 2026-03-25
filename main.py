"""Application entry point for PyInstaller."""

import sys
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from src.utils.platform_utils import ensure_dirs, get_log_dir
from src.utils.constants import APP_NAME, APP_VERSION
from src.data.database import Database
from src.data.repositories.session_repository import SessionRepository
from src.services.crash_recovery_service import CrashRecoveryService
from src.services.config_service import ConfigService
from src.ui.main_window import MainWindow


def setup_logging():
    """Setup application logging."""
    ensure_dirs()
    log_file = get_log_dir() / 'ytdlp_gui.log'

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
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
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('yt_dlp').setLevel(logging.WARNING)

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
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )

    if result == QMessageBox.StandardButton.Yes:
        crash_service.mark_recovered(session)
        return True
    else:
        crash_service.discard_session(session)
        return False


def main():
    """Main application entry point."""
    # Setup logging first
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # Create Qt application
        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)

        # Enable high DPI scaling
        app.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        # Initialize database
        logger.info("Initializing database...")
        database = Database()

        # Initialize services
        config_service = ConfigService()
        session_repo = SessionRepository(database)
        crash_service = CrashRecoveryService(session_repo)

        # Check for crash recovery
        session_to_restore = None
        if check_crash_recovery(crash_service):
            session_to_restore = crash_service.get_recoverable_session()

        # Acquire lock
        crash_service.acquire_lock()

        # Create main window
        logger.info("Creating main window...")
        main_window = MainWindow(database)

        # Restore session if available
        if session_to_restore:
            main_window.restore_session(session_to_restore)

        # Apply saved window geometry
        window_config = config_service.get_section('window')
        if window_config.get('x') is not None and window_config.get('y') is not None:
            main_window.move(window_config['x'], window_config['y'])
        if window_config.get('width') and window_config.get('height'):
            main_window.resize(window_config['width'], window_config['height'])
        if window_config.get('maximized'):
            main_window.showMaximized()
        else:
            main_window.show()

        # Run application
        logger.info("Application started")
        exit_code = app.exec()

        # Save window geometry
        if not main_window.isMaximized():
            config_service.set('window.x', main_window.x(), save=False)
            config_service.set('window.y', main_window.y(), save=False)
            config_service.set('window.width', main_window.width(), save=False)
            config_service.set('window.height', main_window.height(), save=False)
        config_service.set('window.maximized', main_window.isMaximized())

        # Clean shutdown
        crash_service.release_lock()
        database.close()

        logger.info("Application closed")
        return exit_code

    except Exception as e:
        logger.exception("Fatal error in main")
        QMessageBox.critical(
            None,
            "Fatal Error",
            f"An unexpected error occurred:\n\n{str(e)}\n\n"
            "Please check the log file for details."
        )
        return 1


if __name__ == '__main__':
    sys.exit(main())
