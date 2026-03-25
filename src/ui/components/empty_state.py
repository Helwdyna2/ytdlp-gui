"""Empty-state placeholder with icon, message, and optional action."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class EmptyStateWidget(QWidget):
    """Centred placeholder shown when a view has no content yet."""

    def __init__(
        self,
        *,
        icon: str = "",
        title: str = "Nothing here yet",
        description: str = "",
        action_text: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("emptyState")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._icon_label = QLabel(icon)
        self._icon_label.setObjectName("emptyStateIcon")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setVisible(bool(icon.strip()))

        self._title_label = QLabel(title)
        self._title_label.setObjectName("emptyStateTitle")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._desc_label = QLabel(description)
        self._desc_label.setObjectName("emptyStateDesc")
        self._desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._desc_label.setWordWrap(True)
        self._desc_label.setVisible(bool(description))

        self._action_btn = QPushButton(action_text)
        self._action_btn.setObjectName("emptyStateAction")
        self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action_btn.setVisible(bool(action_text))

        inner = QVBoxLayout()
        inner.setSpacing(8)
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(self._icon_label)
        inner.addWidget(self._title_label)
        inner.addWidget(self._desc_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._action_btn)
        btn_row.addStretch()
        inner.addLayout(btn_row)

        root = QVBoxLayout(self)
        root.addStretch()
        root.addLayout(inner)
        root.addStretch()

    @property
    def action_button(self) -> QPushButton:
        """The call-to-action button (connect its clicked signal)."""
        return self._action_btn

    def set_icon(self, icon: str) -> None:
        self._icon_label.setText(icon)
        self._icon_label.setVisible(bool(icon.strip()))

    def set_title(self, title: str) -> None:
        self._title_label.setText(title)

    def set_description(self, desc: str) -> None:
        self._desc_label.setText(desc)
        self._desc_label.setVisible(bool(desc))

    def set_action_text(self, text: str) -> None:
        """Update the action button label and toggle visibility."""
        self._action_btn.setText(text)
        self._action_btn.setVisible(bool(text))
