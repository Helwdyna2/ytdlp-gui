"""Segment list for the Trim editor workflow."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.editor import EditorSession


class SegmentListWidget(QWidget):
    """Simple inspector for the current source segments."""

    segment_selected = pyqtSignal(str)
    segment_toggled = pyqtSignal(str, bool)
    segment_label_changed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._session: Optional[EditorSession] = None
        self._updating = False
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._summary_label = QLabel("No segments yet")
        self._summary_label.setObjectName("dimLabel")
        layout.addWidget(self._summary_label)

        self._tree = QTreeWidget()
        self._tree.setColumnCount(4)
        self._tree.setHeaderLabels(["Segment", "Range", "Label", "Tags"])
        self._tree.setRootIsDecorated(False)
        self._tree.setAlternatingRowColors(True)
        self._tree.setMinimumHeight(220)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tree.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )

        header = self._tree.header()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._tree)

    def _connect_signals(self) -> None:
        self._tree.itemSelectionChanged.connect(self._on_selection_changed)
        self._tree.itemChanged.connect(self._on_item_changed)

    def _on_selection_changed(self) -> None:
        if self._updating:
            return

        item = self._tree.currentItem()
        if item is None:
            return

        segment_id = item.data(0, Qt.ItemDataRole.UserRole)
        if segment_id:
            self.segment_selected.emit(segment_id)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._updating:
            return

        segment_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not segment_id:
            return

        if column == 0:
            enabled = item.checkState(0) == Qt.CheckState.Checked
            self.segment_toggled.emit(segment_id, enabled)
        elif column == 2:
            self.segment_label_changed.emit(segment_id, item.text(2))

    def set_session(self, session: Optional[EditorSession]) -> None:
        """Rebuild the list from the current session."""
        self._session = session
        self._updating = True
        self._tree.clear()

        if session is None or not session.segments:
            self._summary_label.setText("No segments yet")
            self._updating = False
            return

        enabled_count = len(session.enabled_segments())
        self._summary_label.setText(
            f"{len(session.segments)} segment(s), {enabled_count} enabled"
        )

        selected_item: Optional[QTreeWidgetItem] = None
        for index, segment in enumerate(session.segments):
            item = QTreeWidgetItem(
                [
                    segment.display_label(index),
                    self._format_range(segment.start_time, segment.end_time),
                    segment.label,
                    ", ".join(segment.tags),
                ]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, segment.id)
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsEditable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            item.setCheckState(
                0,
                Qt.CheckState.Checked if segment.enabled else Qt.CheckState.Unchecked,
            )
            self._tree.addTopLevelItem(item)
            if segment.id == session.selected_segment_id:
                selected_item = item

        if selected_item is not None:
            self._tree.setCurrentItem(selected_item)

        self._updating = False

    def _format_range(self, start: float, end: float) -> str:
        return f"{self._format_time(start)} - {self._format_time(end)}"

    def _format_time(self, seconds: float) -> str:
        seconds = max(0.0, seconds)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        millis = int((secs % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(secs):02d}.{millis:03d}"
