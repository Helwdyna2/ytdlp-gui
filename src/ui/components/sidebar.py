"""Sidebar navigation component — Digital Obsidian design system."""

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

# Map tool keys to header sections for cross-wiring
TOOL_SECTION_MAP = {
    "add_urls": "downloads",
    "extract_urls": "downloads",
    "convert": "processing",
    "trim": "processing",
    "metadata": "processing",
    "sort": "organization",
    "rename": "organization",
    "match": "organization",
    "settings": "organization",
}


class Sidebar(QWidget):
    """Flat sidebar navigation with branding, sections, icons, badges, and CTA."""

    tool_selected = pyqtSignal(str)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(220)
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

    def _make_tool_button(self, key: str, label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setObjectName("sidebarItem")
        btn.setCheckable(True)
        btn.setIcon(get_icon(key))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._buttons[key] = btn
        self._labels[key] = label
        self._button_group.addButton(btn)
        btn.clicked.connect(lambda checked, k=key: self.tool_selected.emit(k))
        return btn

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(2)

        # Branding
        title = QLabel("Media Core")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        subtitle = QLabel("Download · Convert · Organize")
        subtitle.setObjectName("appSubtitle")
        layout.addWidget(subtitle)

        layout.addSpacing(16)

        # Sections
        for section_name, tools in SECTIONS:
            header = QLabel(section_name)
            header.setObjectName("sidebarSection")
            layout.addWidget(header)

            for key, label in tools:
                btn = self._make_tool_button(key, label)
                layout.addWidget(btn)

            layout.addSpacing(8)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout.addWidget(spacer)

        # CTA button
        self._cta_btn = QPushButton("New Batch")
        self._cta_btn.setObjectName("sidebarCta")
        self._cta_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cta_btn.clicked.connect(lambda: self.tool_selected.emit("add_urls"))
        layout.addWidget(self._cta_btn)

        layout.addSpacing(8)

        # Bottom utility links
        settings_key, settings_label = SETTINGS_ITEM
        settings_btn = self._make_tool_button(settings_key, settings_label)
        layout.addWidget(settings_btn)

    def select_tool(self, key: str) -> None:
        """Programmatically select a tool (checks button, emits signal)."""
        if key in self._buttons:
            self._buttons[key].setChecked(True)
            self.tool_selected.emit(key)

    def set_badge(self, key: str, count: int) -> None:
        """Show/hide a badge count on a sidebar item."""
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
