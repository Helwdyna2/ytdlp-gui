"""MatchPage — match video files against scene databases."""

import logging
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QCheckBox,
    QProgressBar,
    QMessageBox,
    QHeaderView,
    QAbstractItemView,
)

from ...data.models import MatchResult, MatchStatus, MatchConfig
from ...services.config_service import ConfigService
from ...utils.dialog_utils import get_dialog_start_dir, update_dialog_last_dir
from ..playwright_install_prompt import (
    is_playwright_setup_message,
    show_playwright_install_prompt,
)
from ..components.page_header import PageHeader
from ..components.split_layout import SplitLayout

logger = logging.getLogger(__name__)


class MatchPage(QWidget):
    """
    Match page — match video files against scene databases.

    Replaces MatchTabWidget with a SplitLayout-based design.
    Preserves all MatchManager signal connections.

    Layout:
    - PageHeader
    - SplitLayout(right_width=500):
        LEFT: source folder, databases, position tags, options, buttons
        RIGHT: results table, action row
    - Progress bar + status label
    """

    def __init__(self, match_manager=None, parent=None):
        super().__init__(parent)
        self._config = ConfigService()
        self._auth_manager = None
        self._manager = match_manager  # Optional pre-injected manager
        self._scan_worker = None  # MatchScanWorker for background scanning
        self._files: List[MatchResult] = []

        self._setup_ui()
        self._connect_signals()
        self._load_settings()

        # If a manager was pre-injected, connect its signals immediately
        if self._manager is not None:
            self._connect_manager_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Build the full page layout."""
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # 1. Page header
        root.addWidget(
            PageHeader(
                title="Match",
                description="Match files against scene databases.",
            )
        )

        # 2. SplitLayout
        split = SplitLayout(right_width=500, gap=20)

        # ------------------------------------------------------------------
        # LEFT panel
        # ------------------------------------------------------------------
        left_layout = QVBoxLayout(split.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Source folder row
        source_row = QHBoxLayout()
        source_row.setSpacing(8)
        source_row.addWidget(QLabel("Source:"))
        self._source_input = QLineEdit()
        self._source_input.setPlaceholderText("Choose a source folder…")
        self._source_input.setReadOnly(True)
        source_row.addWidget(self._source_input, stretch=1)
        self._source_browse_btn = QPushButton("Browse")
        self._source_browse_btn.setObjectName("btnWire")
        self._source_browse_btn.setProperty("button_role", "secondary")
        source_row.addWidget(self._source_browse_btn)
        left_layout.addLayout(source_row)

        # Databases label + checkboxes
        left_layout.addWidget(QLabel("Databases:"))
        db_row = QHBoxLayout()
        db_row.setSpacing(16)
        self.porndb_checkbox = QCheckBox("Search ThePornDB (prioritized)")
        self.porndb_checkbox.setChecked(True)
        self.stashdb_checkbox = QCheckBox("Search StashDB")
        self.stashdb_checkbox.setChecked(True)
        db_row.addWidget(self.porndb_checkbox)
        db_row.addWidget(self.stashdb_checkbox)
        db_row.addStretch()
        left_layout.addLayout(db_row)

        # Position tags label + checkbox
        left_layout.addWidget(QLabel("Position tags:"))
        tags_row = QHBoxLayout()
        tags_row.setSpacing(8)
        self.preserve_tags_checkbox = QCheckBox("Preserve position tags")
        self.preserve_tags_checkbox.setChecked(True)
        self.preserve_tags_checkbox.setToolTip(
            "Keep position/act tags like 'Missionary', 'BJ' in renamed files"
        )
        tags_row.addWidget(self.preserve_tags_checkbox)
        tags_row.addStretch()
        left_layout.addLayout(tags_row)

        # Include already-named files checkbox
        self.include_named_checkbox = QCheckBox("Include already-named files")
        self.include_named_checkbox.setChecked(False)
        self.include_named_checkbox.setToolTip(
            "Process files that already appear to be properly named"
        )
        left_layout.addWidget(self.include_named_checkbox)

        # Exclude terms row
        left_layout.addWidget(QLabel("Exclude terms:"))
        exclude_row = QHBoxLayout()
        exclude_row.setSpacing(8)
        self.skip_keywords_button = QPushButton("Exclude terms…")
        self.skip_keywords_button.setObjectName("btnWire")
        self.skip_keywords_button.setProperty("button_role", "secondary")
        self.skip_keywords_button.setToolTip(
            "Edit keywords/phrases that should be excluded from search queries"
        )
        self.skip_keywords_status_label = QLabel("")
        exclude_row.addWidget(self.skip_keywords_button)
        exclude_row.addWidget(self.skip_keywords_status_label)
        exclude_row.addStretch()
        left_layout.addLayout(exclude_row)

        left_layout.addStretch()

        # Action buttons
        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.scan_button = QPushButton("Scan Folder")
        self.scan_button.setObjectName("btnWire")
        self.scan_button.setProperty("button_role", "secondary")
        self.match_button = QPushButton("START MATCHING")
        self.match_button.setObjectName("btnPrimary")
        self.match_button.setProperty("button_role", "cta")
        self.match_button.setEnabled(False)
        self.match_button.setMinimumWidth(140)
        action_row.addWidget(self.scan_button)
        action_row.addWidget(self.match_button)
        action_row.addStretch()
        left_layout.addLayout(action_row)

        # ------------------------------------------------------------------
        # RIGHT panel
        # ------------------------------------------------------------------
        right_layout = QVBoxLayout(split.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        results_label = QLabel("Results")
        results_label.setObjectName("dpanelTitle")
        right_layout.addWidget(results_label)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(
            ["☐", "Status", "Confidence", "Original Name", "Matched Name"]
        )
        self.results_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.results_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.results_table.setAlternatingRowColors(True)
        self.results_table.cellDoubleClicked.connect(self._on_table_double_clicked)
        right_layout.addWidget(self.results_table, stretch=1)

        self.selection_label = QLabel("Selected: 0 files")
        self.selection_label.setObjectName("dimLabel")
        right_layout.addWidget(self.selection_label)

        # Action row
        action_bottom = QHBoxLayout()
        action_bottom.setSpacing(8)
        self.view_details_button = QPushButton("View Match Details")
        self.view_details_button.setObjectName("btnWire")
        self.view_details_button.setProperty("button_role", "secondary")
        self.view_details_button.setEnabled(False)
        self.manual_search_button = QPushButton("Manual Search…")
        self.manual_search_button.setObjectName("btnWire")
        self.manual_search_button.setProperty("button_role", "secondary")
        self.manual_search_button.setEnabled(False)
        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("btnDestructive")
        self.stop_button.setProperty("button_role", "destructive")
        self.stop_button.setEnabled(False)
        action_bottom.addWidget(self.view_details_button)
        action_bottom.addWidget(self.manual_search_button)
        action_bottom.addStretch()
        action_bottom.addWidget(self.stop_button)
        right_layout.addLayout(action_bottom)

        root.addWidget(split, stretch=1)

        # 3. Progress bar + status label
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%v / %m files (%p%)")
        root.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready. Select a folder to begin.")
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("dimLabel")
        root.addWidget(self.status_label)

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        self._source_browse_btn.clicked.connect(self._on_browse_source)
        self._source_input.textChanged.connect(self._on_source_changed)
        self.skip_keywords_button.clicked.connect(self._on_skip_keywords_clicked)

        self.scan_button.clicked.connect(self._on_scan_clicked)
        self.match_button.clicked.connect(self._on_match_clicked)
        self.stop_button.clicked.connect(self._on_stop_clicked)

        self.view_details_button.clicked.connect(self._on_view_details_clicked)
        self.manual_search_button.clicked.connect(self._on_manual_search_clicked)

        # Settings persistence
        self.porndb_checkbox.stateChanged.connect(self._save_settings)
        self.stashdb_checkbox.stateChanged.connect(self._save_settings)
        self.preserve_tags_checkbox.stateChanged.connect(self._save_settings)
        self.include_named_checkbox.stateChanged.connect(self._save_settings)

    def _connect_manager_signals(self) -> None:
        """Connect all MatchManager signals to UI handlers."""
        self._manager.scan_started.connect(self._on_scan_started)
        self._manager.scan_progress.connect(self._on_scan_progress)
        self._manager.scan_completed.connect(self._on_scan_completed)
        self._manager.match_started.connect(self._on_match_started)
        self._manager.match_progress.connect(self._on_match_progress)
        self._manager.match_result.connect(self._on_match_result)
        self._manager.login_required.connect(self._on_login_required)
        self._manager.match_completed.connect(self._on_match_completed)
        self._manager.rename_started.connect(self._on_rename_started)
        self._manager.rename_progress.connect(self._on_rename_progress)
        self._manager.rename_completed.connect(self._on_rename_completed)
        self._manager.error.connect(self._on_error)

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _load_settings(self) -> None:
        """Load saved settings from ConfigService."""
        match_config = self._config.get_section("match")
        if match_config:
            folder = match_config.get("last_folder", "")
            if folder:
                self._source_input.setText(folder)
            self.porndb_checkbox.setChecked(match_config.get("search_porndb", True))
            self.stashdb_checkbox.setChecked(match_config.get("search_stashdb", True))
            self.preserve_tags_checkbox.setChecked(
                match_config.get("preserve_tags", True)
            )
            self.include_named_checkbox.setChecked(
                match_config.get("include_already_named", False)
            )
            self._update_skip_keywords_display(match_config.get("skip_keywords", []))

    def _save_settings(self) -> None:
        """Save settings to ConfigService."""
        match_config = self._config.get_section("match") or {}
        match_config.update(
            {
                "last_folder": self._source_input.text(),
                "search_porndb": self.porndb_checkbox.isChecked(),
                "search_stashdb": self.stashdb_checkbox.isChecked(),
                "preserve_tags": self.preserve_tags_checkbox.isChecked(),
                "include_already_named": self.include_named_checkbox.isChecked(),
            }
        )
        self._config.set_section("match", match_config)

    def _get_config(self) -> MatchConfig:
        """Build MatchConfig from current UI state."""
        return MatchConfig(
            source_dir=self._source_input.text(),
            search_porndb=self.porndb_checkbox.isChecked(),
            search_stashdb=self.stashdb_checkbox.isChecked(),
            porndb_first=True,
            preserve_tags=self.preserve_tags_checkbox.isChecked(),
            include_already_named=self.include_named_checkbox.isChecked(),
            custom_studios=self._config.get("match.custom_studios", []),
            skip_keywords=self._config.get("match.skip_keywords", []),
        )

    # ------------------------------------------------------------------
    # Source folder
    # ------------------------------------------------------------------

    def _on_browse_source(self) -> None:
        """Open directory picker for source folder."""
        start_dir = get_dialog_start_dir(
            self._source_input.text(), "match.last_folder"
        )
        folder = QFileDialog.getExistingDirectory(
            self, "Select Source Folder", start_dir
        )
        if folder:
            update_dialog_last_dir(folder)
            self._source_input.setText(folder)
            self._clear_results()
            self._save_settings()

    def _on_source_changed(self, text: str) -> None:
        """Handle source path changes."""
        # Clear results when folder changes (only if it was non-empty before)
        pass

    # ------------------------------------------------------------------
    # UI event handlers
    # ------------------------------------------------------------------

    def _on_skip_keywords_clicked(self) -> None:
        """Open dialog to edit keywords excluded from search."""
        from ..widgets.match_skip_keywords_dialog import MatchSkipKeywordsDialog

        current = self._config.get("match.skip_keywords", [])
        dialog = MatchSkipKeywordsDialog(current, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            keywords = dialog.get_keywords()
            self._config.set("match.skip_keywords", keywords, save=True)
            self._update_skip_keywords_display(keywords)

    def _on_scan_clicked(self) -> None:
        """Handle scan button click."""
        folder = self._source_input.text()
        if not folder or not Path(folder).exists():
            QMessageBox.warning(
                self,
                "Invalid Folder",
                "Please select a valid folder containing video files.",
            )
            return

        if self._manager is None:
            self._init_manager()

        # Cancel any existing scan worker (non-blocking)
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.cancel()
            # Don't wait() - let it finish in background

        self._clear_scan_results()
        self._set_result_actions_enabled(False)

        self.scan_button.setEnabled(False)
        self.match_button.setEnabled(False)
        self.status_label.setText("Scanning folder for video files...")
        self.progress_bar.setValue(0)

        # Import here to avoid circular dependency
        from ...core.match_scan_worker import MatchScanWorker

        # Create worker with current config
        config = self._get_config()
        self._scan_worker = MatchScanWorker(
            folder_path=folder,
            config=config,
            parent=self,
        )

        # Connect signals
        self._scan_worker.progress.connect(self._on_scan_progress)
        self._scan_worker.completed.connect(self._on_scan_completed)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_worker.finished.connect(self._scan_worker.deleteLater)

        # Start worker
        self._scan_worker.start()

    def _on_match_clicked(self) -> None:
        """Handle match button click."""
        if not self._files:
            QMessageBox.warning(self, "No Files", "Please scan a folder first.")
            return

        if (
            not self.porndb_checkbox.isChecked()
            and not self.stashdb_checkbox.isChecked()
        ):
            QMessageBox.warning(
                self,
                "No Databases Selected",
                "Please select at least one database to search.",
            )
            return

        # Update manager config with current UI state
        config = self._get_config()
        self._manager.set_config(config)

        # Disable/enable buttons
        self.match_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.scan_button.setEnabled(False)

        self.status_label.setText("Starting matching process...")
        self.progress_bar.setMaximum(len(self._files))
        self.progress_bar.setValue(0)

        self._manager.start_matching()

    def _on_stop_clicked(self) -> None:
        """Handle stop button click."""
        if self._manager:
            self._manager.stop_matching()

        self.stop_button.setEnabled(False)
        self.match_button.setEnabled(True)
        self.scan_button.setEnabled(True)
        self.status_label.setText("Matching stopped.")

    def _on_view_details_clicked(self) -> None:
        """Open detail dialog for selected file."""
        selected_rows = self._get_selected_rows()
        if not selected_rows:
            QMessageBox.information(
                self, "No Selection", "Please select a file to view details."
            )
            return

        row = selected_rows[0]
        if row < len(self._files):
            result = self._files[row]
            if (
                result.status == MatchStatus.MULTIPLE_MATCHES
                and len(result.matches) > 1
            ):
                self._show_match_detail_dialog(result, row)
            elif result.selected_match:
                self._show_match_info(result)
            else:
                QMessageBox.information(
                    self, "No Match", "This file has no matches to view."
                )

    def _on_manual_search_clicked(self) -> None:
        """Open manual search dialog."""
        selected_rows = self._get_selected_rows()
        if not selected_rows:
            QMessageBox.information(
                self, "No Selection", "Please select a file to manually search for."
            )
            return

        QMessageBox.information(
            self, "Not Implemented", "Manual search feature coming soon."
        )

    def _on_table_double_clicked(self, row: int, column: int) -> None:
        """Handle table double-click."""
        if row < len(self._files):
            result = self._files[row]
            if (
                result.status == MatchStatus.MULTIPLE_MATCHES
                and len(result.matches) > 1
            ):
                self._show_match_detail_dialog(result, row)

    # ------------------------------------------------------------------
    # Manager signal handlers
    # ------------------------------------------------------------------

    def _on_scan_started(self) -> None:
        self.status_label.setText("Scanning folder...")

    def _on_scan_progress(self, current: int, total: int) -> None:
        """Handle scan progress from worker."""
        if self.sender() is not self._scan_worker:
            return
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f"Scanning: {current} / {total} files found")

    def _on_scan_completed(self, files: List[MatchResult]) -> None:
        """Handle scan completed from worker."""
        if self.sender() is not self._scan_worker:
            return

        self._files = files
        self.scan_button.setEnabled(True)
        self.match_button.setEnabled(len(files) > 0)

        # Pass files to manager
        if self._manager is not None:
            config = self._get_config()
            self._manager.set_config(config)
            self._manager.set_scan_results(files)

        # Update table
        self._populate_table()

        self.status_label.setText(f"Scan complete. Found {len(files)} video file(s).")
        self.progress_bar.setValue(len(files))

        # Clear worker reference
        self._scan_worker = None

        if len(files) == 0:
            QMessageBox.information(
                self, "No Files Found", "No video files found in the selected folder."
            )

    def _on_scan_error(self, error_message: str) -> None:
        """Handle scan error from worker."""
        if self.sender() is not self._scan_worker:
            return

        self.scan_button.setEnabled(True)
        self.match_button.setEnabled(False)
        self.status_label.setText(f"Scan error: {error_message}")

        # Show error dialog
        if is_playwright_setup_message(error_message):
            show_playwright_install_prompt(
                self, error_message, self._auth_manager, title="Scan Error"
            )
        else:
            QMessageBox.critical(self, "Scan Error", error_message)

        # Clear worker reference
        self._scan_worker = None

    def _on_match_started(self) -> None:
        self.status_label.setText("Matching started...")

    def _on_match_progress(self, file_index: int, status: str, percent: float) -> None:
        self.progress_bar.setValue(file_index + 1)
        self.status_label.setText(status)

    def _on_match_result(self, index: int, result: MatchResult) -> None:
        if index < len(self._files):
            self._files[index] = result
            self._update_table_row(index, result)

    def _on_login_required(self, database: str, url: str) -> None:
        QMessageBox.information(
            self,
            f"Login Required - {database}",
            "Please authenticate using Add URLs first, "
            "then retry matching.\n\n"
            f"URL: {url}",
        )

    def _on_match_completed(self) -> None:
        self.match_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.scan_button.setEnabled(True)

        matched = sum(
            1
            for f in self._files
            if f.status == MatchStatus.MATCHED
            or f.status == MatchStatus.MULTIPLE_MATCHES
        )
        self.status_label.setText(
            f"Matching complete. {matched} / {len(self._files)} files matched."
        )

    def _on_rename_started(self) -> None:
        self.status_label.setText("Renaming files...")

    def _on_rename_progress(self, current: int, total: int) -> None:
        self.status_label.setText(f"Renaming: {current} / {total}")

    def _on_rename_completed(self, success: int, failed: int) -> None:
        self.status_label.setText(
            f"Rename complete. {success} succeeded, {failed} failed."
        )
        if success > 0:
            QMessageBox.information(
                self,
                "Rename Complete",
                f"Successfully renamed {success} file(s).\n{failed} file(s) failed.",
            )

    def _on_error(self, message: str) -> None:
        if is_playwright_setup_message(message):
            show_playwright_install_prompt(
                self, message, self._auth_manager, title="Error"
            )
        else:
            QMessageBox.critical(self, "Error", message)
        self.status_label.setText(f"Error: {message}")

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _init_manager(self) -> None:
        """Initialize the match manager and connect signals."""
        from ...core.match_manager import MatchManager

        self._manager = MatchManager()
        self._connect_manager_signals()

    def _populate_table(self) -> None:
        """Populate the table with file results."""
        self.results_table.setRowCount(len(self._files))
        for i, result in enumerate(self._files):
            self._update_table_row(i, result)

    def _update_table_row(self, row: int, result: MatchResult) -> None:
        """Update a single row in the table."""
        # Column 0: Checkbox
        checkbox = QCheckBox()
        checkbox.stateChanged.connect(self._on_checkbox_changed)
        checkbox_widget = QWidget()
        checkbox_layout = QHBoxLayout(checkbox_widget)
        checkbox_layout.addWidget(checkbox)
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        self.results_table.setCellWidget(row, 0, checkbox_widget)

        # Column 1: Status
        status_text = self._get_status_display(result.status)
        status_item = QTableWidgetItem(status_text)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.results_table.setItem(row, 1, status_item)

        # Column 2: Confidence
        confidence_text = (
            f"{int(result.confidence * 100)}%" if result.confidence > 0 else "--"
        )
        confidence_item = QTableWidgetItem(confidence_text)
        confidence_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.results_table.setItem(row, 2, confidence_item)

        # Column 3: Original name
        original_item = QTableWidgetItem(Path(result.file_path).name)
        self.results_table.setItem(row, 3, original_item)

        # Column 4: Matched name
        if result.new_filename:
            matched_text = result.new_filename
        elif result.status == MatchStatus.MULTIPLE_MATCHES:
            matched_text = f"[{len(result.matches)} matches - double-click to select]"
        elif result.status == MatchStatus.NO_MATCH:
            matched_text = "(no match)"
        elif result.status == MatchStatus.FAILED:
            matched_text = f"(error: {result.error_message or 'unknown'})"
        else:
            matched_text = ""

        matched_item = QTableWidgetItem(matched_text)
        self.results_table.setItem(row, 4, matched_item)

    def _get_status_display(self, status: MatchStatus) -> str:
        """Get display text for match status."""
        status_map = {
            MatchStatus.PENDING: "PENDING",
            MatchStatus.SEARCHING: "SEARCHING",
            MatchStatus.MATCHED: "MATCHED",
            MatchStatus.MULTIPLE_MATCHES: "MULTIPLE",
            MatchStatus.NO_MATCH: "NO MATCH",
            MatchStatus.RENAMED: "RENAMED",
            MatchStatus.SKIPPED: "SKIPPED",
            MatchStatus.FAILED: "FAILED",
        }
        return status_map.get(status, "UNKNOWN")

    def _get_selected_rows(self) -> List[int]:
        """Get list of selected row indices (via checkboxes)."""
        selected = []
        for row in range(self.results_table.rowCount()):
            checkbox_widget = self.results_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    selected.append(row)
        return selected

    def _on_checkbox_changed(self, state: int) -> None:
        """Handle checkbox state change."""
        selected = self._get_selected_rows()
        self.selection_label.setText(f"Selected: {len(selected)} file(s)")
        if self._scan_worker and self._scan_worker.isRunning():
            self._set_result_actions_enabled(False)
            return

        self.view_details_button.setEnabled(len(selected) > 0)
        self.manual_search_button.setEnabled(len(selected) > 0)

    def _clear_scan_results(self) -> None:
        """Clear stale scan results before starting a replacement scan."""
        self._files = []
        self.results_table.setRowCount(0)
        self.selection_label.setText("Selected: 0 file(s)")

    def _set_result_actions_enabled(self, enabled: bool) -> None:
        """Enable or disable actions that operate on the current result set."""
        self.view_details_button.setEnabled(enabled)
        self.manual_search_button.setEnabled(enabled)
        self.rename_button.setEnabled(enabled)

    def _shutdown_scan_worker(self) -> None:
        """Cancel any active scan worker before the widget is destroyed."""
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.cancel()
            wait = getattr(self._scan_worker, "wait", None)
            if callable(wait):
                wait(1000)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Ensure background scan work is stopped before widget teardown."""
        self._shutdown_scan_worker()
        super().closeEvent(event)

    def _show_match_detail_dialog(self, result: MatchResult, row_index: int) -> None:
        """Show match detail dialog for selecting from multiple matches."""
        from ..widgets.match_detail_dialog import MatchDetailDialog

        dialog = MatchDetailDialog(result, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            selected_match = dialog.get_selected_match()
            if selected_match and self._manager:
                self._manager.select_match(row_index, selected_match)

    def _show_match_info(self, result: MatchResult) -> None:
        """Show information about a single match."""
        if not result.selected_match:
            return

        match = result.selected_match
        info_text = (
            f"<b>Title:</b> {match.title}<br>"
            f"<b>Studio:</b> {match.studio}<br>"
            f"<b>Performers:</b> {', '.join(match.performers)}<br>"
            f"<b>Date:</b> {match.date or 'N/A'}<br>"
            f"<b>Source:</b> {match.source_database.upper()}<br>"
            f"<b>Confidence:</b> {int(result.confidence * 100)}%<br>"
            f"<b>URL:</b> {match.source_url or 'N/A'}"
        )
        QMessageBox.information(self, "Match Details", info_text)

    def _update_skip_keywords_display(self, keywords: List[str]) -> None:
        """Update UI summary for configured search exclusions."""
        count = len(keywords or [])
        if count == 0:
            self.skip_keywords_status_label.setText("No exclusions configured")
            self.skip_keywords_status_label.setToolTip("")
            return

        self.skip_keywords_status_label.setText(f"{count} exclusion(s) configured")
        self.skip_keywords_status_label.setToolTip("\n".join(keywords))

    def _clear_results(self) -> None:
        """Clear scan/match results when the source folder changes."""
        self._files = []
        self.results_table.setRowCount(0)
        self.selection_label.setText("Selected: 0 files")
        self.view_details_button.setEnabled(False)
        self.manual_search_button.setEnabled(False)
        self.match_button.setEnabled(False)
        self.status_label.setText("Ready. Select a folder to begin.")
        self.progress_bar.setValue(0)
