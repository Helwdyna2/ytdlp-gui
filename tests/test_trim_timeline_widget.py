"""Tests for the dense Trim timeline widget."""

from PyQt6.QtCore import QPoint, Qt

from src.core.editor import EditorSegment
from src.ui.widgets.trim_timeline_widget import TrimTimelineWidget


def test_timeline_click_selects_segment(qapp, qtbot):
    widget = TrimTimelineWidget()
    qtbot.addWidget(widget)
    widget.resize(600, 160)
    widget.set_duration(10.0)
    widget.set_segments(
        [
            EditorSegment(start_time=0.0, end_time=3.0, id="a"),
            EditorSegment(start_time=3.0, end_time=7.0, id="b"),
        ],
        "a",
    )
    widget.show()
    qtbot.wait(20)

    selected = []
    widget.segment_selected.connect(selected.append)

    rect = widget._canvas._segment_rects["a"]
    qtbot.mouseClick(widget._canvas, Qt.MouseButton.LeftButton, pos=rect.center().toPoint())

    assert selected == ["a"]


def test_timeline_dragging_selected_handle_emits_new_range(qapp, qtbot):
    widget = TrimTimelineWidget()
    qtbot.addWidget(widget)
    widget.resize(600, 160)
    widget.set_duration(10.0)
    widget.set_segments([EditorSegment(start_time=0.0, end_time=4.0, id="a")], "a")
    widget.set_range(0.0, 4.0)
    widget.show()
    qtbot.wait(20)

    changes = []
    widget.range_changed.connect(lambda start, end: changes.append((start, end)))

    track_rect = widget._canvas._track_rect()
    end_x = int(widget._canvas._time_to_x(4.0, track_rect))
    center_y = int(track_rect.center().y())
    qtbot.mousePress(
        widget._canvas,
        Qt.MouseButton.LeftButton,
        pos=QPoint(end_x, center_y),
    )
    qtbot.mouseMove(widget._canvas, QPoint(end_x + 60, center_y))
    qtbot.mouseRelease(
        widget._canvas,
        Qt.MouseButton.LeftButton,
        pos=QPoint(end_x + 60, center_y),
    )

    assert changes
    assert changes[-1][1] > 4.0
