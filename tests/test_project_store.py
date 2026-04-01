"""Tests for Trim editor project/session persistence."""

from src.core.editor import EditorSession, ProjectStore, QuickSessionStore


def _build_session():
    session = EditorSession()
    session.load_source("/tmp/example.mp4", 15.0)
    session.split_at(5.0)
    session.set_segment_label(session.segments[0].id, "Intro")
    session.set_segment_tags(session.segments[0].id, ["keep", "cold-open"])
    return session


def test_project_store_round_trips_session(tmp_path):
    store = ProjectStore()
    session = _build_session()
    path = tmp_path / "example.cutproj.json"

    store.save(
        str(path),
        session,
        export_state={"mode": "merged", "lossless": True},
        analysis={"keyframe_times": [0.0, 5.0, 15.0]},
    )

    payload = store.load(str(path))
    restored = payload["session"]

    assert restored.source_path == session.source_path
    assert len(restored.segments) == 2
    assert restored.segments[0].label == "Intro"
    assert restored.segments[0].tags == ["keep", "cold-open"]
    assert payload["export"]["mode"] == "merged"


def test_quick_session_store_round_trips_session(tmp_path):
    session = _build_session()
    store = QuickSessionStore(session_path=str(tmp_path / "quick_session.json"))

    store.save(session, export_state={"output": "/tmp/output"}, analysis={})
    payload = store.load()

    assert payload is not None
    assert payload["session"].source_path == session.source_path
    assert payload["export"]["output"] == "/tmp/output"
