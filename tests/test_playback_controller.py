"""Tests for playback controller initialization behavior."""

from src.core.editor.playback_controller import PlaybackController


def test_playback_controller_initializes_on_construction(monkeypatch):
    calls = []

    def fake_initialize(self):
        calls.append(self)

    monkeypatch.setattr(PlaybackController, "_initialize_client", fake_initialize)

    controller = PlaybackController()

    assert calls == [controller]
