"""Tests for the libmpv scrub controller."""

from PyQt6.QtCore import QObject, pyqtSignal

from src.core.editor.scrub_controller import ScrubController
from src.services.config_service import ConfigService


class _FakePlayback(QObject):
    seek_settled = pyqtSignal(int, float)

    def __init__(self):
        super().__init__()
        self.seek_calls = []
        self.mute_calls = []
        self.pause_calls = 0
        self.play_calls = 0
        self._is_playing = False
        self._position = 0.0
        self._next_seek_serial = 0

    def is_playing(self):
        return self._is_playing

    def pause(self):
        self.pause_calls += 1
        self._is_playing = False

    def play(self):
        self.play_calls += 1
        self._is_playing = True

    def seek(self, position, precise=True):
        self._next_seek_serial += 1
        serial = self._next_seek_serial
        self.seek_calls.append((position, precise, serial))
        self._position = position
        return serial

    def set_muted(self, muted):
        self.mute_calls.append(muted)

    def position(self):
        return self._position


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
    assert playback.seek_calls[0][:2] == (12.5, False)
    assert playback.seek_calls[-1][:2] == (12.5, True)
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
    assert playback.seek_calls[-1][:2] == (3.0, True)

    ConfigService._instance = None


def test_scrub_controller_coalesces_large_drag_updates(tmp_path, qtbot):
    _build_config(tmp_path)
    playback = _FakePlayback()
    controller = ScrubController(playback)

    controller.begin_drag()
    controller.update_drag(5.0)
    qtbot.waitUntil(lambda: len(playback.seek_calls) == 1, timeout=500)

    controller.update_drag(120.0)
    controller.update_drag(240.0)
    controller.update_drag(360.0)
    qtbot.wait(10)
    controller.end_drag()

    approximate_positions = [
        position for position, precise, _serial in playback.seek_calls if not precise
    ]
    exact_positions = [
        position for position, precise, _serial in playback.seek_calls if precise
    ]

    assert approximate_positions == [5.0]
    assert exact_positions == [360.0]

    ConfigService._instance = None


def test_scrub_controller_ignores_stale_settle_events(tmp_path, qtbot):
    _build_config(tmp_path)
    playback = _FakePlayback()
    controller = ScrubController(playback)
    preview_override_changes = []
    controller.preview_override_changed.connect(preview_override_changes.append)

    controller.begin_drag()
    controller.update_drag(10.0)
    qtbot.waitUntil(lambda: bool(playback.seek_calls), timeout=500)
    controller.end_drag()
    first_exact_serial = playback.seek_calls[-1][2]

    controller.begin_drag()
    controller.update_drag(20.0)
    controller.end_drag()
    second_exact_serial = playback.seek_calls[-1][2]

    playback.seek_settled.emit(first_exact_serial, 10.0)
    assert preview_override_changes[-1] is True

    playback.seek_settled.emit(second_exact_serial, 20.0)
    assert preview_override_changes[-1] is False

    ConfigService._instance = None
