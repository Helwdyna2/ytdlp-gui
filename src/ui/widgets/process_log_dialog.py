"""Reusable non-modal dialog for runtime process logs and per-item command details."""

from dataclasses import dataclass
from typing import Dict, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..components.log_feed import LogFeed


@dataclass
class ProcessLogRecord:
    """Runtime details for a single processed item."""

    title: str
    input_path: str = ""
    status: str = "Pending"
    output_path: str = ""
    command: str = ""
    details: str = ""


class ProcessLogDialog(QDialog):
    """Reusable log viewer with per-item details and a live event feed."""

    def __init__(self, title: str, description: str, parent=None):
        super().__init__(parent)
        self._description = description
        self._records: Dict[str, ProcessLogRecord] = {}
        self._items: Dict[str, QListWidgetItem] = {}

        self.setWindowTitle(title)
        self.setModal(False)
        self.setMinimumSize(860, 580)
        self.resize(980, 700)

        self._setup_ui()
        self._sync_detail_panel(None)

    def _setup_ui(self) -> None:
        """Build the dialog layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        description_label = QLabel(self._description)
        description_label.setWordWrap(True)
        description_label.setObjectName("dimLabel")
        layout.addWidget(description_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        list_panel = QWidget()
        list_layout = QVBoxLayout(list_panel)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(6)
        list_layout.addWidget(QLabel("Processed Files"))

        self._records_list = QListWidget()
        self._records_list.currentItemChanged.connect(self._on_current_item_changed)
        list_layout.addWidget(self._records_list, stretch=1)

        splitter.addWidget(list_panel)

        detail_panel = QWidget()
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(6)

        detail_layout.addWidget(QLabel("Details"))

        self._status_value = QLabel("No processed files yet.")
        self._status_value.setWordWrap(True)
        detail_layout.addWidget(self._status_value)

        self._input_value = QLabel("")
        self._input_value.setWordWrap(True)
        self._input_value.setObjectName("dimLabel")
        detail_layout.addWidget(self._input_value)

        self._output_value = QLabel("")
        self._output_value.setWordWrap(True)
        self._output_value.setObjectName("dimLabel")
        detail_layout.addWidget(self._output_value)

        detail_layout.addWidget(QLabel("FFmpeg Command"))
        self._command_text = QPlainTextEdit()
        self._command_text.setReadOnly(True)
        self._command_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._command_text.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        detail_layout.addWidget(self._command_text, stretch=1)

        detail_layout.addWidget(QLabel("Notes"))
        self._details_value = QLabel("")
        self._details_value.setWordWrap(True)
        self._details_value.setObjectName("dimLabel")
        detail_layout.addWidget(self._details_value)

        splitter.addWidget(detail_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, stretch=3)

        layout.addWidget(QLabel("Activity"))
        self._log_feed = LogFeed(max_entries=1000)
        layout.addWidget(self._log_feed, stretch=2)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setObjectName("btnWire")
        self._clear_btn.setProperty("button_role", "secondary")
        self._clear_btn.clicked.connect(self.clear)
        button_layout.addWidget(self._clear_btn)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("btnWire")
        close_btn.setProperty("button_role", "secondary")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def add_log_entry(self, level: str, message: str) -> None:
        """Append a message to the live event feed."""
        self._log_feed.add_entry(message, level)

    def upsert_record(
        self,
        record_id: str,
        *,
        title: str,
        input_path: str = "",
        status: Optional[str] = None,
        output_path: Optional[str] = None,
        command: Optional[str] = None,
        details: Optional[str] = None,
    ) -> None:
        """Create or update a processed-item record."""
        record = self._records.get(record_id)
        if record is None:
            record = ProcessLogRecord(title=title, input_path=input_path)
            self._records[record_id] = record

            item = QListWidgetItem()
            item.setData(int(Qt.ItemDataRole.UserRole), record_id)
            item.setToolTip(input_path or title)
            self._records_list.addItem(item)
            self._items[record_id] = item
        else:
            if input_path:
                record.input_path = input_path

        record.title = title or record.title
        if status is not None:
            record.status = status
        if output_path is not None:
            record.output_path = output_path
        if command is not None:
            record.command = command
        if details is not None:
            record.details = details

        item = self._items[record_id]
        item.setText(f"{record.title} - {record.status}")
        item.setToolTip(record.input_path or record.title)

        if self._records_list.currentItem() is None:
            self._records_list.setCurrentItem(item)
        elif self._records_list.currentItem() is item:
            self._sync_detail_panel(record)

    def clear(self) -> None:
        """Reset all process records and log entries."""
        self._records.clear()
        self._items.clear()
        self._records_list.clear()
        self._log_feed.clear()
        self._sync_detail_panel(None)

    def _on_current_item_changed(
        self,
        current: Optional[QListWidgetItem],
        _previous: Optional[QListWidgetItem],
    ) -> None:
        """Refresh the detail pane when the selected item changes."""
        if current is None:
            self._sync_detail_panel(None)
            return

        record_id = current.data(int(Qt.ItemDataRole.UserRole))
        self._sync_detail_panel(self._records.get(record_id))

    def _sync_detail_panel(self, record: Optional[ProcessLogRecord]) -> None:
        """Render the detail panel for the selected record."""
        if record is None:
            self._status_value.setText("No processed files yet.")
            self._input_value.setText("")
            self._output_value.setText("")
            self._command_text.clear()
            self._details_value.setText("")
            return

        self._status_value.setText(f"Status: {record.status}")
        self._input_value.setText(f"Input: {record.input_path}" if record.input_path else "")
        self._output_value.setText(
            f"Output: {record.output_path}" if record.output_path else ""
        )
        self._command_text.setPlainText(record.command or "")
        self._details_value.setText(record.details or "")