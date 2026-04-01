from PyQt6.QtWidgets import QWidget, QHBoxLayout, QSizePolicy


class SplitLayout(QWidget):
    """Two-column bento split layout.

    Default proportions are roughly 8/12 + 4/12 (2:1).
    """

    def __init__(self, right_width: int = 360, gap: int = 20, parent=None):
        super().__init__(parent)
        self.setObjectName("splitLayout")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(gap)

        self.left_panel = QWidget()
        self.left_panel.setObjectName("splitLeft")
        self.left_panel.setMinimumWidth(300)
        self.left_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self.right_panel = QWidget()
        self.right_panel.setObjectName("splitRight")
        self.right_panel.setFixedWidth(right_width)

        layout.addWidget(self.left_panel)
        layout.addWidget(self.right_panel)
