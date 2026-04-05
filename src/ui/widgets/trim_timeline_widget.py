"""LosslessCut-inspired timeline widget for the Trim editor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QLabel, QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from ..theme.style_utils import set_status_color
from ..theme.theme_engine import ThemeEngine


@dataclass(slots=True)
class _SegmentView:
    segment_id: str
    label: str
    start_time: float
    end_time: float
    enabled: bool


class _TimelineCanvas(QWidget):
    range_changed = pyqtSignal(float, float)
    seek_requested = pyqtSignal(float)
    segment_selected = pyqtSignal(str)

    _MARGIN_X = 12
    _TRACK_HEIGHT = 36
    _HANDLE_HIT_RADIUS = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self._duration = 0.0
        self._current_position = 0.0
        self._segments: list[_SegmentView] = []
        self._selected_segment_id: Optional[str] = None
        self._drag_mode: Optional[str] = None
        self._seeking = False
        self._segment_rects: dict[str, QRectF] = {}
        self.setMinimumHeight(88)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_state(
        self,
        duration: float,
        segments: list[_SegmentView],
        selected_segment_id: Optional[str],
        current_position: float,
    ) -> None:
        self._duration = max(0.0, duration)
        self._segments = list(segments)
        self._selected_segment_id = selected_segment_id
        self._current_position = max(0.0, current_position)
        self.update()

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        track_rect = self._track_rect()
        palette = self.palette()
        surface = palette.color(self.backgroundRole())
        engine = ThemeEngine.instance()
        base_border = QColor(engine.get_color("timeline-base-border"))
        base_fill = QColor(engine.get_color("timeline-base-fill"))
        disabled_fill = QColor(engine.get_color("timeline-disabled-fill"))
        selected_fill = QColor(engine.get_color("timeline-selected-fill"))
        selected_border = QColor(engine.get_color("timeline-selected-border"))
        enabled_fill = QColor(engine.get_color("timeline-enabled-fill"))
        handle_fill = QColor(engine.get_color("timeline-handle-fill"))
        playhead_color = QColor(engine.get_color("timeline-playhead"))

        painter.setPen(QPen(base_border, 1))
        painter.setBrush(base_fill)
        painter.drawRoundedRect(track_rect, 10, 10)

        self._segment_rects = {}
        for index, segment in enumerate(self._segments):
            rect = self._segment_rect(track_rect, segment.start_time, segment.end_time)
            self._segment_rects[segment.segment_id] = rect
            is_selected = segment.segment_id == self._selected_segment_id
            fill = selected_fill if is_selected else enabled_fill
            if not segment.enabled:
                fill = disabled_fill
            border = selected_border if is_selected else QColor(fill).lighter(115)
            painter.setPen(QPen(border, 1.5 if is_selected else 1))
            painter.setBrush(fill)
            painter.drawRoundedRect(rect, 8, 8)

            painter.setPen(
                QColor(engine.get_color("text-bright"))
                if is_selected
                else QColor(engine.get_color("timeline-text"))
            )
            label = segment.label or f"{index + 1}"
            text_rect = rect.adjusted(10, 0, -10, 0)
            if text_rect.width() > 18:
                painter.drawText(
                    text_rect.toRect(),
                    int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                    label,
                )

        if self._selected_segment_id:
            selected = self._selected_segment()
            if selected is not None:
                pill_width = 6.0
                pill_height = 20.0
                pill_radius = 3.0
                for handle_x in (
                    self._time_to_x(selected.start_time, track_rect),
                    self._time_to_x(selected.end_time, track_rect),
                ):
                    pill_rect = QRectF(
                        handle_x - pill_width / 2,
                        track_rect.center().y() - pill_height / 2,
                        pill_width,
                        pill_height,
                    )
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(handle_fill)
                    painter.drawRoundedRect(pill_rect, pill_radius, pill_radius)

        if self._duration > 0:
            playhead_x = self._time_to_x(self._current_position, track_rect)
            painter.setPen(QPen(playhead_color, 2))
            painter.drawLine(
                QPointF(playhead_x, track_rect.top() - 8),
                QPointF(playhead_x, track_rect.bottom() + 8),
            )

        painter.setPen(surface.lighter(180))
        painter.drawText(
            QRectF(0, track_rect.bottom() + 10, self.width(), 18),
            Qt.AlignmentFlag.AlignCenter,
            self._format_time(self._current_position),
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self.isEnabled() or self._duration <= 0:
            return

        track_rect = self._track_rect()
        selected = self._selected_segment()
        if (
            selected is not None
            and event.button() == Qt.MouseButton.LeftButton
            and self._pressed_handle(event.position().x(), selected, track_rect)
        ):
            return

        segment_id = self._segment_id_at(event.position())
        if segment_id:
            self.segment_selected.emit(segment_id)

        self.seek_requested.emit(self._x_to_time(event.position().x(), track_rect))
        self._seeking = True

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        track_rect = self._track_rect()
        selected = self._selected_segment()
        if self._drag_mode and selected is not None:
            position = self._x_to_time(event.position().x(), track_rect)
            if self._drag_mode == "start":
                self.range_changed.emit(position, selected.end_time)
            elif self._drag_mode == "end":
                self.range_changed.emit(selected.start_time, position)
            return

        if self._seeking:
            self.seek_requested.emit(self._x_to_time(event.position().x(), track_rect))
            return

        if selected is None:
            self.unsetCursor()
            return

        if self._pressed_handle(
            event.position().x(), selected, track_rect, activate=False
        ):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.unsetCursor()

    def mouseReleaseEvent(self, _event: QMouseEvent) -> None:
        self._drag_mode = None
        self._seeking = False
        self.unsetCursor()

    def leaveEvent(self, _event) -> None:
        if not self._drag_mode:
            self.unsetCursor()

    def _pressed_handle(
        self,
        pos_x: float,
        selected: _SegmentView,
        track_rect: QRectF,
        *,
        activate: bool = True,
    ) -> bool:
        start_x = self._time_to_x(selected.start_time, track_rect)
        end_x = self._time_to_x(selected.end_time, track_rect)
        if abs(pos_x - start_x) <= self._HANDLE_HIT_RADIUS:
            if activate:
                self._drag_mode = "start"
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            return True
        if abs(pos_x - end_x) <= self._HANDLE_HIT_RADIUS:
            if activate:
                self._drag_mode = "end"
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            return True
        return False

    def _selected_segment(self) -> Optional[_SegmentView]:
        if not self._selected_segment_id:
            return None
        for segment in self._segments:
            if segment.segment_id == self._selected_segment_id:
                return segment
        return None

    def _segment_id_at(self, position: QPointF) -> Optional[str]:
        for segment_id, rect in self._segment_rects.items():
            if rect.contains(position):
                return segment_id
        return None

    def _track_rect(self) -> QRectF:
        return QRectF(
            self._MARGIN_X,
            18,
            max(0.0, self.width() - (self._MARGIN_X * 2)),
            self._TRACK_HEIGHT,
        )

    def _segment_rect(self, track_rect: QRectF, start: float, end: float) -> QRectF:
        left = self._time_to_x(start, track_rect)
        right = self._time_to_x(end, track_rect)
        width = max(10.0, right - left)
        return QRectF(left, track_rect.top() + 2, width, track_rect.height() - 4)

    def _time_to_x(self, value: float, track_rect: QRectF) -> float:
        if self._duration <= 0:
            return track_rect.left()
        ratio = max(0.0, min(1.0, value / self._duration))
        return track_rect.left() + (track_rect.width() * ratio)

    def _x_to_time(self, pos_x: float, track_rect: QRectF) -> float:
        if self._duration <= 0 or track_rect.width() <= 0:
            return 0.0
        ratio = (pos_x - track_rect.left()) / track_rect.width()
        ratio = max(0.0, min(1.0, ratio))
        return ratio * self._duration

    def _format_time(self, seconds: float) -> str:
        seconds = max(0.0, seconds)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        millis = int((secs % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(secs):02d}.{millis:03d}"


class TrimTimelineWidget(QWidget):
    """
    Dense timeline widget for selecting, seeking, and editing segment ranges.

    Signals:
        range_changed: Emits (start_time, end_time) when range changes
        seek_requested: Emits position when user clicks to seek
        segment_selected: Emits a segment id when a block is clicked
    """

    range_changed = pyqtSignal(float, float)
    seek_requested = pyqtSignal(float)
    segment_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._duration = 0.0
        self._start_time = 0.0
        self._end_time = 0.0
        self._current_position = 0.0
        self._segments: list[_SegmentView] = []
        self._selected_segment_id: Optional[str] = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        time_layout = QHBoxLayout()
        self._start_label = QLabel("Start: 00:00:00.000")
        self._start_label.setObjectName("boldLabel")
        time_layout.addWidget(self._start_label)

        time_layout.addStretch()

        self._trimmed_duration_label = QLabel("Trimmed: 00:00:00.000")
        set_status_color(self._trimmed_duration_label, "info")
        time_layout.addWidget(self._trimmed_duration_label)

        time_layout.addStretch()

        self._end_label = QLabel("End: 00:00:00.000")
        self._end_label.setObjectName("boldLabel")
        time_layout.addWidget(self._end_label)

        layout.addLayout(time_layout)

        self._canvas = _TimelineCanvas(self)
        layout.addWidget(self._canvas)

        info_label = QLabel(
            "Click or drag to seek. Use the handles to adjust segment boundaries."
        )
        info_label.setObjectName("dimLabel")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

    def _connect_signals(self) -> None:
        self._canvas.range_changed.connect(self._on_canvas_range_changed)
        self._canvas.seek_requested.connect(self.seek_requested.emit)
        self._canvas.segment_selected.connect(self.segment_selected.emit)

    def _on_canvas_range_changed(self, start: float, end: float) -> None:
        self._start_time = start
        self._end_time = end
        self._update_labels()
        self.range_changed.emit(start, end)

    def _update_labels(self) -> None:
        self._start_label.setText(f"Start: {self._format_time(self._start_time)}")
        self._end_label.setText(f"End: {self._format_time(self._end_time)}")
        trimmed_duration = max(0.0, self._end_time - self._start_time)
        self._trimmed_duration_label.setText(
            f"Trimmed: {self._format_time(trimmed_duration)}"
        )

    def _sync_canvas(self) -> None:
        self._canvas.set_state(
            self._duration,
            self._segments,
            self._selected_segment_id,
            self._current_position,
        )

    def _format_time(self, seconds: float) -> str:
        seconds = max(0.0, seconds)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        millis = int((secs % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(secs):02d}.{millis:03d}"

    def set_duration(self, duration: float) -> None:
        self._duration = max(0.0, duration)
        self._start_time = 0.0
        self._end_time = self._duration
        self._update_labels()
        self._sync_canvas()

    def set_range(self, start: float, end: float) -> None:
        self._start_time = max(0.0, min(start, self._duration))
        self._end_time = max(self._start_time, min(end, self._duration))
        for segment in self._segments:
            if segment.segment_id == self._selected_segment_id:
                segment.start_time = self._start_time
                segment.end_time = self._end_time
                break
        self._update_labels()
        self._sync_canvas()

    def set_segments(self, segments: list, selected_segment_id: Optional[str]) -> None:
        views: list[_SegmentView] = []
        for index, segment in enumerate(segments):
            label = getattr(segment, "label", "") or f"Segment {index + 1}"
            views.append(
                _SegmentView(
                    segment_id=getattr(segment, "id"),
                    label=label,
                    start_time=float(getattr(segment, "start_time")),
                    end_time=float(getattr(segment, "end_time")),
                    enabled=bool(getattr(segment, "enabled", True)),
                )
            )
        self._segments = views
        self._selected_segment_id = selected_segment_id
        self._sync_canvas()

    def get_range(self) -> tuple[float, float]:
        return (self._start_time, self._end_time)

    def get_start_time(self) -> float:
        return self._start_time

    def get_end_time(self) -> float:
        return self._end_time

    def get_trimmed_duration(self) -> float:
        return max(0.0, self._end_time - self._start_time)

    def get_duration(self) -> float:
        return self._duration

    def set_current_position(self, position: float) -> None:
        self._current_position = max(0.0, position)
        self._sync_canvas()

    def reset(self) -> None:
        self._duration = 0.0
        self._start_time = 0.0
        self._end_time = 0.0
        self._current_position = 0.0
        self._segments = []
        self._selected_segment_id = None
        self._update_labels()
        self._sync_canvas()

    def set_enabled(self, enabled: bool) -> None:
        self._canvas.setEnabled(enabled)
