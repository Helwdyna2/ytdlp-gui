"""Video preview widget with platform-safe playback backends."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QTimer, Qt, QUrl, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStyle,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...utils.platform_utils import Platform, get_platform

logger = logging.getLogger(__name__)

MPV_AVAILABLE = False
try:
    import mpv

    MPV_AVAILABLE = True
except ImportError:
    logger.warning("python-mpv not installed. Falling back to QtMultimedia preview.")
except Exception as exc:
    logger.warning("Failed to import mpv: %s", exc)

QTMEDIA_AVAILABLE = False
try:
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PyQt6.QtMultimediaWidgets import QVideoWidget

    QTMEDIA_AVAILABLE = True
except ImportError:
    logger.warning("QtMultimedia not available. Video preview fallback disabled.")
except Exception as exc:
    logger.warning("Failed to import QtMultimedia: %s", exc)


class VideoPreviewWidget(QWidget):
    """Embedded preview widget used by the Trim tool."""

    position_changed = pyqtSignal(float)
    duration_loaded = pyqtSignal(float)
    video_loaded = pyqtSignal()
    playback_state_changed = pyqtSignal(bool)

    _FRAME_STEP_SECONDS = 1 / 30

    def __init__(self, parent=None):
        super().__init__(parent)

        self._backend = self._select_backend()
        self._mpv_player = None
        self._qt_player: Optional[QMediaPlayer] = None
        self._audio_output: Optional[QAudioOutput] = None

        self._duration = 0.0
        self._position = 0.0
        self._is_playing = False
        self._video_path: Optional[str] = None
        self._position_update_timer: Optional[QTimer] = None

        self._setup_ui()
        self._connect_signals()
        self._init_backend_if_needed()

    def _select_backend(self) -> Optional[str]:
        """Choose the safest backend for this platform."""
        if get_platform() == Platform.MACOS and QTMEDIA_AVAILABLE:
            return "qt"
        if MPV_AVAILABLE:
            return "mpv"
        if QTMEDIA_AVAILABLE:
            return "qt"
        return None

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        if self._backend == "mpv":
            self._video_surface = QWidget()
            self._video_surface.setAttribute(
                Qt.WidgetAttribute.WA_DontCreateNativeAncestors
            )
            self._video_surface.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
            self._video_surface.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self._video_surface.setMinimumHeight(300)
            self._video_surface.setObjectName("videoPreviewSurface")
        elif self._backend == "qt":
            self._video_surface = QVideoWidget()
            self._video_surface.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self._video_surface.setMinimumHeight(300)
            self._video_surface.setAspectRatioMode(
                Qt.AspectRatioMode.KeepAspectRatio
            )
        else:
            self._video_surface = QLabel(
                "Video preview is unavailable.\n\n"
                "Install libmpv or ensure QtMultimedia is available."
            )
            self._video_surface.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._video_surface.setWordWrap(True)
            self._video_surface.setObjectName("dimLabel")
            self._video_surface.setMinimumHeight(300)

        layout.addWidget(self._video_surface, stretch=1)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)

        self._play_btn = QPushButton()
        self._play_btn.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        )
        self._play_btn.setFixedSize(34, 34)
        controls_row.addWidget(self._play_btn)

        self._frame_back_btn = QPushButton()
        self._frame_back_btn.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekBackward)
        )
        self._frame_back_btn.setFixedSize(34, 34)
        controls_row.addWidget(self._frame_back_btn)

        self._frame_forward_btn = QPushButton()
        self._frame_forward_btn.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekForward)
        )
        self._frame_forward_btn.setFixedSize(34, 34)
        controls_row.addWidget(self._frame_forward_btn)

        self._position_slider = QSlider(Qt.Orientation.Horizontal)
        self._position_slider.setRange(0, 1000)
        controls_row.addWidget(self._position_slider, stretch=1)

        self._time_label = QLabel("00:00:00.000 / 00:00:00.000")
        self._time_label.setMinimumWidth(190)
        controls_row.addWidget(self._time_label)

        layout.addLayout(controls_row)
        self._set_controls_enabled(False)

    def _connect_signals(self) -> None:
        self._play_btn.clicked.connect(self.toggle_playback)
        self._frame_back_btn.clicked.connect(self.step_frame_backward)
        self._frame_forward_btn.clicked.connect(self.step_frame_forward)
        self._position_slider.sliderMoved.connect(self._on_slider_moved)
        self._position_slider.sliderReleased.connect(self._on_slider_released)

    def _init_backend_if_needed(self) -> None:
        if self._backend == "qt":
            self._init_qt_backend()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._backend == "mpv" and self._mpv_player is None:
            QTimer.singleShot(100, self._init_mpv_backend)

    def _init_qt_backend(self) -> None:
        if self._qt_player is not None:
            return

        self._qt_player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._audio_output.setVolume(1.0)
        self._qt_player.setAudioOutput(self._audio_output)
        self._qt_player.setVideoOutput(self._video_surface)
        self._qt_player.durationChanged.connect(self._on_qt_duration_changed)
        self._qt_player.positionChanged.connect(self._on_qt_position_changed)
        self._qt_player.playbackStateChanged.connect(
            self._on_qt_playback_state_changed
        )

    def _init_mpv_backend(self) -> None:
        if self._mpv_player is not None or not MPV_AVAILABLE:
            return

        try:
            import locale

            locale.setlocale(locale.LC_NUMERIC, "C")
            wid = str(int(self._video_surface.winId()))

            self._mpv_player = mpv.MPV(
                wid=wid,
                log_handler=self._mpv_log_handler,
                loglevel="warn",
                osc=False,
                pause=True,
                input_default_bindings=False,
                input_vo_keyboard=False,
                hwdec="auto",
            )
            self._mpv_player.observe_property("duration", self._on_mpv_duration_change)
            self._mpv_player.observe_property("pause", self._on_mpv_pause_change)

            self._position_update_timer = QTimer(self)
            self._position_update_timer.timeout.connect(self._update_mpv_position)
            self._position_update_timer.start(50)
        except Exception as exc:
            logger.exception("Failed to initialize mpv preview backend: %s", exc)
            self._backend = None
            self._mpv_player = None
            self._set_controls_enabled(False)

    def _mpv_log_handler(self, level: str, component: str, message: str) -> None:
        if level == "error":
            logger.error("mpv [%s]: %s", component, message)
        elif level == "warn":
            logger.warning("mpv [%s]: %s", component, message)
        else:
            logger.debug("mpv [%s]: %s", component, message)

    def _on_mpv_duration_change(self, name: str, value) -> None:
        if value is None:
            return
        self._duration = float(value)
        QTimer.singleShot(0, self._emit_duration_loaded)

    def _on_mpv_pause_change(self, name: str, value) -> None:
        if value is None:
            return
        self._is_playing = not value
        QTimer.singleShot(0, self._update_play_button)

    def _update_mpv_position(self) -> None:
        if self._mpv_player is None:
            return

        try:
            pos = self._mpv_player.time_pos
            if pos is None:
                return
            self._position = float(pos)
            self._sync_position_ui()
        except Exception:
            logger.debug("Ignoring transient mpv position read failure.", exc_info=True)

    def _on_qt_duration_changed(self, duration_ms: int) -> None:
        self._duration = max(0.0, duration_ms / 1000.0)
        self._emit_duration_loaded()

    def _on_qt_position_changed(self, position_ms: int) -> None:
        self._position = max(0.0, position_ms / 1000.0)
        self._sync_position_ui()

    def _on_qt_playback_state_changed(self, state) -> None:
        self._is_playing = state == QMediaPlayer.PlaybackState.PlayingState
        self._update_play_button()

    def _emit_duration_loaded(self) -> None:
        self.duration_loaded.emit(self._duration)
        self._set_controls_enabled(self._duration > 0)
        self.video_loaded.emit()
        self._sync_position_ui()

    def _sync_position_ui(self) -> None:
        if not self._position_slider.isSliderDown() and self._duration > 0:
            slider_pos = int((self._position / self._duration) * 1000)
            self._position_slider.setValue(max(0, min(1000, slider_pos)))

        self._update_time_label()
        self.position_changed.emit(self._position)

    def _update_time_label(self) -> None:
        self._time_label.setText(
            f"{self._format_time(self._position)} / {self._format_time(self._duration)}"
        )

    def _format_time(self, seconds: float) -> str:
        seconds = max(0.0, seconds)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        millis = int((secs % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(secs):02d}.{millis:03d}"

    def _update_play_button(self) -> None:
        icon = (
            QStyle.StandardPixmap.SP_MediaPause
            if self._is_playing
            else QStyle.StandardPixmap.SP_MediaPlay
        )
        self._play_btn.setIcon(self.style().standardIcon(icon))
        self.playback_state_changed.emit(self._is_playing)

    def _on_slider_moved(self, value: int) -> None:
        if self._duration <= 0:
            return
        self._position = (value / 1000) * self._duration
        self._update_time_label()

    def _on_slider_released(self) -> None:
        if self._duration <= 0:
            return
        value = self._position_slider.value()
        self.seek((value / 1000) * self._duration)

    def _set_controls_enabled(self, enabled: bool) -> None:
        self._play_btn.setEnabled(enabled)
        self._frame_back_btn.setEnabled(enabled)
        self._frame_forward_btn.setEnabled(enabled)
        self._position_slider.setEnabled(enabled)

    def load_video(self, path: str) -> bool:
        if self._backend is None:
            return False

        resolved_path = str(Path(path).expanduser())
        self._video_path = resolved_path
        self._position = 0.0

        try:
            if self._backend == "qt":
                if self._qt_player is None:
                    self._init_qt_backend()
                assert self._qt_player is not None
                self._qt_player.setSource(QUrl.fromLocalFile(resolved_path))
                self._qt_player.pause()
            else:
                if self._mpv_player is None:
                    self._init_mpv_backend()
                if self._mpv_player is None:
                    return False
                self._mpv_player.play(resolved_path)
                self._mpv_player.pause = True
            logger.info("Loaded preview video via %s backend: %s", self._backend, path)
            return True
        except Exception as exc:
            logger.exception("Failed to load video preview: %s", exc)
            return False

    def unload_video(self) -> None:
        if self._qt_player is not None:
            self._qt_player.stop()
            self._qt_player.setSource(QUrl())
        if self._mpv_player is not None:
            try:
                self._mpv_player.stop()
            except Exception:
                logger.debug("Ignoring mpv stop failure during unload.", exc_info=True)

        self._video_path = None
        self._duration = 0.0
        self._position = 0.0
        self._is_playing = False
        self._position_slider.setValue(0)
        self._update_time_label()
        self._set_controls_enabled(False)

    def play(self) -> None:
        if self._backend == "qt" and self._qt_player is not None:
            self._qt_player.play()
        elif self._backend == "mpv" and self._mpv_player is not None:
            self._mpv_player.pause = False

    def pause(self) -> None:
        if self._backend == "qt" and self._qt_player is not None:
            self._qt_player.pause()
        elif self._backend == "mpv" and self._mpv_player is not None:
            self._mpv_player.pause = True

    def toggle_playback(self) -> None:
        if self._is_playing:
            self.pause()
        else:
            self.play()

    def seek(self, position: float) -> None:
        position = max(0.0, min(position, self._duration or position))
        self._position = position
        if self._backend == "qt" and self._qt_player is not None:
            self._qt_player.setPosition(int(position * 1000))
        elif self._backend == "mpv" and self._mpv_player is not None:
            self._mpv_player.seek(position, "absolute")
        self._sync_position_ui()

    def step_frame_forward(self) -> None:
        if self._backend == "mpv" and self._mpv_player is not None:
            self._mpv_player.frame_step()
            return
        self.seek(self._position + self._FRAME_STEP_SECONDS)

    def step_frame_backward(self) -> None:
        if self._backend == "mpv" and self._mpv_player is not None:
            self._mpv_player.frame_back_step()
            return
        self.seek(self._position - self._FRAME_STEP_SECONDS)

    def get_position(self) -> float:
        return self._position

    def get_duration(self) -> float:
        return self._duration

    def is_playing(self) -> bool:
        return self._is_playing

    def is_available(self) -> bool:
        return self._backend is not None

    def cleanup(self) -> None:
        if self._position_update_timer is not None:
            self._position_update_timer.stop()
            self._position_update_timer = None

        if self._qt_player is not None:
            self._qt_player.stop()
            self._qt_player.deleteLater()
            self._qt_player = None

        if self._mpv_player is not None:
            try:
                self._mpv_player.terminate()
            except Exception:
                logger.debug("Ignoring mpv terminate failure.", exc_info=True)
            self._mpv_player = None

    def closeEvent(self, event) -> None:
        self.cleanup()
        super().closeEvent(event)
