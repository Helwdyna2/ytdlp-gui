"""Compact horizontal bar for source-folder selection."""

from typing import Callable, Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


class SourceFolderBar(QWidget):
    """Single-row widget: label + path + Browse + optional Scan button."""

    folder_changed = pyqtSignal(str)
    scan_requested = pyqtSignal(str)
    path_text_changed = pyqtSignal(str)
    subdirs_state_changed = pyqtSignal(int)

    def __init__(
        self,
        *,
        label: str = "Source:",
        show_scan: bool = True,
        show_subdirs: bool = False,
        start_dir_callback: Optional[Callable[[], str]] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("sourceFolderBar")
        self._start_dir_callback = start_dir_callback

        self._label = QLabel(label)
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Choose a folder…")
        self._path_edit.setReadOnly(True)
        self._path_edit.setObjectName("sourceFolderPath")

        self._browse_btn = QPushButton("Browse")
        self._browse_btn.setObjectName("btnWire")
        self._browse_btn.setProperty("button_role", "secondary")
        self._browse_btn.clicked.connect(self._on_browse)

        self._scan_btn = QPushButton("Scan")
        self._scan_btn.setObjectName("btnPrimary")
        self._scan_btn.setProperty("button_role", "primary")
        self._scan_btn.clicked.connect(self._on_scan)
        self._scan_btn.setVisible(show_scan)

        self._subdirs_check = QCheckBox("Subdirectories")
        self._subdirs_check.setVisible(show_subdirs)

        # Forward internal widget signals to public signals
        self._path_edit.textChanged.connect(self.path_text_changed)
        self._subdirs_check.stateChanged.connect(self.subdirs_state_changed)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(self._label)
        row.addWidget(self._path_edit, stretch=1)
        row.addWidget(self._browse_btn)
        row.addWidget(self._scan_btn)
        row.addWidget(self._subdirs_check)

    # --- Public read/write API ---

    def folder(self) -> str:
        return self._path_edit.text()

    def set_folder(self, path: str) -> None:
        self._path_edit.setText(path)

    def include_subdirs(self) -> bool:
        return self._subdirs_check.isChecked()

    def set_include_subdirs(self, checked: bool) -> None:
        self._subdirs_check.setChecked(checked)

    # --- Public enable/disable API ---

    def set_scan_enabled(self, enabled: bool) -> None:
        """Enable or disable the Scan button."""
        self._scan_btn.setEnabled(enabled)

    def set_browse_enabled(self, enabled: bool) -> None:
        """Enable or disable the Browse button."""
        self._browse_btn.setEnabled(enabled)

    def set_path_enabled(self, enabled: bool) -> None:
        """Enable or disable the path line-edit."""
        self._path_edit.setEnabled(enabled)

    def set_subdirs_enabled(self, enabled: bool) -> None:
        """Enable or disable the subdirectories checkbox."""
        self._subdirs_check.setEnabled(enabled)

    # --- Internal handlers ---

    def _on_browse(self) -> None:
        if self._start_dir_callback is not None:
            start_dir = self._start_dir_callback()
        else:
            start_dir = self.folder()
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", start_dir)
        if folder:
            self._path_edit.setText(folder)
            self.folder_changed.emit(folder)

    def _on_scan(self) -> None:
        path = self.folder()
        if path:
            self.scan_requested.emit(path)
