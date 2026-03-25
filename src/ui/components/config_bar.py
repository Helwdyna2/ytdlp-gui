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
        lbl = QLabel(label)
        lbl.setObjectName("configLabel")
        self._layout.addWidget(lbl)
        self._layout.addWidget(widget)

    def add_separator(self) -> None:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        self._layout.addWidget(line)

    def add_stretch(self) -> None:
        self._layout.addStretch()
