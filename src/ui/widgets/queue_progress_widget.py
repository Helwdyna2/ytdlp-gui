"""Overall queue progress display widget."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QProgressBar,
    QLabel,
    QPushButton,
)
from PyQt6.QtCore import pyqtSignal, QTimer

from ...utils.formatters import format_speed
from ..theme.style_utils import set_status_color


class QueueProgressWidget(QWidget):
    """
    Overall queue progress display.

    Shows completed/total count, aggregate speed, and overall progress bar.
    Includes Start and Cancel buttons.
    """

    start_clicked = pyqtSignal()
    cancel_clicked = pyqtSignal()
    clear_history_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._total = 0
        self._completed = 0
        self._failed = 0
        self._cancelled = 0
        self._is_running = False
        self._is_cancelling = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Progress bar
        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setRange(0, 100)
        self.overall_progress_bar.setValue(0)
        self.overall_progress_bar.setTextVisible(True)
        self.overall_progress_bar.setFormat("Ready")
        self.overall_progress_bar.setMinimumHeight(24)
        self.overall_progress_bar.setAccessibleName("Queue Progress")
        self.overall_progress_bar.setAccessibleDescription(
            "Overall download queue progress percentage"
        )
        layout.addWidget(self.overall_progress_bar)

        # Stats row
        stats_layout = QHBoxLayout()

        self.completed_label = QLabel("0 / 0")
        self.completed_label.setObjectName("boldLabel")
        self.completed_label.setAccessibleName("Completed Downloads")
        self.completed_label.setAccessibleDescription(
            "Number of completed downloads out of total"
        )
        stats_layout.addWidget(self.completed_label)

        self.status_label = QLabel("Ready")
        set_status_color(self.status_label, "muted")
        self.status_label.setAccessibleName("Queue Status")
        self.status_label.setAccessibleDescription("Current download queue status")
        stats_layout.addWidget(self.status_label)

        stats_layout.addStretch()

        self.speed_label = QLabel("")
        self.speed_label.setMinimumWidth(100)
        self.speed_label.setAccessibleName("Download Speed")
        self.speed_label.setAccessibleDescription(
            "Aggregate download speed for all active downloads"
        )
        stats_layout.addWidget(self.speed_label)

        layout.addLayout(stats_layout)

        # Buttons row
        btn_layout = QHBoxLayout()

        self.clear_history_btn = QPushButton("Clear &History")
        self.clear_history_btn.setObjectName("btnWire")
        self.clear_history_btn.setProperty("button_role", "secondary")
        self.clear_history_btn.setToolTip("Clear download history database")
        self.clear_history_btn.setAccessibleName("Clear History")
        self.clear_history_btn.setAccessibleDescription(
            "Clear the download history database"
        )
        self.clear_history_btn.clicked.connect(self.clear_history_clicked.emit)
        btn_layout.addWidget(self.clear_history_btn)

        btn_layout.addStretch()

        self.cancel_btn = QPushButton("&Cancel")
        self.cancel_btn.setObjectName("btnWire")
        self.cancel_btn.setProperty("button_role", "secondary")
        self.cancel_btn.setAccessibleName("Cancel Downloads")
        self.cancel_btn.setAccessibleDescription(
            "Cancel all active downloads in the queue"
        )
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setMinimumWidth(100)
        btn_layout.addWidget(self.cancel_btn)

        self.start_btn = QPushButton("&Start Download")
        self.start_btn.setObjectName("btnCyan")
        self.start_btn.setProperty("button_role", "primary")
        self.start_btn.setAccessibleName("Start Download")
        self.start_btn.setAccessibleDescription("Start downloading all queued URLs")
        self.start_btn.clicked.connect(self._on_start)
        self.start_btn.setMinimumWidth(120)
        btn_layout.addWidget(self.start_btn)

        layout.addLayout(btn_layout)

    def _on_start(self):
        """Handle start button click."""
        self.start_clicked.emit()

    def _on_cancel(self):
        """Handle cancel button click with immediate visual feedback."""
        # Immediate visual feedback - disable button and change text
        self._is_cancelling = True
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("Cancelling...")
        self.status_label.setText("Cancelling...")
        set_status_color(self.status_label, "warning")
        self.status_label.setAccessibleDescription("Cancelling downloads...")

        # Set progress bar to indeterminate mode to show activity
        self.overall_progress_bar.setRange(0, 0)
        self.overall_progress_bar.setAccessibleDescription(
            "Cancelling downloads - please wait"
        )

        # Clear speed label during cancellation
        self.speed_label.setText("")

        # Emit the signal after UI updates
        self.cancel_clicked.emit()

    def on_cancel_complete(self):
        """Called when cancellation is complete to reset UI state."""
        self._is_cancelling = False
        self.cancel_btn.setText("&Cancel")
        self.cancel_btn.setEnabled(False)  # Will be re-enabled when new downloads start
        self.status_label.setText("Cancelled")
        set_status_color(self.status_label, "warning")
        self.status_label.setAccessibleDescription("Downloads cancelled")

        # Reset progress bar to normal mode
        self.overall_progress_bar.setRange(0, 100)
        self.overall_progress_bar.setValue(0)
        self.overall_progress_bar.setFormat("Ready")

    def set_running(self, running: bool):
        """Set running state."""
        self._is_running = running
        self.start_btn.setEnabled(not running)

        # Only enable cancel button if not currently cancelling
        if not self._is_cancelling:
            self.cancel_btn.setEnabled(running)
            self.cancel_btn.setText("&Cancel")

        self.clear_history_btn.setEnabled(not running)

        if running:
            self.status_label.setText("Downloading...")
            set_status_color(self.status_label, "info")
            self.status_label.setAccessibleDescription("Downloading in progress")
            # Reset progress bar to normal mode if it was in indeterminate mode
            if self.overall_progress_bar.maximum() == 0:
                self.overall_progress_bar.setRange(0, 100)
        else:
            parts = []
            if self._failed > 0:
                parts.append(f"{self._failed} failed")
            if self._cancelled > 0:
                parts.append(f"{self._cancelled} cancelled")

            if parts:
                self.status_label.setText(f"Completed ({', '.join(parts)})")
                set_status_color(self.status_label, "warning")
            elif self._completed > 0:
                self.status_label.setText("Completed")
                set_status_color(self.status_label, "success")
            else:
                self.status_label.setText("Ready")
                set_status_color(self.status_label, "muted")

            # Reset cancelling state when no longer running
            self._is_cancelling = False
            self.cancel_btn.setText("&Cancel")

    def update_progress(self, completed: int, failed: int, cancelled: int, total: int):
        """Update queue progress.

        Args:
            completed: Number of successfully completed downloads.
            failed: Number of failed downloads.
            cancelled: Number of cancelled downloads.
            total: Total number of downloads in the queue.
        """
        self._completed = completed
        self._failed = failed
        self._cancelled = cancelled
        self._total = total

        # Update labels
        self.completed_label.setText(f"{completed} / {total}")
        self.completed_label.setAccessibleDescription(
            f"{completed} of {total} downloads completed"
        )

        # Update progress bar - all terminal states count toward completion
        if total > 0:
            done = completed + failed + cancelled
            percent = int(done / total * 100)
            self.overall_progress_bar.setValue(percent)
            self.overall_progress_bar.setFormat(f"{percent}% ({done}/{total})")
            self.overall_progress_bar.setAccessibleDescription(
                f"Queue progress: {percent}%, {done} of {total} done"
            )
        else:
            self.overall_progress_bar.setValue(0)
            self.overall_progress_bar.setFormat("Ready")
            self.overall_progress_bar.setAccessibleDescription(
                "Queue progress: Ready, no downloads queued"
            )

    def update_speed(self, bytes_per_sec: float):
        """Update aggregate download speed."""
        if bytes_per_sec > 0 and not self._is_cancelling:
            self.speed_label.setText(f"Total: {format_speed(bytes_per_sec)}")
        else:
            self.speed_label.setText("")

    def set_url_count(self, count: int):
        """Set the URL count for display (called before downloads start)."""
        # This method exists for API compatibility but the actual tracking
        # is handled via update_progress which receives the total count.
        pass

    def reset(self):
        """Reset to initial state."""
        self._total = 0
        self._completed = 0
        self._failed = 0
        self._cancelled = 0
        self._is_running = False
        self._is_cancelling = False
        self.overall_progress_bar.setValue(0)
        self.overall_progress_bar.setFormat("Ready")
        self.overall_progress_bar.setRange(0, 100)
        self.completed_label.setText("0 / 0")
        self.status_label.setText("Ready")
        set_status_color(self.status_label, "muted")
        self.speed_label.setText("")
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("&Cancel")
        self.clear_history_btn.setEnabled(True)
