"""SettingsPage — full-width settings with collapsible sections."""

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QKeySequenceEdit,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...core.auth_manager import AuthManager
from ...services.config_service import ConfigService
from ..components.collapsible_section import CollapsibleSection
from ..components.page_header import PageHeader
from ..playwright_install_prompt import show_playwright_browser_install_dialog
from ..theme.theme_engine import ThemeEngine

logger = logging.getLogger(__name__)


class SettingsPage(QWidget):
    """Settings page with collapsible sections for all app-wide preferences."""

    def __init__(
        self,
        config_service: Optional[ConfigService] = None,
        theme_engine: Optional[ThemeEngine] = None,
        auth_manager: Optional[AuthManager] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._config = config_service if config_service is not None else ConfigService()
        self._theme_engine = theme_engine
        self._auth_manager = auth_manager
        self._loading = False

        self._setup_ui()
        self._connect_signals()
        self._load_settings()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        # Page header
        header = PageHeader(
            title="Settings",
            description="Configure app-wide preferences.",
        )
        outer.addWidget(header)

        # Scroll area wrapping all sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.viewport().setAutoFillBackground(False)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)

        self._build_appearance_section(main_layout)
        self._build_browser_section(main_layout)
        self._build_download_defaults_section(main_layout)
        self._build_rate_limiting_section(main_layout)
        self._build_retry_logic_section(main_layout)
        self._build_advanced_download_section(main_layout)
        self._build_trim_shortcuts_section(main_layout)

        main_layout.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)

    def _build_appearance_section(self, parent_layout: QVBoxLayout) -> None:
        section = CollapsibleSection("Appearance", expanded=True)
        form = QFormLayout()

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["Dark", "Light"])
        self._theme_combo.setAccessibleName("Theme")
        self._theme_combo.setAccessibleDescription(
            "Select the application colour theme"
        )
        form.addRow("Theme:", self._theme_combo)

        section.content_layout.addLayout(form)
        parent_layout.addWidget(section)

    def _build_browser_section(self, parent_layout: QVBoxLayout) -> None:
        section = CollapsibleSection("Browser & Authentication", expanded=False)
        browser_form = QFormLayout()

        self.browser_combo = QComboBox()
        self.browser_combo.addItem("Chromium", "chromium")
        self.browser_combo.addItem("Firefox", "firefox")
        self.browser_combo.addItem("WebKit", "webkit")
        self.browser_combo.setAccessibleName("Playwright Browser")
        self.browser_combo.setAccessibleDescription(
            "Select which browser engine Playwright uses for authentication"
        )
        browser_form.addRow("Browser:", self.browser_combo)

        button_row = QHBoxLayout()
        self.install_button = QPushButton("Install Playwright Browsers...")
        self.install_button.setObjectName("btnPrimary")
        self.install_button.setProperty("button_role", "primary")
        self.install_button.setAccessibleName("Install Playwright Browsers")
        self.install_button.setAccessibleDescription(
            "Download and install Playwright browser binaries"
        )
        self.reinstall_button = QPushButton("Reinstall Playwright Browsers...")
        self.reinstall_button.setObjectName("btnWire")
        self.reinstall_button.setProperty("button_role", "secondary")
        self.reinstall_button.setAccessibleName("Reinstall Playwright Browsers")
        self.reinstall_button.setAccessibleDescription(
            "Re-download Playwright browser binaries, replacing existing ones"
        )
        button_row.addWidget(self.install_button)
        button_row.addWidget(self.reinstall_button)
        button_row.addStretch()
        browser_form.addRow("", button_row)

        self.profile_path = QLineEdit()
        self.profile_path.setReadOnly(True)
        self.profile_path.setAccessibleName("Playwright Profile Directory")
        self.profile_path.setAccessibleDescription(
            "Path to the Playwright browser profile directory"
        )
        self.profile_open_button = QPushButton("Open Folder")
        self.profile_open_button.setObjectName("btnWire")
        self.profile_open_button.setProperty("button_role", "secondary")
        self.profile_open_button.setAccessibleName("Open Profile Folder")
        self.profile_open_button.setAccessibleDescription(
            "Open the Playwright profile directory in the file manager"
        )
        profile_row = QHBoxLayout()
        profile_row.addWidget(self.profile_path, 1)
        profile_row.addWidget(self.profile_open_button)
        profile_widget = QWidget()
        profile_widget.setLayout(profile_row)
        browser_form.addRow("Profile dir:", profile_widget)

        self.cookies_path = QLineEdit()
        self.cookies_path.setReadOnly(True)
        self.cookies_path.setAccessibleName("Cookies File Path")
        self.cookies_path.setAccessibleDescription(
            "Path to the Netscape cookies file used by yt-dlp"
        )
        self.cookies_open_button = QPushButton("Open Folder")
        self.cookies_open_button.setObjectName("btnWire")
        self.cookies_open_button.setProperty("button_role", "secondary")
        self.cookies_open_button.setAccessibleName("Open Cookies Folder")
        self.cookies_open_button.setAccessibleDescription(
            "Open the folder containing the cookies file in the file manager"
        )
        cookies_row = QHBoxLayout()
        cookies_row.addWidget(self.cookies_path, 1)
        cookies_row.addWidget(self.cookies_open_button)
        cookies_widget = QWidget()
        cookies_widget.setLayout(cookies_row)
        browser_form.addRow("Cookies file:", cookies_widget)

        section.content_layout.addLayout(browser_form)
        parent_layout.addWidget(section)

    def _build_download_defaults_section(self, parent_layout: QVBoxLayout) -> None:
        section = CollapsibleSection("Download Defaults", expanded=True)
        defaults_form = QFormLayout()

        self.force_overwrite_cb = QCheckBox("Force Overwrite")
        self.force_overwrite_cb.setToolTip(
            "Replace existing files instead of skipping them"
        )
        self.force_overwrite_cb.setAccessibleName("Force Overwrite")
        self.force_overwrite_cb.setAccessibleDescription(
            "When enabled, overwrite existing files instead of skipping them"
        )
        defaults_form.addRow(self.force_overwrite_cb)

        self.video_only_cb = QCheckBox("Video Only (No Audio)")
        self.video_only_cb.setToolTip("Download video stream only, skip audio merging")
        self.video_only_cb.setAccessibleName("Video Only")
        self.video_only_cb.setAccessibleDescription(
            "When enabled, download video stream only without merging audio"
        )
        defaults_form.addRow(self.video_only_cb)

        section.content_layout.addLayout(defaults_form)
        parent_layout.addWidget(section)

    def _build_rate_limiting_section(self, parent_layout: QVBoxLayout) -> None:
        section = CollapsibleSection("Rate Limiting", expanded=False)
        rate_form = QFormLayout()

        self.sleep_requests_spin = QDoubleSpinBox()
        self.sleep_requests_spin.setRange(0.0, 60.0)
        self.sleep_requests_spin.setDecimals(2)
        self.sleep_requests_spin.setSingleStep(0.25)
        self.sleep_requests_spin.setAccessibleName("Sleep Between Requests")
        self.sleep_requests_spin.setAccessibleDescription(
            "Seconds to wait between HTTP requests, 0 to 60"
        )
        rate_form.addRow("Sleep between requests (s):", self.sleep_requests_spin)

        self.min_sleep_spin = QDoubleSpinBox()
        self.min_sleep_spin.setRange(0.0, 600.0)
        self.min_sleep_spin.setDecimals(2)
        self.min_sleep_spin.setSingleStep(0.5)
        self.min_sleep_spin.setAccessibleName("Minimum Sleep Before Download")
        self.min_sleep_spin.setAccessibleDescription(
            "Minimum seconds to sleep before starting each download"
        )
        rate_form.addRow("Min sleep before download (s):", self.min_sleep_spin)

        self.max_sleep_spin = QDoubleSpinBox()
        self.max_sleep_spin.setRange(0.0, 600.0)
        self.max_sleep_spin.setDecimals(2)
        self.max_sleep_spin.setSingleStep(0.5)
        self.max_sleep_spin.setAccessibleName("Maximum Sleep Before Download")
        self.max_sleep_spin.setAccessibleDescription(
            "Maximum seconds to sleep before starting each download"
        )
        rate_form.addRow("Max sleep before download (s):", self.max_sleep_spin)

        self.limit_rate_edit = QLineEdit()
        self.limit_rate_edit.setPlaceholderText("e.g. 500K or 2M")
        self.limit_rate_edit.setAccessibleName("Download Rate Limit")
        self.limit_rate_edit.setAccessibleDescription(
            "Maximum download speed, for example 500K or 2M. Leave empty for unlimited"
        )
        rate_form.addRow("Limit rate:", self.limit_rate_edit)

        self.retries_spin = QSpinBox()
        self.retries_spin.setRange(0, 999)
        self.retries_spin.setAccessibleName("Download Retries")
        self.retries_spin.setAccessibleDescription(
            "Number of times to retry a failed download, 0 to 999"
        )
        rate_form.addRow("Retries:", self.retries_spin)

        section.content_layout.addLayout(rate_form)
        parent_layout.addWidget(section)

    def _build_retry_logic_section(self, parent_layout: QVBoxLayout) -> None:
        section = CollapsibleSection("Retry Logic", expanded=False)
        retry_form = QFormLayout()

        self.retry_mode_combo = QComboBox()
        self.retry_mode_combo.addItem("Off", "off")
        self.retry_mode_combo.addItem("Linear", "linear")
        self.retry_mode_combo.addItem("Exponential", "exp")
        self.retry_mode_combo.setAccessibleName("HTTP Retry Sleep Mode")
        self.retry_mode_combo.setAccessibleDescription(
            "Sleep strategy between HTTP retries: Off, Linear, or Exponential"
        )
        retry_form.addRow("Retry sleep (HTTP):", self.retry_mode_combo)

        self.retry_start_spin = QDoubleSpinBox()
        self.retry_start_spin.setRange(0.0, 600.0)
        self.retry_start_spin.setDecimals(2)
        self.retry_start_spin.setSingleStep(0.5)
        self.retry_start_spin.setAccessibleName("Retry Start Delay")
        self.retry_start_spin.setAccessibleDescription(
            "Initial delay in seconds before first retry"
        )
        retry_form.addRow("Retry start (s):", self.retry_start_spin)

        self.retry_end_spin = QDoubleSpinBox()
        self.retry_end_spin.setRange(0.0, 600.0)
        self.retry_end_spin.setDecimals(2)
        self.retry_end_spin.setSingleStep(0.5)
        self.retry_end_spin.setAccessibleName("Retry End Delay")
        self.retry_end_spin.setAccessibleDescription(
            "Maximum delay in seconds between retries"
        )
        retry_form.addRow("Retry end (s):", self.retry_end_spin)

        self.retry_step_spin = QDoubleSpinBox()
        self.retry_step_spin.setRange(0.0, 60.0)
        self.retry_step_spin.setDecimals(2)
        self.retry_step_spin.setSingleStep(0.5)
        self.retry_step_spin.setAccessibleName("Retry Linear Step")
        self.retry_step_spin.setAccessibleDescription(
            "Seconds added to delay between each linear retry"
        )
        retry_form.addRow("Linear step (s):", self.retry_step_spin)

        self.retry_base_spin = QDoubleSpinBox()
        self.retry_base_spin.setRange(1.0, 10.0)
        self.retry_base_spin.setDecimals(2)
        self.retry_base_spin.setSingleStep(0.5)
        self.retry_base_spin.setAccessibleName("Retry Exponential Base")
        self.retry_base_spin.setAccessibleDescription(
            "Base multiplier for exponential retry backoff"
        )
        retry_form.addRow("Exp base:", self.retry_base_spin)

        section.content_layout.addLayout(retry_form)
        parent_layout.addWidget(section)

    def _build_advanced_download_section(self, parent_layout: QVBoxLayout) -> None:
        section = CollapsibleSection("Advanced Download Options", expanded=False)
        fragment_form = QFormLayout()

        self.fragment_enable_cb = QCheckBox("Enable fragment retry sleep")
        self.fragment_enable_cb.setAccessibleName("Enable Fragment Retry Sleep")
        self.fragment_enable_cb.setAccessibleDescription(
            "Enable sleep delays between fragment download retries"
        )
        fragment_form.addRow("", self.fragment_enable_cb)

        self.fragment_mode_combo = QComboBox()
        self.fragment_mode_combo.addItem("Off", "off")
        self.fragment_mode_combo.addItem("Linear", "linear")
        self.fragment_mode_combo.addItem("Exponential", "exp")
        self.fragment_mode_combo.setAccessibleName("Fragment Retry Sleep Mode")
        self.fragment_mode_combo.setAccessibleDescription(
            "Sleep strategy between fragment retries: Off, Linear, or Exponential"
        )
        fragment_form.addRow("Fragment retry sleep:", self.fragment_mode_combo)

        self.fragment_start_spin = QDoubleSpinBox()
        self.fragment_start_spin.setRange(0.0, 600.0)
        self.fragment_start_spin.setDecimals(2)
        self.fragment_start_spin.setSingleStep(0.5)
        self.fragment_start_spin.setAccessibleName("Fragment Retry Start Delay")
        self.fragment_start_spin.setAccessibleDescription(
            "Initial delay in seconds before first fragment retry"
        )
        fragment_form.addRow("Fragment start (s):", self.fragment_start_spin)

        self.fragment_end_spin = QDoubleSpinBox()
        self.fragment_end_spin.setRange(0.0, 600.0)
        self.fragment_end_spin.setDecimals(2)
        self.fragment_end_spin.setSingleStep(0.5)
        self.fragment_end_spin.setAccessibleName("Fragment Retry End Delay")
        self.fragment_end_spin.setAccessibleDescription(
            "Maximum delay in seconds between fragment retries"
        )
        fragment_form.addRow("Fragment end (s):", self.fragment_end_spin)

        self.fragment_step_spin = QDoubleSpinBox()
        self.fragment_step_spin.setRange(0.0, 60.0)
        self.fragment_step_spin.setDecimals(2)
        self.fragment_step_spin.setSingleStep(0.5)
        self.fragment_step_spin.setAccessibleName("Fragment Retry Linear Step")
        self.fragment_step_spin.setAccessibleDescription(
            "Seconds added to delay between each linear fragment retry"
        )
        fragment_form.addRow("Fragment linear step (s):", self.fragment_step_spin)

        self.fragment_base_spin = QDoubleSpinBox()
        self.fragment_base_spin.setRange(1.0, 10.0)
        self.fragment_base_spin.setDecimals(2)
        self.fragment_base_spin.setSingleStep(0.5)
        self.fragment_base_spin.setAccessibleName("Fragment Retry Exponential Base")
        self.fragment_base_spin.setAccessibleDescription(
            "Base multiplier for exponential fragment retry backoff"
        )
        fragment_form.addRow("Fragment exp base:", self.fragment_base_spin)

        section.content_layout.addLayout(fragment_form)
        parent_layout.addWidget(section)

    def _build_trim_shortcuts_section(self, parent_layout: QVBoxLayout) -> None:
        section = CollapsibleSection("Trim & Shortcuts", expanded=False)
        form = QFormLayout()

        self._trim_scrub_step_combo = QComboBox()
        for step in (0.1, 0.25, 0.5, 1.0, 2.0, 5.0):
            label = f"{step:g} s" if step < 1.0 else f"{step:.0f} s"
            self._trim_scrub_step_combo.addItem(label, step)
        form.addRow("Default scrub step:", self._trim_scrub_step_combo)

        self._trim_split_shortcut_edit = QKeySequenceEdit()
        form.addRow("Split at current:", self._trim_split_shortcut_edit)

        self._trim_delete_shortcut_edit = QKeySequenceEdit()
        form.addRow("Delete selected segment:", self._trim_delete_shortcut_edit)

        self._trim_label_shortcut_edit = QKeySequenceEdit()
        form.addRow("Label selected segment:", self._trim_label_shortcut_edit)

        self._trim_close_shortcut_edit = QKeySequenceEdit()
        form.addRow("Close current video:", self._trim_close_shortcut_edit)

        section.content_layout.addLayout(form)

        note = QLabel(
            "These shortcuts only apply while the Trim page is active."
        )
        note.setObjectName("dimLabel")
        note.setWordWrap(True)
        section.content_layout.addWidget(note)
        parent_layout.addWidget(section)

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._theme_combo.currentTextChanged.connect(self._on_theme_changed)

        self.browser_combo.currentIndexChanged.connect(self._on_setting_changed)
        self.install_button.clicked.connect(self._on_install_clicked)
        self.reinstall_button.clicked.connect(self._on_reinstall_clicked)
        self.profile_open_button.clicked.connect(self._on_open_profile)
        self.cookies_open_button.clicked.connect(self._on_open_cookies)

        self.force_overwrite_cb.stateChanged.connect(self._on_setting_changed)
        self.video_only_cb.stateChanged.connect(self._on_setting_changed)

        self.sleep_requests_spin.valueChanged.connect(self._on_setting_changed)
        self.min_sleep_spin.valueChanged.connect(self._on_setting_changed)
        self.max_sleep_spin.valueChanged.connect(self._on_setting_changed)
        self.limit_rate_edit.editingFinished.connect(self._on_setting_changed)
        self.retries_spin.valueChanged.connect(self._on_setting_changed)

        self.retry_mode_combo.currentIndexChanged.connect(self._on_retry_mode_changed)
        self.retry_start_spin.valueChanged.connect(self._on_setting_changed)
        self.retry_end_spin.valueChanged.connect(self._on_setting_changed)
        self.retry_step_spin.valueChanged.connect(self._on_setting_changed)
        self.retry_base_spin.valueChanged.connect(self._on_setting_changed)

        self.fragment_enable_cb.stateChanged.connect(self._on_fragment_mode_changed)
        self.fragment_mode_combo.currentIndexChanged.connect(
            self._on_fragment_mode_changed
        )
        self.fragment_start_spin.valueChanged.connect(self._on_setting_changed)
        self.fragment_end_spin.valueChanged.connect(self._on_setting_changed)
        self.fragment_step_spin.valueChanged.connect(self._on_setting_changed)
        self.fragment_base_spin.valueChanged.connect(self._on_setting_changed)

        self._trim_scrub_step_combo.currentIndexChanged.connect(
            self._on_setting_changed
        )
        self._trim_split_shortcut_edit.editingFinished.connect(self._on_setting_changed)
        self._trim_delete_shortcut_edit.editingFinished.connect(
            self._on_setting_changed
        )
        self._trim_label_shortcut_edit.editingFinished.connect(
            self._on_setting_changed
        )
        self._trim_close_shortcut_edit.editingFinished.connect(
            self._on_setting_changed
        )

    # ------------------------------------------------------------------
    # Load / save
    # ------------------------------------------------------------------

    def _load_settings(self) -> None:
        self._loading = True

        # Theme
        theme = self._config.get("appearance.theme", "dark")
        engine = ThemeEngine.instance()
        engine.set_theme(theme)
        current = engine.current_theme.capitalize()
        index = self._theme_combo.findText(current)
        if index >= 0:
            self._theme_combo.setCurrentIndex(index)

        # Browser & Auth
        browser = self._config.get("playwright.browser", "chromium")
        index = self.browser_combo.findData(browser)
        if index >= 0:
            self.browser_combo.setCurrentIndex(index)

        self.profile_path.setText(self._config.get("auth.profile_dir", ""))
        self.cookies_path.setText(self._config.get("auth.cookies_file_path", ""))

        # Download Defaults
        self.force_overwrite_cb.setChecked(
            self._config.get("download.force_overwrite", False)
        )
        self.video_only_cb.setChecked(self._config.get("download.video_only", False))

        # Rate Limiting & Retry Logic
        polite = self._config.get_section("download_polite")
        self.sleep_requests_spin.setValue(
            float(polite.get("sleep_requests_seconds", 0.0))
        )
        self.min_sleep_spin.setValue(
            float(polite.get("min_sleep_interval_seconds", 0.0))
        )
        self.max_sleep_spin.setValue(
            float(polite.get("max_sleep_interval_seconds", 0.0))
        )
        self.limit_rate_edit.setText(polite.get("limit_rate", ""))
        self.retries_spin.setValue(int(polite.get("retries", 10)))

        http_retry = polite.get("retry_sleep_http", {})
        self.retry_mode_combo.setCurrentIndex(
            self.retry_mode_combo.findData(http_retry.get("mode", "off"))
        )
        self.retry_start_spin.setValue(float(http_retry.get("start", 0.0)))
        self.retry_end_spin.setValue(float(http_retry.get("end", 0.0)))
        self.retry_step_spin.setValue(float(http_retry.get("step", 1.0)))
        self.retry_base_spin.setValue(float(http_retry.get("base", 2.0)))

        # Advanced Download Options (fragment retry)
        fragment_enabled = polite.get("retry_sleep_fragment_enabled", False)
        self.fragment_enable_cb.setChecked(fragment_enabled)
        fragment_retry = polite.get("retry_sleep_fragment", {})
        self.fragment_mode_combo.setCurrentIndex(
            self.fragment_mode_combo.findData(fragment_retry.get("mode", "off"))
        )
        self.fragment_start_spin.setValue(float(fragment_retry.get("start", 0.0)))
        self.fragment_end_spin.setValue(float(fragment_retry.get("end", 0.0)))
        self.fragment_step_spin.setValue(float(fragment_retry.get("step", 1.0)))
        self.fragment_base_spin.setValue(float(fragment_retry.get("base", 2.0)))

        trim_scrub_step = float(
            self._config.get("trim.playback.scrub_step_seconds", 0.25)
        )
        scrub_index = self._trim_scrub_step_combo.findData(trim_scrub_step)
        self._trim_scrub_step_combo.setCurrentIndex(max(scrub_index, 0))

        self._trim_split_shortcut_edit.setKeySequence(
            QKeySequence(self._config.get("trim.shortcuts.split_segment", "S"))
        )
        self._trim_delete_shortcut_edit.setKeySequence(
            QKeySequence(
                self._config.get("trim.shortcuts.delete_segment", "Backspace")
            )
        )
        self._trim_label_shortcut_edit.setKeySequence(
            QKeySequence(self._config.get("trim.shortcuts.label_segment", "L"))
        )
        self._trim_close_shortcut_edit.setKeySequence(
            QKeySequence(
                self._config.get(
                    "trim.shortcuts.close_video",
                    QKeySequence(QKeySequence.StandardKey.Close).toString(),
                )
            )
        )

        self._loading = False
        self._update_retry_controls()
        self._update_fragment_controls()

    def reload_settings(self) -> None:
        """Reload settings from ConfigService."""
        self._load_settings()

    def _save_settings(self) -> None:
        self._config.set("playwright.browser", self.browser_combo.currentData())
        if self._auth_manager is not None:
            self._auth_manager.set_playwright_browser(self.browser_combo.currentData())

        self._config.set(
            "download.force_overwrite", self.force_overwrite_cb.isChecked()
        )
        self._config.set("download.video_only", self.video_only_cb.isChecked())

        polite = {
            "sleep_requests_seconds": float(self.sleep_requests_spin.value()),
            "min_sleep_interval_seconds": float(self.min_sleep_spin.value()),
            "max_sleep_interval_seconds": float(self.max_sleep_spin.value()),
            "limit_rate": self.limit_rate_edit.text().strip(),
            "retries": int(self.retries_spin.value()),
            "retry_sleep_http": {
                "mode": self.retry_mode_combo.currentData(),
                "start": float(self.retry_start_spin.value()),
                "end": float(self.retry_end_spin.value()),
                "step": float(self.retry_step_spin.value()),
                "base": float(self.retry_base_spin.value()),
            },
            "retry_sleep_fragment_enabled": self.fragment_enable_cb.isChecked(),
            "retry_sleep_fragment": {
                "mode": self.fragment_mode_combo.currentData(),
                "start": float(self.fragment_start_spin.value()),
                "end": float(self.fragment_end_spin.value()),
                "step": float(self.fragment_step_spin.value()),
                "base": float(self.fragment_base_spin.value()),
            },
        }

        self._config.set_section("download_polite", polite, save=True)
        self._config.set(
            "trim.playback.scrub_step_seconds",
            float(self._trim_scrub_step_combo.currentData()),
            save=False,
        )
        self._config.set(
            "trim.shortcuts.split_segment",
            self._trim_split_shortcut_edit.keySequence().toString(),
            save=False,
        )
        self._config.set(
            "trim.shortcuts.delete_segment",
            self._trim_delete_shortcut_edit.keySequence().toString(),
            save=False,
        )
        self._config.set(
            "trim.shortcuts.label_segment",
            self._trim_label_shortcut_edit.keySequence().toString(),
            save=False,
        )
        self._config.set(
            "trim.shortcuts.close_video",
            self._trim_close_shortcut_edit.keySequence().toString(),
            save=True,
        )

    # ------------------------------------------------------------------
    # Slot handlers
    # ------------------------------------------------------------------

    def _on_setting_changed(self) -> None:
        if self._loading:
            return
        self._save_settings()

    def _on_theme_changed(self, text: str) -> None:
        if self._loading:
            return
        theme = text.lower()
        engine = ThemeEngine.instance()
        engine.set_theme(theme)
        engine.apply_theme(QApplication.instance())
        self._config.set("appearance.theme", theme)

    def _on_retry_mode_changed(self) -> None:
        self._update_retry_controls()
        self._on_setting_changed()

    def _on_fragment_mode_changed(self) -> None:
        self._update_fragment_controls()
        self._on_setting_changed()

    def _update_retry_controls(self) -> None:
        mode = self.retry_mode_combo.currentData()
        self.retry_step_spin.setEnabled(mode == "linear")
        self.retry_base_spin.setEnabled(mode == "exp")

    def _update_fragment_controls(self) -> None:
        enabled = self.fragment_enable_cb.isChecked()
        self.fragment_mode_combo.setEnabled(enabled)
        self.fragment_start_spin.setEnabled(enabled)
        self.fragment_end_spin.setEnabled(enabled)
        self.fragment_step_spin.setEnabled(
            enabled and self.fragment_mode_combo.currentData() == "linear"
        )
        self.fragment_base_spin.setEnabled(
            enabled and self.fragment_mode_combo.currentData() == "exp"
        )

    def _on_install_clicked(self) -> None:
        if self._auth_manager is None:
            return
        show_playwright_browser_install_dialog(
            parent=self,
            message="Select Playwright browsers to install.",
            auth_manager=self._auth_manager,
            title="Install Playwright Browsers",
            force=False,
        )

    def _on_reinstall_clicked(self) -> None:
        if self._auth_manager is None:
            return
        result = QMessageBox.question(
            self,
            "Reinstall Playwright Browsers",
            "This will re-download browser binaries and may take a while. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            show_playwright_browser_install_dialog(
                parent=self,
                message="Select Playwright browsers to reinstall.",
                auth_manager=self._auth_manager,
                title="Reinstall Playwright Browsers",
                force=True,
            )

    def _on_open_profile(self) -> None:
        path = self.profile_path.text().strip()
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _on_open_cookies(self) -> None:
        path = self.cookies_path.text().strip()
        if path:
            folder = str(Path(path).parent)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
