"""Reusable drag-and-drop overlay widget."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class DropOverlay(QWidget):
    """Full-page semi-transparent overlay shown during drag-over.

    The host page is responsible for showing/hiding this overlay
    by calling show()/hide() in its dragEnterEvent/dragLeaveEvent/dropEvent.

    Args:
        parent: The parent widget (typically a page).
        accepted_extensions: Optional list of file extensions this overlay accepts
            (e.g. [".mp4", ".mkv"]). Informational only — the host page does
            the actual filtering.
    """

    def __init__(
        self,
        parent: QWidget,
        accepted_extensions: list[str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("dropOverlay")
        self.accepted_extensions = accepted_extensions or []
        self.hide()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        icon = QLabel("\u2b07")  # downward arrow unicode
        icon.setObjectName("dropOverlayIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        self._text = QLabel("Drop files here")
        self._text.setObjectName("dropOverlayText")
        self._text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._text)

        self._hint = QLabel("")
        self._hint.setObjectName("dropOverlayHint")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._hint)

    def set_text(self, text: str) -> None:
        """Update the main overlay text."""
        self._text.setText(text)

    def set_hint(self, text: str) -> None:
        """Update the hint text below the main text."""
        self._hint.setText(text)

    def resize_to_parent(self) -> None:
        """Resize the overlay to match the parent widget's geometry."""
        if self.parent():
            self.setGeometry(self.parent().rect())
