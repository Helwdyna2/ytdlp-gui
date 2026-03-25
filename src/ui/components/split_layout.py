from PyQt6.QtWidgets import QWidget, QHBoxLayout, QSizePolicy


class SplitLayout(QWidget):
    def __init__(self, right_width: int = 320, parent=None):
        super().__init__(parent)
        self.setObjectName("splitLayout")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self.left_panel = QWidget()
        self.left_panel.setObjectName("splitLeft")
        self.left_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.right_panel = QWidget()
        self.right_panel.setObjectName("splitRight")
        self.right_panel.setFixedWidth(right_width)

        layout.addWidget(self.left_panel)
        layout.addWidget(self.right_panel)
