"""Shell layout widget — top-level workbench shell."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QStackedWidget

from src.ui.components.sidebar import Sidebar


class Shell(QWidget):
    tool_changed = pyqtSignal(str)
    # Legacy alias
    stage_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool_widgets: dict[str, QWidget] = {}
        self._tool_order: list[str] = []

        self.sidebar = Sidebar()
        self.content_stack = QStackedWidget()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.content_stack)

        self.sidebar.tool_selected.connect(self._on_tool_selected)

    def _on_tool_selected(self, key: str) -> None:
        self._switch(key)
        self.tool_changed.emit(key)
        self.stage_changed.emit(key)

    def _switch(self, key: str) -> None:
        if key in self._tool_widgets:
            idx = self._tool_order.index(key)
            self.content_stack.setCurrentIndex(idx)

    # ── Primary API ────────────────────────────────────────────────────────

    def register_tool(self, key: str, widget: QWidget) -> None:
        self._tool_widgets[key] = widget
        self._tool_order.append(key)
        self.content_stack.addWidget(widget)

    def switch_to_tool(self, key: str) -> None:
        self._switch(key)
        self.sidebar.select_tool(key)

    def active_tool(self) -> str | None:
        idx = self.content_stack.currentIndex()
        if 0 <= idx < len(self._tool_order):
            return self._tool_order[idx]
        return None

    def set_badge(self, key: str, count: int) -> None:
        self.sidebar.set_badge(key, count)

    # ── Backward-compat stage API ──────────────────────────────────────────

    def register_stage(self, definition, widget: QWidget) -> None:
        """Legacy: register_stage(StageDefinition, widget) → register_tool(key, widget)."""
        key = definition.key if hasattr(definition, "key") else str(definition)
        self.register_tool(key, widget)

    def switch_to_stage(self, key: str) -> None:
        """Legacy alias for switch_to_tool."""
        self.switch_to_tool(key)

    def active_stage(self) -> str | None:
        """Legacy alias for active_tool."""
        return self.active_tool()

    def set_stage_status(self, key: str, status) -> None:
        """Legacy no-op — stage status badges are handled via set_badge."""
        pass
