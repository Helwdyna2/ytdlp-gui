"""URL input widget with auto-parsing, sorting, and deduplication."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QLabel,
    QPushButton,
)
from PyQt6.QtCore import pyqtSignal, QTimer, Qt
from typing import List

from ...core.url_parser import UrlParser
from ...utils.constants import DEBOUNCE_PARSE_MS


class UrlInputWidget(QWidget):
    """
    Text input area with auto-parsing, sorting, deduplication.

    Accepts raw text with URLs, extracts and validates them,
    sorts alphabetically, and removes duplicates.
    """

    urls_changed = pyqtSignal(list)  # Emits validated, sorted, deduplicated URLs

    def __init__(self, parent=None):
        super().__init__(parent)
        self.url_parser = UrlParser()
        self._current_urls: List[str] = []
        self._setup_ui()
        self._setup_debounce()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Text input
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText(
            "Paste video links here — one per line, or mixed with other text\n\n"
            "Links are automatically extracted, validated, sorted, and deduplicated."
        )
        self.text_edit.setAccessibleName("URL Input")
        self.text_edit.setAccessibleDescription(
            "Enter video URLs to download, one per line or mixed with text"
        )
        self.text_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.text_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.text_edit)

        # Bottom row: count + buttons
        bottom_layout = QHBoxLayout()

        self.url_count_label = QLabel("No links added yet")
        self.url_count_label.setObjectName("boldLabel")
        self.url_count_label.setAccessibleName("URL Count")
        self.url_count_label.setAccessibleDescription(
            "Number of valid URLs detected in the input"
        )
        bottom_layout.addWidget(self.url_count_label)

        bottom_layout.addStretch()

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("btnWire")
        self.clear_btn.setProperty("button_role", "secondary")
        self.clear_btn.setAccessibleName("Clear URLs")
        self.clear_btn.setAccessibleDescription("Clear all URLs from the input area")
        self.clear_btn.clicked.connect(self._clear_text)
        bottom_layout.addWidget(self.clear_btn)

        layout.addLayout(bottom_layout)

    def _setup_debounce(self):
        """Debounce parsing to avoid excessive CPU on rapid typing."""
        self._parse_timer = QTimer(self)
        self._parse_timer.setSingleShot(True)
        self._parse_timer.timeout.connect(self._parse_urls)

    def _on_text_changed(self):
        """Restart debounce timer on text change."""
        self._parse_timer.start(DEBOUNCE_PARSE_MS)

    def _parse_urls(self):
        """Parse, validate, sort, deduplicate URLs."""
        text = self.text_edit.toPlainText()
        urls = self.url_parser.process_text(text)
        self._current_urls = urls

        # Update count label
        count = len(urls)
        if count == 0:
            self.url_count_label.setText("No links added yet")
        elif count == 1:
            self.url_count_label.setText("1 link ready")
        else:
            self.url_count_label.setText(f"{count} links ready")

        self.urls_changed.emit(urls)

    def _clear_text(self):
        """Clear the text input."""
        self.text_edit.clear()

    def get_urls(self) -> List[str]:
        """Get current parsed URLs."""
        return self._current_urls.copy()

    def add_urls(self, urls: List[str]):
        """Add URLs to existing text."""
        if not urls:
            return

        current = self.text_edit.toPlainText()
        new_text = "\n".join(urls)

        if current:
            new_text = current + "\n" + new_text

        self.text_edit.setPlainText(new_text)

    def set_urls(self, urls: List[str]):
        """Replace current text with URLs."""
        self.text_edit.setPlainText("\n".join(urls))

    def clear(self):
        """Clear the input."""
        self.text_edit.clear()

    def focus_input(self):
        """Focus the URL text input area.

        Can be called from the main window to support keyboard shortcuts
        like Ctrl+L for quick URL entry.
        """
        self.text_edit.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def set_enabled(self, enabled: bool):
        """Enable or disable the widget."""
        self.text_edit.setEnabled(enabled)
        self.clear_btn.setEnabled(enabled)
