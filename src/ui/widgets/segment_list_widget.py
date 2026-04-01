"""Compact segment list for the Trim editor workflow."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.editor import EditorSession


class _SegmentCard(QWidget):
    clicked = pyqtSignal()
    toggle_changed = pyqtSignal(bool)
    label_changed = pyqtSignal(str)

    def __init__(
        self,
        index: int,
        title: str,
        range_text: str,
        duration_text: str,
        enabled: bool,
        label: str,
        parent=None,
    ):
        super().__init__(parent)
        self._setup_ui(index, title, range_text, duration_text, enabled, label)

    def _setup_ui(
        self,
        index: int,
        title: str,
        range_text: str,
        duration_text: str,
        enabled: bool,
        label: str,
    ) -> None:
        frame = QFrame(self)
        frame.setObjectName("trimSegmentCard")
        frame.setFrameShape(QFrame.Shape.StyledPanel)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)

        self._enabled_checkbox = QCheckBox()
        self._enabled_checkbox.setChecked(enabled)
        header.addWidget(self._enabled_checkbox)

        self._index_badge = QLabel(str(index + 1))
        self._index_badge.setObjectName("trimSegmentBadge")
        self._index_badge.setMinimumWidth(22)
        self._index_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self._index_badge)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("boldLabel")
        header.addWidget(self._title_label, stretch=1)

        self._duration_label = QLabel(duration_text)
        self._duration_label.setObjectName("dimLabel")
        header.addWidget(self._duration_label)

        layout.addLayout(header)

        self._range_label = QLabel(range_text)
        self._range_label.setObjectName("dimLabel")
        layout.addWidget(self._range_label)

        self._label_input = QLineEdit(label)
        self._label_input.setPlaceholderText("Optional segment label")
        layout.addWidget(self._label_input)

        self._enabled_checkbox.toggled.connect(self.toggle_changed.emit)
        self._enabled_checkbox.clicked.connect(lambda _checked: self.clicked.emit())
        self._label_input.editingFinished.connect(
            lambda: self.label_changed.emit(self._label_input.text())
        )

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_inputs_enabled(self, enabled: bool) -> None:
        self._enabled_checkbox.setEnabled(enabled)
        self._label_input.setEnabled(enabled)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)


class SegmentListWidget(QWidget):
    """Compact inspector for the current source segments."""

    segment_selected = pyqtSignal(str)
    segment_toggled = pyqtSignal(str, bool)
    segment_label_changed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._session: Optional[EditorSession] = None
        self._updating = False
        self._cards: dict[str, _SegmentCard] = {}
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._summary_label = QLabel("No segments yet")
        self._summary_label.setObjectName("dimLabel")
        layout.addWidget(self._summary_label)

        self._list = QListWidget()
        self._list.setObjectName("trimSegmentList")
        self._list.setAlternatingRowColors(False)
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.setSpacing(8)
        self._list.setMinimumHeight(260)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self._list)

    def _connect_signals(self) -> None:
        self._list.currentItemChanged.connect(self._on_current_item_changed)

    def _on_current_item_changed(
        self,
        current: Optional[QListWidgetItem],
        _previous: Optional[QListWidgetItem],
    ) -> None:
        if self._updating:
            return
        current_id = current.data(Qt.ItemDataRole.UserRole) if current else None
        for segment_id, card in self._cards.items():
            card.set_selected(segment_id == current_id)
        if current_id:
            self.segment_selected.emit(current_id)

    def set_session(self, session: Optional[EditorSession]) -> None:
        self._session = session
        self._updating = True
        self._cards.clear()
        self._list.clear()

        if session is None or not session.segments:
            self._summary_label.setText("No segments yet")
            self._updating = False
            return

        enabled_count = len(session.enabled_segments())
        self._summary_label.setText(
            f"{len(session.segments)} segment(s), {enabled_count} enabled"
        )

        selected_item: Optional[QListWidgetItem] = None
        for index, segment in enumerate(session.segments):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, segment.id)
            title = segment.label.strip() or f"Segment {index + 1}"
            card = _SegmentCard(
                index=index,
                title=title,
                range_text=self._format_range(segment.start_time, segment.end_time),
                duration_text=self._format_time(segment.duration),
                enabled=segment.enabled,
                label=segment.label,
            )
            card.clicked.connect(
                lambda checked=False, list_item=item: self._list.setCurrentItem(list_item)
            )
            card.toggle_changed.connect(
                lambda enabled, segment_id=segment.id: self.segment_toggled.emit(
                    segment_id, enabled
                )
            )
            card.label_changed.connect(
                lambda label, segment_id=segment.id: self.segment_label_changed.emit(
                    segment_id, label
                )
            )
            self._cards[segment.id] = card

            item.setSizeHint(card.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, card)
            if segment.id == session.selected_segment_id:
                selected_item = item

        if selected_item is not None:
            self._list.setCurrentItem(selected_item)
        elif self._list.count() > 0:
            self._list.setCurrentRow(0)

        for segment_id, card in self._cards.items():
            card.set_selected(segment_id == session.selected_segment_id)

        self._updating = False

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self._list.setEnabled(enabled)
        for card in self._cards.values():
            card.set_inputs_enabled(enabled)

    def _format_range(self, start: float, end: float) -> str:
        return f"{self._format_time(start)} - {self._format_time(end)}"

    def _format_time(self, seconds: float) -> str:
        seconds = max(0.0, seconds)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        millis = int((secs % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(secs):02d}.{millis:03d}"
