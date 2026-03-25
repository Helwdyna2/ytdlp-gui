"""Extract URLs page — full-width layout for the redesigned UI."""

from typing import List, Optional, Set

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QCheckBox,
    QVBoxLayout,
    QWidget,
)

from ...core.extract_urls_manager import ExtractUrlsManager
from ...data.models import ExtractUrlsConfig
from ...services.config_service import ConfigService
from ..components.collapsible_section import CollapsibleSection
from ..components.page_header import PageHeader
from ..playwright_install_prompt import show_playwright_install_prompt
from ..widgets.url_input_widget import UrlInputWidget


class ExtractUrlsPage(QWidget):
    """Full-width page for extracting URLs from web pages."""

    extract_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(
        self,
        extract_manager: Optional[ExtractUrlsManager] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._config = ConfigService()
        self._manager = extract_manager if extract_manager is not None else ExtractUrlsManager(self)
        self._current_urls: List[str] = []
        self._found_urls: Set[str] = set()
        self._extract_in_progress = False

        self._setup_ui()
        self._connect_signals()
        self._load_settings()
        self._update_controls()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Build the page layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # 1. Page header
        header = PageHeader(
            title="Extract URLs",
            description="Extract links from web pages.",
        )
        main_layout.addWidget(header)

        # 2. URL input area
        url_label = QLabel("Page URLs")
        url_label.setObjectName("sectionLabel")
        main_layout.addWidget(url_label)

        self.url_input_widget = UrlInputWidget()
        main_layout.addWidget(self.url_input_widget)

        # 3. Options (collapsible)
        scroll_section = CollapsibleSection("Auto-Scroll Options", expanded=False)
        options_layout = QFormLayout()

        self.auto_scroll_checkbox = QCheckBox("Enable auto-scroll")
        options_layout.addRow(self.auto_scroll_checkbox)

        self.max_scrolls_spin = QSpinBox()
        self.max_scrolls_spin.setRange(0, 10000)
        self.max_scrolls_spin.setSingleStep(10)
        options_layout.addRow("Max scrolls:", self.max_scrolls_spin)

        self.idle_limit_spin = QSpinBox()
        self.idle_limit_spin.setRange(0, 50)
        options_layout.addRow("Idle limit:", self.idle_limit_spin)

        self.delay_ms_spin = QSpinBox()
        self.delay_ms_spin.setRange(100, 10000)
        self.delay_ms_spin.setSingleStep(100)
        options_layout.addRow("Delay (ms):", self.delay_ms_spin)

        self.bounce_spin = QSpinBox()
        self.bounce_spin.setRange(0, 20)
        options_layout.addRow("Bounce attempts:", self.bounce_spin)

        scroll_section.content_layout.addLayout(options_layout)
        main_layout.addWidget(scroll_section)

        # 4. Output folder
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output folder:"))
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setReadOnly(True)
        output_layout.addWidget(self.output_dir_input, 1)
        self._browse_btn = QPushButton("Browse")
        self._browse_btn.setObjectName("btnSecondary")
        self._browse_btn.clicked.connect(self._browse_output_dir)
        output_layout.addWidget(self._browse_btn)
        main_layout.addLayout(output_layout)

        # Auth note
        auth_note = QLabel(
            "Sign in using the Download tab first to access private content."
        )
        auth_note.setWordWrap(True)
        auth_note.setObjectName("dimLabel")
        main_layout.addWidget(auth_note)

        # 5. Status label
        self.status_label = QLabel("Ready to extract.")
        self.status_label.setWordWrap(True)
        main_layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%v / %m URLs")
        main_layout.addWidget(self.progress_bar)

        # 7. Results area
        self.results_label = QLabel("No links found yet.")
        self.results_label.setObjectName("resultsLabel")
        self.results_label.setWordWrap(True)
        main_layout.addWidget(self.results_label)

        main_layout.addStretch()

        # 6. Action bar
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("btnSecondary")
        self.stop_button.setEnabled(False)
        action_layout.addWidget(self.stop_button)
        self.extract_button = QPushButton("Extract")
        self.extract_button.setObjectName("btnPrimary")
        action_layout.addWidget(self.extract_button)
        main_layout.addLayout(action_layout)

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        """Connect signals and slots."""
        self.url_input_widget.urls_changed.connect(self._on_urls_changed)
        self.extract_button.clicked.connect(self._on_extract_clicked)
        self.stop_button.clicked.connect(self._on_stop_clicked)

        self.auto_scroll_checkbox.stateChanged.connect(self._save_settings)
        self.max_scrolls_spin.valueChanged.connect(self._save_settings)
        self.idle_limit_spin.valueChanged.connect(self._save_settings)
        self.delay_ms_spin.valueChanged.connect(self._save_settings)
        self.bounce_spin.valueChanged.connect(self._save_settings)

        self._manager.extract_started.connect(self._on_extract_started)
        self._manager.extract_progress.connect(self._on_extract_progress)
        self._manager.extract_result.connect(self._on_extract_result)
        self._manager.extract_completed.connect(self._on_extract_completed)
        self._manager.error.connect(self._on_error)

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _load_settings(self) -> None:
        """Load settings from ConfigService."""
        section = self._config.get_section("extract_urls")
        config = self._manager.get_config()

        self.output_dir_input.setText(section.get("output_dir", config.output_dir))
        self.auto_scroll_checkbox.setChecked(
            section.get("auto_scroll_enabled", config.auto_scroll_enabled)
        )
        self.max_scrolls_spin.setValue(section.get("max_scrolls", config.max_scrolls))
        self.idle_limit_spin.setValue(section.get("idle_limit", config.idle_limit))
        self.delay_ms_spin.setValue(section.get("delay_ms", config.delay_ms))
        self.bounce_spin.setValue(
            section.get("max_bounce_attempts", config.max_bounce_attempts)
        )

    def _save_settings(self) -> None:
        """Save settings to ConfigService."""
        section = self._config.get_section("extract_urls") or {}
        section.update(
            {
                "output_dir": self.output_dir_input.text(),
                "auto_scroll_enabled": self.auto_scroll_checkbox.isChecked(),
                "max_scrolls": self.max_scrolls_spin.value(),
                "idle_limit": self.idle_limit_spin.value(),
                "delay_ms": self.delay_ms_spin.value(),
                "max_bounce_attempts": self.bounce_spin.value(),
            }
        )
        self._config.set_section("extract_urls", section, save=False)
        self._config.queue_save()

    # ------------------------------------------------------------------
    # Slot handlers
    # ------------------------------------------------------------------

    def _browse_output_dir(self) -> None:
        """Open a directory picker for the output folder."""
        current = self.output_dir_input.text()
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", current
        )
        if dir_path:
            self.output_dir_input.setText(dir_path)
            self._save_settings()

    def _on_urls_changed(self, urls: List[str]) -> None:
        self._current_urls = urls
        self._update_controls()

    def _on_extract_clicked(self) -> None:
        """Start extraction."""
        if not self._current_urls:
            QMessageBox.information(self, "No URLs", "Please add URLs to extract from.")
            return

        config = self._build_config()
        self._found_urls.clear()
        self.results_label.setText("No links found yet.")
        self.status_label.setText("Starting extraction...")
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(self._current_urls))

        self._extract_in_progress = True
        self._update_controls()
        self._manager.start_extract(self._current_urls, config)
        self.extract_requested.emit()

    def _on_stop_clicked(self) -> None:
        """Stop extraction."""
        self.status_label.setText("Stopping...")
        self._manager.stop()
        self.stop_requested.emit()

    def _on_extract_started(self, total: int) -> None:
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(0)
        self.status_label.setText("Extraction started...")

    def _on_extract_progress(self, index: int, total: int, message: str) -> None:
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(index)
        self.status_label.setText(message)

    def _on_extract_result(self, index: int, new_urls: List[str]) -> None:
        if new_urls:
            self._found_urls.update(new_urls)
        count = len(self._found_urls)
        if count == 0:
            self.results_label.setText("No links found yet.")
        else:
            self.results_label.setText(f"Found: {count} links")

    def _on_extract_completed(self, count: int, output_path: str) -> None:
        self._extract_in_progress = False
        self.status_label.setText(f"Completed. Saved {count} URLs.")
        self._update_controls()
        QMessageBox.information(
            self,
            "Extraction Complete",
            f"Saved {count} URLs to:\n{output_path}",
        )

    def _on_error(self, message: str) -> None:
        self._extract_in_progress = False
        self.status_label.setText(message)
        show_playwright_install_prompt(self, message, None, title="Error")
        self._update_controls()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_config(self) -> ExtractUrlsConfig:
        """Build ExtractUrlsConfig from current UI settings."""
        base = self._manager.get_config()
        return ExtractUrlsConfig(
            output_dir=self.output_dir_input.text() or base.output_dir,
            profile_dir=base.profile_dir,
            auto_scroll_enabled=self.auto_scroll_checkbox.isChecked(),
            max_scrolls=self.max_scrolls_spin.value(),
            idle_limit=self.idle_limit_spin.value(),
            delay_ms=self.delay_ms_spin.value(),
            max_bounce_attempts=self.bounce_spin.value(),
        )

    def _update_controls(self) -> None:
        """Enable/disable controls based on current state."""
        input_enabled = not self._extract_in_progress
        self.url_input_widget.set_enabled(input_enabled)
        self.extract_button.setEnabled(
            bool(self._current_urls) and not self._extract_in_progress
        )
        self.stop_button.setEnabled(self._extract_in_progress)
