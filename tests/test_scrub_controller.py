"""Tests for the libmpv scrub controller."""

from src.core.editor.scrub_controller import ScrubController
from src.services.config_service import ConfigService


class _FakePlayback:
    def __init__(self):
        self.seek_calls = []
        self.mute_calls = []
        self.pause_calls = 0
        self.play_calls = 0
        self._is_playing = False

    def is_playing(self):
        return self._is_playing

    def pause(self):
        self.pause_calls += 1
        self._is_playing = False

    def play(self):
        self.play_calls += 1
        self._is_playing = True

    def seek(self, position, precise=True):
        self.seek_calls.append((position, precise))

    def set_muted(self, muted):
        self.mute_calls.append(muted)


def _build_config(tmp_path, *, resume_after_scrub=False):
    ConfigService._instance = None
    config = ConfigService(config_path=str(tmp_path / "config.json"))
    config.set("trim.playback.scrub_send_interval_ms", 5, save=False)
    config.set("trim.playback.scrub_exact_settle_delay_ms", 5, save=False)
    config.set("trim.playback.resume_after_scrub", resume_after_scrub, save=False)
    config.set("trim.playback.mute_during_scrub", True, save=False)
    return config


def test_scrub_controller_sends_approximate_then_exact_seek(tmp_path, qtbot):
    _build_config(tmp_path)
    playback = _FakePlayback()
    controller = ScrubController(playback)

    controller.begin_drag()
    controller.update_drag(12.5)

    qtbot.waitUntil(lambda: bool(playback.seek_calls), timeout=500)
    controller.end_drag()

    assert playback.pause_calls == 1
    assert playback.seek_calls[0] == (12.5, False)
    assert playback.seek_calls[-1] == (12.5, True)
    assert playback.mute_calls == [True, False]
    assert playback.play_calls == 0

    ConfigService._instance = None


def test_scrub_controller_can_resume_after_drag(tmp_path, qtbot):
    _build_config(tmp_path, resume_after_scrub=True)
    playback = _FakePlayback()
    playback._is_playing = True
    controller = ScrubController(playback)

    controller.begin_drag()
    controller.update_drag(3.0)

    qtbot.waitUntil(lambda: bool(playback.seek_calls), timeout=500)
    controller.end_drag()

    assert playback.play_calls == 1
    assert playback.seek_calls[-1] == (3.0, True)

    ConfigService._instance = None
