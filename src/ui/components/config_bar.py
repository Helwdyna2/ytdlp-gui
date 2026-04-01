from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt


class ConfigBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("configBar")

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 8, 12, 8)
        self._layout.setSpacing(16)

    def add_field(self, label: str, widget: QWidget) -> None:
        lbl = QLabel(label.upper())
        lbl.setObjectName("configLabel")
        self._layout.addWidget(lbl)
        self._layout.addWidget(widget)

    def add_separator(self) -> None:
        # Replaced visual separator with spacing for Digital Obsidian
        self._layout.addSpacing(8)

    def add_stretch(self) -> None:
        self._layout.addStretch()
