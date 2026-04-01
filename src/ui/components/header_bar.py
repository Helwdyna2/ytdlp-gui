"""HeaderBar — top header bar for the Digital Obsidian shell."""

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


SECTION_TABS = [
    ("downloads", "Downloads"),
    ("processing", "Processing"),
    ("organization", "Organization"),
]


class HeaderBar(QWidget):
    """Top header bar with brand label and section tabs."""

    section_selected = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("headerBar")
        self.setFixedHeight(48)

        self._buttons: dict[str, QPushButton] = {}
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(4)

        # Section tabs
        for key, label in SECTION_TABS:
            btn = QPushButton(label)
            btn.setObjectName("headerTab")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self.section_selected.emit(k))
            self._buttons[key] = btn
            self._button_group.addButton(btn)
            layout.addWidget(btn)

        layout.addStretch()

        # Select first tab by default
        first_key = SECTION_TABS[0][0]
        if first_key in self._buttons:
            self._buttons[first_key].setChecked(True)

    def select_section(self, key: str) -> None:
        """Programmatically select a section tab."""
        if key in self._buttons:
            self._buttons[key].setChecked(True)

    def active_section(self) -> str | None:
        """Return the key of the currently selected section."""
        for key, btn in self._buttons.items():
            if btn.isChecked():
                return key
        return None
