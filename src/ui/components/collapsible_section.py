"""Collapsible section — tonal header, no visible border box."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class CollapsibleSection(QFrame):
    """A section with a tonal header row that toggles content visibility."""

    def __init__(
        self,
        title: str,
        *,
        expanded: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("collapsibleSection")
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._expanded = expanded

        # Header row
        self._toggle_btn = QPushButton()
        self._toggle_btn.setObjectName("collapsibleToggle")
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setChecked(expanded)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setFixedSize(20, 20)
        self._toggle_btn.clicked.connect(self._on_toggle)
        self._update_arrow()

        self._title_label = QLabel(title)
        self._title_label.setObjectName("collapsibleTitle")
        self._title_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._title_label.mousePressEvent = lambda _e: self._toggle_btn.click()

        header = QHBoxLayout()
        header.setContentsMargins(0, 4, 0, 4)
        header.setSpacing(8)
        header.addWidget(self._toggle_btn)
        header.addWidget(self._title_label)
        header.addStretch()

        # Content container
        self._content = QWidget()
        self._content.setObjectName("collapsibleContent")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(28, 8, 0, 0)
        self._content_layout.setSpacing(8)
        self._content.setVisible(expanded)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addLayout(header)
        root.addWidget(self._content)

    @property
    def content_layout(self) -> QVBoxLayout:
        """Layout inside the collapsible body — add child widgets here."""
        return self._content_layout

    def set_content_widget(self, widget: QWidget) -> None:
        """Replace the content area with a single widget."""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self._content_layout.addWidget(widget)

    def is_expanded(self) -> bool:
        return self._expanded

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self._toggle_btn.setChecked(expanded)
        self._content.setVisible(expanded)
        self._update_arrow()

    def set_title(self, title: str) -> None:
        self._title_label.setText(title)

    def _on_toggle(self) -> None:
        self._expanded = self._toggle_btn.isChecked()
        self._content.setVisible(self._expanded)
        self._update_arrow()

    def _update_arrow(self) -> None:
        self._toggle_btn.setText("▾" if self._expanded else "▸")
