"""AddUrlsPage — landing screen for adding URLs and starting downloads."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..components.config_bar import ConfigBar
from ..components.page_header import PageHeader


class AddUrlsPage(QWidget):
    """Landing screen for pasting URLs, configuring output, and starting downloads."""

    start_download = pyqtSignal()
    cancel_download = pyqtSignal()
    load_from_file = pyqtSignal()
    clear_urls = pyqtSignal()

    def __init__(
        self,
        url_input=None,
        auth_status=None,
        output_config=None,
        queue_progress=None,
        progress=None,
        download_log=None,
        parent=None,
    ):
        super().__init__(parent)

        self._url_input = url_input
        self._auth_status = auth_status
        self._output_config = output_config
        self._queue_progress = queue_progress
        self._progress = progress
        self._download_log = download_log

        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # 1. Page header with right-side stats
        self._header = PageHeader(
            title="Add URLs",
            description="Paste video links, sign in if needed, then download.",
        )
        self._header.add_stat("Queued", "0")
        self._header.add_stat("Active", "0")
        self._header.add_stat("Done", "0")
        self._header.add_stat("Elapsed", "0:00")
        root.addWidget(self._header)

        # 2. URL input — fills available vertical space
        if self._url_input is not None:
            root.addWidget(self._url_input, stretch=1)

        # 3. Status row: count label + Clear button
        status_row = QHBoxLayout()
        self._status_label = QLabel("No links added yet")
        status_row.addWidget(self._status_label)
        status_row.addStretch()
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setObjectName("btnDestructive")
        self._clear_btn.clicked.connect(self.clear_urls)
        status_row.addWidget(self._clear_btn)
        root.addLayout(status_row)

        # 4. ConfigBar: output config widget + concurrent spinbox + format label
        self._config_bar = ConfigBar()
        if self._output_config is not None:
            self._config_bar.add_field("Output", self._output_config)
            self._config_bar.add_separator()
        self._concurrent_spinbox = QSpinBox()
        self._concurrent_spinbox.setRange(1, 10)
        self._concurrent_spinbox.setValue(3)
        self._config_bar.add_field("Concurrent", self._concurrent_spinbox)
        self._config_bar.add_separator()
        self._format_label = QLabel("Best available")
        self._config_bar.add_field("Format", self._format_label)
        self._config_bar.add_stretch()
        root.addWidget(self._config_bar)

        # 5. Auth status widget
        if self._auth_status is not None:
            root.addWidget(self._auth_status)

        # 6. Action bar
        action_row = QHBoxLayout()
        self._load_file_btn = QPushButton("Load from file...")
        self._load_file_btn.clicked.connect(self.load_from_file)
        action_row.addWidget(self._load_file_btn)
        action_row.addStretch()
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("btnSecondary")
        self._cancel_btn.clicked.connect(self.cancel_download)
        action_row.addWidget(self._cancel_btn)
        self._start_btn = QPushButton("Start Download")
        self._start_btn.setObjectName("btnPrimary")
        self._start_btn.clicked.connect(self.start_download)
        action_row.addWidget(self._start_btn)
        root.addLayout(action_row)

        # 7. Progress section (hidden initially)
        self._progress_section = QWidget()
        progress_layout = QVBoxLayout(self._progress_section)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)
        if self._queue_progress is not None:
            progress_layout.addWidget(self._queue_progress)
        if self._progress is not None:
            progress_layout.addWidget(self._progress)
        if self._download_log is not None:
            progress_layout.addWidget(self._download_log)
        self._progress_section.setVisible(False)
        root.addWidget(self._progress_section)

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------

    def set_queue_stats(
        self, queued: int, active: int, done: int, elapsed: str
    ) -> None:
        """Update the PageHeader stats area."""
        self._header.update_stat("Queued", str(queued))
        self._header.update_stat("Active", str(active))
        self._header.update_stat("Done", str(done))
        self._header.update_stat("Elapsed", elapsed)

    def set_download_mode(self, active: bool) -> None:
        """Show/hide progress section and toggle action button states."""
        self._progress_section.setVisible(active)
        self._start_btn.setEnabled(not active)
        self._cancel_btn.setEnabled(active)
        if self._output_config is not None:
            self._output_config.setEnabled(not active)
        if self._url_input is not None:
            self._url_input.setEnabled(not active)
