"""Approximate-drag / exact-settle seek controller."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, QTimer

from ...services.config_service import ConfigService
from .playback_controller import PlaybackController


class ScrubController(QObject):
    """Coordinates drag scrubbing against the playback controller."""

    def __init__(self, playback: PlaybackController, parent=None):
        super().__init__(parent)
        self._playback = playback
        config = ConfigService()
        self._send_interval_ms = config.get(
            "trim.playback.scrub_send_interval_ms", 24
        )
        self._exact_settle_delay_ms = config.get(
            "trim.playback.scrub_exact_settle_delay_ms", 120
        )
        self._resume_after_scrub = config.get(
            "trim.playback.resume_after_scrub", False
        )
        self._mute_during_scrub = config.get(
            "trim.playback.mute_during_scrub", True
        )

        self._drag_active = False
        self._requested_position: Optional[float] = None
        self._last_sent_position: Optional[float] = None
        self._last_exact_position: Optional[float] = None
        self._was_playing_before_drag = False

        self._dispatch_timer = QTimer(self)
        self._dispatch_timer.setInterval(self._send_interval_ms)
        self._dispatch_timer.timeout.connect(self._dispatch_approximate_seek)

        self._settle_timer = QTimer(self)
        self._settle_timer.setSingleShot(True)
        self._settle_timer.setInterval(self._exact_settle_delay_ms)
        self._settle_timer.timeout.connect(self._dispatch_exact_seek)

    def begin_drag(self) -> None:
        if self._drag_active:
            return
        self._drag_active = True
        self._was_playing_before_drag = self._playback.is_playing()
        self._playback.pause()
        if self._mute_during_scrub:
            self._playback.set_muted(True)

    def update_drag(self, position: float) -> None:
        self._requested_position = position
        if not self._drag_active:
            return

        if not self._dispatch_timer.isActive():
            self._dispatch_approximate_seek()
            self._dispatch_timer.start()

        self._settle_timer.start()

    def end_drag(self) -> None:
        if not self._drag_active:
            return

        self._drag_active = False
        self._dispatch_timer.stop()
        self._settle_timer.stop()
        self._dispatch_exact_seek()

        if self._mute_during_scrub:
            self._playback.set_muted(False)

        if self._was_playing_before_drag and self._resume_after_scrub:
            self._playback.play()

    def _dispatch_approximate_seek(self) -> None:
        if self._requested_position is None:
            return
        if self._requested_position == self._last_sent_position:
            return
        self._playback.seek(self._requested_position, precise=False)
        self._last_sent_position = self._requested_position

    def _dispatch_exact_seek(self) -> None:
        if self._requested_position is None:
            return
        if self._requested_position == self._last_exact_position:
            return
        self._playback.seek(self._requested_position, precise=True)
        self._last_sent_position = self._requested_position
        self._last_exact_position = self._requested_position
