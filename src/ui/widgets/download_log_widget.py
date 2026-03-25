"""Scrollable download log widget with timestamps."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QPushButton,
    QLabel,
)

from ...services.config_service import ConfigService
from ...utils.constants import LOG_MAX_LINES
from ..components.log_feed import LogFeed


class DownloadLogWidget(QWidget):
    """
    Scrollable download log with timestamps.

    Displays log entries with timestamps and log levels.
    Supports auto-scroll and log level filtering.
    Delegates rendering to the themed LogFeed component.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = ConfigService()
        self._log_buffer: list[str] = []
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # LogFeed component handles all rendering
        self._log_feed = LogFeed(max_entries=LOG_MAX_LINES)
        self._log_feed.setAccessibleName("Download Log")
        self._log_feed.setAccessibleDescription(
            "Read-only log of download events with timestamps"
        )
        layout.addWidget(self._log_feed)

        # Controls row
        controls_layout = QHBoxLayout()

        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(True)
        self.auto_scroll_cb.setAccessibleName("Auto-scroll Log")
        self.auto_scroll_cb.setAccessibleDescription(
            "Automatically scroll to the latest log entry"
        )
        self.auto_scroll_cb.stateChanged.connect(self._on_auto_scroll_changed)
        controls_layout.addWidget(self.auto_scroll_cb)

        controls_layout.addStretch()

        self.line_count_label = QLabel("0 entries")
        self.line_count_label.setObjectName("dimLabel")
        self.line_count_label.setAccessibleName("Log Entry Count")
        self.line_count_label.setAccessibleDescription(
            "Number of entries in the download log"
        )
        controls_layout.addWidget(self.line_count_label)

        self.clear_btn = QPushButton("Clear Log")
        self.clear_btn.setObjectName("btnWire")
        self.clear_btn.setProperty("button_role", "secondary")
        self.clear_btn.setAccessibleName("Clear Log")
        self.clear_btn.setAccessibleDescription(
            "Clear all entries from the download log"
        )
        self.clear_btn.clicked.connect(self.clear)
        controls_layout.addWidget(self.clear_btn)

        layout.addLayout(controls_layout)

    def _load_settings(self) -> None:
        """Load saved settings."""
        auto_scroll = self._config.get("behavior.download_log_auto_scroll", True)
        self.auto_scroll_cb.setChecked(auto_scroll)
        self._log_feed.set_auto_scroll(auto_scroll)

    def _on_auto_scroll_changed(self) -> None:
        """Handle auto-scroll checkbox change."""
        enabled = self.auto_scroll_cb.isChecked()
        self._config.set("behavior.download_log_auto_scroll", enabled)
        self._log_feed.set_auto_scroll(enabled)

    def add_entry(self, level: str, message: str):
        """
        Add a log entry with timestamp.

        Args:
            level: Log level ('info', 'warning', 'error')
            message: Log message
        """
        self._log_feed.add_entry(message, level)
        self._log_buffer.append(f"[{level.upper()}] {message}")

        # Update count
        count = self._log_feed.entry_count()
        self.line_count_label.setText(f"{count} entries")

    def add_info(self, message: str):
        """Add an info log entry."""
        self.add_entry("info", message)

    def add_warning(self, message: str):
        """Add a warning log entry."""
        self.add_entry("warning", message)

    def add_error(self, message: str):
        """Add an error log entry."""
        self.add_entry("error", message)

    def clear(self):
        """Clear the log."""
        self._log_feed.clear()
        self._log_buffer.clear()
        self.line_count_label.setText("0 entries")

    def get_log_text(self) -> str:
        """Get log as plain text.

        Returns:
            All log entries joined by newlines.
        """
        return "\n".join(self._log_buffer)

    def set_enabled(self, enabled: bool):
        """Enable or disable controls."""
        self.auto_scroll_cb.setEnabled(enabled)
        self.clear_btn.setEnabled(enabled)
