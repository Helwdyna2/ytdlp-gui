"""Tests for Trim editor session models."""

from src.core.editor import EditorSession


def test_editor_session_load_source_creates_single_segment():
    session = EditorSession()

    session.load_source("/tmp/example.mp4", 12.5)

    assert session.source_path == "/tmp/example.mp4"
    assert session.duration == 12.5
    assert len(session.segments) == 1
    assert session.selected_segment is not None
    assert session.selected_segment.start_time == 0.0
    assert session.selected_segment.end_time == 12.5
    assert session.selected_segment.enabled is True


def test_editor_session_split_at_creates_two_segments():
    session = EditorSession()
    session.load_source("/tmp/example.mp4", 10.0)

    result = session.split_at(4.0)

    assert result is not None
    assert len(session.segments) == 2
    assert session.segments[0].start_time == 0.0
    assert session.segments[0].end_time == 4.0
    assert session.segments[1].start_time == 4.0
    assert session.segments[1].end_time == 10.0
    assert session.selected_segment == session.segments[1]


def test_editor_session_update_selected_range_clamps_to_neighbors():
    session = EditorSession()
    session.load_source("/tmp/example.mp4", 10.0)
    session.split_at(4.0)
    session.select_segment(session.segments[0].id)

    session.update_selected_range(0.5, 8.0)

    assert session.segments[0].start_time == 0.5
    assert session.segments[0].end_time == 4.0


def test_editor_session_enabled_segments_reflect_toggles():
    session = EditorSession()
    session.load_source("/tmp/example.mp4", 10.0)
    session.split_at(5.0)

    session.set_segment_enabled(session.segments[0].id, False)

    enabled = session.enabled_segments()
    assert len(enabled) == 1
    assert enabled[0].id == session.segments[1].id
