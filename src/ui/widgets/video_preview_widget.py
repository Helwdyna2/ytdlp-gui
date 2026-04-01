"""Video preview widget backed by libmpv's OpenGL render API."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ...core.editor import PlaybackController, ScrubController
from ...services.config_service import ConfigService

logger = logging.getLogger(__name__)


class _MpvRenderSurface(QOpenGLWidget):
    """OpenGL surface that libmpv renders into."""

    render_ready = pyqtSignal(bool)

    def __init__(self, playback: PlaybackController, parent=None):
        super().__init__(parent)
        self._playback = playback
        self._render_ready = False

        self.setMinimumHeight(320)
        self.setAutoFillBackground(False)
        self._playback.render_update_requested.connect(self._schedule_update)

    def initializeGL(self) -> None:
        self._render_ready = self._playback.attach_render_context()
        self.render_ready.emit(self._render_ready)
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
    scrub_step_changed = pyqtSignal(float)
    _POSITION_SLIDER_STEPS = 100000
    _STEP_OPTIONS = [0.1, 0.25, 0.5, 1.0, 2.0, 5.0]

    def __init__(self, parent=None):
        super().__init__(parent)

        self._config = ConfigService()
        self._playback = PlaybackController(self)
        self._scrub_controller = ScrubController(self._playback, self)

        self._duration = 0.0
        self._position = 0.0
        self._requested_display_position: Optional[float] = None
        self._decoder_mode = "unknown"
        self._decoder_name = ""
        self._decoder_description = ""
        self._is_playing = False
        self._video_path: Optional[str] = None
        self._pending_video_path: Optional[str] = None

        self._setup_ui()
        self._connect_signals()
        self._load_scrub_step_setting()
        self._sync_availability_message(self._playback.is_available())
        self._set_controls_enabled(False)
        self._update_play_button()
        self._update_time_label()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._render_surface = _MpvRenderSurface(self._playback)
        layout.addWidget(self._render_surface, stretch=1)

        status_row = QHBoxLayout()
        status_row.setSpacing(12)

        self._availability_label = QLabel()
        self._availability_label.setObjectName("dimLabel")
        self._availability_label.setWordWrap(True)
        self._availability_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        status_row.addWidget(self._availability_label, stretch=1)

        self._decoder_status_label = QLabel("")
        self._decoder_status_label.setObjectName("dimLabel")
        self._decoder_status_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._decoder_status_label.setVisible(False)
        status_row.addWidget(self._decoder_status_label)

        layout.addLayout(status_row)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)

        self._play_btn = QPushButton()
        self._play_btn.setObjectName("btnWire")
        self._play_btn.setMinimumWidth(78)
        self._play_btn.setMinimumHeight(34)
        self._play_btn.setToolTip("Play/Pause (Space)")
        controls_layout.addWidget(self._play_btn)

        self._jump_back_btn = QPushButton("- Step")
        self._jump_back_btn.setObjectName("btnWire")
        self._jump_back_btn.setMinimumHeight(34)
        self._jump_back_btn.setToolTip("Jump backward by the configured scrub step")
        controls_layout.addWidget(self._jump_back_btn)

        self._frame_back_btn = QPushButton("Prev Frame")
        self._frame_back_btn.setObjectName("btnWire")
        self._frame_back_btn.setMinimumHeight(34)
        self._frame_back_btn.setToolTip("Previous frame (,)")
        controls_layout.addWidget(self._frame_back_btn)

        self._frame_forward_btn = QPushButton("Next Frame")
        self._frame_forward_btn.setObjectName("btnWire")
        self._frame_forward_btn.setMinimumHeight(34)
        self._frame_forward_btn.setToolTip("Next frame (.)")
        controls_layout.addWidget(self._frame_forward_btn)

        self._jump_forward_btn = QPushButton("+ Step")
        self._jump_forward_btn.setObjectName("btnWire")
        self._jump_forward_btn.setMinimumHeight(34)
        self._jump_forward_btn.setToolTip("Jump forward by the configured scrub step")
        controls_layout.addWidget(self._jump_forward_btn)

        controls_layout.addWidget(QLabel("Step"))

        self._scrub_step_combo = QComboBox()
        self._scrub_step_combo.setObjectName("trimScrubStepCombo")
        self._scrub_step_combo.setMinimumWidth(92)
        for step in self._STEP_OPTIONS:
            self._scrub_step_combo.addItem(self._format_step_label(step), step)
        controls_layout.addWidget(self._scrub_step_combo)

        self._position_slider = QSlider(Qt.Orientation.Horizontal)
        self._position_slider.setRange(0, self._POSITION_SLIDER_STEPS)
        controls_layout.addWidget(self._position_slider, stretch=1)

        self._time_label = QLabel("00:00:00.000 / 00:00:00.000")
        self._time_label.setMinimumWidth(180)
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        controls_layout.addWidget(self._time_label)

        layout.addLayout(controls_layout)

    def _connect_signals(self) -> None:
        self._play_btn.clicked.connect(self.toggle_playback)
        self._jump_back_btn.clicked.connect(self.jump_backward)
        self._frame_back_btn.clicked.connect(self.step_frame_backward)
        self._frame_forward_btn.clicked.connect(self.step_frame_forward)
        self._jump_forward_btn.clicked.connect(self.jump_forward)
        self._scrub_step_combo.currentIndexChanged.connect(self._on_scrub_step_changed)
        self._position_slider.sliderPressed.connect(self._on_slider_pressed)
        self._position_slider.sliderMoved.connect(self._on_slider_moved)
        self._position_slider.sliderReleased.connect(self._on_slider_released)

        self._playback.position_changed.connect(self._on_position_changed)
        self._playback.duration_changed.connect(self._on_duration_changed)
        self._playback.playback_state_changed.connect(self._on_playback_state_changed)
        self._playback.file_loaded.connect(self._on_file_loaded)
        self._playback.error_occurred.connect(self._on_playback_error)
        self._playback.availability_changed.connect(self._sync_availability_message)
        self._playback.decoder_status_changed.connect(self._on_decoder_status_changed)
        self._render_surface.render_ready.connect(self._on_render_surface_ready)
        self._scrub_controller.preview_position_changed.connect(
            self._on_scrub_preview_position_changed
        )
        self._scrub_controller.preview_override_changed.connect(
            self._on_scrub_preview_override_changed
        )

    def _load_scrub_step_setting(self) -> None:
        self.set_scrub_step_seconds(
            float(self._config.get("trim.playback.scrub_step_seconds", 0.25))
        )

    def _on_slider_pressed(self) -> None:
        if self._duration <= 0:
            return
        self._scrub_controller.begin_drag()

    def _on_slider_moved(self, value: int) -> None:
        if self._duration <= 0:
            return
        position = (value / self._POSITION_SLIDER_STEPS) * self._duration
        self._scrub_controller.update_drag(position)

    def _on_slider_released(self) -> None:
        if self._duration <= 0:
            return
        value = self._position_slider.value()
        position = (value / self._POSITION_SLIDER_STEPS) * self._duration
        self._scrub_controller.update_drag(position)
        self._scrub_controller.end_drag()
        self._update_time_label()

    def _on_position_changed(self, position: float) -> None:
        self._position = max(0.0, position)
        if not self._position_slider.isSliderDown() and self._duration > 0:
            slider_value = int(
                (self._position / self._duration) * self._POSITION_SLIDER_STEPS
            )
            self._position_slider.blockSignals(True)
            self._position_slider.setValue(slider_value)
            self._position_slider.blockSignals(False)

        if self._requested_display_position is None:
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
            self._sync_availability_message(True)
            self._render_surface.update()

    def _on_playback_error(self, message: str) -> None:
        logger.error("Video preview error: %s", message)
        self._availability_label.setText(f"Preview error: {message}")
        self._availability_label.setVisible(True)
        self._decoder_status_label.setVisible(False)

    def _sync_availability_message(self, available: bool) -> None:
        if available:
            self._render_surface.show()
            if self._video_path:
                self._availability_label.clear()
                self._availability_label.setVisible(False)
            else:
                self._availability_label.setText("Load a video to preview and scrub.")
                self._availability_label.setVisible(True)
            self._update_decoder_status_label()
            return

        if not self._playback.has_attempted_initialization():
            self._availability_label.setText(
                "Load a video to initialize preview playback and scrub controls."
            )
            self._availability_label.setVisible(True)
            self._render_surface.hide()
            self._decoder_status_label.setVisible(False)
            return

        self._availability_label.setText(
            "Preview playback is unavailable because libmpv could not be initialized.\n"
            "You can still load files, split segments, and export enabled ranges."
        )
        self._availability_label.setVisible(True)
        self._render_surface.hide()
        self._decoder_status_label.setVisible(False)

    def _update_play_button(self) -> None:
        self._play_btn.setText("Pause" if self._is_playing else "Play")

    def _update_time_label(self) -> None:
        self._time_label.setText(
            f"{self._format_time(self._display_position())} / {self._format_time(self._duration)}"
        )

    def _update_decoder_status_label(self) -> None:
        if not self._playback.is_available():
            self._decoder_status_label.setText("Decoder: unavailable")
            self._decoder_status_label.setVisible(True)
            return

        decoder_display = self._decoder_description or self._decoder_name
        if not self._video_path or not decoder_display:
            self._decoder_status_label.clear()
            self._decoder_status_label.setVisible(False)
            return

        if self._decoder_mode in {"", "unknown"}:
            self._decoder_status_label.clear()
            self._decoder_status_label.setVisible(False)
            return

        if self._decoder_mode == "no":
            status = f"Decoder: software ({decoder_display})"
        else:
            status = f"Decoder: hardware ({self._decoder_mode}, {decoder_display})"
        self._decoder_status_label.setText(status)
        self._decoder_status_label.setVisible(True)

    def _display_position(self) -> float:
        if self._requested_display_position is not None:
            return self._requested_display_position
        return self._position

    def _format_time(self, seconds: float) -> str:
        if seconds < 0:
            seconds = 0

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        millis = int((secs % 1) * 1000)
        secs = int(secs)

        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def _format_step_label(self, value: float) -> str:
        if value < 1.0:
            return f"{value:g} s"
        return f"{value:.0f} s"

    def _set_controls_enabled(self, enabled: bool) -> None:
        self._play_btn.setEnabled(enabled)
        self._jump_back_btn.setEnabled(enabled)
        self._frame_back_btn.setEnabled(enabled)
        self._frame_forward_btn.setEnabled(enabled)
        self._jump_forward_btn.setEnabled(enabled)
        self._position_slider.setEnabled(enabled)
        self._scrub_step_combo.setEnabled(True)

    def _on_scrub_step_changed(self, _index: int) -> None:
        step = self.get_scrub_step_seconds()
        self._config.set("trim.playback.scrub_step_seconds", step)
        self.scrub_step_changed.emit(step)

    def set_scrub_step_seconds(self, seconds: float) -> None:
        target = min(self._STEP_OPTIONS, key=lambda value: abs(value - seconds))
        index = self._scrub_step_combo.findData(target)
        if index < 0:
            index = 0
        self._scrub_step_combo.blockSignals(True)
        self._scrub_step_combo.setCurrentIndex(index)
        self._scrub_step_combo.blockSignals(False)

    def get_scrub_step_seconds(self) -> float:
        value = self._scrub_step_combo.currentData()
        return float(value) if value is not None else 0.25

    def jump_backward(self) -> None:
        self._requested_display_position = None
        self._playback.seek_relative(-self.get_scrub_step_seconds(), precise=True)

    def jump_forward(self) -> None:
        self._requested_display_position = None
        self._playback.seek_relative(self.get_scrub_step_seconds(), precise=True)

    def load_video(self, path: str) -> bool:
        self._video_path = path
        self._pending_video_path = None
        self._position = 0.0
        self._requested_display_position = None
        self._decoder_mode = "unknown"
        self._decoder_name = ""
        self._decoder_description = ""
        self._duration = 0.0
        self._position_slider.blockSignals(True)
        self._position_slider.setValue(0)
        self._position_slider.blockSignals(False)
        self._update_time_label()
        self._sync_availability_message(self._playback.is_available())

        if not self._playback.initialize_if_needed():
            logger.warning("libmpv playback is unavailable, cannot load %s", path)
            self._sync_availability_message(self._playback.is_available())
            return False

        if not self._render_surface.isValid():
            self._pending_video_path = path
            self._render_surface.update()
            return True

        return self._playback.load_file(path)

    def unload_video(self) -> None:
        self._playback.unload()
        self._video_path = None
        self._pending_video_path = None
        self._duration = 0.0
        self._position = 0.0
        self._requested_display_position = None
        self._decoder_mode = "unknown"
        self._decoder_name = ""
        self._decoder_description = ""
        self._is_playing = False
        self._set_controls_enabled(False)
        self._position_slider.blockSignals(True)
        self._position_slider.setValue(0)
        self._position_slider.blockSignals(False)
        self._update_play_button()
        self._sync_availability_message(self._playback.is_available())
        self._update_time_label()
        self._update_decoder_status_label()

    def play(self) -> None:
        self._playback.play()

    def pause(self) -> None:
        self._playback.pause()

    def toggle_playback(self) -> None:
        self._playback.toggle_playback()

    def seek(self, position: float, precise: bool = True) -> None:
        self._requested_display_position = None
        self._playback.seek(position, precise=precise)

    def step_frame_forward(self) -> None:
        self._requested_display_position = None
        self._playback.step_frame_forward()

    def step_frame_backward(self) -> None:
        self._requested_display_position = None
        self._playback.step_frame_backward()

    def get_position(self) -> float:
        return self._display_position()

    def get_duration(self) -> float:
        return self._duration

    def is_playing(self) -> bool:
        return self._is_playing

    def is_available(self) -> bool:
        return self._playback.is_available()

    def _on_scrub_preview_position_changed(self, position: float) -> None:
        self._requested_display_position = max(0.0, position)
        self._update_time_label()

    def _on_scrub_preview_override_changed(self, active: bool) -> None:
        if active:
            return
        self._requested_display_position = None
        self._update_time_label()

    def _on_decoder_status_changed(
        self, hwdec_current: str, decoder_name: str, decoder_description: str
    ) -> None:
        self._decoder_mode = hwdec_current or "unknown"
        self._decoder_name = decoder_name or ""
        self._decoder_description = decoder_description or ""
        self._update_decoder_status_label()

    def cleanup(self) -> None:
        self._playback.cleanup()

    def closeEvent(self, event) -> None:
        self.cleanup()
        super().closeEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._pending_video_path and self._render_surface.isValid():
            pending = self._pending_video_path
            self._pending_video_path = None
            self._playback.load_file(pending)

    def _on_render_surface_ready(self, ready: bool) -> None:
        if not ready or not self._pending_video_path:
            return
        pending = self._pending_video_path
        self._pending_video_path = None
        self._playback.load_file(pending)
