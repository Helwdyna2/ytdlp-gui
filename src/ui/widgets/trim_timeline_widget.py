"""Timeline widget for video trimming with range selection."""

import logging
from typing import Tuple, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QSizePolicy,
)

from ..theme.style_utils import set_status_color

logger = logging.getLogger(__name__)

# Try to import superqt for range slider, fall back to basic implementation
SUPERQT_AVAILABLE = False
try:
    from superqt import QLabeledDoubleRangeSlider

    SUPERQT_AVAILABLE = True
except ImportError:
    logger.warning("superqt not installed. Using basic range controls.")
except Exception as e:
    logger.warning(f"Failed to import superqt: {e}")


class TrimTimelineWidget(QWidget):
    """
    Timeline widget for selecting trim start and end points.

    Features:
    - Draggable range slider for selecting start/end points
    - Time display labels
    - Playhead position indicator
    - Click-to-seek functionality

    Signals:
        range_changed: Emits (start_time, end_time) when range changes
        seek_requested: Emits position when user clicks to seek
    """

    range_changed = pyqtSignal(float, float)  # start_time, end_time
    seek_requested = pyqtSignal(float)  # position in seconds

    def __init__(self, parent=None):
        """Initialize the timeline widget."""
        super().__init__(parent)

        self._duration: float = 0.0
        self._start_time: float = 0.0
        self._end_time: float = 0.0
        self._current_position: float = 0.0
        self._superqt_available = SUPERQT_AVAILABLE

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Time display row
        time_layout = QHBoxLayout()

        self._start_label = QLabel("Start: 00:00:00.000")
        self._start_label.setObjectName("boldLabel")
        time_layout.addWidget(self._start_label)

        time_layout.addStretch()

        self._trimmed_duration_label = QLabel("Trimmed: 00:00:00.000")
        set_status_color(self._trimmed_duration_label, "info")
        time_layout.addWidget(self._trimmed_duration_label)

        time_layout.addStretch()

        self._end_label = QLabel("End: 00:00:00.000")
        self._end_label.setObjectName("boldLabel")
        time_layout.addWidget(self._end_label)

        layout.addLayout(time_layout)

        # Range slider for trim selection
        if self._superqt_available:
            self._range_slider = QLabeledDoubleRangeSlider(Qt.Orientation.Horizontal)
            self._range_slider.setRange(0, 100)
            self._range_slider.setValue((0, 100))
            self._range_slider.setDecimals(3)
            # Hide the built-in labels since we show our own
            self._range_slider.setHandleLabelPosition(
                QLabeledDoubleRangeSlider.LabelPosition.NoLabel
            )
            layout.addWidget(self._range_slider)
        else:
            # Fallback: Two separate sliders for start and end
            range_container = QWidget()
            range_layout = QHBoxLayout(range_container)
            range_layout.setContentsMargins(0, 0, 0, 0)

            # Start slider
            start_container = QWidget()
            start_layout = QVBoxLayout(start_container)
            start_layout.setContentsMargins(0, 0, 0, 0)
            start_layout.addWidget(QLabel("Start:"))
            self._start_slider = QSlider(Qt.Orientation.Horizontal)
            self._start_slider.setRange(0, 1000)
            self._start_slider.setValue(0)
            start_layout.addWidget(self._start_slider)
            range_layout.addWidget(start_container)

            # End slider
            end_container = QWidget()
            end_layout = QVBoxLayout(end_container)
            end_layout.setContentsMargins(0, 0, 0, 0)
            end_layout.addWidget(QLabel("End:"))
            self._end_slider = QSlider(Qt.Orientation.Horizontal)
            self._end_slider.setRange(0, 1000)
            self._end_slider.setValue(1000)
            end_layout.addWidget(self._end_slider)
            range_layout.addWidget(end_container)

            layout.addWidget(range_container)

            # Placeholder for the range_slider attribute
            self._range_slider = None

        # Info label
        info_label = QLabel(
            "Drag the handles to set trim start and end points. "
            "Lossless mode cuts at keyframes (may vary slightly)."
        )
        info_label.setObjectName("dimLabel")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

    def _connect_signals(self) -> None:
        """Wire up signal connections."""
        if self._superqt_available and self._range_slider:
            self._range_slider.valuesChanged.connect(self._on_range_changed)
        else:
            self._start_slider.valueChanged.connect(self._on_fallback_start_changed)
            self._end_slider.valueChanged.connect(self._on_fallback_end_changed)

    def _on_range_changed(self, values: Tuple[float, float]) -> None:
        """Handle range slider value change (superqt version)."""
        self._start_time = values[0]
        self._end_time = values[1]
        self._update_labels()
        self.range_changed.emit(self._start_time, self._end_time)

    def _on_fallback_start_changed(self, value: int) -> None:
        """Handle start slider change (fallback version)."""
        if self._duration > 0:
            self._start_time = (value / 1000) * self._duration

            # Ensure start doesn't exceed end
            end_value = self._end_slider.value()
            if value >= end_value:
                self._start_slider.setValue(max(0, end_value - 1))
                return

            self._update_labels()
            self.range_changed.emit(self._start_time, self._end_time)

    def _on_fallback_end_changed(self, value: int) -> None:
        """Handle end slider change (fallback version)."""
        if self._duration > 0:
            self._end_time = (value / 1000) * self._duration

            # Ensure end doesn't go below start
            start_value = self._start_slider.value()
            if value <= start_value:
                self._end_slider.setValue(min(1000, start_value + 1))
                return

            self._update_labels()
            self.range_changed.emit(self._start_time, self._end_time)

    def _update_labels(self) -> None:
        """Update time display labels."""
        self._start_label.setText(f"Start: {self._format_time(self._start_time)}")
        self._end_label.setText(f"End: {self._format_time(self._end_time)}")

        trimmed_duration = max(0, self._end_time - self._start_time)
        self._trimmed_duration_label.setText(
            f"Trimmed: {self._format_time(trimmed_duration)}"
        )

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

    # ========== Public API ==========

    def set_duration(self, duration: float) -> None:
        """
        Set the video duration and initialize the range.

        Args:
            duration: Video duration in seconds
        """
        self._duration = duration
        self._start_time = 0.0
        self._end_time = duration

        if self._superqt_available and self._range_slider:
            self._range_slider.setRange(0, duration)
            self._range_slider.setValue((0, duration))
        else:
            self._start_slider.setValue(0)
            self._end_slider.setValue(1000)

        self._update_labels()

    def set_range(self, start: float, end: float) -> None:
        """
        Set the trim range.

        Args:
            start: Start time in seconds
            end: End time in seconds
        """
        self._start_time = max(0, min(start, self._duration))
        self._end_time = max(self._start_time, min(end, self._duration))

        if self._superqt_available and self._range_slider:
            self._range_slider.setValue((self._start_time, self._end_time))
        else:
            if self._duration > 0:
                start_val = int((self._start_time / self._duration) * 1000)
                end_val = int((self._end_time / self._duration) * 1000)
                self._start_slider.blockSignals(True)
                self._end_slider.blockSignals(True)
                self._start_slider.setValue(start_val)
                self._end_slider.setValue(end_val)
                self._start_slider.blockSignals(False)
                self._end_slider.blockSignals(False)

        self._update_labels()

    def get_range(self) -> Tuple[float, float]:
        """
        Get the current trim range.

        Returns:
            Tuple of (start_time, end_time) in seconds
        """
        return (self._start_time, self._end_time)

    def get_start_time(self) -> float:
        """Get the trim start time in seconds."""
        return self._start_time

    def get_end_time(self) -> float:
        """Get the trim end time in seconds."""
        return self._end_time

    def get_trimmed_duration(self) -> float:
        """Get the duration of the trimmed segment in seconds."""
        return max(0, self._end_time - self._start_time)

    def get_duration(self) -> float:
        """Get the total video duration."""
        return self._duration

    def set_current_position(self, position: float) -> None:
        """
        Set the current playback position (for visual feedback).

        Args:
            position: Current position in seconds
        """
        self._current_position = position
        # Could add a visual indicator here if desired

    def reset(self) -> None:
        """Reset the timeline to default state."""
        self._duration = 0.0
        self._start_time = 0.0
        self._end_time = 0.0
        self._current_position = 0.0

        if self._superqt_available and self._range_slider:
            self._range_slider.setRange(0, 100)
            self._range_slider.setValue((0, 100))
        else:
            self._start_slider.setValue(0)
            self._end_slider.setValue(1000)

        self._update_labels()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the timeline controls."""
        if self._superqt_available and self._range_slider:
            self._range_slider.setEnabled(enabled)
        else:
            self._start_slider.setEnabled(enabled)
            self._end_slider.setEnabled(enabled)
