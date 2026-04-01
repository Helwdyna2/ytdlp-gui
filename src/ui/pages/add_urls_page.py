"""AddUrlsPage — Digital Obsidian bento layout for adding URLs and starting downloads."""

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..components.collapsible_section import CollapsibleSection
from ..components.data_panel import DataPanel
from ..components.page_header import PageHeader
from ..components.split_layout import SplitLayout


class AddUrlsPage(QWidget):
    """Bento-grid landing screen for pasting URLs, configuring output, and downloading."""

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
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # 1. Page header with stat cards
        self._header = PageHeader(
            title="Add URLs",
            description="Paste video links, sign in if needed, then download.",
        )
        self._header.add_stat("Queued", "0")
        self._header.add_stat("Active", "0")
        self._header.add_stat("Elapsed", "0:00")
        root.addWidget(self._header)

        # 2. Bento split: left URL panel (8/12) + right config (4/12)
        self._split = SplitLayout(right_width=340, gap=20)

        # -- Left panel: URL input --
        left_layout = QVBoxLayout(self._split.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        url_panel = DataPanel("URL Input")
        if self._url_input is not None:
            url_panel.body_layout.addWidget(self._url_input)

        # Status row inside the URL panel
        status_row = QHBoxLayout()
        self._status_label = QLabel("No links added yet")
        self._status_label.setObjectName("dimLabel")
        status_row.addWidget(self._status_label)
        status_row.addStretch()
        self._load_file_btn = QPushButton("Load from file…")
        self._load_file_btn.setProperty("button_role", "secondary")
        self._load_file_btn.clicked.connect(self.load_from_file)
        status_row.addWidget(self._load_file_btn)
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setProperty("button_role", "destructive")
        self._clear_btn.clicked.connect(self.clear_urls)
        status_row.addWidget(self._clear_btn)
        url_panel.body_layout.addLayout(status_row)

        left_layout.addWidget(url_panel, stretch=1)

        # -- Right panel: destination + parameters + CTA --
        right_layout = QVBoxLayout(self._split.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # Destination panel
        if self._output_config is not None:
            dest_panel = DataPanel("Destination")
            dest_panel.body_layout.addWidget(self._output_config)
            right_layout.addWidget(dest_panel)

        # Parameters panel
        params_panel = DataPanel("Parameters")
        params_layout = params_panel.body_layout

        # Concurrent tasks
        concurrent_row = QHBoxLayout()
        concurrent_label = QLabel("CONCURRENT TASKS")
        concurrent_label.setObjectName("configLabel")
        concurrent_row.addWidget(concurrent_label)
        concurrent_row.addStretch()
        self._concurrent_spinbox = QSpinBox()
        self._concurrent_spinbox.setRange(1, 10)
        self._concurrent_spinbox.setValue(3)
        self._concurrent_spinbox.setFixedWidth(60)
        concurrent_row.addWidget(self._concurrent_spinbox)
        params_layout.addLayout(concurrent_row)

        # Format
        format_row = QHBoxLayout()
        format_label = QLabel("FORMAT")
        format_label.setObjectName("configLabel")
        format_row.addWidget(format_label)
        format_row.addStretch()
        self._format_label = QLabel("Best available")
        format_row.addWidget(self._format_label)
        params_layout.addLayout(format_row)

        right_layout.addWidget(params_panel)

        # Auth status (collapsible)
        if self._auth_status is not None:
            auth_section = CollapsibleSection("Authentication", expanded=False)
            auth_section.content_layout.addWidget(self._auth_status)
            right_layout.addWidget(auth_section)

        right_layout.addStretch()

        # CTA button
        self._start_btn = QPushButton("INGEST BATCH")
        self._start_btn.setProperty("button_role", "cta")
        self._start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_btn.clicked.connect(self.start_download)
        right_layout.addWidget(self._start_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setProperty("button_role", "secondary")
        self._cancel_btn.clicked.connect(self.cancel_download)
        self._cancel_btn.setEnabled(False)
        right_layout.addWidget(self._cancel_btn)

        root.addWidget(self._split, stretch=1)

        # 3. Progress section (hidden initially, shown below split during downloads)
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
        self, queued: int, active: int, elapsed: str
    ) -> None:
        """Update the PageHeader stats area."""
        self._header.update_stat("Queued", str(queued))
        self._header.update_stat("Active", str(active))
        self._header.update_stat("Elapsed", elapsed)

    def set_download_mode(self, active: bool) -> None:
        """Show/hide progress section and toggle action button states."""
        self._progress_section.setVisible(active)
        self._start_btn.setEnabled(not active)
        self._cancel_btn.setEnabled(active)
        if self._output_config is not None:
            self._output_config.setEnabled(not active)
        if self._url_input is not None:
            self._url_input.setVisible(not active)
