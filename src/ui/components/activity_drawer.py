"""Collapsible activity drawer for logs and recent actions."""

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class ActivityDrawer(QWidget):
    """Collapsible region for recent activity and logs."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("activityDrawer")
        self._expanded = False

        self._toggle_button = QPushButton(title)
        self._toggle_button.setObjectName("activityDrawerToggle")
        self._toggle_button.clicked.connect(self._on_toggle_clicked)

        self._badge_label = QLabel("")
        self._badge_label.setObjectName("activityDrawerBadge")

        self._content_widget = QWidget()
        self._content_widget.setObjectName("activityDrawerContent")
        self._content_widget.setVisible(False)
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        header_layout.addWidget(self._toggle_button)
        header_layout.addStretch(1)
        header_layout.addWidget(self._badge_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addLayout(header_layout)
        layout.addWidget(self._content_widget)

    def _on_toggle_clicked(self) -> None:
        """Flip the drawer open state."""
        self.set_expanded(not self._expanded)

    def set_content_widget(self, widget: QWidget) -> None:
        """Replace the activity content widget."""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            child = item.widget()
            if child is not None:
                child.setParent(None)
        self._content_layout.addWidget(widget)

    def set_badge_text(self, text: str) -> None:
        """Update the status badge text."""
        self._badge_label.setText(text)

    def badge_text(self) -> str:
        """Return the visible badge text."""
        return self._badge_label.text()

    def set_expanded(self, expanded: bool) -> None:
        """Update the drawer expansion state."""
        self._expanded = expanded
        self._content_widget.setVisible(expanded)

    def is_expanded(self) -> bool:
        """Return the current expansion state."""
        return self._expanded
