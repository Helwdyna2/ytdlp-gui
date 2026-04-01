"""Tests for editor export planning."""

from src.core.editor import EditorSession
from src.core.editor.export_planner import ExportMode, ExportPlanner


def test_export_planner_builds_separate_outputs(tmp_path):
    session = EditorSession()
    session.load_source("/tmp/example.mp4", 12.0)
    session.split_at(5.0)

    planner = ExportPlanner()
    plan = planner.build_plan(
        session,
        mode=ExportMode.SEPARATE,
        lossless=True,
        output_target=str(tmp_path),
        keyframe_times=[0.0, 5.0, 12.0],
        source_metadata={"codec": "h264"},
    )

    assert len(plan.segments) == 2
    assert all(segment.output_path.startswith(str(tmp_path)) for segment in plan.segments)
    assert plan.warnings == []


def test_export_planner_warns_for_off_keyframe_lossless_merge():
    session = EditorSession()
    session.load_source("/tmp/example.mp4", 10.0)
    session.split_at(4.0)
    session.update_selected_range(4.2, 10.0)
    session.select_segment(session.segments[0].id)
    session.update_selected_range(0.0, 3.9)

    planner = ExportPlanner()
    plan = planner.build_plan(
        session,
        mode=ExportMode.MERGED,
        lossless=True,
        output_target=None,
        keyframe_times=[0.0, 4.0, 10.0],
        source_metadata={"codec": "h264"},
    )

    assert plan.requires_confirmation is True
    assert any(warning.code == "copy-boundary-risk" for warning in plan.warnings)
    assert any(warning.code == "merge-copy-risk" for warning in plan.warnings)
