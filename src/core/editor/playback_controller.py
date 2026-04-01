"""Playback controller built on libmpv's render API."""

from __future__ import annotations

import ctypes
import logging
import os
from typing import Optional

from PyQt6.QtCore import QObject, QMetaObject, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QOpenGLContext

from .mpv_binding import (
    GetProcAddressCallback,
    LibMpv,
    MPV_EVENT_END_FILE,
    MPV_EVENT_FILE_LOADED,
    MPV_EVENT_NONE,
    MPV_EVENT_PROPERTY_CHANGE,
    MPV_FORMAT_DOUBLE,
    MPV_FORMAT_FLAG,
    MpvBindingError,
    MpvClient,
    MpvEventProperty,
    MpvOpenGLInitParams,
    MpvRenderContext,
    RenderUpdateCallback,
    WakeupCallback,
)

logger = logging.getLogger(__name__)


class PlaybackController(QObject):
    """Owns the libmpv client and render context for the Trim player."""

    position_changed = pyqtSignal(float)
    duration_changed = pyqtSignal(float)
    playback_state_changed = pyqtSignal(bool)
    file_loaded = pyqtSignal()
    render_update_requested = pyqtSignal()
    error_occurred = pyqtSignal(str)
    availability_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._binding: Optional[LibMpv] = None
        self._client: Optional[MpvClient] = None
        self._render_context: Optional[MpvRenderContext] = None
        self._position = 0.0
        self._duration = 0.0
        self._is_playing = False
        self._available = False
        self._last_loaded_path: Optional[str] = None

        self._wakeup_callback: Optional[WakeupCallback] = None
        self._render_update_callback: Optional[RenderUpdateCallback] = None
        self._get_proc_callback: Optional[GetProcAddressCallback] = None
        self._gl_init_params: Optional[MpvOpenGLInitParams] = None

        self._initialize_client()

    def _initialize_client(self) -> None:
        if os.environ.get("QT_QPA_PLATFORM") in {"offscreen", "minimal"}:
            logger.info("Skipping libmpv initialization on headless Qt platform.")
            self._available = False
            return
        try:
            self._binding = LibMpv()
            self._client = MpvClient(self._binding)
            self._client.set_option_string("vo", "libmpv")
            self._client.set_option_string("osc", "no")
            self._client.set_option_string("input-default-bindings", "no")
            self._client.set_option_string("input-vo-keyboard", "no")
            self._client.set_option_string("hwdec", "auto-safe")
            self._client.set_option_string("keep-open", "yes")
            self._client.initialize()

            self._client.observe_property(1, "time-pos", MPV_FORMAT_DOUBLE)
            self._client.observe_property(2, "duration", MPV_FORMAT_DOUBLE)
            self._client.observe_property(3, "pause", MPV_FORMAT_FLAG)

            self._wakeup_callback = WakeupCallback(self._on_wakeup)
            self._client.set_wakeup_callback(self._wakeup_callback)
            self._available = True
            self.availability_changed.emit(True)
        except Exception as exc:
            logger.exception("Failed to initialize libmpv playback controller: %s", exc)
            self._available = False
            self.availability_changed.emit(False)
            self.error_occurred.emit(str(exc))

    def is_available(self) -> bool:
        return self._available and self._client is not None

    def attach_render_context(self) -> bool:
        if not self.is_available() or self._render_context is not None:
            return self._render_context is not None

        context = QOpenGLContext.currentContext()
        if context is None:
            self.error_occurred.emit("No current OpenGL context for mpv render setup.")
            return False

        try:
            self._get_proc_callback = GetProcAddressCallback(self._get_proc_address)
            self._gl_init_params = MpvOpenGLInitParams(
                get_proc_address=self._get_proc_callback,
                get_proc_address_ctx=None,
                extra_exts=None,
            )
            self._render_context = MpvRenderContext.create(
                self._binding,
                self._client,
                self._gl_init_params,
            )
            self._render_update_callback = RenderUpdateCallback(self._on_render_update)
            self._render_context.set_update_callback(self._render_update_callback)
            return True
        except Exception as exc:
            logger.exception("Failed to create libmpv render context: %s", exc)
            self.error_occurred.emit(str(exc))
            return False

    def detach_render_context(self) -> None:
        if self._render_context is not None:
            self._render_context.free()
            self._render_context = None
        self._render_update_callback = None
        self._get_proc_callback = None
        self._gl_init_params = None

    def render(self, fbo: int, width: int, height: int) -> None:
        if self._render_context is None:
            return
        self._render_context.render(fbo, width, height, flip_y=True)

    def load_file(self, path: str) -> bool:
        if not self.is_available():
            return False
        try:
            self._position = 0.0
            self.position_changed.emit(0.0)
            self._client.command(["loadfile", path, "replace"])
            self.pause()
            self._last_loaded_path = path
            return True
        except Exception as exc:
            logger.exception("Failed to load file into libmpv: %s", exc)
            self.error_occurred.emit(str(exc))
            return False

    def play(self) -> None:
        if not self.is_available():
            return
        try:
            self._client.set_property_flag("pause", False)
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def pause(self) -> None:
        if not self.is_available():
            return
        try:
            self._client.set_property_flag("pause", True)
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def toggle_playback(self) -> None:
        if self._is_playing:
            self.pause()
        else:
            self.play()

    def unload(self) -> None:
        if not self.is_available():
            self._position = 0.0
            self._duration = 0.0
            self._is_playing = False
            return
        try:
            self._client.command(["stop"])
            self._position = 0.0
            self._duration = 0.0
            self._is_playing = False
            self.position_changed.emit(0.0)
            self.duration_changed.emit(0.0)
            self.playback_state_changed.emit(False)
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def seek(self, seconds: float, precise: bool = True) -> None:
        if not self.is_available():
            return
        mode = "absolute+exact" if precise else "absolute+keyframes"
        try:
            self._client.command(["seek", f"{seconds:.6f}", mode])
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def step_frame_forward(self) -> None:
        if not self.is_available():
            return
        try:
            self.pause()
            self._client.command(["frame-step"])
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def step_frame_backward(self) -> None:
        if not self.is_available():
            return
        try:
            self.pause()
            self._client.command(["frame-back-step"])
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def set_muted(self, muted: bool) -> None:
        if not self.is_available():
            return
        try:
            self._client.set_property_flag("mute", muted)
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def position(self) -> float:
        return self._position

    def duration(self) -> float:
        return self._duration

    def is_playing(self) -> bool:
        return self._is_playing

    def cleanup(self) -> None:
        self.detach_render_context()
        if self._client is not None:
            self._client.terminate()
            self._client = None
        self._binding = None
        self._wakeup_callback = None

    def _get_proc_address(self, _ctx, name: bytes):
        context = QOpenGLContext.currentContext()
        if context is None:
            return None
        try:
            proc = context.getProcAddress(name.decode("utf-8"))
        except TypeError:
            proc = context.getProcAddress(name)
        if proc is None:
            return None
        return int(proc)

    def _on_wakeup(self, _ctx) -> None:
        QMetaObject.invokeMethod(
            self,
            "_drain_events",
            Qt.ConnectionType.QueuedConnection,
        )

    def _on_render_update(self, _ctx) -> None:
        QMetaObject.invokeMethod(
            self,
            "_emit_render_update",
            Qt.ConnectionType.QueuedConnection,
        )

    @pyqtSlot()
    def _emit_render_update(self) -> None:
        self.render_update_requested.emit()

    @pyqtSlot()
    def _drain_events(self) -> None:
        if not self.is_available():
            return

        while True:
            event = self._client.wait_event()
            if event.event_id == MPV_EVENT_NONE:
                break
            self._handle_event(event)

    def _handle_event(self, event) -> None:
        if event.event_id == MPV_EVENT_PROPERTY_CHANGE:
            self._handle_property_change(event)
        elif event.event_id == MPV_EVENT_FILE_LOADED:
            self._position = 0.0
            self.file_loaded.emit()
        elif event.event_id == MPV_EVENT_END_FILE:
            self._position = 0.0
            self._is_playing = False
            self.position_changed.emit(0.0)
            self.playback_state_changed.emit(False)

    def _handle_property_change(self, event) -> None:
        prop = ctypes.cast(event.data, ctypes.POINTER(MpvEventProperty)).contents
        name = prop.name.decode("utf-8") if prop.name else ""

        if prop.format == MPV_FORMAT_DOUBLE and prop.data:
            value = ctypes.cast(prop.data, ctypes.POINTER(ctypes.c_double)).contents.value
            if name == "time-pos":
                self._position = max(0.0, float(value))
                self.position_changed.emit(self._position)
            elif name == "duration":
                self._duration = max(0.0, float(value))
                self.duration_changed.emit(self._duration)
        elif prop.format == MPV_FORMAT_FLAG and prop.data:
            value = bool(ctypes.cast(prop.data, ctypes.POINTER(ctypes.c_int)).contents.value)
            if name == "pause":
                self._is_playing = not value
                self.playback_state_changed.emit(self._is_playing)
