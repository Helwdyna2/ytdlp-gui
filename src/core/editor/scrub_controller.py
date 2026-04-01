"""Approximate-drag / exact-settle seek controller."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from ...services.config_service import ConfigService
from .playback_controller import PlaybackController


class ScrubController(QObject):
    """Coordinates drag scrubbing against the playback controller."""

    preview_position_changed = pyqtSignal(float)
    preview_override_changed = pyqtSignal(bool)

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
        self._scrub_step_seconds = float(
            config.get("trim.playback.scrub_step_seconds", 0.25)
        )
        self._resume_after_scrub = config.get(
            "trim.playback.resume_after_scrub", False
        )
        self._mute_during_scrub = config.get(
            "trim.playback.mute_during_scrub", True
        )

        self._drag_active = False
        self._preview_override_active = False
        self._requested_position: Optional[float] = None
        self._last_sent_position: Optional[float] = None
        self._last_exact_position: Optional[float] = None
        self._was_playing_before_drag = False
        self._target_generation = 0
        self._pending_exact_generation: Optional[int] = None
        self._pending_exact_seek_serial: Optional[int] = None

        self._dispatch_timer = QTimer(self)
        self._dispatch_timer.setInterval(self._send_interval_ms)
        self._dispatch_timer.timeout.connect(self._dispatch_approximate_seek)

        self._settle_timer = QTimer(self)
        self._settle_timer.setSingleShot(True)
        self._settle_timer.setInterval(self._exact_settle_delay_ms)
        self._settle_timer.timeout.connect(self._dispatch_exact_seek)

        self._playback.seek_settled.connect(self._on_seek_settled)

    def begin_drag(self) -> None:
        if self._drag_active:
            return
        self._drag_active = True
        self._was_playing_before_drag = self._playback.is_playing()
        self._playback.pause()
        if self._mute_during_scrub:
            self._playback.set_muted(True)

    def update_drag(self, position: float) -> None:
        if self._requested_position != position:
            self._target_generation += 1
        self._requested_position = position
        self._set_preview_override(True)
        self.preview_position_changed.emit(position)
        if self._pending_exact_generation is not None:
            if self._pending_exact_generation < self._target_generation:
                self._pending_exact_generation = None
                self._pending_exact_seek_serial = None
        if not self._drag_active:
            return

        if not self._dispatch_timer.isActive():
            self._dispatch_approximate_seek()
        self._restart_dispatch_timer()

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
        precise = self._should_use_precise_preview_seek()
        self._playback.seek(self._requested_position, precise=precise)
        self._last_sent_position = self._requested_position
        if self._drag_active:
            self._restart_dispatch_timer()

    def _dispatch_exact_seek(self) -> None:
        if self._requested_position is None:
            return
        if self._requested_position == self._last_exact_position:
            if not self._drag_active and self._pending_exact_seek_serial is None:
                self._set_preview_override(False)
            return
        seek_serial = self._playback.seek(self._requested_position, precise=True)
        self._last_sent_position = self._requested_position
        self._last_exact_position = self._requested_position
        self._pending_exact_generation = self._target_generation
        self._pending_exact_seek_serial = seek_serial
        if seek_serial is None and not self._drag_active:
            self._set_preview_override(False)

    def _on_seek_settled(self, serial: int, _position: float) -> None:
        if self._pending_exact_seek_serial is None:
            return
        if serial != self._pending_exact_seek_serial:
            return
        if self._pending_exact_generation != self._target_generation:
            return
        self._pending_exact_seek_serial = None
        self._pending_exact_generation = None
        if not self._drag_active:
            self._set_preview_override(False)

    def _set_preview_override(self, active: bool) -> None:
        if self._preview_override_active == active:
            return
        self._preview_override_active = active
        self.preview_override_changed.emit(active)

    def _restart_dispatch_timer(self) -> None:
        interval = self._next_dispatch_interval_ms()
        self._dispatch_timer.setInterval(interval)
        self._dispatch_timer.start()

    def _next_dispatch_interval_ms(self) -> int:
        if self._requested_position is None:
            return self._send_interval_ms

        anchor = self._last_sent_position
        if anchor is None:
            anchor = self._playback.position()

        distance = abs(self._requested_position - anchor)
        if distance < 1.0:
            multiplier = 1.0
        elif distance < 5.0:
            multiplier = 1.5
        elif distance < 15.0:
            multiplier = 2.5
        elif distance < 60.0:
            multiplier = 4.0
        else:
            multiplier = 6.0

        return max(self._send_interval_ms, int(round(self._send_interval_ms * multiplier)))

    def _should_use_precise_preview_seek(self) -> bool:
        if self._requested_position is None:
            return False
        anchor = self._last_sent_position
        if anchor is None:
            anchor = self._playback.position()
        distance = abs(self._requested_position - anchor)
        return distance <= max(0.75, self._scrub_step_seconds * 4.0)
