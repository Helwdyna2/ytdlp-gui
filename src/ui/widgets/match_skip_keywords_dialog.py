"""Dialog for editing keywords excluded from Match Videos search."""

import logging
from typing import List

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPlainTextEdit,
    QDialogButtonBox,
    QPushButton,
)

logger = logging.getLogger(__name__)


class MatchSkipKeywordsDialog(QDialog):
    """Edit keywords/phrases to ignore when generating search queries."""

    def __init__(self, keywords: List[str], parent=None):
        """
        Initialize dialog.

        Args:
            keywords: Current list of keywords/phrases.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._keywords = keywords
        self._text_edit: QPlainTextEdit
        self._setup_ui()

    def get_keywords(self) -> List[str]:
        """Get cleaned keyword list from UI."""
        raw_text = self._text_edit.toPlainText()
        parts: List[str] = []

        for line in raw_text.splitlines():
            for item in line.split(","):
                keyword = item.strip()
                if keyword:
                    parts.append(keyword)

        # De-duplicate (case-insensitive) while preserving order.
        seen = set()
        cleaned: List[str] = []
        for keyword in parts:
            key = " ".join(keyword.lower().split())
            if not key or key in seen:
                continue
            seen.add(key)
            cleaned.append(keyword)

        return cleaned

    def _setup_ui(self) -> None:
        """Build dialog layout."""
        self.setWindowTitle("Search Exclusions")
        self.setMinimumSize(520, 360)

        layout = QVBoxLayout(self)

        info = QLabel(
            "Keywords/phrases listed here are ignored when generating search queries.\n"
            "One per line (commas are also accepted). Matching is case-insensitive.\n"
            "Tip: Use this for personal tags like 'Missionary', 'BJ', 'Doggy Style'."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self._text_edit = QPlainTextEdit()
        self._text_edit.setPlaceholderText("Missionary\nBJ\nDoggy Style\nPOV")
        self._text_edit.setPlainText("\n".join(self._keywords or []))
        layout.addWidget(self._text_edit, 1)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        clear_button = QPushButton("Clear")
        clear_button.setObjectName("btnWire")
        clear_button.clicked.connect(self._text_edit.clear)
        button_box.addButton(clear_button, QDialogButtonBox.ButtonRole.ResetRole)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
