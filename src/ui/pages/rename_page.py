"""RenamePage — batch file renaming with token-based pattern builder."""

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QCheckBox,
    QProgressBar,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QSpinBox,
    QHeaderView,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QSizePolicy,
)

from ...core.ffprobe_worker import FFprobeWorker
from ...core.folder_scan_worker import FolderScanWorker
from ...data.models import VideoMetadata, RenameToken
from ...services.config_service import ConfigService
from ...utils.dialog_utils import get_dialog_start_dir, update_dialog_last_dir
from ..components.page_header import PageHeader
from ..components.split_layout import SplitLayout
from ..theme.theme_engine import ThemeEngine
from ..theme.style_utils import set_status_color

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# RenameTokenWidget — drag-reorderable token list (preserved from rename_tab_widget)
# ---------------------------------------------------------------------------


class RenameTokenWidget(QListWidget):
    """
    Drag-reorderable list of rename tokens with enable/disable checkboxes.

    Signals:
        tokens_changed: Emitted when token order or enabled state changes.
    """

    tokens_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

        self._checkboxes: Dict[RenameToken, QCheckBox] = {}
        self._setup_tokens()

        model = self.model()
        if model is not None:
            model.rowsMoved.connect(self._on_rows_moved)

    def _setup_tokens(self) -> None:
        """Set up the default token list."""
        default_tokens = [
            (RenameToken.ORIGINAL, "Original Name", True),
            (RenameToken.INDEX, "Index Number", False),
            (RenameToken.DATE_MODIFIED, "Date Modified", False),
            (RenameToken.RESOLUTION, "Resolution", False),
            (RenameToken.FPS, "FPS", False),
            (RenameToken.CODEC, "Codec", False),
            (RenameToken.DURATION, "Duration", False),
            (RenameToken.BITRATE, "Bitrate", False),
            (RenameToken.CUSTOM_TEXT, "Custom Text", False),
        ]
        for token, label, enabled in default_tokens:
            self._add_token_item(token, label, enabled)

    def _add_token_item(self, token: RenameToken, label: str, enabled: bool) -> None:
        """Add a single token item to the list."""
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, token)

        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 2, 4, 2)

        drag_handle = QLabel("⠿")
        drag_handle.setObjectName("dragHandle")

        checkbox = QCheckBox(label)
        checkbox.setChecked(enabled)
        checkbox.stateChanged.connect(self._on_checkbox_changed)

        layout.addWidget(drag_handle)
        layout.addWidget(checkbox)
        layout.addStretch()

        self._checkboxes[token] = checkbox
        item.setSizeHint(widget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widget)

    def _on_checkbox_changed(self, state: int) -> None:
        self.tokens_changed.emit()

    def _on_rows_moved(self) -> None:
        self.tokens_changed.emit()

    def get_ordered_tokens(self) -> List[RenameToken]:
        """Get tokens in current order."""
        tokens = []
        for i in range(self.count()):
            item = self.item(i)
            if item is not None:
                token = item.data(Qt.ItemDataRole.UserRole)
                tokens.append(token)
        return tokens

    def get_enabled_tokens(self) -> Dict[RenameToken, bool]:
        """Get enabled state for each token."""
        return {
            token: checkbox.isChecked() for token, checkbox in self._checkboxes.items()
        }

    def set_token_order(self, order: List[str]) -> None:
        """Reorder tokens based on string values."""
        items_data = []
        for i in range(self.count()):
            item = self.item(i)
            if item:
                token = item.data(Qt.ItemDataRole.UserRole)
                items_data.append((token, self._checkboxes[token].isChecked()))

        def sort_key(item_tuple):
            token, _ = item_tuple
            try:
                return order.index(token.value)
            except ValueError:
                return len(order)

        items_data.sort(key=sort_key)
        self.clear()
        self._checkboxes.clear()
        for token, enabled in items_data:
            label = token.name.replace("_", " ").title()
            self._add_token_item(token, label, enabled)

    def set_tokens_enabled(self, enabled_map: Dict[str, bool]) -> None:
        """Set enabled state for tokens."""
        for token, checkbox in self._checkboxes.items():
            if token.value in enabled_map:
                checkbox.setChecked(enabled_map[token.value])


# ---------------------------------------------------------------------------
# RenamePreviewTable — preview table with conflict highlighting (preserved)
# ---------------------------------------------------------------------------


class RenamePreviewTable(QTableWidget):
    """Table widget showing rename preview with conflict highlighting."""

    selection_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["☐", "Original Name", "New Name"])

        self._checked_states: List[bool] = []
        self._conflict_rows: set = set()

        self._engine = ThemeEngine.instance()
        self._update_theme_colors()
        self._engine.theme_changed.connect(self._on_theme_changed)

        header = self.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.setColumnWidth(0, 30)

        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.itemChanged.connect(self._on_item_changed)

    def _update_theme_colors(self) -> None:
        self._conflict_color = QColor(self._engine.get_color("red-dim"))

    def _on_theme_changed(self, _theme: str) -> None:
        self._update_theme_colors()
        self._reapply_row_colors()

    def _reapply_row_colors(self) -> None:
        for row in range(self.rowCount()):
            is_conflict = row in self._conflict_rows
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item:
                    if is_conflict:
                        item.setBackground(self._conflict_color)
                    else:
                        item.setBackground(QBrush())

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() == 0:
            row = item.row()
            is_checked = item.checkState() == Qt.CheckState.Checked
            if row < len(self._checked_states):
                self._checked_states[row] = is_checked
            self.selection_changed.emit()

    def set_all_checked(self, checked: bool) -> None:
        self.blockSignals(True)
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item:
                item.setCheckState(
                    Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
                )
                if row < len(self._checked_states):
                    self._checked_states[row] = checked
        self.blockSignals(False)
        self.selection_changed.emit()

    def get_checked_indices(self) -> List[int]:
        return [i for i, checked in enumerate(self._checked_states) if checked]

    def get_checked_count(self) -> int:
        return sum(1 for checked in self._checked_states if checked)

    def get_checked_conflict_count(self) -> int:
        return sum(
            1
            for i, checked in enumerate(self._checked_states)
            if checked and i in self._conflict_rows
        )

    def clear_preview(self) -> None:
        self.clearSelection()
        self._checked_states = []
        self._conflict_rows = set()
        self.setRowCount(0)

    def update_preview(
        self, rename_pairs: List[Tuple[str, str]], conflicts: set
    ) -> None:
        self.blockSignals(True)
        old_checked = self._checked_states.copy()
        new_count = len(rename_pairs)

        self._checked_states = []
        for i in range(new_count):
            if i < len(old_checked):
                self._checked_states.append(old_checked[i])
            else:
                self._checked_states.append(True)

        self._conflict_rows = set()
        self.setRowCount(new_count)

        for row, (original, new_name) in enumerate(rename_pairs):
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            )
            checkbox_item.setCheckState(
                Qt.CheckState.Checked
                if self._checked_states[row]
                else Qt.CheckState.Unchecked
            )
            original_item = QTableWidgetItem(original)
            new_item = QTableWidgetItem(new_name)

            if new_name in conflicts:
                self._conflict_rows.add(row)
                for it in [checkbox_item, original_item, new_item]:
                    it.setBackground(self._conflict_color)

            self.setItem(row, 0, checkbox_item)
            self.setItem(row, 1, original_item)
            self.setItem(row, 2, new_item)

        self.blockSignals(False)
        self.selection_changed.emit()


# ---------------------------------------------------------------------------
# RenamePage — main page widget
# ---------------------------------------------------------------------------


class RenamePage(QWidget):
    """
    Rename page — batch file renaming with token-based pattern builder.

    Replaces RenameTabWidget with a SplitLayout-based design.
    Preserves all business logic: scanning, token ordering, preview, rename.

    Signals:
        apply_requested: Emitted when the user clicks Apply Rename.
        preview_requested: Emitted when the user clicks Refresh Preview.
    """

    apply_requested = pyqtSignal()
    preview_requested = pyqtSignal()

    # Legacy compatibility signals (mirrors RenameTabWidget)
    rename_started = pyqtSignal()
    rename_completed = pyqtSignal(int, int)  # success, failures

    def __init__(self, rename_manager=None, parent=None):
        super().__init__(parent)
        self._rename_manager = rename_manager
        self._metadata_list: List[VideoMetadata] = []
        self._ffprobe_worker: Optional[FFprobeWorker] = None
        self._folder_scan_worker: Optional[FolderScanWorker] = None
        self._has_conflicts = False
        self._config = ConfigService()

        self._setup_ui()
        self._connect_signals()
        self._load_settings()

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
                title="Rename",
                description="Build a filename pattern from tokens, then preview and apply.",
            )
        )

        # 2. Source bar
        source_row = QHBoxLayout()
        source_row.setSpacing(8)
        source_row.addWidget(QLabel("Source:"))
        self._source_input = QLineEdit()
        self._source_input.setPlaceholderText("Choose a folder to rename files in…")
        source_row.addWidget(self._source_input, stretch=1)
        self._browse_btn = QPushButton("Browse")
        self._browse_btn.setObjectName("btnWire")
        self._browse_btn.setProperty("button_role", "secondary")
        source_row.addWidget(self._browse_btn)
        self._scan_btn = QPushButton("Scan")
        self._scan_btn.setObjectName("btnPrimary")
        self._scan_btn.setProperty("button_role", "primary")
        self._scan_btn.setEnabled(False)
        source_row.addWidget(self._scan_btn)
        root.addLayout(source_row)

        # 3. Scan progress row (hidden until scan starts)
        scan_row = QHBoxLayout()
        self._scan_progress = QProgressBar()
        self._scan_progress.setVisible(False)
        self._scan_status = QLabel("")
        self._scan_status.setVisible(False)
        scan_row.addWidget(self._scan_progress)
        scan_row.addWidget(self._scan_status)
        root.addLayout(scan_row)

        # 4. SplitLayout: token builder left (fixed ~260px), preview right (flex)
        # We use a custom horizontal layout to give left a fixed width
        split_container = QWidget()
        split_container.setObjectName("splitLayout")
        split_h = QHBoxLayout(split_container)
        split_h.setContentsMargins(0, 0, 0, 0)
        split_h.setSpacing(20)

        # --- LEFT panel (fixed 260px): token builder ---
        left_panel = QWidget()
        left_panel.setObjectName("splitLeft")
        left_panel.setFixedWidth(260)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # "Pattern Tokens" section header
        tokens_label = QLabel("Pattern Tokens")
        tokens_label.setObjectName("sidebarSection")
        left_layout.addWidget(tokens_label)

        self._token_widget = RenameTokenWidget()
        left_layout.addWidget(self._token_widget, stretch=1)

        # Separator line
        sep_line = QFrame()
        sep_line.setFrameShape(QFrame.Shape.HLine)
        sep_line.setFrameShadow(QFrame.Shadow.Sunken)
        left_layout.addWidget(sep_line)

        # Token settings
        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(6)

        sep_row = QHBoxLayout()
        sep_row.addWidget(QLabel("Separator:"))
        self._separator_input = QLineEdit("_")
        self._separator_input.setMaximumWidth(60)
        sep_row.addWidget(self._separator_input)
        sep_row.addStretch()
        settings_layout.addLayout(sep_row)

        custom_row = QHBoxLayout()
        custom_row.addWidget(QLabel("Custom text:"))
        self._custom_text_input = QLineEdit()
        self._custom_text_input.setPlaceholderText("Text for custom token…")
        custom_row.addWidget(self._custom_text_input)
        settings_layout.addLayout(custom_row)

        index_row = QHBoxLayout()
        index_row.addWidget(QLabel("Index Start:"))
        self._index_start_spin = QSpinBox()
        self._index_start_spin.setMinimum(0)
        self._index_start_spin.setMaximum(9999)
        self._index_start_spin.setValue(1)
        index_row.addWidget(self._index_start_spin)
        index_row.addStretch()
        settings_layout.addLayout(index_row)

        padding_row = QHBoxLayout()
        padding_row.addWidget(QLabel("Padding:"))
        self._index_padding_spin = QSpinBox()
        self._index_padding_spin.setMinimum(1)
        self._index_padding_spin.setMaximum(6)
        self._index_padding_spin.setValue(2)
        padding_row.addWidget(self._index_padding_spin)
        padding_row.addStretch()
        settings_layout.addLayout(padding_row)

        date_row = QHBoxLayout()
        date_row.addWidget(QLabel("Date Format:"))
        self._date_format_input = QLineEdit("%Y-%m-%d")
        date_row.addWidget(self._date_format_input)
        settings_layout.addLayout(date_row)

        remove_row = QHBoxLayout()
        remove_row.addWidget(QLabel("Remove chars:"))
        self._remove_first_spin = QSpinBox()
        self._remove_first_spin.setMinimum(0)
        self._remove_first_spin.setMaximum(999)
        self._remove_first_spin.setValue(0)
        self._remove_first_spin.setToolTip("Characters to remove from start of name")
        remove_row.addWidget(self._remove_first_spin)
        remove_row.addWidget(QLabel("first /"))
        self._remove_last_spin = QSpinBox()
        self._remove_last_spin.setMinimum(0)
        self._remove_last_spin.setMaximum(999)
        self._remove_last_spin.setValue(0)
        self._remove_last_spin.setToolTip("Characters to remove from end of name")
        remove_row.addWidget(self._remove_last_spin)
        remove_row.addWidget(QLabel("last"))
        settings_layout.addLayout(remove_row)

        left_layout.addLayout(settings_layout)

        split_h.addWidget(left_panel)

        # --- RIGHT panel (flex): preview table ---
        right_panel = QWidget()
        right_panel.setObjectName("splitRight")
        right_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        preview_label = QLabel("Preview")
        preview_label.setObjectName("sidebarSection")
        right_layout.addWidget(preview_label)

        # Select all row
        select_row = QHBoxLayout()
        self._select_all_checkbox = QCheckBox("Select All")
        self._select_all_checkbox.setChecked(True)
        self._select_all_checkbox.setTristate(True)
        select_row.addWidget(self._select_all_checkbox)
        select_row.addStretch()
        self._selected_count_label = QLabel("0 of 0 selected")
        select_row.addWidget(self._selected_count_label)
        right_layout.addLayout(select_row)

        self._preview_table = RenamePreviewTable()
        right_layout.addWidget(self._preview_table, stretch=1)

        # Conflict warning label
        self._conflict_label = QLabel("")
        self._conflict_label.setObjectName("boldLabel")
        set_status_color(self._conflict_label, "error")
        self._conflict_label.setVisible(False)
        right_layout.addWidget(self._conflict_label)

        split_h.addWidget(right_panel)

        root.addWidget(split_container, stretch=1)

        # 5. Action bar
        action_row = QHBoxLayout()
        action_row.addStretch()

        self._refresh_btn = QPushButton("Refresh Preview")
        self._refresh_btn.setObjectName("btnSecondary")
        self._refresh_btn.setProperty("button_role", "secondary")
        self._refresh_btn.setEnabled(False)

        self._apply_btn = QPushButton("APPLY RENAME")
        self._apply_btn.setObjectName("btnPrimary")
        self._apply_btn.setProperty("button_role", "cta")
        self._apply_btn.setEnabled(False)
        self._apply_btn.setMinimumWidth(140)

        action_row.addWidget(self._refresh_btn)
        action_row.addWidget(self._apply_btn)
        root.addLayout(action_row)

        # 6. Progress + status label
        self._rename_progress = QProgressBar()
        self._rename_progress.setVisible(False)
        root.addWidget(self._rename_progress)

        self._status_label = QLabel("")
        self._status_label.setVisible(False)
        root.addWidget(self._status_label)

    def _connect_signals(self) -> None:
        """Wire up all signal connections."""
        self._browse_btn.clicked.connect(self._on_browse)
        self._source_input.textChanged.connect(self._on_source_changed)
        self._scan_btn.clicked.connect(self._on_scan)

        self._token_widget.tokens_changed.connect(self._on_settings_changed)
        self._separator_input.textChanged.connect(self._on_settings_changed)
        self._custom_text_input.textChanged.connect(self._on_settings_changed)
        self._index_start_spin.valueChanged.connect(self._on_settings_changed)
        self._index_padding_spin.valueChanged.connect(self._on_settings_changed)
        self._date_format_input.textChanged.connect(self._on_settings_changed)
        self._remove_first_spin.valueChanged.connect(self._on_settings_changed)
        self._remove_last_spin.valueChanged.connect(self._on_settings_changed)

        self._refresh_btn.clicked.connect(self._on_refresh_preview)
        self._apply_btn.clicked.connect(self._on_apply_rename)

        self._preview_table.selection_changed.connect(self._on_selection_changed)
        self._select_all_checkbox.stateChanged.connect(self._on_select_all_changed)

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _load_settings(self) -> None:
        """Load saved settings from config."""
        source = self._config.get("rename.last_folder", "")
        if source:
            self._source_input.setText(source)

        token_order = self._config.get("rename.token_order", [])
        if token_order:
            self._token_widget.set_token_order(token_order)

        token_enabled = self._config.get("rename.token_enabled", {})
        if token_enabled:
            self._token_widget.set_tokens_enabled(token_enabled)

        self._separator_input.setText(self._config.get("rename.separator", "_"))
        self._custom_text_input.setText(self._config.get("rename.custom_text", ""))
        self._index_start_spin.setValue(self._config.get("rename.index_start", 1))
        self._index_padding_spin.setValue(self._config.get("rename.index_padding", 2))
        self._date_format_input.setText(
            self._config.get("rename.date_format", "%Y-%m-%d")
        )
        self._remove_first_spin.setValue(self._config.get("rename.remove_first", 0))
        self._remove_last_spin.setValue(self._config.get("rename.remove_last", 0))

    def _save_settings(self) -> None:
        """Save current settings to config."""
        self._config.set(
            "rename.last_folder", self._source_input.text(), save=False
        )
        token_order = [t.value for t in self._token_widget.get_ordered_tokens()]
        self._config.set("rename.token_order", token_order, save=False)

        token_enabled = {
            t.value: e for t, e in self._token_widget.get_enabled_tokens().items()
        }
        self._config.set("rename.token_enabled", token_enabled, save=False)

        self._config.set("rename.separator", self._separator_input.text(), save=False)
        self._config.set(
            "rename.custom_text", self._custom_text_input.text(), save=False
        )
        self._config.set(
            "rename.index_start", self._index_start_spin.value(), save=False
        )
        self._config.set(
            "rename.index_padding", self._index_padding_spin.value(), save=False
        )
        self._config.set(
            "rename.date_format", self._date_format_input.text(), save=False
        )
        self._config.set(
            "rename.remove_first", self._remove_first_spin.value(), save=False
        )
        self._config.set(
            "rename.remove_last", self._remove_last_spin.value(), save=False
        )
        self._config.save()

    # ------------------------------------------------------------------
    # Source folder handling
    # ------------------------------------------------------------------

    def _on_browse(self) -> None:
        """Open directory picker for source folder."""
        start_dir = get_dialog_start_dir(
            self._source_input.text(), "rename.last_folder"
        )
        folder = QFileDialog.getExistingDirectory(
            self, "Select Source Folder", start_dir
        )
        if folder:
            update_dialog_last_dir(folder)
            self._source_input.setText(folder)
            self._clear_preview_state()
            self._save_settings()

    def _on_source_changed(self, text: str) -> None:
        """Enable scan button only when path points to a real directory."""
        self._scan_btn.setEnabled(bool(text) and Path(text).is_dir())

    # ------------------------------------------------------------------
    # Scan flow
    # ------------------------------------------------------------------

    def _on_scan(self) -> None:
        """Start scanning the source folder."""
        source_path = self._source_input.text()
        if not source_path or not Path(source_path).is_dir():
            QMessageBox.warning(self, "Invalid Folder", "Please select a valid folder.")
            return

        self._scan_progress.setVisible(True)
        self._scan_progress.setMaximum(0)
        self._scan_progress.setValue(0)
        self._scan_status.setVisible(True)
        self._scan_status.setText("Finding video files…")
        self._scan_btn.setEnabled(False)
        self._browse_btn.setEnabled(False)
        self._source_input.setEnabled(False)

        self._folder_scan_worker = FolderScanWorker(source_path, recursive=False)
        self._folder_scan_worker.progress.connect(self._on_folder_scan_progress)
        self._folder_scan_worker.completed.connect(self._on_folder_scan_completed)
        self._folder_scan_worker.error.connect(self._on_folder_scan_error)
        self._folder_scan_worker.files_deleted.connect(self._on_files_deleted)
        self._folder_scan_worker.start()

    def _on_folder_scan_progress(self, count: int, message: str) -> None:
        self._scan_status.setText(message)

    def _on_folder_scan_completed(self, video_files: List[str]) -> None:
        """Transition from folder scan to ffprobe metadata extraction."""
        if self._folder_scan_worker:
            self._folder_scan_worker.deleteLater()
            self._folder_scan_worker = None

        if not video_files:
            QMessageBox.information(
                self,
                "No Videos Found",
                "No video files found in the selected folder.",
            )
            self._restore_scan_controls()
            return

        source_path = self._source_input.text()
        self._metadata_list.clear()
        self._ffprobe_worker = FFprobeWorker(video_files, base_folder=source_path)
        self._ffprobe_worker.progress.connect(self._on_scan_progress)
        self._ffprobe_worker.metadata_ready.connect(self._on_metadata_ready)
        self._ffprobe_worker.completed.connect(self._on_scan_completed)

        self._scan_progress.setMaximum(len(video_files))
        self._scan_progress.setValue(0)
        self._scan_status.setText("Extracting metadata…")
        self._ffprobe_worker.start()

    def _on_folder_scan_error(self, error_message: str) -> None:
        QMessageBox.warning(
            self, "Scan Error", f"Failed to scan folder:\n{error_message}"
        )
        if self._folder_scan_worker:
            self._folder_scan_worker.deleteLater()
            self._folder_scan_worker = None
        self._restore_scan_controls()

    def _on_scan_progress(self, current: int, total: int, file_path: str) -> None:
        self._scan_progress.setValue(current)
        self._scan_status.setText(f"Scanning: {Path(file_path).name}")

    def _on_metadata_ready(self, metadata: VideoMetadata) -> None:
        self._metadata_list.append(metadata)

    def _on_scan_completed(self, results: List[VideoMetadata]) -> None:
        """Handle scan completion."""
        self._scan_progress.setVisible(False)
        self._scan_status.setVisible(False)
        self._restore_scan_controls()

        self._metadata_list = sorted(
            results, key=lambda m: Path(m.file_path).name.lower()
        )

        if self._metadata_list:
            self._refresh_btn.setEnabled(True)
            self._update_preview()
            self._save_settings()

        logger.info("Scan completed: %d files found", len(self._metadata_list))

    def _restore_scan_controls(self) -> None:
        """Re-enable source controls after scan finishes or errors."""
        self._source_input.setEnabled(True)
        self._browse_btn.setEnabled(True)
        self._scan_btn.setEnabled(Path(self._source_input.text()).is_dir())

    # ------------------------------------------------------------------
    # Settings change
    # ------------------------------------------------------------------

    def _on_settings_changed(self) -> None:
        """Handle any settings change — update preview and save."""
        self._save_settings()
        if self._metadata_list:
            self._update_preview()

    # ------------------------------------------------------------------
    # Selection handling
    # ------------------------------------------------------------------

    def _on_selection_changed(self) -> None:
        self._update_selection_ui()

    def _on_select_all_changed(self, state: int) -> None:
        if state == Qt.CheckState.PartiallyChecked.value:
            return
        checked = state == Qt.CheckState.Checked.value
        self._preview_table.set_all_checked(checked)

    def _update_selection_ui(self) -> None:
        checked_count = self._preview_table.get_checked_count()
        total_count = len(self._metadata_list)
        conflict_count = self._preview_table.get_checked_conflict_count()

        self._selected_count_label.setText(f"{checked_count} of {total_count} selected")

        self._select_all_checkbox.blockSignals(True)
        if checked_count == 0:
            self._select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        elif checked_count == total_count:
            self._select_all_checkbox.setCheckState(Qt.CheckState.Checked)
        else:
            self._select_all_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        self._select_all_checkbox.blockSignals(False)

        self._update_apply_button(checked_count, conflict_count)

    def _update_apply_button(self, checked_count: int, conflict_count: int) -> None:
        if checked_count == 0:
            self._apply_btn.setEnabled(False)
            self._apply_btn.setText("Apply Rename")
        elif conflict_count > 0:
            self._apply_btn.setEnabled(False)
            self._apply_btn.setText(
                f"Rename {checked_count} File{'s' if checked_count != 1 else ''}"
            )
        else:
            self._apply_btn.setEnabled(True)
            self._apply_btn.setText(
                f"Rename {checked_count} File{'s' if checked_count != 1 else ''}"
            )

    # ------------------------------------------------------------------
    # Preview generation
    # ------------------------------------------------------------------

    def _generate_new_name(self, metadata: VideoMetadata, index: int) -> str:
        """Generate new filename stem based on current token settings."""
        parts = []
        separator = self._separator_input.text()
        enabled = self._token_widget.get_enabled_tokens()
        ordered = self._token_widget.get_ordered_tokens()

        original_name = Path(metadata.file_path).stem

        for token in ordered:
            if not enabled.get(token, False):
                continue

            if token == RenameToken.ORIGINAL:
                name = original_name
                remove_first = self._remove_first_spin.value()
                remove_last = self._remove_last_spin.value()
                if remove_first > 0:
                    name = name[remove_first:]
                if remove_last > 0 and len(name) > remove_last:
                    name = name[:-remove_last]
                elif remove_last > 0:
                    name = ""
                parts.append(name)
            elif token == RenameToken.INDEX:
                padding = self._index_padding_spin.value()
                start = self._index_start_spin.value()
                parts.append(str(start + index).zfill(padding))
            elif token == RenameToken.DATE_MODIFIED:
                try:
                    mtime = os.path.getmtime(metadata.file_path)
                    date_str = datetime.fromtimestamp(mtime).strftime(
                        self._date_format_input.text() or "%Y-%m-%d"
                    )
                    parts.append(date_str)
                except Exception:
                    parts.append("unknown_date")
            elif token == RenameToken.RESOLUTION:
                parts.append(metadata.resolution)
            elif token == RenameToken.FPS:
                parts.append(f"{metadata.fps:.2f}fps")
            elif token == RenameToken.CODEC:
                parts.append(metadata.codec)
            elif token == RenameToken.DURATION:
                minutes = int(metadata.duration // 60)
                seconds = int(metadata.duration % 60)
                parts.append(f"{minutes}m{seconds}s")
            elif token == RenameToken.BITRATE:
                parts.append(metadata.bitrate_label)
            elif token == RenameToken.CUSTOM_TEXT:
                custom = self._custom_text_input.text()
                if custom:
                    parts.append(custom)

        new_name = separator.join(parts) if parts else original_name
        return new_name

    def _on_refresh_preview(self) -> None:
        """Handle Refresh Preview button click."""
        self.preview_requested.emit()
        self._update_preview()

    def _update_preview(self) -> None:
        """Update the preview table with current token settings."""
        if not self._metadata_list:
            return

        rename_pairs = []
        new_names_count: Dict[str, int] = {}

        for i, metadata in enumerate(self._metadata_list):
            original_name = Path(metadata.file_path).name
            ext = Path(metadata.file_path).suffix
            new_stem = self._generate_new_name(metadata, i)
            new_name = f"{new_stem}{ext}"
            rename_pairs.append((original_name, new_name))
            new_names_count[new_name] = new_names_count.get(new_name, 0) + 1

        conflicts = {name for name, count in new_names_count.items() if count > 1}
        self._preview_table.update_preview(rename_pairs, conflicts)

        self._has_conflicts = bool(conflicts)
        if self._has_conflicts:
            set_status_color(self._conflict_label, "error")
            self._conflict_label.setText(
                f"Warning: {len(conflicts)} naming conflict(s) detected! "
                "Files with the same new name are highlighted."
            )
            self._conflict_label.setVisible(True)
        else:
            self._conflict_label.setVisible(False)

        self._update_selection_ui()

    # ------------------------------------------------------------------
    # Apply rename
    # ------------------------------------------------------------------

    def _on_apply_rename(self) -> None:
        """Execute the batch rename operation."""
        self.apply_requested.emit()

        checked_indices = self._preview_table.get_checked_indices()
        checked_count = len(checked_indices)

        if checked_count == 0:
            QMessageBox.warning(
                self,
                "No Files Selected",
                "Please select at least one file to rename.",
            )
            return

        conflict_count = self._preview_table.get_checked_conflict_count()
        if conflict_count > 0:
            QMessageBox.warning(
                self,
                "Conflicts Detected",
                f"{conflict_count} selected file(s) have naming conflicts. "
                "Please uncheck conflicting files or adjust your settings.",
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirm Rename",
            f"Are you sure you want to rename {checked_count} file(s)?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.rename_started.emit()

        success_count = 0
        failure_count = 0
        errors = []

        for i in checked_indices:
            if i >= len(self._metadata_list):
                continue
            metadata = self._metadata_list[i]
            try:
                old_path = Path(metadata.file_path)
                ext = old_path.suffix
                new_stem = self._generate_new_name(metadata, i)
                new_path = old_path.parent / f"{new_stem}{ext}"
                if old_path != new_path:
                    old_path.rename(new_path)
                    success_count += 1
                    logger.info("Renamed: %s -> %s", old_path.name, new_path.name)
            except Exception as e:
                failure_count += 1
                errors.append(f"{Path(metadata.file_path).name}: {str(e)}")
                logger.error("Failed to rename %s: %s", metadata.file_path, e)

        self.rename_completed.emit(success_count, failure_count)

        if failure_count == 0:
            QMessageBox.information(
                self,
                "Rename Complete",
                f"Successfully renamed {success_count} file(s).",
            )
        else:
            error_text = "\n".join(errors[:10])
            if len(errors) > 10:
                error_text += f"\n… and {len(errors) - 10} more errors"
            QMessageBox.warning(
                self,
                "Rename Completed with Errors",
                f"Renamed {success_count} file(s), {failure_count} failed.\n\n"
                f"Errors:\n{error_text}",
            )

        # Rescan to refresh the list after rename
        self._on_scan()

    # ------------------------------------------------------------------
    # Preview state helpers
    # ------------------------------------------------------------------

    def _clear_preview_state(self) -> None:
        """Invalidate any existing preview when source folder changes."""
        self._metadata_list = []
        self._has_conflicts = False
        self._preview_table.clear_preview()
        self._selected_count_label.setText("0 of 0 selected")
        self._conflict_label.setVisible(False)
        self._refresh_btn.setEnabled(False)
        self._apply_btn.setEnabled(False)
        self._apply_btn.setText("Apply Rename")
        self._select_all_checkbox.blockSignals(True)
        self._select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
        self._select_all_checkbox.blockSignals(False)

    def _on_files_deleted(self, count: int, paths: List[str]) -> None:
        """Notify user when zero-byte files are moved to trash during scan."""
        if count > 0:
            QMessageBox.information(
                self,
                "Invalid Files Removed",
                f"Moved {count} zero-byte corrupted file(s) to trash.\n\n"
                "These files can be recovered from your system trash if needed.",
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the entire page."""
        self._source_input.setEnabled(enabled)
        self._browse_btn.setEnabled(enabled)
        self._scan_btn.setEnabled(
            enabled and bool(self._source_input.text())
            and Path(self._source_input.text()).is_dir()
        )
        self._token_widget.setEnabled(enabled)
        self._select_all_checkbox.setEnabled(enabled and bool(self._metadata_list))
        self._preview_table.setEnabled(enabled)
        if enabled and self._metadata_list:
            self._update_selection_ui()
        else:
            self._apply_btn.setEnabled(False)
