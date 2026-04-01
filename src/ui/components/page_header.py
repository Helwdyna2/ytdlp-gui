from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel


class PageHeader(QWidget):
    def __init__(self, title: str = "", description: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("pageHeader")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(16)

        # Left: title + description stacked
        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("pageTitle")

        self.description_label = QLabel(description)
        self.description_label.setObjectName("pageDescription")

        text_col.addWidget(self.title_label)
        text_col.addWidget(self.description_label)
        layout.addLayout(text_col)
        layout.addStretch()

        # Right: stat cards area
        self._stats_layout = QHBoxLayout()
        self._stats_layout.setSpacing(12)
        self._stat_value_labels: dict[str, QLabel] = {}
        self._stat_cards: dict[str, QWidget] = {}
        layout.addLayout(self._stats_layout)

    def set_title(self, text: str) -> None:
        self.title_label.setText(text)

    def set_description(self, text: str) -> None:
        self.description_label.setText(text)

    def add_stat(self, label: str, value: str, color: str | None = None) -> None:
        card = QWidget()
        card.setObjectName("statCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 8, 12, 8)
        card_layout.setSpacing(2)

        val_label = QLabel(value)
        val_label.setObjectName("statValue")
        val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if color:
            val_label.setProperty("dataColor", color)

        lbl_label = QLabel(label.upper())
        lbl_label.setObjectName("statLabel")
        lbl_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(val_label)
        card_layout.addWidget(lbl_label)
        self._stats_layout.addWidget(card)
        self._stat_value_labels[label] = val_label
        self._stat_cards[label] = card

    def update_stat(self, label: str, value: str, color: str | None = None) -> None:
        if label in self._stat_value_labels:
            lbl = self._stat_value_labels[label]
            lbl.setText(value)
            if color:
                lbl.setProperty("dataColor", color)
                lbl.style().unpolish(lbl)
                lbl.style().polish(lbl)
