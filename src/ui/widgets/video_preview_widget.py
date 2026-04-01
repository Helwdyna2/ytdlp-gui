"""Video preview widget backed by libmpv's OpenGL render API."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from ...core.editor import PlaybackController, ScrubController

logger = logging.getLogger(__name__)


class _MpvRenderSurface(QOpenGLWidget):
    """OpenGL surface that libmpv renders into."""

    def __init__(self, playback: PlaybackController, parent=None):
        super().__init__(parent)
        self._playback = playback
        self._render_ready = False

        self.setMinimumHeight(280)
        self.setAutoFillBackground(False)
        self._playback.render_update_requested.connect(self._schedule_update)

    def initializeGL(self) -> None:
        self._render_ready = self._playback.attach_render_context()
        self.update()

    def paintGL(self) -> None:
        if not self._render_ready:
            return

        pixel_ratio = self.devicePixelRatioF()
        width = max(1, int(self.width() * pixel_ratio))
        height = max(1, int(self.height() * pixel_ratio))
        self._playback.render(self.defaultFramebufferObject(), width, height)

    def _schedule_update(self) -> None:
        self.update()


class VideoPreviewWidget(QWidget):
    """
    Embedded video preview widget with libmpv playback and scrub controls.

    Signals:
        position_changed: Emits current playback position in seconds
        duration_loaded: Emits video duration when loaded
        video_loaded: Emitted when a video is successfully loaded
        playback_state_changed: Emits True when playing, False when paused
    """

    position_changed = pyqtSignal(float)
    duration_loaded = pyqtSignal(float)
    video_loaded = pyqtSignal()
    playback_state_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._playback = PlaybackController(self)
        self._scrub_controller = ScrubController(self._playback, self)

        self._duration = 0.0
        self._position = 0.0
        self._is_playing = False
        self._video_path: Optional[str] = None

        self._setup_ui()
        self._connect_signals()
        self._sync_availability_message(self._playback.is_available())
        self._set_controls_enabled(False)
        self._update_play_button()
        self._update_time_label()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._render_surface = _MpvRenderSurface(self._playback)
        layout.addWidget(self._render_surface, stretch=1)

        self._availability_label = QLabel()
        self._availability_label.setObjectName("dimLabel")
        self._availability_label.setWordWrap(True)
        self._availability_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._availability_label)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)

        self._play_btn = QPushButton()
        self._play_btn.setFixedSize(32, 32)
        self._play_btn.setToolTip("Play/Pause (Space)")
        controls_layout.addWidget(self._play_btn)

        self._frame_back_btn = QPushButton()
        self._frame_back_btn.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekBackward)
        )
        self._frame_back_btn.setFixedSize(32, 32)
        self._frame_back_btn.setToolTip("Previous frame (,)")
        controls_layout.addWidget(self._frame_back_btn)

        self._frame_forward_btn = QPushButton()
        self._frame_forward_btn.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekForward)
        )
        self._frame_forward_btn.setFixedSize(32, 32)
        self._frame_forward_btn.setToolTip("Next frame (.)")
        controls_layout.addWidget(self._frame_forward_btn)

        self._position_slider = QSlider(Qt.Orientation.Horizontal)
        self._position_slider.setRange(0, 1000)
        controls_layout.addWidget(self._position_slider, stretch=1)

        self._time_label = QLabel("00:00:00.000 / 00:00:00.000")
        self._time_label.setMinimumWidth(180)
        controls_layout.addWidget(self._time_label)

        layout.addLayout(controls_layout)

    def _connect_signals(self) -> None:
        self._play_btn.clicked.connect(self.toggle_playback)
        self._frame_back_btn.clicked.connect(self.step_frame_backward)
        self._frame_forward_btn.clicked.connect(self.step_frame_forward)
        self._position_slider.sliderPressed.connect(self._on_slider_pressed)
        self._position_slider.sliderMoved.connect(self._on_slider_moved)
        self._position_slider.sliderReleased.connect(self._on_slider_released)

        self._playback.position_changed.connect(self._on_position_changed)
        self._playback.duration_changed.connect(self._on_duration_changed)
        self._playback.playback_state_changed.connect(self._on_playback_state_changed)
        self._playback.file_loaded.connect(self._on_file_loaded)
        self._playback.error_occurred.connect(self._on_playback_error)
        self._playback.availability_changed.connect(self._sync_availability_message)

    def _on_slider_pressed(self) -> None:
        if self._duration <= 0:
            return
        self._scrub_controller.begin_drag()

    def _on_slider_moved(self, value: int) -> None:
        if self._duration <= 0:
            return
        position = (value / 1000.0) * self._duration
        self._position = position
        self._update_time_label()
        self._scrub_controller.update_drag(position)

    def _on_slider_released(self) -> None:
        if self._duration <= 0:
            return
        value = self._position_slider.value()
        position = (value / 1000.0) * self._duration
        self._position = position
        self._scrub_controller.update_drag(position)
        self._scrub_controller.end_drag()
        self._update_time_label()

    def _on_position_changed(self, position: float) -> None:
        self._position = max(0.0, position)
        if not self._position_slider.isSliderDown() and self._duration > 0:
            slider_value = int((self._position / self._duration) * 1000)
            self._position_slider.blockSignals(True)
            self._position_slider.setValue(slider_value)
            self._position_slider.blockSignals(False)

        self._update_time_label()
        self.position_changed.emit(self._position)

    def _on_duration_changed(self, duration: float) -> None:
        self._duration = max(0.0, duration)
        has_media = self._duration > 0
        self._set_controls_enabled(has_media)
        self._update_time_label()
        if has_media:
            self.duration_loaded.emit(self._duration)

    def _on_playback_state_changed(self, is_playing: bool) -> None:
        self._is_playing = is_playing
        self._update_play_button()
        self.playback_state_changed.emit(is_playing)

    def _on_file_loaded(self) -> None:
        self._set_controls_enabled(self._duration > 0)
        self.video_loaded.emit()
        if self._playback.is_available():
            self._availability_label.setText("libmpv render backend active.")

    def _on_playback_error(self, message: str) -> None:
        logger.error("Video preview error: %s", message)
        self._availability_label.setText(f"Preview error: {message}")

    def _sync_availability_message(self, available: bool) -> None:
        if available:
            self._availability_label.setText("Load a video to preview and scrub.")
            self._render_surface.show()
            return

        self._availability_label.setText(
            "Preview playback is unavailable because libmpv could not be initialized.\n"
            "You can still load files, split segments, and export enabled ranges."
        )
        self._render_surface.hide()

    def _update_play_button(self) -> None:
        icon = (
            QStyle.StandardPixmap.SP_MediaPause
            if self._is_playing
            else QStyle.StandardPixmap.SP_MediaPlay
        )
        self._play_btn.setIcon(self.style().standardIcon(icon))

    def _update_time_label(self) -> None:
        self._time_label.setText(
            f"{self._format_time(self._position)} / {self._format_time(self._duration)}"
        )

    def _format_time(self, seconds: float) -> str:
        if seconds < 0:
            seconds = 0

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        millis = int((secs % 1) * 1000)
        secs = int(secs)

        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def _set_controls_enabled(self, enabled: bool) -> None:
        self._play_btn.setEnabled(enabled)
        self._frame_back_btn.setEnabled(enabled)
        self._frame_forward_btn.setEnabled(enabled)
        self._position_slider.setEnabled(enabled)

    def load_video(self, path: str) -> bool:
        if not self.is_available():
            logger.warning("libmpv playback is unavailable, cannot load %s", path)
            return False

        self._video_path = path
        self._position = 0.0
        self._duration = 0.0
        self._position_slider.blockSignals(True)
        self._position_slider.setValue(0)
        self._position_slider.blockSignals(False)
        self._update_time_label()
        self._availability_label.setText(f"Loading {path}…")
        return self._playback.load_file(path)

    def unload_video(self) -> None:
        self._playback.unload()
        self._video_path = None
        self._duration = 0.0
        self._position = 0.0
        self._is_playing = False
        self._set_controls_enabled(False)
        self._position_slider.blockSignals(True)
        self._position_slider.setValue(0)
        self._position_slider.blockSignals(False)
        self._update_play_button()
        self._sync_availability_message(self._playback.is_available())
        self._update_time_label()

    def play(self) -> None:
        self._playback.play()

    def pause(self) -> None:
        self._playback.pause()

    def toggle_playback(self) -> None:
        self._playback.toggle_playback()

    def seek(self, position: float, precise: bool = True) -> None:
        self._playback.seek(position, precise=precise)

    def step_frame_forward(self) -> None:
        self._playback.step_frame_forward()

    def step_frame_backward(self) -> None:
        self._playback.step_frame_backward()

    def get_position(self) -> float:
        return self._position

    def get_duration(self) -> float:
        return self._duration

    def is_playing(self) -> bool:
        return self._is_playing

    def is_available(self) -> bool:
        return self._playback.is_available()

    def cleanup(self) -> None:
        self._playback.cleanup()

    def closeEvent(self, event) -> None:
        self.cleanup()
        super().closeEvent(event)
