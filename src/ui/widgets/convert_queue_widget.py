"""Queue widget for the Convert tool."""

from __future__ import annotations

from typing import Dict, List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.convert_saved_task import ConvertQueueItem, ConvertQueueItemStatus


class _ConvertQueueRow(QWidget):
    """Single queue row with status and actions."""

    move_up_requested = pyqtSignal(str)
    move_down_requested = pyqtSignal(str)
    skip_requested = pyqtSignal(str)
    prioritize_requested = pyqtSignal(str)

    def __init__(self, item: ConvertQueueItem, parent=None):
        super().__init__(parent)
        self._item_id = item.item_id
        self._setup_ui()
        self.update_item(item, is_first=True, is_last=True, actions_enabled=True)

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self._title_label = QLabel()
        self._title_label.setWordWrap(True)
        self._status_label = QLabel()
        self._status_label.setObjectName("convertQueueStatus")
        self._status_label.setProperty("text_role", "muted")
        self._status_label.setWordWrap(True)

        text_layout.addWidget(self._title_label)
        text_layout.addWidget(self._status_label)

        layout.addLayout(text_layout, stretch=1)

        self._move_up_btn = QPushButton("Up")
        self._move_up_btn.setObjectName("btnWire")
        self._move_up_btn.setProperty("button_role", "secondary")
        self._move_down_btn = QPushButton("Down")
        self._move_down_btn.setObjectName("btnWire")
        self._move_down_btn.setProperty("button_role", "secondary")
        self._prioritize_btn = QPushButton("Top")
        self._prioritize_btn.setObjectName("btnWire")
        self._prioritize_btn.setProperty("button_role", "secondary")
        self._skip_btn = QPushButton("Skip")
        self._skip_btn.setObjectName("btnWire")
        self._skip_btn.setProperty("button_role", "secondary")

        for button in (
            self._move_up_btn,
            self._move_down_btn,
            self._prioritize_btn,
            self._skip_btn,
        ):
            layout.addWidget(button)

        self._move_up_btn.clicked.connect(
            lambda: self.move_up_requested.emit(self._item_id)
        )
        self._move_down_btn.clicked.connect(
            lambda: self.move_down_requested.emit(self._item_id)
        )
        self._prioritize_btn.clicked.connect(
            lambda: self.prioritize_requested.emit(self._item_id)
        )
        self._skip_btn.clicked.connect(lambda: self.skip_requested.emit(self._item_id))

    def update_item(
        self,
        item: ConvertQueueItem,
        *,
        is_first: bool,
        is_last: bool,
        actions_enabled: bool,
    ) -> None:
        """Refresh row text and state from the queue item."""
        self._title_label.setText(item.display_name or item.input_path)
        self._title_label.setToolTip(item.input_path)
        self._status_label.setText(_status_text_for_item(item))

        is_completed = item.status is ConvertQueueItemStatus.COMPLETED
        self.setProperty("completed", is_completed)
        self._status_label.setProperty("completed", is_completed)

        title_font = QFont(self._title_label.font())
        title_font.setStrikeOut(is_completed)
        self._title_label.setFont(title_font)

        is_processing = item.status is ConvertQueueItemStatus.PROCESSING
        is_skipped = item.status is ConvertQueueItemStatus.SKIPPED
        can_reorder = actions_enabled and not is_processing
        self._move_up_btn.setEnabled(can_reorder and not is_first)
        self._move_down_btn.setEnabled(can_reorder and not is_last)
        self._prioritize_btn.setEnabled(can_reorder and not is_first)
        self._skip_btn.setEnabled(actions_enabled and not is_processing and not is_skipped)

        self.style().unpolish(self)
        self.style().polish(self)

    def status_text(self) -> str:
        """Return the current row status text."""
        return self._status_label.text()

    def is_completed(self) -> bool:
        """Return whether the row is visually marked complete."""
        return bool(self.property("completed"))


def _status_text_for_item(item: ConvertQueueItem) -> str:
    """Build the user-visible queue status text."""
    if item.status is ConvertQueueItemStatus.PROCESSING:
        return item.detail or f"{item.progress_percent:.0f}%"
    if item.status is ConvertQueueItemStatus.COMPLETED:
        return item.detail or "Complete"
    if item.status is ConvertQueueItemStatus.SKIPPED:
        return item.detail or "Skipped"
    if item.status is ConvertQueueItemStatus.FAILED:
        return item.error_message or item.detail or "Failed"
    if item.status is ConvertQueueItemStatus.INCOMPLETE:
        return item.error_message or item.detail or "Incomplete"
    return item.detail or "Pending"


class ConvertQueueWidget(QWidget):
    """List view for Convert queue items and queue actions."""

    reorder_requested = pyqtSignal(int, int)
    skip_requested = pyqtSignal(str)
    prioritize_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._actions_enabled = True
        self._items_by_item_id: Dict[str, ConvertQueueItem] = {}
        self._rows_by_item_id: Dict[str, _ConvertQueueRow] = {}
        self._indexes_by_item_id: Dict[str, int] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._list_widget = QListWidget()
        self._list_widget.setAlternatingRowColors(True)
        self._list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(self._list_widget)

    def set_actions_enabled(self, enabled: bool) -> None:
        """Enable or disable queue action controls."""
        self._actions_enabled = enabled
        for item_id, row in self._rows_by_item_id.items():
            item = self._items_by_item_id.get(item_id)
            if item is None:
                continue
            index = self._indexes_by_item_id.get(item_id, 0)
            last_index = len(self._indexes_by_item_id) - 1
            row.update_item(
                item,
                is_first=index == 0,
                is_last=index == last_index,
                actions_enabled=enabled,
            )

    def set_queue_items(self, items: List[ConvertQueueItem]) -> None:
        """Replace the visible queue rows."""
        self._list_widget.clear()
        self._items_by_item_id = {item.item_id: item for item in items}
        self._rows_by_item_id.clear()
        self._indexes_by_item_id = {
            item.item_id: index for index, item in enumerate(items)
        }

        last_index = len(items) - 1
        for index, item in enumerate(items):
            list_item = QListWidgetItem()
            list_item.setData(Qt.ItemDataRole.UserRole, item.item_id)
            row = _ConvertQueueRow(item, self._list_widget)
            row.move_up_requested.connect(self._on_move_up_requested)
            row.move_down_requested.connect(self._on_move_down_requested)
            row.skip_requested.connect(lambda value: self.skip_requested.emit(value))
            row.prioritize_requested.connect(
                lambda value: self.prioritize_requested.emit(value)
            )
            row.update_item(
                item,
                is_first=index == 0,
                is_last=index == last_index,
                actions_enabled=self._actions_enabled,
            )
            list_item.setSizeHint(row.sizeHint())
            self._list_widget.addItem(list_item)
            self._list_widget.setItemWidget(list_item, row)
            self._rows_by_item_id[item.item_id] = row

    def status_text_for(self, item_id: str) -> str:
        """Return the visible status text for the requested row."""
        row = self._rows_by_item_id.get(item_id)
        return row.status_text() if row else ""

    def is_item_completed(self, item_id: str) -> bool:
        """Return whether the requested row is styled as complete."""
        row = self._rows_by_item_id.get(item_id)
        return row.is_completed() if row else False

    def _on_move_up_requested(self, item_id: str) -> None:
        index = self._indexes_by_item_id.get(item_id)
        if index is None or index <= 0:
            return
        self.reorder_requested.emit(index, index - 1)

    def _on_move_down_requested(self, item_id: str) -> None:
        index = self._indexes_by_item_id.get(item_id)
        if index is None or index >= self._list_widget.count() - 1:
            return
        self.reorder_requested.emit(index, index + 1)
