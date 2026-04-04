"""ConvertPage — video conversion tool page using SplitLayout."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QComboBox,
    QSlider,
    QCheckBox,
    QProgressBar,
    QMessageBox,
)

from ...core.convert_saved_task import (
    ConvertQueueItem,
    ConvertQueueItemStatus,
    build_convert_task_payload,
    detect_existing_outputs,
    load_convert_task_payload,
)
from ...core.conversion_manager import ConversionManager
from ...core.conversion_paths import (
    build_conversion_output_name,
    build_conversion_output_path,
    get_conversion_output_extension,
    get_conversion_preview_folder,
)
from ...core.ffprobe_worker import FFprobeWorker
from ...core.folder_scan_worker import FolderScanWorker
from ...data.models import ConversionConfig, ConversionJob
from ...services.config_service import ConfigService
from ...utils.constants import (
    DEFAULT_CRF,
    MIN_CRF,
    MAX_CRF,
    DEFAULT_PRESET,
    CONVERSION_PRESETS,
    VIDEO_FILE_FILTER,
)
from ...utils.dialog_utils import get_dialog_start_dir, update_dialog_last_dir
from ...utils.hardware_accel import (
    HardwareEncoder,
    get_cached_hardware_encoders,
    get_compatible_hardware_encoders,
    get_hardware_detection_message,
)
from ..components.page_header import PageHeader
from ..components.split_layout import SplitLayout
from ..components.data_panel import DataPanel
from ..widgets.convert_queue_widget import ConvertQueueWidget
from ..widgets.folder_preview_widget import FolderPreviewWidget

logger = logging.getLogger(__name__)

OUTPUT_FORMATS = [
    ("mp4 / H.264", "h264"),
    ("mp4 / H.265 (HEVC)", "hevc"),
    ("webm / VP9", "vp9"),
    ("mp3", "mp3"),
    ("aac", "aac"),
    ("flac", "flac"),
]

FILE_PATH_ROLE = int(Qt.ItemDataRole.UserRole)
SOURCE_ROOT_ROLE = FILE_PATH_ROLE + 1
RESOLUTION_DATA_ROLE = SOURCE_ROOT_ROLE + 1

SAME_AS_SOURCE_RESOLUTION = "source"
HORIZONTAL_RESOLUTIONS = [
    "3840x2160",
    "2560x1440",
    "1920x1080",
    "1280x720",
]
VERTICAL_RESOLUTIONS = [
    "2160x3840",
    "1440x2560",
    "1080x1920",
    "720x1280",
]
ORIENTATION_RESOLUTION_OPTIONS = {
    "horizontal": HORIZONTAL_RESOLUTIONS,
    "vertical": VERTICAL_RESOLUTIONS,
}
OPPOSITE_ORIENTATION = {
    "horizontal": "vertical",
    "vertical": "horizontal",
}


class FileListWidget(QWidget):
    """Widget for managing the list of files to convert."""

    files_changed = pyqtSignal()  # Emitted when files are added/removed
    loading_state_changed = pyqtSignal(bool)

    RENDER_BATCH_SIZE = 200

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scan_worker: Optional[FolderScanWorker] = None
        self._scan_root: Optional[str] = None
        self._entries: List[Tuple[str, Optional[str]]] = []
        self._render_index = 0
        self._loading_state = False
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._render_next_batch)
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Build the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Buttons
        btn_layout = QHBoxLayout()
        self._add_files_btn = QPushButton("Add Files")
        self._add_files_btn.setObjectName("btnWire")
        self._add_files_btn.setProperty("button_role", "secondary")
        self._add_folder_btn = QPushButton("Add Folder")
        self._add_folder_btn.setObjectName("btnWire")
        self._add_folder_btn.setProperty("button_role", "secondary")
        self._remove_btn = QPushButton("Remove Selected")
        self._remove_btn.setObjectName("btnDestructive")
        self._remove_btn.setProperty("button_role", "destructive")
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setObjectName("btnWire")
        self._clear_btn.setProperty("button_role", "secondary")

        btn_layout.addWidget(self._add_files_btn)
        btn_layout.addWidget(self._add_folder_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self._remove_btn)
        btn_layout.addWidget(self._clear_btn)

        layout.addLayout(btn_layout)

        # File list
        self._list_widget = QListWidget()
        self._list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self._list_widget)

    def _connect_signals(self) -> None:
        """Wire up signals."""
        self._add_files_btn.clicked.connect(self._on_add_files)
        self._add_folder_btn.clicked.connect(self._on_add_folder)
        self._remove_btn.clicked.connect(self._on_remove)
        self._clear_btn.clicked.connect(self._on_clear)

    def _on_add_files(self) -> None:
        """Add individual files."""
        start_dir = get_dialog_start_dir(fallback_config_key="convert.output_dir")
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Video Files", start_dir, VIDEO_FILE_FILTER
        )
        if files:
            update_dialog_last_dir(files[0])
            self._add_paths(files)

    def _on_add_folder(self) -> None:
        """Add all videos from a folder."""
        start_dir = get_dialog_start_dir(fallback_config_key="convert.output_dir")
        folder = QFileDialog.getExistingDirectory(
            self, "Select Video Folder", start_dir
        )
        if folder:
            update_dialog_last_dir(folder)
            self._scan_root = folder
            # Disable buttons during scan
            self._add_files_btn.setEnabled(False)
            self._add_folder_btn.setEnabled(False)
            self._add_folder_btn.setText("Scanning...")

            # Start background scan
            self._scan_worker = FolderScanWorker(folder, recursive=True)
            self._update_loading_state()
            self._scan_worker.progress.connect(self._on_scan_progress)
            self._scan_worker.completed.connect(self._on_scan_completed)
            self._scan_worker.error.connect(self._on_scan_error)
            self._scan_worker.start()

    def _on_scan_progress(self, count: int, message: str) -> None:
        """Handle folder scan progress."""
        self._add_folder_btn.setText(f"Scanning... ({count})")

    def _on_scan_completed(self, video_files: List[str]) -> None:
        """Handle folder scan completion."""
        self._add_paths(video_files, source_root=self._scan_root)

        # Re-enable buttons
        self._add_files_btn.setEnabled(True)
        self._add_folder_btn.setEnabled(True)
        self._add_folder_btn.setText("Add Folder")

        # Clean up worker
        if self._scan_worker:
            self._scan_worker.deleteLater()
            self._scan_worker = None
        self._scan_root = None
        self._update_loading_state()

    def _on_scan_error(self, error_message: str) -> None:
        """Handle folder scan error."""
        QMessageBox.warning(
            self, "Scan Error", f"Failed to scan folder:\n{error_message}"
        )

        # Re-enable buttons
        self._add_files_btn.setEnabled(True)
        self._add_folder_btn.setEnabled(True)
        self._add_folder_btn.setText("Add Folder")

        # Clean up worker
        if self._scan_worker:
            self._scan_worker.deleteLater()
            self._scan_worker = None
        self._scan_root = None
        self._update_loading_state()

    def _add_paths(
        self, paths: List[str], source_root: Optional[str] = None
    ) -> None:
        """Add file paths to the list, skipping duplicates."""
        existing = set(self.get_file_paths())
        added_any = False
        for path in paths:
            if path not in existing:
                self._entries.append((path, source_root))
                existing.add(path)
                added_any = True

        if not added_any:
            return

        self._schedule_render()
        self.files_changed.emit()

    def _display_name_for_path(self, path: str, source_root: Optional[str]) -> str:
        """Return the label shown in the file list."""
        file_path = Path(path)
        if source_root:
            try:
                return file_path.relative_to(Path(source_root)).as_posix()
            except ValueError:
                pass
        return file_path.name

    def _on_remove(self) -> None:
        """Remove selected files."""
        selected_paths = {
            item.data(FILE_PATH_ROLE) for item in self._list_widget.selectedItems()
        }
        if not selected_paths:
            return

        self._entries = [
            entry for entry in self._entries if entry[0] not in selected_paths
        ]
        self._rebuild_list_widget()
        self.files_changed.emit()

    def _on_clear(self) -> None:
        """Clear all files."""
        if not self._entries:
            return

        self._entries = []
        self._render_index = 0
        self._render_timer.stop()
        self._list_widget.clear()
        self._update_loading_state()
        self.files_changed.emit()

    def get_file_paths(self) -> List[str]:
        """Get all file paths in the list."""
        return [path for path, _source_root in self._entries]

    def get_entries(self) -> List[Tuple[str, Optional[str]]]:
        """Get all file entries with their optional source roots."""
        return list(self._entries)

    def get_selected_file_path(self) -> Optional[str]:
        """Get the first selected file path, or None if no selection."""
        items = self._list_widget.selectedItems()
        if items:
            return items[0].data(FILE_PATH_ROLE)
        return None

    def count(self) -> int:
        """Get number of files."""
        return len(self._entries)

    def is_busy(self) -> bool:
        """Return whether the list is still scanning or rendering."""
        return self._scan_worker is not None or self._render_index < len(self._entries)

    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable the widget."""
        self._add_files_btn.setEnabled(enabled)
        self._add_folder_btn.setEnabled(enabled)
        self._remove_btn.setEnabled(enabled)
        self._clear_btn.setEnabled(enabled)
        self._list_widget.setEnabled(enabled)

    def _schedule_render(self) -> None:
        """Render pending list items in batches."""
        if self._render_index >= len(self._entries):
            self._update_loading_state()
            return

        self._update_loading_state()
        pending_count = len(self._entries) - self._render_index
        if pending_count <= self.RENDER_BATCH_SIZE and not self._render_timer.isActive():
            self._render_next_batch()
            return

        if not self._render_timer.isActive():
            self._render_timer.start(0)

    def _render_next_batch(self) -> None:
        """Append the next batch of queued items to the visible list."""
        end_index = min(self._render_index + self.RENDER_BATCH_SIZE, len(self._entries))
        for path, source_root in self._entries[self._render_index:end_index]:
            item = QListWidgetItem(self._display_name_for_path(path, source_root))
            item.setData(FILE_PATH_ROLE, path)
            item.setData(SOURCE_ROOT_ROLE, source_root)
            item.setToolTip(path)
            self._list_widget.addItem(item)

        self._render_index = end_index
        if self._render_index < len(self._entries):
            self._render_timer.start(0)

        self._update_loading_state()

    def _rebuild_list_widget(self) -> None:
        """Re-render the visible list from the internal entry model."""
        self._render_timer.stop()
        self._list_widget.clear()
        self._render_index = 0
        self._schedule_render()

    def _update_loading_state(self) -> None:
        """Emit loading changes when scan/render state changes."""
        is_loading = self.is_busy()
        if self._loading_state == is_loading:
            return
        self._loading_state = is_loading
        self.loading_state_changed.emit(is_loading)


class ConvertPage(QWidget):
    """
    Convert page — transcode video files to different formats.

    Uses SplitLayout: file list on the left, settings panel on the right.
    """

    start_requested = pyqtSignal()
    cancel_requested = pyqtSignal()

    # Re-expose for callers that listened to ConvertTabWidget signals
    conversion_started = pyqtSignal()
    conversion_completed = pyqtSignal(int, int)  # success, failures

    def __init__(self, conversion_manager=None, parent=None):
        super().__init__(parent)
        self._conversion_manager: Optional[ConversionManager] = conversion_manager
        self._preflight_worker: Optional[FFprobeWorker] = None
        self._preflight_request_id = 0
        self._queue_items: List[ConvertQueueItem] = []
        self._job_id_to_queue_item_id: Dict[int, str] = {}
        self._active_queue_item_id: Optional[str] = None
        self._cancel_requested_during_run = False
        self._pause_requested_during_run = False
        self._restored_output_paths: Dict[str, str] = {}
        self._config_service = ConfigService()
        self._hardware_encoders: List[HardwareEncoder] = []
        self._file_codecs: Dict[str, str] = {}
        self._file_metadata: Dict[str, object] = {}
        self._loading_settings = False

        self._setup_ui()
        self._connect_signals()
        self._load_settings()
        self._detect_hardware()
        self._refresh_preflight_scan()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Build the full page layout."""
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # 1. Page header
        header = PageHeader(
            title="Convert",
            description="Transcode video files to different formats.",
        )
        root.addWidget(header)

        # 2. Split layout: file list left, settings right
        split = SplitLayout(right_width=340, gap=20)

        # --- LEFT panel: file list ---
        left_layout = QVBoxLayout(split.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        files_panel = DataPanel("Source Files")
        files_panel.body_layout.setSpacing(10)
        self._file_list = FileListWidget()
        files_panel.body_layout.addWidget(self._file_list)

        queue_label = QLabel("Queue")
        files_panel.body_layout.addWidget(queue_label)

        self._queue_widget = ConvertQueueWidget()
        self._queue_widget.setVisible(False)
        self._queue_widget.setMinimumHeight(120)
        files_panel.body_layout.addWidget(self._queue_widget)

        self._overall_progress = QProgressBar()
        self._overall_progress.setVisible(False)
        files_panel.body_layout.addWidget(self._overall_progress)

        left_layout.addWidget(files_panel, stretch=3)

        preview_panel = DataPanel("Preview")
        preview_panel.body_layout.setSpacing(10)
        self._preview_tree = FolderPreviewWidget()
        preview_panel.body_layout.addWidget(self._preview_tree, stretch=1)

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
        preview_panel.body_layout.addLayout(expand_row)

        left_layout.addWidget(preview_panel, stretch=2)

        # --- RIGHT panel: settings card ---
        right_layout = QVBoxLayout(split.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        settings_panel = DataPanel("Output Settings")
        sl = settings_panel.body_layout

        # Output Format
        sl.addWidget(QLabel("Output Format"))
        self._codec_combo = QComboBox()
        for label, codec in OUTPUT_FORMATS:
            self._codec_combo.addItem(label, codec)
        sl.addWidget(self._codec_combo)

        sl.addWidget(QLabel("Output Resolution"))
        self._resolution_combo = QComboBox()
        self._resolution_combo.setToolTip(
            "Automatically shows presets for the detected orientation, with"
            " opposite-orientation overrides below the divider."
        )
        self._refresh_resolution_options()
        sl.addWidget(self._resolution_combo)

        # Quality
        sl.addWidget(QLabel("Quality"))
        quality_row = QHBoxLayout()
        self._crf_slider = QSlider(Qt.Orientation.Horizontal)
        self._crf_slider.setToolTip(
            "CRF — lower values mean higher quality and larger files"
        )
        self._crf_slider.setMinimum(MIN_CRF)
        self._crf_slider.setMaximum(MAX_CRF)
        self._crf_slider.setValue(DEFAULT_CRF)
        self._crf_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._crf_slider.setTickInterval(5)
        self._crf_label = QLabel(str(DEFAULT_CRF))
        self._crf_label.setMinimumWidth(30)
        quality_row.addWidget(self._crf_slider)
        quality_row.addWidget(self._crf_label)
        sl.addLayout(quality_row)

        # Preset
        sl.addWidget(QLabel("Preset"))
        self._preset_combo = QComboBox()
        self._preset_combo.addItems(CONVERSION_PRESETS)
        self._preset_combo.setCurrentText(DEFAULT_PRESET)
        sl.addWidget(self._preset_combo)

        # Hardware Acceleration
        sl.addWidget(QLabel("Hardware Acceleration"))
        self._hw_combo = QComboBox()
        sl.addWidget(self._hw_combo)
        self._hw_status_label = QLabel()
        self._hw_status_label.setWordWrap(True)
        self._hw_status_label.setVisible(False)
        sl.addWidget(self._hw_status_label)

        self._source_codec_filter_check = QCheckBox(
            "Skip files already in selected output format"
        )
        sl.addWidget(self._source_codec_filter_check)

        self._preflight_status_label = QLabel("Add files to prepare the queue.")
        self._preflight_status_label.setWordWrap(True)
        sl.addWidget(self._preflight_status_label)

        # Output Folder
        sl.addWidget(QLabel("Output Folder"))
        output_row = QHBoxLayout()
        self._output_input = QLineEdit()
        self._output_input.setPlaceholderText("Same as input (adds _converted suffix)")
        self._output_browse_btn = QPushButton("Browse")
        self._output_browse_btn.setObjectName("btnWire")
        self._output_browse_btn.setProperty("button_role", "secondary")
        output_row.addWidget(self._output_input)
        output_row.addWidget(self._output_browse_btn)
        sl.addLayout(output_row)

        right_layout.addWidget(settings_panel)
        right_layout.addStretch()

        # CTA
        self._start_btn = QPushButton("START CONVERT")
        self._start_btn.setProperty("button_role", "cta")
        self._start_btn.setEnabled(False)
        right_layout.addWidget(self._start_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setProperty("button_role", "secondary")
        self._cancel_btn.setVisible(False)
        right_layout.addWidget(self._cancel_btn)

        root.addWidget(split, stretch=1)

    def _connect_signals(self) -> None:
        """Wire up all signal connections."""
        self._file_list.files_changed.connect(self._on_files_changed)
        self._file_list.loading_state_changed.connect(self._on_file_list_loading_changed)
        self._queue_widget.reorder_requested.connect(self._on_queue_reorder_requested)
        self._queue_widget.skip_requested.connect(self._on_queue_skip_requested)
        self._queue_widget.prioritize_requested.connect(
            self._on_queue_prioritize_requested
        )
        self._start_btn.clicked.connect(self._on_start)
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._crf_slider.valueChanged.connect(self._on_crf_changed)
        self._codec_combo.currentIndexChanged.connect(self._on_output_codec_changed)
        self._resolution_combo.currentIndexChanged.connect(
            self._on_resolution_changed
        )
        self._preset_combo.currentIndexChanged.connect(self._on_settings_changed)
        self._hw_combo.currentIndexChanged.connect(self._on_settings_changed)
        self._source_codec_filter_check.toggled.connect(
            self._on_skip_matching_output_toggled
        )
        self._output_input.textChanged.connect(self._on_output_dir_changed)
        self._output_input.textChanged.connect(self._on_settings_changed)
        self._output_input.textChanged.connect(self._sync_queue_items)
        self._output_input.textChanged.connect(self._update_preview)
        self._output_browse_btn.clicked.connect(self._on_browse_output)
        self._expand_all_btn.clicked.connect(self._preview_tree.expandAll)
        self._collapse_all_btn.clicked.connect(self._preview_tree.collapseAll)

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _load_settings(self) -> None:
        """Load settings from config service."""
        self._loading_settings = True
        try:
            codec = self._normalize_output_codec(
                self._config_service.get("convert.codec", "h264")
            )
            self._set_selected_output_codec(codec)

            resolution = self._normalize_resolution_value(
                self._config_service.get("convert.resolution", SAME_AS_SOURCE_RESOLUTION)
            )
            self._set_selected_resolution(resolution)

            crf = self._config_service.get("convert.crf", DEFAULT_CRF)
            self._crf_slider.setValue(crf)
            self._crf_label.setText(str(crf))

            preset = self._config_service.get("convert.preset", DEFAULT_PRESET)
            idx = self._preset_combo.findText(preset)
            if idx >= 0:
                self._preset_combo.setCurrentIndex(idx)

            output_dir = self._config_service.get("convert.output_dir", "")
            self._output_input.setText(output_dir)

            source_filter_enabled = self._config_service.get(
                "convert.skip_matching_output_enabled", False
            )
            self._source_codec_filter_check.setChecked(source_filter_enabled)
        finally:
            self._loading_settings = False

        self._sync_queue_items()
        self._update_start_button_state()

    def _save_settings(self) -> None:
        """Save current settings to config service."""
        if self._loading_settings:
            return

        codec = self._get_selected_output_codec()
        hardware_encoder = self._hw_combo.currentData()
        self._config_service.set("convert.codec", codec)
        self._config_service.set("convert.resolution", self._get_selected_resolution())
        self._config_service.set("convert.crf", self._crf_slider.value())
        self._config_service.set("convert.preset", self._preset_combo.currentText())
        self._config_service.set(
            "convert.use_hardware_accel", hardware_encoder is not None
        )
        self._config_service.set("convert.hardware_encoder", hardware_encoder or "")
        self._config_service.set(
            "convert.skip_matching_output_enabled",
            self._source_codec_filter_check.isChecked(),
        )
        self._config_service.set("convert.output_dir", self._output_input.text())

    def _detect_hardware(self) -> None:
        """Detect available hardware encoders and configure combo."""
        try:
            self._hardware_encoders = get_cached_hardware_encoders()
            preferred_hardware = self._config_service.get("convert.hardware_encoder", "")
            saved_use_hardware = self._config_service.get(
                "convert.use_hardware_accel", False
            )
            self._refresh_hardware_options(
                preferred_name=preferred_hardware or None,
                prefer_none=not saved_use_hardware,
            )
        except Exception as e:
            logger.warning("Hardware detection failed: %s", e)
            self._hardware_encoders = []
            self._refresh_hardware_options(preferred_name=None, prefer_none=True)

    def _on_crf_changed(self, value: int) -> None:
        """Update CRF label and save."""
        self._crf_label.setText(str(value))
        self._on_settings_changed()

    def _on_output_codec_changed(self) -> None:
        """Refresh dependent controls when the output codec changes."""
        self._clear_auto_skipped_queue_items()
        self._restored_output_paths = {}
        preferred_hardware = self._hw_combo.currentData()
        self._refresh_hardware_options(
            preferred_name=preferred_hardware, prefer_none=preferred_hardware is None
        )
        self._sync_queue_items()
        self._update_preview()
        self._update_start_button_state()
        self._on_settings_changed()

    def _on_resolution_changed(self) -> None:
        """Refresh queue readiness when the output resolution changes."""
        self._clear_auto_skipped_queue_items()
        self._restored_output_paths = {}
        self._sync_queue_items()
        self._update_preview()
        self._on_settings_changed()
        self._update_start_button_state()

    def _on_skip_matching_output_toggled(self) -> None:
        """Refresh queue readiness when skip-matching is toggled."""
        self._clear_auto_skipped_queue_items()
        self._on_settings_changed()
        self._update_start_button_state()

    def _on_output_dir_changed(self) -> None:
        """Clear restored output paths when output directory changes."""
        self._restored_output_paths = {}

    def _on_settings_changed(self) -> None:
        """Save settings on any change."""
        self._save_settings()

    def _on_browse_output(self) -> None:
        """Browse for output directory."""
        start_dir = get_dialog_start_dir(
            self._output_input.text(), "convert.output_dir"
        )
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", start_dir
        )
        if folder:
            update_dialog_last_dir(folder)
            self._output_input.setText(folder)

    def _on_files_changed(self) -> None:
        """Refresh queue readiness when the file set changes."""
        self._sync_queue_items()
        self._refresh_preflight_scan()
        self._update_preview()
        self._update_start_button_state()

    def _on_file_list_loading_changed(self, _loading: bool) -> None:
        """Refresh readiness state while the list is still rendering."""
        self._update_start_button_state()

    def _on_start(self) -> None:
        """Start conversion."""
        if not self._queue_items:
            return
        self._clear_auto_skipped_queue_items()

        if self._file_list.is_busy() or self._preflight_worker is not None:
            QMessageBox.information(
                self,
                "Preparing Queue",
                "Please wait for file loading and analysis to finish before starting the conversion.",
            )
            return

        startable_items = self._prepare_queue_items_for_start(self._queue_items)
        self._start_conversion_for_queue_items(startable_items)

    def _on_cancel(self) -> None:
        """Cancel all conversions."""
        self._cancel_requested_during_run = True
        if self._conversion_manager:
            self._conversion_manager.cancel_all()
        self.cancel_requested.emit()

    def pause_for_saved_task(self) -> dict:
        """Pause the current run and return a persistence payload."""
        is_running = (
            self._conversion_manager is not None
            and (
                bool(self._job_id_to_queue_item_id)
                or self._active_queue_item_id is not None
                or self._cancel_btn.isVisible()
            )
        )
        if is_running:
            self._pause_requested_during_run = True
            if self._conversion_manager:
                self._conversion_manager.cancel_all()
            self._mark_active_queue_item_incomplete()
            self._mark_unstarted_queue_items_incomplete(
                detail="Paused before start"
            )
        return self.build_saved_task_payload()

    def build_saved_task_payload(self) -> dict:
        """Serialize the current convert queue and settings for persistence."""
        return build_convert_task_payload(
            self._queue_items,
            self._build_config_payload(),
        )

    def restore_saved_task(
        self,
        payload: dict,
        config_payload: Optional[dict] = None,
        saved_task_id: Optional[int] = None,
    ) -> None:
        """Restore queue state and settings from a saved Convert task."""
        self._cancel_preflight_scan()
        self._job_id_to_queue_item_id = {}
        self._active_queue_item_id = None
        self._cancel_requested_during_run = False
        self._pause_requested_during_run = False

        self._apply_config_payload(config_payload or payload.get("config", {}))
        restored_items = self._normalize_restored_queue_items(
            load_convert_task_payload(payload)
        )
        restored_items = detect_existing_outputs(restored_items)
        self._restored_output_paths = {
            item.input_path: item.output_path for item in restored_items
        }
        self._set_restored_file_entries(restored_items)
        self._queue_items = restored_items
        self._refresh_queue_widget()
        self._refresh_preflight_scan()
        self._update_preview()
        self._update_start_button_state()

    # ------------------------------------------------------------------
    # Manager signal handlers
    # ------------------------------------------------------------------

    def _on_job_creation_progress(self, current: int, total: int) -> None:
        """Update UI while jobs are being created."""
        self._overall_progress.setMaximum(total if total > 0 else 1)

    def _on_jobs_created(self, jobs: List[ConversionJob]) -> None:
        """Prepare progress display once all jobs are created."""
        self._job_id_to_queue_item_id = {}
        for job in jobs:
            if job.id is not None:
                queue_item = self._find_queue_item_by_path(job.input_path)
                if queue_item is not None:
                    self._job_id_to_queue_item_id[job.id] = queue_item.item_id
        self._overall_progress.setMaximum(len(jobs))
        self._overall_progress.setValue(0)
        self._refresh_queue_widget()

        self.conversion_started.emit()

        # Start processing
        if self._conversion_manager is not None:
            self._conversion_manager.start()

    def _on_job_started(self, job_id: int) -> None:
        """Mark the matching queue item as in progress."""
        queue_item_id = self._job_id_to_queue_item_id.get(job_id)
        if queue_item_id is None:
            return
        self._active_queue_item_id = queue_item_id
        self._update_queue_item(
            queue_item_id,
            status=ConvertQueueItemStatus.PROCESSING,
            detail="Converting...",
            progress_percent=0.0,
            error_message="",
        )

    def _on_job_progress(
        self, job_id: int, percent: float, speed: str, eta: str
    ) -> None:
        """Update the queue item progress details."""
        queue_item_id = self._job_id_to_queue_item_id.get(job_id)
        if queue_item_id is None:
            return
        self._update_queue_item(
            queue_item_id,
            status=ConvertQueueItemStatus.PROCESSING,
            progress_percent=percent,
            detail=f"{percent:.0f}% | {speed} | ETA {eta}",
            error_message="",
        )

    def _on_job_completed(
        self, job_id: int, success: bool, output_path: str, error: str
    ) -> None:
        """Mark job as complete or failed in the queue."""
        queue_item_id = self._job_id_to_queue_item_id.get(job_id)
        if queue_item_id is None:
            return

        if success:
            if self._active_queue_item_id == queue_item_id:
                self._active_queue_item_id = None
            self._update_queue_item(
                queue_item_id,
                status=ConvertQueueItemStatus.COMPLETED,
                progress_percent=100.0,
                detail="Complete",
                error_message="",
            )
            return

        error_text = error or "Failed"
        was_cancelled = "cancelled" in error_text.lower() or "canceled" in error_text.lower()
        if self._active_queue_item_id == queue_item_id:
            self._active_queue_item_id = None
        self._update_queue_item(
            queue_item_id,
            status=(
                ConvertQueueItemStatus.INCOMPLETE
                if was_cancelled
                else ConvertQueueItemStatus.FAILED
            ),
            detail=(
                "Restart from beginning"
                if was_cancelled and self._pause_requested_during_run
                else ("Cancelled" if was_cancelled else "Failed")
            ),
            progress_percent=0.0 if was_cancelled else None,
            error_message=error_text,
        )

    def _on_queue_progress(self, completed: int, total: int, in_progress: int) -> None:
        """Update overall progress bar."""
        self._overall_progress.setMaximum(total if total > 0 else 1)
        self._overall_progress.setValue(completed)

    def _on_all_completed(self) -> None:
        """Reset UI after all conversions finish."""
        if self._cancel_requested_during_run:
            self._mark_unstarted_queue_items_incomplete()
        elif self._pause_requested_during_run:
            self._mark_unstarted_queue_items_incomplete(detail="Paused before start")

        self._file_list.set_enabled(True)
        self._queue_widget.set_actions_enabled(True)
        self._cancel_btn.setVisible(False)
        self._overall_progress.setVisible(False)

        if self._conversion_manager:
            completed = self._conversion_manager.completed_count
            failed = self._conversion_manager.failed_count

            self.conversion_completed.emit(completed, failed)

            if self._pause_requested_during_run:
                pass
            elif failed == 0:
                QMessageBox.information(
                    self,
                    "Conversion Complete",
                    f"Successfully converted {completed} files.",
                )
            else:
                QMessageBox.warning(
                    self,
                    "Conversion Complete",
                    f"Converted {completed} files.\n{failed} files failed.",
                )

            self._conversion_manager.reset_counts()

        self._job_id_to_queue_item_id = {}
        self._active_queue_item_id = None
        self._cancel_requested_during_run = False
        self._pause_requested_during_run = False
        self._update_start_button_state()

    def _on_files_deleted(self, count: int, paths: List[str]) -> None:
        """Notify user when zero-byte files are moved to trash."""
        if count > 0:
            QMessageBox.information(
                self,
                "Invalid Files Removed",
                f"Moved {count} zero-byte corrupted file(s) to trash.\n\n"
                f"These files can be recovered from your system trash if needed.",
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _normalize_output_codec(self, codec: str) -> str:
        """Normalize stored output codec values."""
        codec_map = {
            "libx264": "h264",
            "libx265": "hevc",
        }
        return codec_map.get(codec, codec)

    def _normalize_source_codec(self, codec: str) -> str:
        """Normalize source codec values from ffprobe."""
        normalized = codec.strip().lower()
        if normalized == "h265":
            return "hevc"
        return normalized

    def _get_selected_output_codec(self) -> str:
        """Get the selected output codec."""
        return self._codec_combo.currentData() or "h264"

    def _normalize_resolution_value(self, value: Optional[str]) -> str:
        """Normalize stored output resolution values."""
        normalized = (value or "").strip().lower()
        if normalized == SAME_AS_SOURCE_RESOLUTION:
            return SAME_AS_SOURCE_RESOLUTION

        combined = HORIZONTAL_RESOLUTIONS + VERTICAL_RESOLUTIONS
        return normalized if normalized in combined else SAME_AS_SOURCE_RESOLUTION

    def _set_selected_output_codec(self, codec: str) -> None:
        """Set the selected output codec."""
        normalized = self._normalize_output_codec(codec)
        index = self._codec_combo.findData(normalized)
        self._codec_combo.setCurrentIndex(index if index >= 0 else 0)

    def _get_selected_resolution(self) -> str:
        """Get the selected output resolution value."""
        resolution = self._resolution_combo.currentData(RESOLUTION_DATA_ROLE)
        return self._normalize_resolution_value(resolution)

    def _set_selected_resolution(self, resolution: str) -> None:
        """Set the selected output resolution."""
        normalized = self._normalize_resolution_value(resolution)
        index = self._find_resolution_index(normalized)
        self._resolution_combo.setCurrentIndex(index if index >= 0 else 0)

    def _find_resolution_index(self, resolution: str) -> int:
        """Find the first combo index with the given resolution payload."""
        for index in range(self._resolution_combo.count()):
            if (
                self._resolution_combo.itemData(index, RESOLUTION_DATA_ROLE)
                == resolution
            ):
                return index
        return -1

    def _get_auto_orientation(self) -> str:
        """Get the detected orientation for the current file list."""
        orientations: List[str] = []
        for path in self._file_list.get_file_paths():
            metadata = self._file_metadata.get(path)
            orientation = getattr(metadata, "orientation", "")
            if orientation in {"horizontal", "vertical"}:
                orientations.append(orientation)

        if not orientations:
            return "horizontal"

        horizontal_count = orientations.count("horizontal")
        vertical_count = orientations.count("vertical")
        if horizontal_count == vertical_count:
            return orientations[0]
        return "horizontal" if horizontal_count > vertical_count else "vertical"

    def _format_resolution_label(
        self, resolution: str, orientation: str, *, is_override: bool
    ) -> str:
        """Build a user-facing resolution option label."""
        if not is_override:
            return resolution
        return f"{resolution} ({orientation.title()} override)"

    def _refresh_resolution_options(self) -> None:
        """Refresh resolution options from the detected file orientation."""
        selected_resolution = self._get_selected_resolution()
        auto_orientation = self._get_auto_orientation()
        override_orientation = OPPOSITE_ORIENTATION[auto_orientation]

        self._resolution_combo.blockSignals(True)
        self._resolution_combo.clear()
        self._resolution_combo.addItem("Same as source")
        self._resolution_combo.setItemData(
            0, SAME_AS_SOURCE_RESOLUTION, RESOLUTION_DATA_ROLE
        )

        for resolution in ORIENTATION_RESOLUTION_OPTIONS[auto_orientation]:
            self._resolution_combo.addItem(
                self._format_resolution_label(
                    resolution, auto_orientation, is_override=False
                )
            )
            self._resolution_combo.setItemData(
                self._resolution_combo.count() - 1,
                resolution,
                RESOLUTION_DATA_ROLE,
            )

        self._resolution_combo.insertSeparator(self._resolution_combo.count())

        for resolution in ORIENTATION_RESOLUTION_OPTIONS[override_orientation]:
            self._resolution_combo.addItem(
                self._format_resolution_label(
                    resolution, override_orientation, is_override=True
                )
            )
            self._resolution_combo.setItemData(
                self._resolution_combo.count() - 1,
                resolution,
                RESOLUTION_DATA_ROLE,
            )

        self._set_selected_resolution(selected_resolution)
        self._resolution_combo.blockSignals(False)

    def _matches_selected_output_format(self, file_path: str) -> bool:
        """Return whether the input already matches the selected output format."""
        output_codec = self._get_selected_output_codec()
        expected_extension = get_conversion_output_extension(output_codec)
        if Path(file_path).suffix.lower() != expected_extension:
            return False

        if output_codec in {"h264", "hevc", "vp9"}:
            if self._file_codecs.get(file_path) != output_codec:
                return False

            selected_resolution = self._get_selected_resolution()
            if selected_resolution == SAME_AS_SOURCE_RESOLUTION:
                return True

            metadata = self._file_metadata.get(file_path)
            return metadata is not None and metadata.resolution == selected_resolution

        return True

    def _format_hardware_label(self, encoder: HardwareEncoder) -> str:
        """Get a compact user-facing hardware encoder label."""
        label_map = {
            "nvenc": "NVENC",
            "videotoolbox": "VideoToolbox",
            "amf": "AMD AMF",
            "qsv": "Intel Quick Sync",
        }
        return label_map.get(encoder.name, encoder.display_name)

    def _refresh_hardware_options(
        self, preferred_name: Optional[str], prefer_none: bool
    ) -> None:
        """Populate the hardware acceleration combo for the selected codec."""
        output_codec = self._get_selected_output_codec()
        hardware_supported = output_codec in {"h264", "hevc"}
        compatible_encoders = get_compatible_hardware_encoders(
            output_codec, self._hardware_encoders
        )

        self._hw_combo.blockSignals(True)
        self._hw_combo.clear()
        if compatible_encoders:
            self._hw_combo.addItem("None", None)
            for encoder in compatible_encoders:
                self._hw_combo.addItem(
                    self._format_hardware_label(encoder), encoder.name
                )
        elif hardware_supported:
            self._hw_combo.addItem("No hardware acceleration detected", None)
        else:
            self._hw_combo.addItem("Not available for this format", None)

        selected_index = 0
        if compatible_encoders and preferred_name:
            preferred_index = self._hw_combo.findData(preferred_name)
            if preferred_index >= 0:
                selected_index = preferred_index
            elif not prefer_none and compatible_encoders:
                selected_index = 1
        elif compatible_encoders and not prefer_none:
            selected_index = 1

        self._hw_combo.setCurrentIndex(selected_index)
        self._hw_combo.setEnabled(bool(compatible_encoders))
        status_message = ""
        if not compatible_encoders:
            status_message = get_hardware_detection_message(output_codec)
        self._hw_combo.setToolTip(status_message)
        self._hw_status_label.setText(status_message)
        self._hw_status_label.setVisible(bool(status_message))
        self._hw_combo.blockSignals(False)

    def _refresh_preflight_scan(self) -> None:
        """Probe the current file list and cache metadata needed for conversion."""
        self._cancel_preflight_scan()

        current_paths = self._file_list.get_file_paths()
        self._file_codecs = {
            path: codec for path, codec in self._file_codecs.items() if path in current_paths
        }
        self._file_metadata = {
            path: metadata
            for path, metadata in self._file_metadata.items()
            if path in current_paths
        }

        if not current_paths:
            self._refresh_resolution_options()
            self._update_start_button_state()
            return

        self._preflight_request_id += 1
        request_id = self._preflight_request_id

        worker = FFprobeWorker(
            current_paths,
            trash_zero_byte_files=False,
            parent=self,
        )
        self._preflight_worker = worker
        worker.completed.connect(
            lambda results, rid=request_id, active_worker=worker: self._on_preflight_scan_completed(
                rid, active_worker, results
            )
        )
        worker.error.connect(
            lambda file_path, error, rid=request_id: self._on_preflight_scan_error(
                rid, file_path, error
            )
        )
        worker.start()
        self._update_start_button_state()

    def _cancel_preflight_scan(self) -> None:
        """Cancel any in-progress metadata probe."""
        if self._preflight_worker is not None:
            self._preflight_worker.cancel()
            self._preflight_worker.deleteLater()
            self._preflight_worker = None

    def _on_preflight_scan_completed(
        self, request_id: int, worker: FFprobeWorker, results: List[object]
    ) -> None:
        """Handle completion of queue preflight analysis."""
        worker.deleteLater()
        if request_id != self._preflight_request_id:
            return

        if self._preflight_worker is worker:
            self._preflight_worker = None

        current_paths = set(self._file_list.get_file_paths())
        self._file_codecs = {}
        self._file_metadata = {}
        for metadata in results:
            file_path = getattr(metadata, "file_path", None)
            codec = getattr(metadata, "codec", "")
            if file_path and file_path in current_paths:
                self._file_metadata[file_path] = metadata
                if codec:
                    self._file_codecs[file_path] = self._normalize_source_codec(codec)

        self._refresh_resolution_options()
        self._sync_queue_items()
        self._update_start_button_state()

    def _on_preflight_scan_error(
        self, request_id: int, file_path: str, error: str
    ) -> None:
        """Log metadata scan failures without interrupting the UI."""
        if request_id != self._preflight_request_id:
            return
        logger.warning("Convert preflight probe failed for %s: %s", file_path, error)

    def _build_config(self) -> ConversionConfig:
        """Build a ConversionConfig from the current UI state."""
        codec = self._get_selected_output_codec()
        hw_encoder = self._hw_combo.currentData()
        use_hw = hw_encoder is not None

        return ConversionConfig(
            output_codec=codec,
            output_resolution=(
                None
                if self._get_selected_resolution() == SAME_AS_SOURCE_RESOLUTION
                else self._get_selected_resolution()
            ),
            crf_value=self._crf_slider.value(),
            preset=self._preset_combo.currentText(),
            use_hardware_accel=use_hw,
            hardware_encoder=hw_encoder,
            output_dir=self._output_input.text() or None,
        )

    def _build_config_payload(self) -> dict:
        """Serialize the current convert settings for saved-task persistence."""
        config = self._build_config()
        return {
            "output_codec": config.output_codec,
            "output_resolution": config.output_resolution,
            "crf_value": config.crf_value,
            "preset": config.preset,
            "use_hardware_accel": config.use_hardware_accel,
            "hardware_encoder": config.hardware_encoder,
            "output_dir": config.output_dir,
            "skip_matching_output_enabled": self._source_codec_filter_check.isChecked(),
        }

    def _apply_config_payload(self, config_payload: dict) -> None:
        """Apply saved Convert settings to the current controls."""
        self._loading_settings = True
        try:
            self._set_selected_output_codec(
                self._normalize_output_codec(
                    str(config_payload.get("output_codec", "h264"))
                )
            )
            self._set_selected_resolution(
                self._normalize_resolution_value(config_payload.get("output_resolution"))
            )
            raw_crf = config_payload.get("crf_value")
            try:
                crf_parsed = int(raw_crf) if raw_crf is not None else DEFAULT_CRF
            except (TypeError, ValueError):
                crf_parsed = DEFAULT_CRF
            crf_clamped = max(self._crf_slider.minimum(), min(self._crf_slider.maximum(), crf_parsed))
            self._crf_slider.setValue(crf_clamped)
            self._crf_label.setText(str(self._crf_slider.value()))

            preset = str(config_payload.get("preset", DEFAULT_PRESET))
            preset_index = self._preset_combo.findText(preset)
            self._preset_combo.setCurrentIndex(preset_index if preset_index >= 0 else 0)

            self._output_input.setText(str(config_payload.get("output_dir") or ""))

            skip_matching = bool(config_payload.get("skip_matching_output_enabled", False))
            self._source_codec_filter_check.setChecked(skip_matching)

            hardware_encoder = config_payload.get("hardware_encoder")
            use_hardware = bool(config_payload.get("use_hardware_accel"))
            self._refresh_hardware_options(
                preferred_name=str(hardware_encoder) if hardware_encoder else None,
                prefer_none=not use_hardware,
            )
        finally:
            self._loading_settings = False

    def _build_output_paths(
        self, input_paths: List[str], output_dir: Optional[str]
    ) -> Dict[str, str]:
        """Build output paths for the selected inputs."""
        source_roots = dict(self._file_list.get_entries())
        return {
            input_path: build_conversion_output_path(
                input_path,
                output_dir=output_dir,
                source_root=source_roots.get(input_path),
                output_codec=self._get_selected_output_codec(),
            )
            for input_path in input_paths
        }

    def _build_queue_output_path(self, input_path: str, source_root: Optional[str]) -> str:
        """Build the output path for a queue item."""
        output_dir = self._output_input.text().strip() or None
        return build_conversion_output_path(
            input_path,
            output_dir=output_dir,
            source_root=source_root,
            output_codec=self._get_selected_output_codec(),
        )

    def _display_name_for_queue_item(
        self, input_path: str, source_root: Optional[str]
    ) -> str:
        """Build the visible label for a queue item."""
        file_path = Path(input_path)
        if source_root:
            try:
                return file_path.relative_to(Path(source_root)).as_posix()
            except ValueError:
                pass
        return file_path.name

    def _replace_queue_item(
        self,
        item: ConvertQueueItem,
        *,
        item_id: Optional[str] = None,
        status: Optional[ConvertQueueItemStatus] = None,
        progress_percent: Optional[float] = None,
        detail: Optional[str] = None,
        error_message: Optional[str] = None,
        output_path: Optional[str] = None,
        display_name: Optional[str] = None,
        source_root: Optional[str] = None,
    ) -> ConvertQueueItem:
        """Return a copy of a queue item with updated fields."""
        return ConvertQueueItem(
            item_id=item.item_id if item_id is None else item_id,
            input_path=item.input_path,
            output_path=item.output_path if output_path is None else output_path,
            display_name=item.display_name if display_name is None else display_name,
            source_root=item.source_root if source_root is None else source_root,
            status=item.status if status is None else status,
            progress_percent=(
                item.progress_percent
                if progress_percent is None
                else progress_percent
            ),
            detail=item.detail if detail is None else detail,
            error_message=(
                item.error_message if error_message is None else error_message
            ),
        )

    def _sync_queue_items(self) -> None:
        """Sync durable queue items with the current file list and settings."""
        entries = self._file_list.get_entries()
        source_root_by_path = {
            input_path: source_root for input_path, source_root in entries
        }
        self._restored_output_paths = {
            input_path: output_path
            for input_path, output_path in self._restored_output_paths.items()
            if input_path in source_root_by_path
        }
        existing_by_path = {item.input_path: item for item in self._queue_items}

        ordered_paths = [
            item.input_path
            for item in self._queue_items
            if item.input_path in source_root_by_path
        ]
        for input_path, _source_root in entries:
            if input_path not in ordered_paths:
                ordered_paths.append(input_path)

        updated_items: List[ConvertQueueItem] = []
        for input_path in ordered_paths:
            source_root = source_root_by_path[input_path]
            existing_item = existing_by_path.get(input_path)
            output_path = self._restored_output_paths.get(input_path)
            if output_path is None:
                output_path = self._build_queue_output_path(input_path, source_root)
            display_name = self._display_name_for_queue_item(input_path, source_root)
            if existing_item is None:
                updated_items.append(
                    ConvertQueueItem(
                        item_id=input_path,
                        input_path=input_path,
                        output_path=output_path,
                        display_name=display_name,
                        source_root=source_root,
                        detail="Pending",
                    )
                )
                continue

            updated_items.append(
                self._replace_queue_item(
                    existing_item,
                    output_path=output_path,
                    display_name=display_name,
                    source_root=source_root,
                )
            )

        self._queue_items = updated_items
        self._refresh_queue_widget()

    def _clear_auto_skipped_queue_items(self) -> None:
        """Reset filter-generated skips while preserving explicit user skips."""
        updated_items: List[ConvertQueueItem] = []
        changed = False
        for item in self._queue_items:
            if (
                item.status is ConvertQueueItemStatus.SKIPPED
                and item.detail.startswith("Skipped (")
            ):
                updated_items.append(
                    self._replace_queue_item(
                        item,
                        status=ConvertQueueItemStatus.PENDING,
                        detail="Pending",
                    )
                )
                changed = True
                continue
            updated_items.append(item)

        if not changed:
            return

        self._queue_items = updated_items
        self._refresh_queue_widget()

    def _refresh_queue_widget(self) -> None:
        """Render the durable queue item list."""
        self._queue_widget.set_queue_items(self._queue_items)
        self._queue_widget.setVisible(bool(self._queue_items))

    def _has_startable_queue_items(self) -> bool:
        """Return whether the queue has at least one item that can run now."""
        return any(
            item.status
            in {
                ConvertQueueItemStatus.PENDING,
                ConvertQueueItemStatus.INCOMPLETE,
                ConvertQueueItemStatus.PROCESSING,
            }
            for item in self._queue_items
        )

    def _mark_unstarted_queue_items_incomplete(
        self, *, detail: str = "Cancelled before start"
    ) -> None:
        """Mark queued-but-never-started items as incomplete after interruption."""
        updated_items: List[ConvertQueueItem] = []
        changed = False
        for item in self._queue_items:
            if item.status is ConvertQueueItemStatus.PENDING:
                updated_items.append(
                    self._replace_queue_item(
                        item,
                        status=ConvertQueueItemStatus.INCOMPLETE,
                        progress_percent=0.0,
                        detail=detail,
                        error_message="",
                    )
                )
                changed = True
                continue
            updated_items.append(item)

        if not changed:
            return

        self._queue_items = updated_items
        self._refresh_queue_widget()

    def _mark_active_queue_item_incomplete(self) -> None:
        """Reset the active row so resume restarts it from the beginning."""
        if self._active_queue_item_id is None:
            return

        self._update_queue_item(
            self._active_queue_item_id,
            status=ConvertQueueItemStatus.INCOMPLETE,
            progress_percent=0.0,
            detail="Restart from beginning",
            error_message="",
        )
        self._active_queue_item_id = None

    def _normalize_restored_queue_items(
        self, items: List[ConvertQueueItem]
    ) -> List[ConvertQueueItem]:
        """Map restored rows onto resumable Convert states."""
        normalized_items: List[ConvertQueueItem] = []
        for item in items:
            item = self._replace_queue_item(
                item,
                item_id=item.input_path,
                display_name=item.display_name or self._display_name_for_queue_item(
                    item.input_path, item.source_root
                ),
            )
            if item.status is ConvertQueueItemStatus.PROCESSING:
                normalized_items.append(
                    self._replace_queue_item(
                        item,
                        status=ConvertQueueItemStatus.INCOMPLETE,
                        progress_percent=0.0,
                        detail="Restart from beginning",
                        error_message="",
                    )
                )
                continue
            if item.status is ConvertQueueItemStatus.INCOMPLETE:
                normalized_items.append(
                    self._replace_queue_item(
                        item,
                        progress_percent=0.0,
                        detail="Restart from beginning",
                    )
                )
                continue
            normalized_items.append(item)
        return normalized_items

    def _set_restored_file_entries(self, items: List[ConvertQueueItem]) -> None:
        """Populate the source-file list from restored queue items."""
        self._file_list._entries = [
            (item.input_path, item.source_root) for item in items
        ]
        self._file_list._render_index = 0
        self._file_list._render_timer.stop()
        self._file_list._rebuild_list_widget()

    def _prepare_queue_items_for_start(
        self, queue_items: List[ConvertQueueItem]
    ) -> List[ConvertQueueItem]:
        """Return the subset that should run and refresh row states for this attempt."""
        selected_output_format = self._codec_combo.currentText()
        startable_items: List[ConvertQueueItem] = []
        auto_skipped_count = 0
        selected_item_ids = {queue_item.item_id for queue_item in queue_items}

        for index, item in enumerate(self._queue_items):
            if item.item_id not in selected_item_ids:
                continue

            if item.status in {
                ConvertQueueItemStatus.SKIPPED,
                ConvertQueueItemStatus.COMPLETED,
                ConvertQueueItemStatus.FAILED,
            }:
                continue

            matches_output = self._source_codec_filter_check.isChecked() and (
                self._matches_selected_output_format(item.input_path)
            )
            if matches_output:
                auto_skipped_count += 1
                self._queue_items[index] = self._replace_queue_item(
                    item,
                    status=ConvertQueueItemStatus.SKIPPED,
                    progress_percent=0.0,
                    detail=f"Skipped ({selected_output_format})",
                    error_message="",
                )
                continue

            self._queue_items[index] = self._replace_queue_item(
                item,
                status=ConvertQueueItemStatus.PENDING,
                progress_percent=0.0,
                detail="Pending",
                error_message="",
            )
            startable_items.append(self._queue_items[index])

        self._refresh_queue_widget()

        if self._source_codec_filter_check.isChecked():
            if not startable_items:
                QMessageBox.information(
                    self,
                    "Nothing To Convert",
                    f'All selected files already match "{selected_output_format}".',
                )
                return []
            if auto_skipped_count > 0:
                QMessageBox.information(
                    self,
                    "Skipping Matching Files",
                    f"Skipping {auto_skipped_count} file(s) that already match {selected_output_format}.",
                )
        elif not startable_items:
            return []

        return startable_items

    def _start_conversion_for_queue_items(
        self, queue_items: List[ConvertQueueItem]
    ) -> None:
        """Start conversion using the supplied queue subset and saved output paths."""
        if not queue_items:
            return

        self._cancel_requested_during_run = False
        self._pause_requested_during_run = False
        self._active_queue_item_id = None

        config = self._build_config()
        files_to_convert = [item.input_path for item in queue_items]
        output_paths = {item.input_path: item.output_path for item in queue_items}

        self._conversion_manager = ConversionManager()
        self._conversion_manager.set_config(config)
        self._conversion_manager.job_started.connect(self._on_job_started)
        self._conversion_manager.job_progress.connect(self._on_job_progress)
        self._conversion_manager.job_completed.connect(self._on_job_completed)
        self._conversion_manager.queue_progress.connect(self._on_queue_progress)
        self._conversion_manager.all_completed.connect(self._on_all_completed)
        self._conversion_manager.job_creation_progress.connect(
            self._on_job_creation_progress
        )
        self._conversion_manager.jobs_created.connect(self._on_jobs_created)
        self._conversion_manager.files_deleted.connect(self._on_files_deleted)

        self._file_list.set_enabled(False)
        self._queue_widget.set_actions_enabled(False)
        self._start_btn.setEnabled(False)
        self._cancel_btn.setVisible(True)

        self._overall_progress.setMaximum(len(files_to_convert))
        self._overall_progress.setValue(0)
        self._overall_progress.setVisible(True)

        self.start_requested.emit()
        self._conversion_manager.add_files_async(
            files_to_convert,
            config.output_dir,
            output_paths=output_paths,
        )

    def _find_queue_item_by_path(self, input_path: str) -> Optional[ConvertQueueItem]:
        """Find a queue item by source path."""
        for item in self._queue_items:
            if item.input_path == input_path:
                return item
        return None

    def _find_queue_index(self, item_id: str) -> int:
        """Find the index of a queue item by item id."""
        for index, item in enumerate(self._queue_items):
            if item.item_id == item_id:
                return index
        return -1

    def _update_queue_item(self, item_id: str, **changes) -> None:
        """Apply updates to a queue item and refresh the widget."""
        index = self._find_queue_index(item_id)
        if index < 0:
            return
        self._queue_items[index] = self._replace_queue_item(
            self._queue_items[index], **changes
        )
        self._refresh_queue_widget()

    def _on_queue_reorder_requested(self, source_index: int, target_index: int) -> None:
        """Move a queue item to a new position."""
        if source_index == target_index:
            return
        if source_index < 0 or target_index < 0:
            return
        if source_index >= len(self._queue_items) or target_index >= len(self._queue_items):
            return

        item = self._queue_items.pop(source_index)
        self._queue_items.insert(target_index, item)
        self._refresh_queue_widget()

    def _on_queue_skip_requested(self, item_id: str) -> None:
        """Toggle whether a queue item is skipped."""
        index = self._find_queue_index(item_id)
        if index < 0:
            return

        item = self._queue_items[index]
        if item.status is ConvertQueueItemStatus.PROCESSING:
            return

        if item.status is ConvertQueueItemStatus.SKIPPED:
            self._queue_items[index] = self._replace_queue_item(
                item,
                status=ConvertQueueItemStatus.PENDING,
                progress_percent=0.0,
                detail="Pending",
                error_message="",
            )
        else:
            self._queue_items[index] = self._replace_queue_item(
                item,
                status=ConvertQueueItemStatus.SKIPPED,
                progress_percent=0.0,
                detail="Skipped",
                error_message="",
            )

        self._refresh_queue_widget()
        self._update_start_button_state()

    def _on_queue_prioritize_requested(self, item_id: str) -> None:
        """Move the selected queue item to the front."""
        index = self._find_queue_index(item_id)
        if index <= 0:
            return
        item = self._queue_items.pop(index)
        self._queue_items.insert(0, item)
        self._refresh_queue_widget()

    def _update_preview(self) -> None:
        """Refresh the Convert preview tree."""
        entries = self._file_list.get_entries()
        if not entries:
            self._preview_tree.clear()
            return

        output_dir = self._output_input.text().strip() or None
        preview: Dict[str, List[str]] = {}
        for input_path, source_root in entries:
            folder = get_conversion_preview_folder(
                input_path,
                output_dir=output_dir,
                source_root=source_root,
            )
            preview.setdefault(folder, []).append(
                build_conversion_output_name(
                    input_path, output_codec=self._get_selected_output_codec()
                )
            )

        self._preview_tree.update_preview(preview)

    def _update_start_button_state(self) -> None:
        """Enable the start button only when the queue is fully prepared."""
        can_start = (
            self._file_list.count() > 0
            and self._has_startable_queue_items()
            and not self._file_list.is_busy()
            and self._preflight_worker is None
            and not self._cancel_btn.isVisible()
        )
        self._start_btn.setEnabled(can_start)
        self._update_preflight_status()

    def _update_preflight_status(self) -> None:
        """Explain why the queue is or is not ready to start."""
        if self._cancel_btn.isVisible():
            self._preflight_status_label.setText("Conversion in progress.")
            return

        file_count = self._file_list.count()
        if file_count == 0:
            self._preflight_status_label.setText("Add files to prepare the queue.")
            return

        if self._file_list.is_busy():
            self._preflight_status_label.setText(
                f"Loading {file_count} file(s) into the queue..."
            )
            return

        if self._preflight_worker is not None:
            self._preflight_status_label.setText(
                f"Analyzing {file_count} file(s) with ffprobe..."
            )
            return

        if not self._has_startable_queue_items():
            self._preflight_status_label.setText(
                "All queued files are skipped. Unskip at least one file to start."
            )
            return

        if not self._source_codec_filter_check.isChecked():
            self._preflight_status_label.setText(
                f"Ready to convert {file_count} file(s)."
            )
            return

        matching_count = sum(
            1
            for path in self._file_list.get_file_paths()
            if self._matches_selected_output_format(path)
        )
        if matching_count == 0:
            self._preflight_status_label.setText(
                f"Ready to convert {file_count} file(s)."
            )
            return

        self._preflight_status_label.setText(
            f"Ready. {matching_count} file(s) already match {self._codec_combo.currentText()} and will be skipped."
        )

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the page."""
        self._file_list.set_enabled(enabled)
        self._codec_combo.setEnabled(enabled)
        self._resolution_combo.setEnabled(enabled)
        self._crf_slider.setEnabled(enabled)
        self._preset_combo.setEnabled(enabled)
        if enabled:
            self._queue_widget.set_actions_enabled(True)
            self._hw_combo.setEnabled(self._hw_combo.count() > 1)
            self._source_codec_filter_check.setEnabled(True)
            self._update_start_button_state()
        else:
            self._queue_widget.set_actions_enabled(False)
            self._hw_combo.setEnabled(False)
            self._source_codec_filter_check.setEnabled(False)
            self._start_btn.setEnabled(False)
        self._output_input.setEnabled(enabled)
        self._output_browse_btn.setEnabled(enabled)