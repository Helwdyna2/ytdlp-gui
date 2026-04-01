"""StatusBar — bottom status bar for the Digital Obsidian shell."""

import shutil
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget


class StatusBar(QWidget):
    """Bottom status bar with status dot, text, and dependency metadata."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setFixedHeight(28)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)

        # Status dot
        self._status_dot = QLabel()
        self._status_dot.setObjectName("statusDot")
        self._status_dot.setFixedSize(8, 8)
        layout.addWidget(self._status_dot)

        # Status text
        self._status_text = QLabel("Status: Idle")
        self._status_text.setObjectName("statusBarText")
        layout.addWidget(self._status_text)

        layout.addStretch()

        # Dependency metadata
        self._meta_labels: dict[str, QLabel] = {}
        self._add_meta("yt-dlp", self._detect_version("yt-dlp"))
        self._add_meta("ffmpeg", self._detect_version("ffmpeg"))

    def _add_meta(self, name: str, version: str) -> None:
        """Add a metadata label for a dependency."""
        lbl = QLabel(f"{name}: {version}")
        lbl.setObjectName("statusBarMeta")
        self._meta_labels[name] = lbl
        self.layout().addWidget(lbl)

    @staticmethod
    def _detect_version(tool: str) -> str:
        """Check if a tool is available in PATH."""
        return "OK" if shutil.which(tool) else "Not found"

    def set_status(self, text: str) -> None:
        """Update the status text."""
        self._status_text.setText(f"Status: {text}")

    def set_metadata(self, key: str, value: str) -> None:
        """Update a metadata entry."""
        if key in self._meta_labels:
            self._meta_labels[key].setText(f"{key}: {value}")
