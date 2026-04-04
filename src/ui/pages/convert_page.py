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

from ...core.conversion_manager import ConversionManager
from ...core.conversion_paths import (
    SAME_AS_SOURCE_CODEC,
    build_conversion_output_name,
    build_conversion_output_path,
    get_conversion_output_extension,
    get_conversion_preview_folder,
    normalize_conversion_codec,
    resolve_conversion_output_codec,
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
from ..widgets.folder_preview_widget import FolderPreviewWidget
from ..widgets.process_log_dialog import ProcessLogDialog

logger = logging.getLogger(__name__)

OUTPUT_FORMATS = [
    ("Same as source", SAME_AS_SOURCE_CODEC),
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
AUDIO_MODE_DATA_ROLE = RESOLUTION_DATA_ROLE + 1
FRAME_RATE_DATA_ROLE = AUDIO_MODE_DATA_ROLE + 1

SAME_AS_SOURCE_RESOLUTION = "source"
SAME_AS_SOURCE_FRAME_RATE = "source"
DEFAULT_AUDIO_MODE = "copy"
DEFAULT_FRAME_RATE = SAME_AS_SOURCE_FRAME_RATE
AUDIO_MODE_OPTIONS = [
    ("Copy audio", "copy"),
    ("No audio", "none"),
]
FRAME_RATE_OPTIONS = [
    ("Same as source", SAME_AS_SOURCE_FRAME_RATE),
    ("23.976 fps", "23.976"),
    ("24 fps", "24"),
    ("25 fps", "25"),
    ("29.97 fps", "29.97"),
    ("30 fps", "30"),
    ("48 fps", "48"),
    ("50 fps", "50"),
    ("59.94 fps", "59.94"),
    ("60 fps", "60"),
]
HORIZONTAL_RESOLUTIONS = ["2160p", "1440p", "1080p", "720p"]
VERTICAL_RESOLUTIONS = ["2160p", "1440p", "1080p", "720p"]
ORIENTATION_RESOLUTION_OPTIONS = {
    "horizontal": HORIZONTAL_RESOLUTIONS,
    "vertical": VERTICAL_RESOLUTIONS,
}
OPPOSITE_ORIENTATION = {
    "horizontal": "vertical",
    "vertical": "horizontal",
}
MP4_COPY_COMPATIBLE_AUDIO_CODECS = {"aac", "mp3", "ac3", "eac3", "alac"}
WEBM_COPY_COMPATIBLE_AUDIO_CODECS = {"opus", "vorbis"}


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
        self._pending_job_widgets: Dict[int, str] = {}  # job_id -> filename
        self._done_count: int = 0
        self._failed_count: int = 0
        self._config_service = ConfigService()
        self._hardware_encoders: List[HardwareEncoder] = []
        self._saved_hw_encoder: Optional[str] = None
        self._file_codecs: Dict[str, str] = {}
        self._file_metadata: Dict[str, object] = {}
        self._job_input_paths: Dict[int, str] = {}
        self._loading_settings = False
        self._process_log_dialog = ProcessLogDialog(
            title="Convert Log",
            description=(
                "Live conversion activity with per-file output status and the exact FFmpeg command used."
            ),
            parent=self,
        )

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

        self._jobs_list = QListWidget()
        self._jobs_list.setMaximumHeight(120)
        self._jobs_list.setVisible(False)
        files_panel.body_layout.addWidget(self._jobs_list)

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

        sl.addWidget(QLabel("Audio"))
        self._audio_mode_combo = QComboBox()
        self._audio_mode_combo.setToolTip(
            "Video outputs can either copy the source audio track or drop audio entirely."
        )
        for label, mode in AUDIO_MODE_OPTIONS:
            self._audio_mode_combo.addItem(label, mode)
        sl.addWidget(self._audio_mode_combo)

        sl.addWidget(QLabel("Frame Rate"))
        self._frame_rate_combo = QComboBox()
        self._frame_rate_combo.setToolTip(
            "Choose a fixed output frame rate or keep the source frame rate."
        )
        for label, value in FRAME_RATE_OPTIONS:
            self._frame_rate_combo.addItem(label, value)
        sl.addWidget(self._frame_rate_combo)

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

        self._view_log_btn = QPushButton("View Log")
        self._view_log_btn.setObjectName("btnWire")
        self._view_log_btn.setProperty("button_role", "secondary")
        right_layout.addWidget(self._view_log_btn)

        root.addWidget(split, stretch=1)

    def _connect_signals(self) -> None:
        """Wire up all signal connections."""
        self._file_list.files_changed.connect(self._on_files_changed)
        self._file_list.loading_state_changed.connect(self._on_file_list_loading_changed)
        self._start_btn.clicked.connect(self._on_start)
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._crf_slider.valueChanged.connect(self._on_crf_changed)
        self._codec_combo.currentIndexChanged.connect(self._on_output_codec_changed)
        self._resolution_combo.currentIndexChanged.connect(self._on_settings_changed)
        self._audio_mode_combo.currentIndexChanged.connect(self._on_settings_changed)
        self._frame_rate_combo.currentIndexChanged.connect(self._on_settings_changed)
        self._preset_combo.currentIndexChanged.connect(self._on_settings_changed)
        self._hw_combo.currentIndexChanged.connect(self._on_settings_changed)
        self._source_codec_filter_check.toggled.connect(self._on_settings_changed)
        self._output_input.textChanged.connect(self._on_settings_changed)
        self._output_input.textChanged.connect(self._update_preview)
        self._output_browse_btn.clicked.connect(self._on_browse_output)
        self._view_log_btn.clicked.connect(self._on_view_log)
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

            audio_mode = self._normalize_audio_mode(
                self._config_service.get("convert.audio_mode", DEFAULT_AUDIO_MODE)
            )
            self._set_selected_audio_mode(audio_mode)

            frame_rate = self._normalize_frame_rate_value(
                self._config_service.get(
                    "convert.frame_rate", SAME_AS_SOURCE_FRAME_RATE
                )
            )
            self._set_selected_frame_rate(frame_rate)

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
            if codec == SAME_AS_SOURCE_CODEC:
                source_filter_enabled = False
            self._source_codec_filter_check.setChecked(source_filter_enabled)
        finally:
            self._loading_settings = False

        self._sync_output_format_state()
        self._update_start_button_state()

    def _save_settings(self) -> None:
        """Save current settings to config service."""
        if self._loading_settings:
            return

        codec = self._get_selected_output_codec()
        hardware_encoder = self._hw_combo.currentData()
        self._config_service.set("convert.codec", codec)
        self._config_service.set("convert.resolution", self._get_selected_resolution())
        self._config_service.set("convert.audio_mode", self._get_selected_audio_mode())
        self._config_service.set("convert.frame_rate", self._get_selected_frame_rate())
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
        self._sync_output_format_state()
        preferred_hardware = self._hw_combo.currentData()
        self._refresh_hardware_options(
            preferred_name=preferred_hardware, prefer_none=preferred_hardware is None
        )
        self._update_preview()
        self._update_start_button_state()
        self._on_settings_changed()

    def _on_settings_changed(self) -> None:
        """Save settings on any change."""
        self._save_settings()
        self._update_start_button_state()

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

    def _on_view_log(self) -> None:
        """Show the live conversion log dialog."""
        self._process_log_dialog.show()
        self._process_log_dialog.raise_()
        self._process_log_dialog.activateWindow()

    def _on_files_changed(self) -> None:
        """Refresh queue readiness when the file set changes."""
        self._refresh_preflight_scan()
        self._update_preview()
        self._update_start_button_state()

    def _on_file_list_loading_changed(self, _loading: bool) -> None:
        """Refresh readiness state while the list is still rendering."""
        self._update_start_button_state()

    def _on_start(self) -> None:
        """Start conversion."""
        files = self._file_list.get_file_paths()
        if not files:
            return

        if self._file_list.is_busy() or self._preflight_worker is not None:
            QMessageBox.information(
                self,
                "Preparing Queue",
                "Please wait for file loading and analysis to finish before starting the conversion.",
            )
            return

        files_to_convert = files
        selected_output_format = self._codec_combo.currentText()
        if self._source_codec_filter_check.isChecked():
            files_to_convert = [
                path
                for path in files
                if not self._matches_selected_output_format(path)
            ]
            skipped_count = len(files) - len(files_to_convert)
            if not files_to_convert:
                QMessageBox.information(
                    self,
                    "Nothing To Convert",
                    f'All selected files already match "{selected_output_format}".',
                )
                return
            if skipped_count > 0:
                QMessageBox.information(
                    self,
                    "Skipping Matching Files",
                    f"Skipping {skipped_count} file(s) that already match {selected_output_format}.",
                )

        config = self._build_config()
        unsupported_source_paths = self._unsupported_source_output_paths(files_to_convert)
        if unsupported_source_paths:
            unsupported_names = [Path(path).name for path in unsupported_source_paths[:5]]
            remaining = len(unsupported_source_paths) - len(unsupported_names)
            suffix = ""
            if remaining > 0:
                suffix = f"\n...and {remaining} more file(s)."
            QMessageBox.warning(
                self,
                "Unsupported Source Format",
                "Same as source is only available for H.264, H.265, VP9, MP3, AAC, and FLAC inputs.\n\n"
                "Unsupported files:\n" + "\n".join(unsupported_names) + suffix,
            )
            return

        incompatible_audio_paths = self._incompatible_audio_copy_paths(files_to_convert)
        if incompatible_audio_paths:
            incompatible_names = [Path(path).name for path in incompatible_audio_paths[:5]]
            remaining = len(incompatible_audio_paths) - len(incompatible_names)
            suffix = ""
            if remaining > 0:
                suffix = f"\n...and {remaining} more file(s)."
            output_label = self._codec_combo.currentText()
            QMessageBox.warning(
                self,
                "Audio Copy Not Supported",
                "The selected output container cannot copy one or more source audio tracks. "
                "Choose No audio or use files with a compatible audio codec.\n\n"
                f"Output format: {output_label}\n\n"
                f"Affected files:\n" + "\n".join(incompatible_names) + suffix,
            )
            return

        output_paths = self._build_output_paths(files_to_convert, config.output_dir)
        source_codecs = self._build_source_codec_map(files_to_convert)

        # Create manager
        self._conversion_manager = ConversionManager()
        self._conversion_manager.set_config(config)
        self._process_log_dialog.clear()
        self._process_log_dialog.add_log_entry(
            "info",
            f"Queued {len(files_to_convert)} file(s) for conversion.",
        )

        # Connect manager signals
        self._conversion_manager.job_started.connect(self._on_job_started)
        self._conversion_manager.job_progress.connect(self._on_job_progress)
        self._conversion_manager.job_completed.connect(self._on_job_completed)
        self._conversion_manager.job_command_built.connect(self._on_job_command_built)
        self._conversion_manager.queue_progress.connect(self._on_queue_progress)
        self._conversion_manager.all_completed.connect(self._on_all_completed)
        self._conversion_manager.job_creation_progress.connect(
            self._on_job_creation_progress
        )
        self._conversion_manager.jobs_created.connect(self._on_jobs_created)
        self._conversion_manager.files_deleted.connect(self._on_files_deleted)
        self._conversion_manager.log.connect(self._on_manager_log)

        # Disable controls while running
        self._file_list.set_enabled(False)
        self._start_btn.setEnabled(False)
        self._cancel_btn.setVisible(True)

        # Show preparing status
        self._overall_progress.setMaximum(len(files_to_convert))
        self._overall_progress.setValue(0)
        self._overall_progress.setVisible(True)
        self._jobs_list.setVisible(False)

        self.start_requested.emit()

        # Start async job creation (non-blocking)
        self._conversion_manager.add_files_async(
            files_to_convert,
            config.output_dir,
            output_paths=output_paths,
            source_codecs=source_codecs,
        )

    def _on_cancel(self) -> None:
        """Cancel all conversions."""
        if self._conversion_manager:
            self._conversion_manager.cancel_all()
        self.cancel_requested.emit()

    # ------------------------------------------------------------------
    # Manager signal handlers
    # ------------------------------------------------------------------

    def _on_job_creation_progress(self, current: int, total: int) -> None:
        """Update UI while jobs are being created."""
        self._overall_progress.setMaximum(total if total > 0 else 1)

    def _on_jobs_created(self, jobs: List[ConversionJob]) -> None:
        """Prepare progress display once all jobs are created."""
        self._pending_job_widgets = {}
        self._job_input_paths = {}
        for job in jobs:
            if job.id is not None:
                self._pending_job_widgets[job.id] = Path(job.input_path).name
                self._job_input_paths[job.id] = job.input_path
                self._process_log_dialog.upsert_record(
                    str(job.id),
                    title=Path(job.input_path).name,
                    input_path=job.input_path,
                    status="Queued",
                    output_path=job.output_path,
                )

        self._done_count = 0
        self._failed_count = 0
        self._jobs_list.clear()
        self._jobs_list.setVisible(bool(jobs))
        self._overall_progress.setMaximum(len(jobs))
        self._overall_progress.setValue(0)

        self.conversion_started.emit()

        # Start processing
        self._conversion_manager.start()

    def _on_job_started(self, job_id: int) -> None:
        """Add job entry to the jobs list when it starts."""
        if job_id in self._pending_job_widgets:
            filename = self._pending_job_widgets.pop(job_id)
            item = QListWidgetItem(f"{filename} — Converting…")
            item.setData(Qt.ItemDataRole.UserRole, job_id)
            self._jobs_list.addItem(item)
            self._process_log_dialog.upsert_record(
                str(job_id),
                title=filename,
                input_path=self._job_input_paths.get(job_id, ""),
                status="Converting",
            )

    def _on_job_progress(
        self, job_id: int, percent: float, speed: str, eta: str
    ) -> None:
        """Update job list item text with progress info."""
        for i in range(self._jobs_list.count()):
            item = self._jobs_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == job_id:
                name = item.text().split(" — ")[0]
                item.setText(f"{name} — {percent:.0f}% | {speed} | ETA {eta}")
                break

    def _on_job_completed(
        self, job_id: int, success: bool, output_path: str, error: str
    ) -> None:
        """Mark job as complete or failed in the list."""
        status_text = "Complete" if success else ("Cancelled" if "Cancelled" in error else "Failed")
        for i in range(self._jobs_list.count()):
            item = self._jobs_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == job_id:
                name = item.text().split(" — ")[0]
                if success:
                    self._done_count += 1
                    item.setText(f"{name} — {status_text}")
                else:
                    self._failed_count += 1
                    item.setText(f"{name} — {status_text}")
                break

        self._process_log_dialog.upsert_record(
            str(job_id),
            title=Path(self._job_input_paths.get(job_id, output_path or str(job_id))).name,
            input_path=self._job_input_paths.get(job_id, ""),
            status=status_text,
            output_path=output_path,
            details=error or "Output ready.",
        )

    def _on_queue_progress(self, completed: int, total: int, in_progress: int) -> None:
        """Update overall progress bar."""
        self._overall_progress.setMaximum(total if total > 0 else 1)
        self._overall_progress.setValue(completed)

    def _on_all_completed(self) -> None:
        """Reset UI after all conversions finish."""
        self._file_list.set_enabled(True)
        self._cancel_btn.setVisible(False)
        self._overall_progress.setVisible(False)

        if self._conversion_manager:
            completed = self._conversion_manager.completed_count
            failed = self._conversion_manager.failed_count

            self.conversion_completed.emit(completed, failed)

            if failed == 0:
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

            self._process_log_dialog.add_log_entry(
                "warning" if failed else "info",
                f"Conversion finished: {completed} completed, {failed} failed.",
            )

            self._conversion_manager.reset_counts()

        self._done_count = 0
        self._failed_count = 0
        if self._jobs_list.count() == 0:
            self._jobs_list.setVisible(False)
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
        return normalize_conversion_codec(codec_map.get(codec, codec))

    def _normalize_source_codec(self, codec: str) -> str:
        """Normalize source codec values from ffprobe."""
        return normalize_conversion_codec(codec)

    def _get_selected_output_codec(self) -> str:
        """Get the selected output codec."""
        return self._codec_combo.currentData() or "h264"

    def _sync_output_format_state(self) -> None:
        """Keep dependent controls in sync with the selected output format."""
        is_source_output = self._get_selected_output_codec() == SAME_AS_SOURCE_CODEC
        if is_source_output and self._source_codec_filter_check.isChecked():
            self._source_codec_filter_check.setChecked(False)
        self._source_codec_filter_check.setEnabled(
            self.isEnabled() and not is_source_output
        )

    def _build_source_codec_map(self, input_paths: List[str]) -> Dict[str, str]:
        """Build a source codec map for queued files."""
        return {
            path: self._file_codecs[path]
            for path in input_paths
            if path in self._file_codecs
        }

    def _unsupported_source_output_paths(
        self, input_paths: Optional[List[str]] = None
    ) -> List[str]:
        """Return queued files that cannot use Same as source output."""
        if self._get_selected_output_codec() != SAME_AS_SOURCE_CODEC:
            return []

        paths = input_paths if input_paths is not None else self._file_list.get_file_paths()
        unsupported_paths: List[str] = []
        for path in paths:
            if resolve_conversion_output_codec(
                SAME_AS_SOURCE_CODEC,
                self._file_codecs.get(path),
            ) is None:
                unsupported_paths.append(path)
        return unsupported_paths

    def _on_manager_log(self, level: str, message: str) -> None:
        """Append manager and worker log entries to the popout log."""
        self._process_log_dialog.add_log_entry(level, message)

    def _on_job_command_built(self, job_id: int, input_path: str, command: str) -> None:
        """Store the FFmpeg command used for a queued file."""
        self._process_log_dialog.upsert_record(
            str(job_id),
            title=Path(input_path).name,
            input_path=input_path,
            command=command,
        )

    def _normalize_resolution_value(self, value: Optional[str]) -> str:
        """Normalize stored output resolution values."""
        normalized = (value or "").strip().lower()
        if normalized == SAME_AS_SOURCE_RESOLUTION:
            return SAME_AS_SOURCE_RESOLUTION

        legacy_map = {
            "3840x2160": "2160p",
            "2560x1440": "1440p",
            "1920x1080": "1080p",
            "1280x720": "720p",
            "2160x3840": "vertical:2160p",
            "1440x2560": "vertical:1440p",
            "1080x1920": "vertical:1080p",
            "720x1280": "vertical:720p",
        }
        normalized = legacy_map.get(normalized, normalized)

        combined = set(HORIZONTAL_RESOLUTIONS)
        combined.update(f"horizontal:{resolution}" for resolution in HORIZONTAL_RESOLUTIONS)
        combined.update(f"vertical:{resolution}" for resolution in VERTICAL_RESOLUTIONS)
        return normalized if normalized in combined else SAME_AS_SOURCE_RESOLUTION

    def _normalize_audio_mode(self, value: Optional[str]) -> str:
        """Normalize stored audio mode values."""
        normalized = (value or "").strip().lower()
        supported_values = {mode for _, mode in AUDIO_MODE_OPTIONS}
        return normalized if normalized in supported_values else DEFAULT_AUDIO_MODE

    def _normalize_frame_rate_value(self, value: Optional[str]) -> str:
        """Normalize stored output frame rate values."""
        normalized = (value or "").strip().lower()
        supported_values = {frame_rate for _, frame_rate in FRAME_RATE_OPTIONS}
        if normalized in supported_values:
            return normalized
        return SAME_AS_SOURCE_FRAME_RATE

    def _set_selected_output_codec(self, codec: str) -> None:
        """Set the selected output codec."""
        normalized = self._normalize_output_codec(codec)
        index = self._codec_combo.findData(normalized)
        self._codec_combo.setCurrentIndex(index if index >= 0 else 0)

    def _get_selected_resolution(self) -> str:
        """Get the selected output resolution value."""
        resolution = self._resolution_combo.currentData(RESOLUTION_DATA_ROLE)
        return self._normalize_resolution_value(resolution)

    def _get_selected_audio_mode(self) -> str:
        """Get the selected audio mode."""
        audio_mode = self._audio_mode_combo.currentData()
        return self._normalize_audio_mode(audio_mode)

    def _get_selected_frame_rate(self) -> str:
        """Get the selected output frame rate."""
        frame_rate = self._frame_rate_combo.currentData()
        return self._normalize_frame_rate_value(frame_rate)

    def _set_selected_resolution(self, resolution: str) -> None:
        """Set the selected output resolution."""
        normalized = self._normalize_resolution_value(resolution)
        index = self._find_resolution_index(normalized)
        self._resolution_combo.setCurrentIndex(index if index >= 0 else 0)

    def _set_selected_audio_mode(self, audio_mode: str) -> None:
        """Set the selected audio mode."""
        normalized = self._normalize_audio_mode(audio_mode)
        index = self._audio_mode_combo.findData(normalized)
        self._audio_mode_combo.setCurrentIndex(index if index >= 0 else 0)

    def _set_selected_frame_rate(self, frame_rate: str) -> None:
        """Set the selected output frame rate."""
        normalized = self._normalize_frame_rate_value(frame_rate)
        index = self._frame_rate_combo.findData(normalized)
        self._frame_rate_combo.setCurrentIndex(index if index >= 0 else 0)

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

    def _resolution_value_for_orientation(
        self, resolution: str, orientation: str, *, is_override: bool
    ) -> str:
        """Build the stored resolution token for a combo entry."""
        if not is_override:
            return resolution
        return f"{orientation}:{resolution}"

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
                self._resolution_value_for_orientation(
                    resolution, auto_orientation, is_override=False
                ),
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
                self._resolution_value_for_orientation(
                    resolution, override_orientation, is_override=True
                ),
                RESOLUTION_DATA_ROLE,
            )

        self._set_selected_resolution(selected_resolution)
        self._resolution_combo.blockSignals(False)

    def _matches_selected_output_format(self, file_path: str) -> bool:
        """Return whether the input already matches the selected output format."""
        output_codec = self._get_selected_output_codec()
        resolved_output_codec = resolve_conversion_output_codec(
            output_codec,
            self._file_codecs.get(file_path),
        )
        if resolved_output_codec is None:
            return False

        expected_extension = get_conversion_output_extension(
            output_codec,
            input_path=file_path,
            source_codec=self._file_codecs.get(file_path),
        )
        if Path(file_path).suffix.lower() != expected_extension:
            return False

        if resolved_output_codec in {"h264", "hevc", "vp9"}:
            return self._file_codecs.get(file_path) == resolved_output_codec

        return True

    def _incompatible_audio_copy_paths(
        self, input_paths: Optional[List[str]] = None
    ) -> List[str]:
        """Return queued files whose audio cannot be copied into the selected container."""
        if self._get_selected_audio_mode() != "copy":
            return []

        selected_output_codec = self._get_selected_output_codec()
        if selected_output_codec not in {"h264", "hevc", "vp9"}:
            return []

        allowed_audio_codecs = (
            WEBM_COPY_COMPATIBLE_AUDIO_CODECS
            if selected_output_codec == "vp9"
            else MP4_COPY_COMPATIBLE_AUDIO_CODECS
        )

        paths = input_paths if input_paths is not None else self._file_list.get_file_paths()
        incompatible_paths: List[str] = []
        for path in paths:
            metadata = self._file_metadata.get(path)
            audio_codec = getattr(metadata, "audio_codec", "")
            normalized_audio_codec = normalize_conversion_codec(audio_codec)
            if normalized_audio_codec and normalized_audio_codec not in allowed_audio_codecs:
                incompatible_paths.append(path)
        return incompatible_paths

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
        if output_codec == SAME_AS_SOURCE_CODEC:
            self._saved_hw_encoder = self._hw_combo.currentData()
            self._hw_combo.blockSignals(True)
            self._hw_combo.setEnabled(False)
            status_message = (
                "Hardware acceleration is unavailable when output format is set to Same as source."
            )
            self._hw_combo.setToolTip(status_message)
            self._hw_status_label.setText(status_message)
            self._hw_status_label.setVisible(True)
            self._hw_combo.blockSignals(False)
            return

        # Restore saved encoder selection when leaving SAME_AS_SOURCE_CODEC
        if preferred_name is None and self._saved_hw_encoder is not None:
            preferred_name = self._saved_hw_encoder
            prefer_none = False
        self._saved_hw_encoder = None

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
            audio_mode=self._get_selected_audio_mode(),
            frame_rate=(
                None
                if self._get_selected_frame_rate() == SAME_AS_SOURCE_FRAME_RATE
                else self._get_selected_frame_rate()
            ),
            crf_value=self._crf_slider.value(),
            preset=self._preset_combo.currentText(),
            use_hardware_accel=use_hw,
            hardware_encoder=hw_encoder,
            output_dir=self._output_input.text() or None,
        )

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
                source_codec=self._file_codecs.get(input_path),
            )
            for input_path in input_paths
        }

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
                    input_path,
                    output_codec=self._get_selected_output_codec(),
                    source_codec=self._file_codecs.get(input_path),
                )
            )

        self._preview_tree.update_preview(preview)

    def _update_start_button_state(self) -> None:
        """Enable the start button only when the queue is fully prepared."""
        can_start = (
            self._file_list.count() > 0
            and not self._file_list.is_busy()
            and self._preflight_worker is None
            and not self._incompatible_audio_copy_paths()
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

        unsupported_source_paths = self._unsupported_source_output_paths()
        if unsupported_source_paths:
            self._preflight_status_label.setText(
                "Same as source is only available for H.264, H.265, VP9, MP3, AAC, and FLAC inputs."
            )
            return

        incompatible_audio_paths = self._incompatible_audio_copy_paths()
        if incompatible_audio_paths:
            self._preflight_status_label.setText(
                "Copy audio is unavailable for one or more files in the selected output format."
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
        self._audio_mode_combo.setEnabled(enabled)
        self._frame_rate_combo.setEnabled(enabled)
        self._crf_slider.setEnabled(enabled)
        self._preset_combo.setEnabled(enabled)
        if enabled:
            self._hw_combo.setEnabled(self._hw_combo.count() > 1)
            self._sync_output_format_state()
            self._update_start_button_state()
        else:
            self._hw_combo.setEnabled(False)
            self._source_codec_filter_check.setEnabled(False)
            self._start_btn.setEnabled(False)
        self._output_input.setEnabled(enabled)
        self._output_browse_btn.setEnabled(enabled)
        self._view_log_btn.setEnabled(True)
