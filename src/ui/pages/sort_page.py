"""SortPage — organize media files into folder structures."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QTreeWidget,
    QTreeWidgetItem,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
    QProgressBar,
    QMessageBox,
    QRadioButton,
    QButtonGroup,
)

from ...core.ffprobe_worker import FFprobeWorker, delete_macos_dotfiles
from ...core.folder_scan_worker import FolderScanWorker
from ...core.sort_manager import SortManager, SortWorker
from ...data.models import VideoMetadata, SortCriterion
from ...services.config_service import ConfigService
from ...utils.dialog_utils import get_dialog_start_dir, update_dialog_last_dir
from ..components.page_header import PageHeader
from ..components.split_layout import SplitLayout

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Reusable sub-widgets (adapted from sort_tab_widget.py)
# ---------------------------------------------------------------------------


class SortCriteriaWidget(QListWidget):
    """
    Drag-reorderable list of sort criteria with enable/disable checkboxes.

    Signals:
        criteria_changed: Emitted when criteria order or enabled state changes.
    """

    criteria_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

        self._checkboxes: Dict[SortCriterion, QCheckBox] = {}
        self._setup_criteria()

        model = self.model()
        if model is not None:
            model.rowsMoved.connect(self._on_rows_moved)

    def _setup_criteria(self) -> None:
        """Set up the default criteria list."""
        default_criteria = [
            (SortCriterion.FPS, "FPS", True),
            (SortCriterion.RESOLUTION, "Resolution", True),
            (SortCriterion.ORIENTATION, "Orientation", True),
            (SortCriterion.CODEC, "Codec", False),
            (SortCriterion.BITRATE, "Bitrate", False),
        ]
        for criterion, label, enabled in default_criteria:
            self._add_criterion_item(criterion, label, enabled)

    def _on_checkbox_changed(self, state: int) -> None:
        self.criteria_changed.emit()

    def _on_rows_moved(self) -> None:
        self.criteria_changed.emit()

    def get_ordered_criteria(self) -> List[SortCriterion]:
        """Return criteria in current visual order."""
        criteria = []
        for i in range(self.count()):
            item = self.item(i)
            if item is not None:
                criteria.append(item.data(Qt.ItemDataRole.UserRole))
        return criteria

    def get_enabled_criteria(self) -> Dict[SortCriterion, bool]:
        """Return enabled state for each criterion."""
        return {c: cb.isChecked() for c, cb in self._checkboxes.items()}

    def set_criteria_order(self, order: List[str]) -> None:
        """Reorder criteria based on criterion value strings."""
        items_data = []
        for i in range(self.count()):
            item = self.item(i)
            if item:
                criterion = item.data(Qt.ItemDataRole.UserRole)
                items_data.append(
                    (criterion, self._checkboxes[criterion].isChecked())
                )

        def sort_key(pair):
            criterion, _ = pair
            try:
                return order.index(criterion.value)
            except ValueError:
                return len(order)

        items_data.sort(key=sort_key)

        self.clear()
        self._checkboxes.clear()
        for criterion, enabled in items_data:
            self._add_criterion_item(
                criterion, criterion.name.replace("_", " ").title(), enabled
            )

    def set_criteria_enabled(self, enabled_map: Dict[str, bool]) -> None:
        """Set enabled state for criteria by value string map."""
        for criterion, checkbox in self._checkboxes.items():
            if criterion.value in enabled_map:
                checkbox.setChecked(enabled_map[criterion.value])

    def _add_criterion_item(
        self, criterion: SortCriterion, label: str, enabled: bool
    ) -> None:
        """Add a single criterion row with grip handle and checkbox."""
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, criterion)

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

        self._checkboxes[criterion] = checkbox
        item.setSizeHint(widget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widget)


class FolderPreviewWidget(QTreeWidget):
    """Tree widget showing a preview of the proposed folder structure."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Proposed Structure"])
        self.setRootIsDecorated(True)

    def update_preview(self, preview: Dict[str, List[str]]) -> None:
        """Populate the tree from a folder-path -> file-list mapping."""
        self.clear()
        if not preview:
            return

        root_items: Dict[str, QTreeWidgetItem] = {}

        for folder_path, files in sorted(preview.items()):
            parts = folder_path.strip("/").split("/") if folder_path else []

            current_parent = None
            current_path = ""

            for part in parts:
                current_path = f"{current_path}/{part}" if current_path else part
                if current_path not in root_items:
                    node = QTreeWidgetItem([f"📁 {part}"])
                    if current_parent:
                        current_parent.addChild(node)
                    else:
                        self.addTopLevelItem(node)
                    root_items[current_path] = node
                current_parent = root_items[current_path]

            parent_item = current_parent if current_parent else self.invisibleRootItem()
            for filename in sorted(files):
                file_item = QTreeWidgetItem([f"📄 {filename}"])
                if parent_item is not None:
                    parent_item.addChild(file_item)

        self.expandAll()


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------


class SortPage(QWidget):
    """
    Sort page — organize media into folder structures.

    Replaces SortTabWidget with a SplitLayout-based design.
    Preserves all SortManager / SortWorker signal connections.
    """

    sort_started = pyqtSignal()
    sort_completed = pyqtSignal(int, int)  # success, failures

    def __init__(self, sort_manager=None, parent=None):
        super().__init__(parent)
        self._metadata_list: List[VideoMetadata] = []
        self._ffprobe_worker: Optional[FFprobeWorker] = None
        self._folder_scan_worker: Optional[FolderScanWorker] = None
        self._sort_manager: Optional[SortManager] = sort_manager
        self._sort_worker: Optional[SortWorker] = None
        self._last_scanned_folder: Optional[str] = None
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
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # 1. Page header
        root.addWidget(
            PageHeader(
                title="Sort",
                description="Organize media into folder structures.",
            )
        )

        # 2. Source bar
        source_row = QHBoxLayout()
        source_row.setSpacing(8)
        source_row.addWidget(QLabel("Source:"))
        self._source_input = QLineEdit()
        self._source_input.setPlaceholderText("Choose a source folder…")
        self._source_input.setReadOnly(True)
        source_row.addWidget(self._source_input, stretch=1)
        self._source_browse_btn = QPushButton("Browse")
        self._source_browse_btn.setObjectName("btnDefault")
        source_row.addWidget(self._source_browse_btn)
        self._scan_btn = QPushButton("Scan")
        self._scan_btn.setObjectName("btnCyan")
        self._scan_btn.setEnabled(False)
        source_row.addWidget(self._scan_btn)
        root.addLayout(source_row)

        # 3. Scan progress row (hidden until a scan starts)
        scan_progress_row = QHBoxLayout()
        self._scan_progress = QProgressBar()
        self._scan_progress.setVisible(False)
        self._scan_status = QLabel("")
        self._scan_status.setVisible(False)
        self._scan_cancel_btn = QPushButton("Cancel Scan")
        self._scan_cancel_btn.setObjectName("btnWire")
        self._scan_cancel_btn.setProperty("button_role", "secondary")
        self._scan_cancel_btn.setVisible(False)
        scan_progress_row.addWidget(self._scan_progress)
        scan_progress_row.addWidget(self._scan_status)
        scan_progress_row.addWidget(self._scan_cancel_btn)
        root.addLayout(scan_progress_row)

        # 4. SplitLayout: criteria left, preview right
        split = SplitLayout(right_width=320)

        # --- LEFT panel: drag-reorderable criteria list ---
        left_layout = QVBoxLayout(split.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        criteria_label = QLabel("Sort by:")
        criteria_label.setObjectName("dpanelTitle")
        left_layout.addWidget(criteria_label)

        self._criteria_widget = SortCriteriaWidget()
        left_layout.addWidget(self._criteria_widget, stretch=1)

        # Up/down reorder buttons
        reorder_row = QHBoxLayout()
        self._move_up_btn = QPushButton("▲")
        self._move_up_btn.setObjectName("btnWire")
        self._move_up_btn.setProperty("button_role", "secondary")
        self._move_up_btn.setToolTip("Move selected criterion up")
        self._move_down_btn = QPushButton("▼")
        self._move_down_btn.setObjectName("btnWire")
        self._move_down_btn.setProperty("button_role", "secondary")
        self._move_down_btn.setToolTip("Move selected criterion down")
        reorder_row.addWidget(self._move_up_btn)
        reorder_row.addWidget(self._move_down_btn)
        reorder_row.addStretch()
        left_layout.addLayout(reorder_row)

        # Preserve subfolder hierarchy (lives naturally next to criteria)
        self._preserve_subfolders_cb = QCheckBox("Preserve subfolder hierarchy")
        self._preserve_subfolders_cb.setChecked(True)
        self._preserve_subfolders_cb.setToolTip(
            "Keep files within their original subfolders during sorting.\n"
            "Files will be sorted within each subfolder independently."
        )
        left_layout.addWidget(self._preserve_subfolders_cb)

        # --- RIGHT panel: preview tree ---
        right_layout = QVBoxLayout(split.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        preview_label = QLabel("Preview")
        preview_label.setObjectName("dpanelTitle")
        right_layout.addWidget(preview_label)

        self._preview_tree = FolderPreviewWidget()
        right_layout.addWidget(self._preview_tree, stretch=1)

        expand_row = QHBoxLayout()
        self._expand_all_btn = QPushButton("Expand All")
        self._expand_all_btn.setObjectName("btnWire")
        self._expand_all_btn.setProperty("button_role", "secondary")
        self._collapse_all_btn = QPushButton("Collapse All")
        self._collapse_all_btn.setObjectName("btnWire")
        self._collapse_all_btn.setProperty("button_role", "secondary")
        expand_row.addWidget(self._expand_all_btn)
        expand_row.addWidget(self._collapse_all_btn)
        expand_row.addStretch()
        right_layout.addLayout(expand_row)

        root.addWidget(split, stretch=1)

        # 5. Destination section
        dest_label = QLabel("Destination:")
        dest_label.setObjectName("dpanelTitle")
        root.addWidget(dest_label)

        dest_row = QHBoxLayout()
        self._dest_input = QLineEdit()
        self._dest_input.setPlaceholderText(
            "Output folder (leave empty to sort in place)"
        )
        self._dest_browse_btn = QPushButton("Browse")
        self._dest_browse_btn.setObjectName("btnWire")
        self._dest_browse_btn.setProperty("button_role", "secondary")
        dest_row.addWidget(self._dest_input, stretch=1)
        dest_row.addWidget(self._dest_browse_btn)
        root.addLayout(dest_row)

        # Move vs Copy
        mode_row = QHBoxLayout()
        self._move_radio = QRadioButton("Move files")
        self._copy_radio = QRadioButton("Copy files")
        self._move_radio.setChecked(True)
        self._option_group = QButtonGroup(self)
        self._option_group.addButton(self._move_radio)
        self._option_group.addButton(self._copy_radio)
        mode_row.addWidget(self._move_radio)
        mode_row.addWidget(self._copy_radio)
        mode_row.addStretch()
        root.addLayout(mode_row)

        # macOS dotfiles cleanup
        self._delete_dotfiles_cb = QCheckBox(
            "Remove hidden macOS files (._*) during scan"
        )
        self._delete_dotfiles_cb.setChecked(True)
        self._delete_dotfiles_cb.setToolTip(
            "Automatically delete macOS resource fork files (files starting with '._')\n"
            "that are created when copying files from macOS to other drives."
        )
        root.addWidget(self._delete_dotfiles_cb)

        # Undo sort checkbox (shown as a QCheckBox per plan spec)
        self._unsort_cb = QCheckBox("Undo sort (move files back)")
        self._unsort_cb.setToolTip(
            "Move all files back up to their first-level parent folder.\n"
            "Example: Account1/30fps/1080p/video.mp4 → Account1/video.mp4"
        )
        self._unsort_cb.setEnabled(False)
        root.addWidget(self._unsort_cb)

        # 6. Action bar
        action_row = QHBoxLayout()
        action_row.addStretch()

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("btnSecondary")
        self._cancel_btn.setProperty("button_role", "secondary")
        self._cancel_btn.setVisible(False)

        self._sort_btn = QPushButton("Sort Files")
        self._sort_btn.setObjectName("btnPrimary")
        self._sort_btn.setProperty("button_role", "primary")
        self._sort_btn.setEnabled(False)

        action_row.addWidget(self._cancel_btn)
        action_row.addWidget(self._sort_btn)
        root.addLayout(action_row)

        # 7. Progress bar + status label
        self._sort_progress = QProgressBar()
        self._sort_progress.setVisible(False)
        root.addWidget(self._sort_progress)

        self._status_label = QLabel("")
        self._status_label.setVisible(False)
        root.addWidget(self._status_label)

    def _connect_signals(self) -> None:
        """Wire up all signal connections."""
        # Source bar
        self._source_browse_btn.clicked.connect(self._on_browse_source)
        self._source_input.textChanged.connect(self._on_source_changed)
        self._scan_btn.clicked.connect(self._on_scan)
        self._scan_cancel_btn.clicked.connect(self._on_cancel_scan)

        # Criteria
        self._criteria_widget.criteria_changed.connect(self._update_preview)
        self._criteria_widget.criteria_changed.connect(self._save_settings)
        self._move_up_btn.clicked.connect(self._on_move_criterion_up)
        self._move_down_btn.clicked.connect(self._on_move_criterion_down)

        # Preserve subfolders
        self._preserve_subfolders_cb.stateChanged.connect(self._update_preview)
        self._preserve_subfolders_cb.stateChanged.connect(self._save_settings)

        # Preview tree controls
        self._expand_all_btn.clicked.connect(self._preview_tree.expandAll)
        self._collapse_all_btn.clicked.connect(self._preview_tree.collapseAll)

        # Destination
        self._dest_browse_btn.clicked.connect(self._on_browse_dest)
        self._dest_input.editingFinished.connect(self._save_settings)

        # Options
        self._move_radio.toggled.connect(self._save_settings)
        self._delete_dotfiles_cb.stateChanged.connect(self._save_settings)

        # Action buttons
        self._sort_btn.clicked.connect(self._on_sort)
        self._cancel_btn.clicked.connect(self._on_cancel)

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _load_settings(self) -> None:
        """Load saved settings from config."""
        last_source = self._config.get("sort.last_source_folder", "")
        last_dest = self._config.get("sort.last_dest_folder", "")
        if last_source:
            self._source_input.setText(last_source)
        if last_dest:
            self._dest_input.setText(last_dest)

        use_copy = self._config.get("sort.use_copy", False)
        if use_copy:
            self._copy_radio.setChecked(True)
        else:
            self._move_radio.setChecked(True)

        preserve = self._config.get("sort.preserve_subfolders", True)
        self._preserve_subfolders_cb.setChecked(preserve)

        delete_dotfiles = self._config.get("sort.delete_macos_dotfiles", True)
        self._delete_dotfiles_cb.setChecked(delete_dotfiles)

        criteria_order = self._config.get("sort.criteria_order", [])
        criteria_enabled = self._config.get("sort.criteria_enabled", {})
        if criteria_order:
            self._criteria_widget.set_criteria_order(criteria_order)
        if criteria_enabled:
            self._criteria_widget.set_criteria_enabled(criteria_enabled)

    def _save_settings(self) -> None:
        """Save current settings to config."""
        self._config.set(
            "sort.last_source_folder", self._source_input.text(), save=False
        )
        self._config.set("sort.last_dest_folder", self._dest_input.text(), save=False)
        self._config.set("sort.use_copy", self._copy_radio.isChecked(), save=False)
        self._config.set(
            "sort.preserve_subfolders",
            self._preserve_subfolders_cb.isChecked(),
            save=False,
        )
        self._config.set(
            "sort.delete_macos_dotfiles",
            self._delete_dotfiles_cb.isChecked(),
            save=False,
        )

        criteria_order = [
            c.value for c in self._criteria_widget.get_ordered_criteria()
        ]
        criteria_enabled = {
            c.value: enabled
            for c, enabled in self._criteria_widget.get_enabled_criteria().items()
        }
        self._config.set("sort.criteria_order", criteria_order, save=False)
        self._config.set("sort.criteria_enabled", criteria_enabled, save=False)

        self._config.save()

    # ------------------------------------------------------------------
    # Source folder handling
    # ------------------------------------------------------------------

    def _on_browse_source(self) -> None:
        """Open directory picker for source folder."""
        start_dir = get_dialog_start_dir(
            self._source_input.text(), "sort.last_source_folder"
        )
        folder = QFileDialog.getExistingDirectory(
            self, "Select Source Folder", start_dir
        )
        if folder:
            update_dialog_last_dir(folder)
            self._source_input.setText(folder)
            self._reset_scan_state(folder)
            self._save_settings()

    def _on_source_changed(self, text: str) -> None:
        """Enable scan button only when path points to a real directory."""
        self._scan_btn.setEnabled(Path(text).is_dir())

    # ------------------------------------------------------------------
    # Scan flow
    # ------------------------------------------------------------------

    def _on_scan(self) -> None:
        """Start scanning the source folder."""
        source_path = self._source_input.text()
        if not source_path or not Path(source_path).is_dir():
            return

        if self._delete_dotfiles_cb.isChecked():
            deleted_count, _ = delete_macos_dotfiles(source_path, recursive=True)
            if deleted_count > 0:
                logger.info(
                    "Cleaned up %d macOS dotfiles from %s", deleted_count, source_path
                )

        # Show scan progress
        self._scan_progress.setVisible(True)
        self._scan_progress.setMaximum(0)
        self._scan_progress.setValue(0)
        self._scan_status.setVisible(True)
        self._scan_status.setText("Finding video files…")
        self._scan_btn.setEnabled(False)
        self._source_browse_btn.setEnabled(False)
        self._source_input.setEnabled(False)

        self._folder_scan_worker = FolderScanWorker(source_path, recursive=True)
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
                "No video files were found in the selected folder.",
            )
            self._restore_scan_controls()
            return

        self._metadata_list.clear()
        self._preview_tree.clear()

        source_path = self._source_input.text()
        self._ffprobe_worker = FFprobeWorker(video_files, base_folder=source_path)
        self._ffprobe_worker.progress.connect(self._on_scan_progress)
        self._ffprobe_worker.metadata_ready.connect(self._on_metadata_ready)
        self._ffprobe_worker.completed.connect(self._on_scan_completed)

        self._scan_progress.setMaximum(len(video_files))
        self._scan_progress.setValue(0)
        self._scan_status.setText("Extracting metadata…")
        self._scan_cancel_btn.setVisible(True)
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

    def _on_scan_completed(self, results: list) -> None:
        """Handle ffprobe scan completion."""
        self._scan_progress.setVisible(False)
        self._scan_cancel_btn.setVisible(False)
        self._scan_cancel_btn.setEnabled(True)
        self._restore_scan_controls()

        was_cancelled = (
            self._ffprobe_worker._cancelled if self._ffprobe_worker else False
        )

        if was_cancelled:
            self._scan_status.setText("Scan cancelled")
            self._scan_status.setVisible(True)
            self._metadata_list.clear()
            self._preview_tree.clear()
        elif self._metadata_list:
            self._scan_status.setText(
                f"Found {len(self._metadata_list)} video files"
            )
            self._scan_status.setVisible(True)
            self._sort_btn.setEnabled(True)
            self._unsort_cb.setEnabled(True)
            self._update_preview()
        else:
            self._scan_status.setVisible(False)
            QMessageBox.warning(
                self,
                "Scan Failed",
                "Failed to extract metadata from video files. "
                "Make sure ffprobe is installed.",
            )

        self._ffprobe_worker = None

    def _on_cancel_scan(self) -> None:
        """Cancel the running ffprobe scan."""
        if self._ffprobe_worker:
            self._ffprobe_worker.cancel()
            self._scan_status.setText("Cancelling…")
            self._scan_cancel_btn.setEnabled(False)

    def _restore_scan_controls(self) -> None:
        """Re-enable source controls after a scan finishes or errors."""
        self._source_input.setEnabled(True)
        self._source_browse_btn.setEnabled(True)
        self._scan_btn.setEnabled(Path(self._source_input.text()).is_dir())

    def _reset_scan_state(self, folder: Optional[str] = None) -> None:
        """Reset scan-derived state so a new folder starts cleanly."""
        self._metadata_list = []
        self._last_scanned_folder = folder or None
        self._preview_tree.clear()
        self._scan_progress.setVisible(False)
        self._scan_progress.setValue(0)
        self._scan_cancel_btn.setVisible(False)
        self._scan_cancel_btn.setEnabled(True)
        self._scan_status.setVisible(False)
        self._sort_btn.setEnabled(False)
        self._unsort_cb.setEnabled(False)

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _update_preview(self) -> None:
        """Rebuild the folder structure preview from current metadata + criteria."""
        if not self._metadata_list:
            return

        criteria = self._criteria_widget.get_ordered_criteria()
        enabled = self._criteria_widget.get_enabled_criteria()
        preserve_subfolders = self._preserve_subfolders_cb.isChecked()

        if not any(enabled.values()):
            self._preview_tree.clear()
            return

        manager = SortManager()
        preview = manager.preview_structure(
            self._metadata_list, criteria, enabled, preserve_subfolders
        )
        self._preview_tree.update_preview(preview)

    # ------------------------------------------------------------------
    # Criteria reordering via arrow buttons
    # ------------------------------------------------------------------

    def _on_move_criterion_up(self) -> None:
        """Move the selected criterion one position up."""
        row = self._criteria_widget.currentRow()
        if row > 0:
            item = self._criteria_widget.takeItem(row)
            self._criteria_widget.insertItem(row - 1, item)
            self._criteria_widget.setCurrentRow(row - 1)
            self._criteria_widget.criteria_changed.emit()

    def _on_move_criterion_down(self) -> None:
        """Move the selected criterion one position down."""
        row = self._criteria_widget.currentRow()
        if row < self._criteria_widget.count() - 1:
            item = self._criteria_widget.takeItem(row)
            self._criteria_widget.insertItem(row + 1, item)
            self._criteria_widget.setCurrentRow(row + 1)
            self._criteria_widget.criteria_changed.emit()

    # ------------------------------------------------------------------
    # Destination
    # ------------------------------------------------------------------

    def _on_browse_dest(self) -> None:
        """Open directory picker for destination folder."""
        start_dir = get_dialog_start_dir(
            self._dest_input.text() or self._source_input.text(),
            "sort.last_dest_folder",
        )
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", start_dir
        )
        if folder:
            update_dialog_last_dir(folder)
            self._dest_input.setText(folder)
            self._save_settings()

    # ------------------------------------------------------------------
    # Sort / Unsort actions
    # ------------------------------------------------------------------

    def _on_sort(self) -> None:
        """Dispatch to sort or unsort depending on the undo checkbox."""
        if self._unsort_cb.isChecked():
            self._do_unsort()
        else:
            self._do_sort()

    def _do_sort(self) -> None:
        """Apply the sort operation."""
        if not self._metadata_list:
            return

        action = "move" if self._move_radio.isChecked() else "copy"
        reply = QMessageBox.question(
            self,
            "Confirm Sort",
            f"This will {action} {len(self._metadata_list)} files into the new "
            "structure.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        dest_path = self._dest_input.text() or self._source_input.text()
        criteria = self._criteria_widget.get_ordered_criteria()
        enabled = self._criteria_widget.get_enabled_criteria()
        preserve_subfolders = self._preserve_subfolders_cb.isChecked()

        self._sort_manager = SortManager()
        self._sort_manager.progress.connect(self._on_sort_progress)
        self._sort_manager.completed.connect(self._on_sort_completed)

        structure = self._sort_manager.build_folder_structure(
            self._metadata_list, criteria, enabled, preserve_subfolders
        )

        self._sort_progress.setVisible(True)
        self._sort_progress.setMaximum(len(self._metadata_list))
        self._sort_progress.setValue(0)
        self._sort_btn.setEnabled(False)
        self._cancel_btn.setVisible(True)

        self.sort_started.emit()

        self._sort_worker = SortWorker(
            manager=self._sort_manager,
            mode="sort",
            folder_structure=structure,
            destination_root=dest_path,
            move_files=self._move_radio.isChecked(),
        )
        self._sort_worker.finished.connect(self._on_sort_worker_finished)
        self._sort_worker.start()

    def _do_unsort(self) -> None:
        """Flatten all files back to their first-level parent folders."""
        if not self._metadata_list:
            return

        source_path = self._source_input.text()
        if not source_path:
            return

        manager = SortManager()
        unsort_map = manager.build_unsort_structure(self._metadata_list, source_path)

        if not unsort_map:
            QMessageBox.information(
                self,
                "Nothing to Unsort",
                "All files are already in their first-level parent folders.",
            )
            return

        preview = manager.preview_unsort(self._metadata_list, source_path)
        preview_text = "\n".join(
            f"  {folder}/: {len(files)} file(s)"
            for folder, files in sorted(preview.items())
        )

        action = "move" if self._move_radio.isChecked() else "copy"
        reply = QMessageBox.question(
            self,
            "Confirm Unsort",
            f"This will {action} {len(unsort_map)} files to their first-level parent "
            f"folders:\n\n{preview_text}\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._sort_manager = SortManager()
        self._sort_manager.progress.connect(self._on_sort_progress)
        self._sort_manager.completed.connect(self._on_unsort_completed)

        self._sort_progress.setVisible(True)
        self._sort_progress.setMaximum(len(unsort_map))
        self._sort_progress.setValue(0)
        self._sort_btn.setEnabled(False)
        self._cancel_btn.setVisible(True)

        self.sort_started.emit()

        self._sort_worker = SortWorker(
            manager=self._sort_manager,
            mode="unsort",
            unsort_map=unsort_map,
            move_files=self._move_radio.isChecked(),
            source_root=source_path,
        )
        self._sort_worker.finished.connect(self._on_sort_worker_finished)
        self._sort_worker.start()

    def _on_sort_progress(self, current: int, total: int, file_path: str) -> None:
        self._sort_progress.setValue(current)

    def _on_sort_worker_finished(self) -> None:
        if self._sort_worker:
            self._sort_worker.deleteLater()
            self._sort_worker = None

    def _on_sort_completed(self, success: int, failures: int, duplicates: int) -> None:
        """Handle sort completion."""
        self._sort_progress.setVisible(False)
        self._cancel_btn.setVisible(False)
        self._sort_btn.setEnabled(False)
        self._unsort_cb.setEnabled(False)

        self.sort_completed.emit(success, failures)

        parts = []
        if success > 0:
            parts.append(f"Successfully sorted {success} files.")
        if duplicates > 0:
            parts.append(f"Deleted {duplicates} duplicate(s).")
        if failures > 0:
            parts.append(f"{failures} files failed to sort.")

        message = "\n".join(parts) if parts else "No files were sorted."
        if failures == 0:
            QMessageBox.information(self, "Sort Complete", message)
        else:
            QMessageBox.warning(self, "Sort Complete", message)

        self._metadata_list.clear()
        self._preview_tree.clear()
        self._sort_manager = None

    def _on_unsort_completed(
        self, success: int, failures: int, duplicates: int
    ) -> None:
        """Handle unsort completion."""
        self._sort_progress.setVisible(False)
        self._cancel_btn.setVisible(False)
        self._sort_btn.setEnabled(False)
        self._unsort_cb.setEnabled(False)

        self.sort_completed.emit(success, failures)

        parts = []
        if success > 0:
            parts.append(
                f"Successfully flattened {success} files to their parent folders."
            )
        if duplicates > 0:
            parts.append(f"Deleted {duplicates} duplicate(s).")
        if failures > 0:
            parts.append(f"{failures} files failed.")

        message = "\n".join(parts) if parts else "No files were moved."
        if failures == 0:
            QMessageBox.information(self, "Unsort Complete", message)
        else:
            QMessageBox.warning(self, "Unsort Complete", message)

        self._metadata_list.clear()
        self._preview_tree.clear()
        self._sort_manager = None

    def _on_cancel(self) -> None:
        """Cancel the running sort/unsort operation."""
        if self._sort_manager:
            self._sort_manager.cancel()

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
        self._source_browse_btn.setEnabled(enabled)
        self._scan_btn.setEnabled(enabled and Path(self._source_input.text()).is_dir())
        self._dest_input.setEnabled(enabled)
        self._dest_browse_btn.setEnabled(enabled)
        self._criteria_widget.setEnabled(enabled)
