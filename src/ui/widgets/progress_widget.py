"""Progress display widgets for individual downloads."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QLabel,
    QProgressBar,
    QFrame,
    QSizePolicy,
    QCheckBox,
)
from PyQt6.QtCore import Qt
from typing import Dict

from ...utils.formatters import format_size, format_speed, format_eta, truncate_string
from ...services.config_service import ConfigService
from ..theme.style_utils import set_status_color


class DownloadProgressItem(QFrame):
    """Single download progress display."""

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url
        self._title = url
        self._status = (
            "starting"  # starting, downloading, finished, completed, failed, cancelled
        )
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Title row
        title_layout = QHBoxLayout()

        self.title_label = QLabel(truncate_string(self.url, 70))
        self.title_label.setObjectName("boldLabel")
        self.title_label.setToolTip(self.url)
        self.title_label.setAccessibleName("Download Title")
        self.title_label.setAccessibleDescription(f"Download: {self.url}")
        title_layout.addWidget(self.title_label, stretch=1)

        self.status_label = QLabel("Starting...")
        self.status_label.setProperty("dataColor", "dim")
        self.status_label.setAccessibleName("Download Status")
        self.status_label.setAccessibleDescription("Download status: Starting")
        title_layout.addWidget(self.status_label)

        layout.addLayout(title_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setAccessibleName("Download Progress")
        self.progress_bar.setAccessibleDescription("Download progress: 0%")
        layout.addWidget(self.progress_bar)

        # Stats row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        self.size_label = QLabel("0 B / 0 B")
        self.size_label.setAccessibleName("Download Size")
        self.size_label.setAccessibleDescription("Downloaded size: 0 B of 0 B")
        stats_layout.addWidget(self.size_label)

        stats_layout.addStretch()

        self.speed_label = QLabel("-- /s")
        self.speed_label.setMinimumWidth(80)
        self.speed_label.setAccessibleName("Download Speed")
        self.speed_label.setAccessibleDescription("Current download speed")
        stats_layout.addWidget(self.speed_label)

        self.eta_label = QLabel("ETA: --:--")
        self.eta_label.setMinimumWidth(80)
        self.eta_label.setAccessibleName("Estimated Time")
        self.eta_label.setAccessibleDescription("Estimated time remaining for download")
        stats_layout.addWidget(self.eta_label)

        layout.addLayout(stats_layout)

    def get_status(self) -> str:
        """Get the current status of this download."""
        return self._status

    def set_cancelling(self):
        """Mark as being cancelled - shows immediate feedback."""
        self._status = "cancelling"
        self.status_label.setText("Cancelling...")
        set_status_color(self.status_label, "warning")
        self.status_label.setAccessibleDescription(
            f"Cancelling download: {self._title}"
        )
        # Set progress bar to indeterminate mode
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setAccessibleDescription("Download is being cancelled")
        # Clear speed and ETA
        self.speed_label.setText("-- /s")
        self.eta_label.setText("Stopping...")

    def update_progress(self, progress: dict):
        """Update with progress data from worker."""
        status = progress.get("status", "downloading")

        if status == "downloading":
            self._status = "downloading"
            percent = int(progress.get("percent", 0))
            self.progress_bar.setValue(percent)
            self.progress_bar.setAccessibleDescription(f"Download progress: {percent}%")

            downloaded = progress.get("downloaded", 0)
            total = progress.get("total", 0)
            self.size_label.setText(f"{format_size(downloaded)} / {format_size(total)}")

            speed = progress.get("speed", 0)
            self.speed_label.setText(format_speed(speed))

            eta = progress.get("eta", 0)
            self.eta_label.setText(f"ETA: {format_eta(eta)}")

            self.status_label.setText("Downloading")
            set_status_color(self.status_label, "info")
            self.status_label.setAccessibleDescription(
                f"Downloading: {percent}% at {format_speed(speed)}"
            )

        elif status == "finished":
            self._status = "finished"
            self.progress_bar.setValue(100)
            self.progress_bar.setAccessibleDescription("Download progress: 100%")
            self.status_label.setText("Processing...")
            set_status_color(self.status_label, "warning")
            self.status_label.setAccessibleDescription(
                "Download status: Processing downloaded file"
            )
            self.speed_label.setText("-- /s")
            self.eta_label.setText("ETA: --:--")

    def set_title(self, title: str):
        """Update the display title."""
        self._title = title
        self.title_label.setText(truncate_string(title, 70))
        self.title_label.setToolTip(title)
        self.title_label.setAccessibleDescription(f"Download: {title}")

    def set_completed(self, success: bool, message: str = "", cancelled: bool = False):
        """Mark as completed.

        Args:
            success: Whether the download succeeded.
            message: Error or status message.
            cancelled: Whether the download was cancelled (overrides failed state).
        """
        if success:
            self._status = "completed"
            self.status_label.setText("Completed")
            set_status_color(self.status_label, "success")
            self.status_label.setAccessibleDescription(
                f"Download completed successfully: {self._title}"
            )
            self.progress_bar.setValue(100)
            self.progress_bar.setAccessibleDescription(
                "Download progress: 100%, completed"
            )
        elif cancelled:
            self._status = "cancelled"
            self.status_label.setText("Cancelled")
            set_status_color(self.status_label, "warning")
            self.status_label.setAccessibleDescription(
                f"Download cancelled: {self._title}"
            )
        else:
            self._status = "failed"
            self.status_label.setText("Failed")
            set_status_color(self.status_label, "error")
            self.status_label.setAccessibleDescription(
                f"Download failed: {self._title}. {message}"
                if message
                else f"Download failed: {self._title}"
            )
            if message:
                self.title_label.setToolTip(f"{self._title}\n\nError: {message}")

        self.speed_label.setText("-- /s")
        self.eta_label.setText("")


class ProgressWidget(QWidget):
    """Container for all active download progress items."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: Dict[str, DownloadProgressItem] = {}
        self._config = ConfigService()
        self._hide_completed = False
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Controls row with "Hide completed" checkbox
        controls_layout = QHBoxLayout()

        self.hide_completed_cb = QCheckBox("Hide completed")
        self.hide_completed_cb.setChecked(False)
        self.hide_completed_cb.setAccessibleName("Hide Completed Downloads")
        self.hide_completed_cb.setAccessibleDescription(
            "Toggle visibility of completed and cancelled downloads"
        )
        self.hide_completed_cb.toggled.connect(self._on_hide_completed_toggled)
        controls_layout.addWidget(self.hide_completed_cb)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Scroll area for progress items
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll_area.setAccessibleName("Active Downloads")
        self.scroll_area.setAccessibleDescription(
            "Scrollable list of active download progress items"
        )

        # Container widget inside scroll area
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(4)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Placeholder label
        self.placeholder = QLabel("No active downloads")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setObjectName("dimLabel")
        self.container_layout.addWidget(self.placeholder)

        self.scroll_area.setWidget(self.container)
        layout.addWidget(self.scroll_area)

    def _load_settings(self) -> None:
        """Load saved settings."""
        hide_completed = self._config.get("behavior.hide_completed_downloads", False)
        self.hide_completed_cb.setChecked(hide_completed)
        self._hide_completed = hide_completed

    def _save_settings(self) -> None:
        """Save current settings."""
        self._config.set(
            "behavior.hide_completed_downloads", self.hide_completed_cb.isChecked()
        )

    def _on_hide_completed_toggled(self, hide: bool):
        """Handle hide completed checkbox toggle.

        Args:
            hide: Whether to hide completed/cancelled downloads.
        """
        self._hide_completed = hide
        self._save_settings()

        for item in self._items.values():
            self._update_item_visibility(item)

    def _update_item_visibility(self, item: DownloadProgressItem):
        """Update visibility of a single item based on its status and hide setting.

        Args:
            item: The download progress item to update.
        """
        status = item.get_status()

        # Hide completed and cancelled items when toggle is on
        # Failed items are always visible (they need attention)
        if self._hide_completed and status in ("completed", "cancelled"):
            item.hide()
        else:
            item.show()

    def add_download(self, url: str):
        """Add a new download progress item."""
        if url in self._items:
            return

        # Hide placeholder
        self.placeholder.hide()

        item = DownloadProgressItem(url)
        self._items[url] = item
        self.container_layout.addWidget(item)

    def update_progress(self, url: str, progress: dict):
        """Update progress for a download."""
        if url in self._items:
            self._items[url].update_progress(progress)

    def set_title(self, url: str, title: str):
        """Update title for a download."""
        if url in self._items:
            self._items[url].set_title(title)

    def set_cancelling(self, url: str):
        """Mark a download as being cancelled - shows immediate feedback."""
        if url in self._items:
            item = self._items[url]
            item.set_cancelling()

    def set_completed(
        self, url: str, success: bool, message: str = "", cancelled: bool = False
    ):
        """Mark a download as completed."""
        if url in self._items:
            item = self._items[url]
            item.set_completed(success, message, cancelled)

            # Check if we should hide this item
            self._update_item_visibility(item)

    def remove_download(self, url: str):
        """Remove a download item."""
        if url in self._items:
            item = self._items.pop(url)
            item.deleteLater()

        # Show placeholder if empty
        if not self._items:
            self.placeholder.show()

    def clear_completed(self) -> int:
        """Clear all completed downloads. Returns count cleared."""
        cleared = 0
        to_remove = []

        for url, item in list(self._items.items()):
            if item.status_label.text() in ("Completed", "Failed", "Cancelled"):
                to_remove.append(url)

        for url in to_remove:
            self.remove_download(url)
            cleared += 1

        return cleared

    def get_active_urls(self) -> list:
        """Get list of URLs that are still active (not completed)."""
        active = []
        for url, item in self._items.items():
            status = item.status_label.text()
            if status not in ("Completed", "Failed", "Cancelled"):
                active.append(url)
        return active

    def has_active_downloads(self) -> bool:
        """Check if there are any active downloads."""
        return len(self.get_active_urls()) > 0
