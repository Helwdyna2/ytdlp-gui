"""File browser widget for URL files."""

import logging
import os
from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QFileDialog,
    QMessageBox,
)

from ...core.file_parser import FileParser
from ...utils.constants import URL_FILE_FILTER
from ...utils.dialog_utils import get_dialog_start_dir, update_dialog_last_dir

logger = logging.getLogger(__name__)


class FilePickerWidget(QWidget):
    """
    File browser for URL files.

    Provides a file picker for .txt/.md files containing URLs.
    """

    urls_loaded = pyqtSignal(list)  # Emitted when URLs are loaded from file

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.file_parser = FileParser()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # URL file picker
        url_file_layout = QHBoxLayout()
        url_file_layout.addWidget(QLabel("URL File:"))

        self.url_file_path_edit = QLineEdit()
        self.url_file_path_edit.setPlaceholderText(
            "Select a .txt or .md file with URLs..."
        )
        self.url_file_path_edit.setReadOnly(True)
        url_file_layout.addWidget(self.url_file_path_edit, stretch=1)

        self.url_file_browse_btn = QPushButton("Browse...")
        self.url_file_browse_btn.setObjectName("btnWire")
        self.url_file_browse_btn.setProperty("button_role", "secondary")
        self.url_file_browse_btn.clicked.connect(self._browse_url_file)
        url_file_layout.addWidget(self.url_file_browse_btn)

        self.url_file_load_btn = QPushButton("Load")
        self.url_file_load_btn.setObjectName("btnPrimary")
        self.url_file_load_btn.setProperty("button_role", "primary")
        self.url_file_load_btn.clicked.connect(self._load_url_file)
        self.url_file_load_btn.setEnabled(False)
        url_file_layout.addWidget(self.url_file_load_btn)

        layout.addLayout(url_file_layout)

    def _browse_url_file(self) -> None:
        """Open file dialog for URL file."""
        start_dir = get_dialog_start_dir(self.url_file_path_edit.text())
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select URL File", start_dir, URL_FILE_FILTER
        )

        if file_path:
            update_dialog_last_dir(file_path)
            self.url_file_path_edit.setText(file_path)
            self.url_file_load_btn.setEnabled(True)

    def _validate_file_path(self, file_path: str) -> tuple[bool, str]:
        """
        Validate a file path and return (is_valid, error_message).

        Args:
            file_path: Path to the file to validate.

        Returns:
            Tuple of (is_valid, error_message). If is_valid is True,
            error_message will be empty.
        """
        if not file_path:
            return False, "No file selected."

        if not os.path.exists(file_path):
            return (
                False,
                f"File does not exist:\n{file_path}\n\n"
                "The file may have been moved or deleted. "
                "Please select a different file.",
            )

        if not os.path.isfile(file_path):
            return (
                False,
                f"Selected path is not a file:\n{file_path}\n\n"
                "Please select a text file (.txt or .md) containing URLs.",
            )

        if not os.access(file_path, os.R_OK):
            return (
                False,
                f"Permission denied:\n{file_path}\n\n"
                "You don't have read access to this file. "
                "Try:\n"
                "• Check file permissions\n"
                "• Run the application with appropriate privileges\n"
                "• Copy the file to a location you can access",
            )

        return True, ""

    def _load_url_file(self) -> None:
        """Load URLs from the selected file with improved error handling."""
        file_path = self.url_file_path_edit.text()

        # Validate the file path first
        is_valid, error_msg = self._validate_file_path(file_path)
        if not is_valid:
            logger.warning(f"File validation failed: {error_msg}")
            QMessageBox.warning(
                self, "Invalid File Selection", error_msg, QMessageBox.StandardButton.Ok
            )
            return

        try:
            urls = self.file_parser.parse_file(file_path)
            if urls:
                logger.info(f"Loaded {len(urls)} URLs from {file_path}")
                self.urls_loaded.emit(urls)
            else:
                # Clear path if no URLs found
                logger.warning(f"No URLs found in file: {file_path}")
                self.url_file_path_edit.setText("")
                self.url_file_load_btn.setEnabled(False)
                QMessageBox.information(
                    self,
                    "No URLs Found",
                    f"The file does not contain any valid URLs:\n{file_path}\n\n"
                    "Please check that the file contains URLs starting with http:// or https://",
                    QMessageBox.StandardButton.Ok,
                )

        except FileNotFoundError as e:
            logger.error(f"File not found during parse: {e}")
            QMessageBox.warning(
                self,
                "File Not Found",
                f"The file could not be accessed:\n{file_path}\n\n"
                "The file may have been moved or deleted after selection.",
                QMessageBox.StandardButton.Ok,
            )

        except PermissionError as e:
            logger.error(f"Permission denied reading file: {e}")
            QMessageBox.warning(
                self,
                "Permission Denied",
                f"Cannot read the file:\n{file_path}\n\n"
                "You don't have permission to access this file. "
                "Try copying it to a different location.",
                QMessageBox.StandardButton.Ok,
            )

        except ValueError as e:
            logger.error(f"Unsupported file type: {e}")
            QMessageBox.warning(
                self,
                "Unsupported File Type",
                f"The selected file is not supported:\n{file_path}\n\n"
                "Please select a .txt or .md file containing URLs.",
                QMessageBox.StandardButton.Ok,
            )

        except Exception as e:
            logger.exception(f"Unexpected error loading URLs from {file_path}")
            QMessageBox.critical(
                self,
                "Error Loading File",
                f"An unexpected error occurred while loading the file:\n{file_path}\n\n"
                f"Error: {str(e)}\n\n"
                "Please try again or select a different file.",
                QMessageBox.StandardButton.Ok,
            )

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the widget."""
        self.url_file_browse_btn.setEnabled(enabled)
        self.url_file_load_btn.setEnabled(
            enabled and bool(self.url_file_path_edit.text())
        )
