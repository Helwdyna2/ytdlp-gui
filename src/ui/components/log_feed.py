"""LogFeed — Digital Obsidian structured log display.

Replaces plain QTextEdit log areas with a structured, themed log feed
featuring timestamps, colored level tags, and auto-scroll.
"""

import logging
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class StatusTag(QLabel):
    """Inline status pill styled via QSS dynamic properties."""

    def __init__(self, text: str, color: str = "cyan", parent=None):
        super().__init__(text, parent)
        self.setObjectName("statusTag")
        self.setProperty("color", color)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

_LEVEL_MAP = {
    "info": ("INFO", "cyan"),
    "warning": ("WARN", "orange"),
    "error": ("ERROR", "red"),
}


class LogFeed(QWidget):
    """Styled log display with timestamps, level tags, and auto-scroll.

    Args:
        max_entries: Maximum number of log entries to retain (oldest removed first).
        parent: Optional parent widget.
    """

    def __init__(
        self,
        max_entries: int = 500,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("logFeed")
        self._max_entries = max_entries
        self._auto_scroll = True
        self._entry_count = 0

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the scroll area and inner container."""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(4, 4, 4, 4)
        self._container_layout.setSpacing(2)
        self._container_layout.addStretch()

        self._scroll_area.setWidget(self._container)
        outer_layout.addWidget(self._scroll_area)

    def add_entry(self, message: str, level: str = "info") -> None:
        """Add a log entry.

        Args:
            message: The log message text.
            level: One of "info", "warning", "error".
        """
        # Build row widget
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        # Timestamp
        timestamp = QLabel(datetime.now().strftime("%H:%M:%S"))
        timestamp.setObjectName("logTimestamp")
        timestamp.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        row_layout.addWidget(timestamp)

        # Level tag
        tag_text, tag_color = _LEVEL_MAP.get(level, ("INFO", "cyan"))
        tag = StatusTag(tag_text, tag_color)
        row_layout.addWidget(tag)

        # Message
        msg_label = QLabel(message)
        msg_label.setObjectName("logMessage")
        msg_label.setWordWrap(True)
        msg_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        row_layout.addWidget(msg_label)

        # Insert before the stretch item (which is always last)
        insert_index = self._container_layout.count() - 1
        self._container_layout.insertWidget(insert_index, row)
        self._entry_count += 1

        # Enforce max_entries by removing oldest (top) entries
        while self._entry_count > self._max_entries:
            item = self._container_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
            self._entry_count -= 1

        # Auto-scroll to bottom
        if self._auto_scroll:
            vbar = self._scroll_area.verticalScrollBar()
            if vbar:
                vbar.setValue(vbar.maximum())

    def clear(self) -> None:
        """Remove all log entries."""
        # Remove all widgets except the trailing stretch
        while self._container_layout.count() > 1:
            item = self._container_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._entry_count = 0

    def entry_count(self) -> int:
        """Return the number of log entries currently displayed."""
        return self._entry_count

    def set_auto_scroll(self, enabled: bool) -> None:
        """Enable or disable auto-scroll to bottom on new entries.

        Args:
            enabled: Whether to auto-scroll.
        """
        self._auto_scroll = enabled
