"""Video preview widget using mpv for playback."""

import logging
import os
import sys
from typing import Optional, Callable

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QSlider,
    QSizePolicy,
)

logger = logging.getLogger(__name__)

# Try to import mpv, but handle gracefully if not available
MPV_AVAILABLE = False
try:
    import mpv

    MPV_AVAILABLE = True
except ImportError:
    logger.warning("python-mpv not installed. Video preview will be disabled.")
except Exception as e:
    logger.warning(f"Failed to import mpv: {e}")


class VideoPreviewWidget(QWidget):
    """
    Embedded video player widget using mpv for preview and seeking.

    Provides frame-accurate seeking and playback controls for video trimming.

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
        """Initialize the video preview widget."""
        super().__init__(parent)

        self._player = None
        self._duration: float = 0.0
        self._position: float = 0.0
        self._is_playing: bool = False
        self._video_path: Optional[str] = None
        self._position_update_timer: Optional[QTimer] = None
        self._mpv_available = MPV_AVAILABLE

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        if self._mpv_available:
            # Container for mpv to render into
            self._video_container = QWidget()
            self._video_container.setAttribute(
                Qt.WidgetAttribute.WA_DontCreateNativeAncestors
            )
            self._video_container.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
            self._video_container.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self._video_container.setMinimumHeight(200)
            layout.addWidget(self._video_container, stretch=1)
        else:
            # Fallback message when mpv is not available
            self._video_container = QLabel(
                "Video preview not available.\n\n"
                "Install libmpv and python-mpv:\n"
                "  pip install python-mpv\n\n"
                "macOS: brew install mpv\n"
                "Linux: apt install libmpv-dev\n"
                "Windows: Download mpv and add to PATH"
            )
            self._video_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._video_container.setObjectName("dimLabel")
            self._video_container.setMinimumHeight(200)
            layout.addWidget(self._video_container, stretch=1)

        # Playback controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)

        # Play/Pause button
        self._play_btn = QPushButton()
        self._play_btn.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        )
        self._play_btn.setFixedSize(32, 32)
        self._play_btn.setToolTip("Play/Pause (Space)")
        controls_layout.addWidget(self._play_btn)

        # Frame step buttons
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

        # Position slider (for seeking)
        self._position_slider = QSlider(Qt.Orientation.Horizontal)
        self._position_slider.setRange(0, 1000)  # Use 1000 steps for precision
        self._position_slider.setEnabled(False)
        controls_layout.addWidget(self._position_slider, stretch=1)

        # Time label
        self._time_label = QLabel("00:00:00.000 / 00:00:00.000")
        self._time_label.setMinimumWidth(180)
        controls_layout.addWidget(self._time_label)

        layout.addLayout(controls_layout)

        # Initially disable controls
        self._set_controls_enabled(False)

    def _connect_signals(self) -> None:
        """Wire up signal connections."""
        self._play_btn.clicked.connect(self.toggle_playback)
        self._frame_back_btn.clicked.connect(self.step_frame_backward)
        self._frame_forward_btn.clicked.connect(self.step_frame_forward)
        self._position_slider.sliderMoved.connect(self._on_slider_moved)
        self._position_slider.sliderPressed.connect(self._on_slider_pressed)
        self._position_slider.sliderReleased.connect(self._on_slider_released)

    def showEvent(self, event) -> None:
        """Handle show event - initialize mpv when widget becomes visible."""
        super().showEvent(event)
        if self._mpv_available and self._player is None:
            # Delay mpv initialization slightly to ensure window is ready
            QTimer.singleShot(100, self._init_mpv)

    def _init_mpv(self) -> None:
        """Initialize the mpv player."""
        if not self._mpv_available:
            return

        try:
            # Required locale fix for mpv + Qt
            import locale

            locale.setlocale(locale.LC_NUMERIC, "C")

            # Get the window ID for embedding
            wid = str(int(self._video_container.winId()))

            # Create mpv player instance
            self._player = mpv.MPV(
                wid=wid,
                log_handler=self._mpv_log_handler,
                loglevel="warn",
                # Enable OSC (on-screen controller) for basic controls
                osc=False,  # We provide our own controls
                # Keep video paused when opened
                pause=True,
                # Disable default input handling (we handle it)
                input_default_bindings=False,
                input_vo_keyboard=False,
                # Performance settings
                hwdec="auto",
            )

            # Observe properties for updates
            self._player.observe_property("duration", self._on_duration_change)
            self._player.observe_property("pause", self._on_pause_change)

            # Start position update timer
            self._position_update_timer = QTimer(self)
            self._position_update_timer.timeout.connect(self._update_position)
            self._position_update_timer.start(50)  # 20 FPS updates

            logger.info("mpv player initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize mpv: {e}")
            self._mpv_available = False
            self._player = None

    def _mpv_log_handler(self, level: str, component: str, message: str) -> None:
        """Handle mpv log messages."""
        if level == "error":
            logger.error(f"mpv [{component}]: {message}")
        elif level == "warn":
            logger.warning(f"mpv [{component}]: {message}")
        else:
            logger.debug(f"mpv [{component}]: {message}")

    def _on_duration_change(self, name: str, value) -> None:
        """Handle duration property change from mpv."""
        if value is not None:
            self._duration = float(value)
            # Emit from main thread
            QTimer.singleShot(0, lambda: self._emit_duration_loaded())

    def _emit_duration_loaded(self) -> None:
        """Emit duration loaded signal (called from main thread)."""
        self.duration_loaded.emit(self._duration)
        self._set_controls_enabled(True)
        self.video_loaded.emit()

    def _on_pause_change(self, name: str, value) -> None:
        """Handle pause property change from mpv."""
        if value is not None:
            self._is_playing = not value
            # Update from main thread
            QTimer.singleShot(0, lambda: self._update_play_button())

    def _update_play_button(self) -> None:
        """Update play button icon based on playback state."""
        if self._is_playing:
            self._play_btn.setIcon(
                self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause)
            )
        else:
            self._play_btn.setIcon(
                self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
            )
        self.playback_state_changed.emit(self._is_playing)

    def _update_position(self) -> None:
        """Update position from mpv (called by timer)."""
        if not self._player:
            return

        try:
            pos = self._player.time_pos
            if pos is not None:
                self._position = float(pos)

                # Update slider if not being dragged
                if not self._position_slider.isSliderDown():
                    if self._duration > 0:
                        slider_pos = int((self._position / self._duration) * 1000)
                        self._position_slider.setValue(slider_pos)

                # Update time label
                self._update_time_label()

                # Emit position changed
                self.position_changed.emit(self._position)

        except Exception:
            pass  # Ignore errors during position updates

    def _update_time_label(self) -> None:
        """Update the time display label."""
        pos_str = self._format_time(self._position)
        dur_str = self._format_time(self._duration)
        self._time_label.setText(f"{pos_str} / {dur_str}")

    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to HH:MM:SS.mmm format."""
        if seconds < 0:
            seconds = 0

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        millis = int((secs % 1) * 1000)
        secs = int(secs)

        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def _on_slider_moved(self, value: int) -> None:
        """Handle slider drag."""
        if self._duration > 0:
            position = (value / 1000) * self._duration
            self._position = position
            self._update_time_label()

    def _on_slider_pressed(self) -> None:
        """Handle slider press - pause updates."""
        pass

    def _on_slider_released(self) -> None:
        """Handle slider release - seek to position."""
        if self._duration > 0:
            value = self._position_slider.value()
            position = (value / 1000) * self._duration
            self.seek(position)

    def _set_controls_enabled(self, enabled: bool) -> None:
        """Enable or disable playback controls."""
        self._play_btn.setEnabled(enabled)
        self._frame_back_btn.setEnabled(enabled)
        self._frame_forward_btn.setEnabled(enabled)
        self._position_slider.setEnabled(enabled)

    # ========== Public API ==========

    def load_video(self, path: str) -> bool:
        """
        Load a video file for preview.

        Args:
            path: Path to the video file

        Returns:
            True if loading started, False if not available
        """
        if not self._mpv_available or not self._player:
            logger.warning("mpv not available, cannot load video")
            return False

        try:
            self._video_path = path
            self._player.play(path)
            self._player.pause = True  # Start paused
            logger.info(f"Loading video: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load video: {e}")
            return False

    def unload_video(self) -> None:
        """Unload the current video."""
        if self._player:
            try:
                self._player.stop()
            except Exception:
                pass

        self._video_path = None
        self._duration = 0.0
        self._position = 0.0
        self._is_playing = False
        self._set_controls_enabled(False)
        self._time_label.setText("00:00:00.000 / 00:00:00.000")
        self._position_slider.setValue(0)

    def play(self) -> None:
        """Start playback."""
        if self._player:
            try:
                self._player.pause = False
            except Exception as e:
                logger.error(f"Failed to play: {e}")

    def pause(self) -> None:
        """Pause playback."""
        if self._player:
            try:
                self._player.pause = True
            except Exception as e:
                logger.error(f"Failed to pause: {e}")

    def toggle_playback(self) -> None:
        """Toggle between play and pause."""
        if self._is_playing:
            self.pause()
        else:
            self.play()

    def seek(self, position: float) -> None:
        """
        Seek to a specific position.

        Args:
            position: Position in seconds
        """
        if self._player:
            try:
                self._player.seek(position, "absolute")
            except Exception as e:
                logger.error(f"Failed to seek: {e}")

    def step_frame_forward(self) -> None:
        """Step forward one frame."""
        if self._player:
            try:
                self._player.frame_step()
            except Exception as e:
                logger.error(f"Failed to step frame: {e}")

    def step_frame_backward(self) -> None:
        """Step backward one frame."""
        if self._player:
            try:
                self._player.frame_back_step()
            except Exception as e:
                logger.error(f"Failed to step frame back: {e}")

    def get_position(self) -> float:
        """Get current playback position in seconds."""
        return self._position

    def get_duration(self) -> float:
        """Get video duration in seconds."""
        return self._duration

    def is_playing(self) -> bool:
        """Check if video is currently playing."""
        return self._is_playing

    def is_available(self) -> bool:
        """Check if video preview is available (mpv installed)."""
        return self._mpv_available

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._position_update_timer:
            self._position_update_timer.stop()

        if self._player:
            try:
                self._player.terminate()
            except Exception:
                pass
            self._player = None

    def closeEvent(self, event) -> None:
        """Handle close event."""
        self.cleanup()
        super().closeEvent(event)
