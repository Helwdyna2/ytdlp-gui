"""Sidebar navigation component with flat nav and sections."""

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QButtonGroup, QFrame, QSizePolicy
)

from src.ui.theme.icons import get_icon

SECTIONS = [
    ("DOWNLOAD", [
        ("add_urls", "Add URLs"),
        ("extract_urls", "Extract URLs"),
    ]),
    ("PROCESS", [
        ("convert", "Convert"),
        ("trim", "Trim"),
        ("metadata", "Metadata"),
    ]),
    ("ORGANIZE", [
        ("sort", "Sort"),
        ("rename", "Rename"),
        ("match", "Match"),
    ]),
]
SETTINGS_ITEM = ("settings", "Settings")


class Sidebar(QWidget):
    """Flat sidebar navigation with sections, icons, and badges."""

    tool_selected = pyqtSignal(str)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(190)
        self.setObjectName("sidebar")

        self._buttons: dict[str, QPushButton] = {}
        self._labels: dict[str, str] = {}
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        self._build_layout()

        # Check first tool by default
        first_key = SECTIONS[0][1][0][0]
        if first_key in self._buttons:
            self._buttons[first_key].setChecked(True)

    def _make_separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line

    def _make_tool_button(self, key: str, label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setObjectName("sidebarItem")
        btn.setCheckable(True)
        btn.setIcon(get_icon(key))
        self._buttons[key] = btn
        self._labels[key] = label
        self._button_group.addButton(btn)
        btn.clicked.connect(lambda checked, k=key: self.tool_selected.emit(k))
        return btn

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(2)

        # App title
        title = QLabel("yt-dlp")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        # App subtitle
        subtitle = QLabel("Download \u00b7 Convert \u00b7 Organize")
        subtitle.setObjectName("appSubtitle")
        layout.addWidget(subtitle)

        # Separator
        layout.addWidget(self._make_separator())
        layout.addSpacing(4)

        # Sections
        for section_name, tools in SECTIONS:
            header = QLabel(section_name)
            header.setObjectName("sidebarSection")
            layout.addWidget(header)

            for key, label in tools:
                btn = self._make_tool_button(key, label)
                layout.addWidget(btn)

            layout.addSpacing(6)

        # Spacer to push settings to bottom
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout.addWidget(spacer)

        # Bottom separator
        layout.addWidget(self._make_separator())

        # Settings button
        settings_key, settings_label = SETTINGS_ITEM
        settings_btn = self._make_tool_button(settings_key, settings_label)
        layout.addWidget(settings_btn)

    def select_tool(self, key: str) -> None:
        """Programmatically select a tool (checks button, emits signal)."""
        if key in self._buttons:
            self._buttons[key].setChecked(True)
            self.tool_selected.emit(key)

    def set_badge(self, key: str, count: int) -> None:
        """Show/hide a badge count on a sidebar item (visual only)."""
        if key in self._buttons:
            btn = self._buttons[key]
            base = self._labels[key]
            if count > 0:
                btn.setText(f"{base}  {count}")
            else:
                btn.setText(base)

    def item_count(self) -> int:
        """Return total number of nav items (including settings)."""
        return len(self._buttons)

    def active_tool(self) -> str | None:
        """Return the currently selected tool key."""
        for key, btn in self._buttons.items():
            if btn.isChecked():
                return key
        return None
