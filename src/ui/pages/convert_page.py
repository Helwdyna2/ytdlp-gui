"""ConvertPage — video conversion tool page using SplitLayout."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt, pyqtSignal
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
    build_conversion_output_name,
    build_conversion_output_path,
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

SOURCE_CODEC_DISPLAY_NAMES = {
    "h264": "H.264",
    "hevc": "H.265 (HEVC)",
    "vp9": "VP9",
}

TARGET_CODECS_WITH_SOURCE_FILTER = {"h264", "hevc"}
FILE_PATH_ROLE = int(Qt.ItemDataRole.UserRole)
SOURCE_ROOT_ROLE = FILE_PATH_ROLE + 1


class FileListWidget(QWidget):
    """Widget for managing the list of files to convert."""

    files_changed = pyqtSignal()  # Emitted when files are added/removed

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scan_worker: Optional[FolderScanWorker] = None
        self._scan_root: Optional[str] = None
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

    def _add_paths(
        self, paths: List[str], source_root: Optional[str] = None
    ) -> None:
        """Add file paths to the list, skipping duplicates."""
        existing = set(self.get_file_paths())
        for path in paths:
            if path not in existing:
                item = QListWidgetItem(self._display_name_for_path(path, source_root))
                item.setData(FILE_PATH_ROLE, path)
                item.setData(SOURCE_ROOT_ROLE, source_root)
                item.setToolTip(path)
                self._list_widget.addItem(item)
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
        for item in self._list_widget.selectedItems():
            self._list_widget.takeItem(self._list_widget.row(item))
        self.files_changed.emit()

    def _on_clear(self) -> None:
        """Clear all files."""
        self._list_widget.clear()
        self.files_changed.emit()

    def get_file_paths(self) -> List[str]:
        """Get all file paths in the list."""
        paths = []
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item is not None:
                paths.append(item.data(FILE_PATH_ROLE))
        return paths

    def get_entries(self) -> List[Tuple[str, Optional[str]]]:
        """Get all file entries with their optional source roots."""
        entries: List[Tuple[str, Optional[str]]] = []
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item is not None:
                entries.append(
                    (item.data(FILE_PATH_ROLE), item.data(SOURCE_ROOT_ROLE))
                )
        return entries

    def get_selected_file_path(self) -> Optional[str]:
        """Get the first selected file path, or None if no selection."""
        items = self._list_widget.selectedItems()
        if items:
            return items[0].data(FILE_PATH_ROLE)
        return None

    def count(self) -> int:
        """Get number of files."""
        return self._list_widget.count()

    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable the widget."""
        self._add_files_btn.setEnabled(enabled)
        self._add_folder_btn.setEnabled(enabled)
        self._remove_btn.setEnabled(enabled)
        self._clear_btn.setEnabled(enabled)
        self._list_widget.setEnabled(enabled)


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
        self._codec_probe_worker: Optional[FFprobeWorker] = None
        self._codec_probe_request_id = 0
        self._pending_job_widgets: Dict[int, str] = {}  # job_id -> filename
        self._done_count: int = 0
        self._failed_count: int = 0
        self._config_service = ConfigService()
        self._hardware_encoders: List[HardwareEncoder] = []
        self._file_codecs: Dict[str, str] = {}
        self._loading_settings = False

        self._setup_ui()
        self._connect_signals()
        self._load_settings()
        self._detect_hardware()
        self._refresh_source_codec_scan()

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

        self._source_codec_filter_check = QCheckBox("Only convert source codec")
        sl.addWidget(self._source_codec_filter_check)

        self._source_codec_combo = QComboBox()
        self._source_codec_combo.setEnabled(False)
        sl.addWidget(self._source_codec_combo)

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
        self._start_btn.clicked.connect(self._on_start)
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._crf_slider.valueChanged.connect(self._on_crf_changed)
        self._codec_combo.currentIndexChanged.connect(self._on_output_codec_changed)
        self._preset_combo.currentIndexChanged.connect(self._on_settings_changed)
        self._hw_combo.currentIndexChanged.connect(self._on_settings_changed)
        self._source_codec_filter_check.toggled.connect(
            self._on_source_codec_filter_toggled
        )
        self._source_codec_combo.currentIndexChanged.connect(self._on_settings_changed)
        self._output_input.textChanged.connect(self._on_settings_changed)
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
                "convert.source_codec_filter_enabled", False
            )
            self._source_codec_filter_check.setChecked(source_filter_enabled)
        finally:
            self._loading_settings = False

        self._refresh_source_codec_combo()
        self._update_source_filter_controls()

    def _save_settings(self) -> None:
        """Save current settings to config service."""
        if self._loading_settings:
            return

        codec = self._get_selected_output_codec()
        hardware_encoder = self._hw_combo.currentData()
        source_codec = self._get_selected_source_codec()

        self._config_service.set("convert.codec", codec)
        self._config_service.set("convert.crf", self._crf_slider.value())
        self._config_service.set("convert.preset", self._preset_combo.currentText())
        self._config_service.set(
            "convert.use_hardware_accel", hardware_encoder is not None
        )
        self._config_service.set("convert.hardware_encoder", hardware_encoder or "")
        self._config_service.set(
            "convert.source_codec_filter_enabled",
            self._source_codec_filter_check.isChecked(),
        )
        self._config_service.set("convert.source_codec_filter", source_codec or "")
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
        preferred_hardware = self._hw_combo.currentData()
        self._refresh_hardware_options(
            preferred_name=preferred_hardware, prefer_none=preferred_hardware is None
        )
        self._update_source_filter_controls()
        self._on_settings_changed()

    def _on_source_codec_filter_toggled(self, checked: bool) -> None:
        """Enable or disable the source codec selector."""
        self._update_source_filter_controls()
        self._on_settings_changed()

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
        """Enable/disable start button based on file count."""
        self._start_btn.setEnabled(self._file_list.count() > 0)
        self._refresh_source_codec_scan()
        self._update_preview()

    def _on_start(self) -> None:
        """Start conversion."""
        files = self._file_list.get_file_paths()
        if not files:
            return

        files_to_convert = files
        selected_source_codec = None
        if self._is_source_codec_filter_active():
            if self._codec_probe_worker is not None:
                QMessageBox.information(
                    self,
                    "Scanning Codecs",
                    "Please wait for codec detection to finish before starting a filtered conversion.",
                )
                return

            selected_source_codec = self._get_selected_source_codec()
            if not selected_source_codec:
                QMessageBox.information(
                    self,
                    "No Source Codec Selected",
                    "Choose a source codec to filter before starting the conversion.",
                )
                return

            files_to_convert = [
                path for path in files if self._file_codecs.get(path) == selected_source_codec
            ]
            skipped_count = len(files) - len(files_to_convert)
            if not files_to_convert:
                QMessageBox.information(
                    self,
                    "No Matching Files",
                    f'No files match the selected source codec "{self._format_source_codec_label(selected_source_codec)}".',
                )
                return
            if skipped_count > 0:
                QMessageBox.information(
                    self,
                    "Skipping Non-Matching Files",
                    f"Skipping {skipped_count} file(s) that do not match {self._format_source_codec_label(selected_source_codec)}.",
                )

        config = self._build_config()
        output_paths = self._build_output_paths(
            files_to_convert, config.output_dir
        )

        # Create manager
        self._conversion_manager = ConversionManager()
        self._conversion_manager.set_config(config)

        # Connect manager signals
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
        for job in jobs:
            if job.id is not None:
                self._pending_job_widgets[job.id] = Path(job.input_path).name

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
        for i in range(self._jobs_list.count()):
            item = self._jobs_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == job_id:
                name = item.text().split(" — ")[0]
                if success:
                    self._done_count += 1
                    item.setText(f"{name} — Complete")
                else:
                    self._failed_count += 1
                    status = "Cancelled" if "Cancelled" in error else "Failed"
                    item.setText(f"{name} — {status}")
                break

    def _on_queue_progress(self, completed: int, total: int, in_progress: int) -> None:
        """Update overall progress bar."""
        self._overall_progress.setMaximum(total if total > 0 else 1)
        self._overall_progress.setValue(completed)

    def _on_all_completed(self) -> None:
        """Reset UI after all conversions finish."""
        self._file_list.set_enabled(True)
        self._start_btn.setEnabled(self._file_list.count() > 0)
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

            self._conversion_manager.reset_counts()

        self._done_count = 0
        self._failed_count = 0
        if self._jobs_list.count() == 0:
            self._jobs_list.setVisible(False)

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

    def _set_selected_output_codec(self, codec: str) -> None:
        """Set the selected output codec."""
        normalized = self._normalize_output_codec(codec)
        index = self._codec_combo.findData(normalized)
        self._codec_combo.setCurrentIndex(index if index >= 0 else 0)

    def _get_selected_source_codec(self) -> Optional[str]:
        """Get the selected source codec filter."""
        return self._source_codec_combo.currentData()

    def _format_source_codec_label(self, codec: str) -> str:
        """Get a user-facing source codec label."""
        return SOURCE_CODEC_DISPLAY_NAMES.get(codec, codec.upper())

    def _format_hardware_label(self, encoder: HardwareEncoder) -> str:
        """Get a compact user-facing hardware encoder label."""
        label_map = {
            "nvenc": "NVENC",
            "videotoolbox": "VideoToolbox",
            "amf": "AMD AMF",
            "qsv": "Intel Quick Sync",
        }
        return label_map.get(encoder.name, encoder.display_name)

    def _is_source_codec_filter_supported(self) -> bool:
        """Check whether source filtering is supported for the current target."""
        return self._get_selected_output_codec() in TARGET_CODECS_WITH_SOURCE_FILTER

    def _is_source_codec_filter_active(self) -> bool:
        """Check whether source filtering should be applied."""
        return (
            self._is_source_codec_filter_supported()
            and self._source_codec_filter_check.isChecked()
        )

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

    def _refresh_source_codec_scan(self) -> None:
        """Probe the current file list and extract source codec options."""
        self._cancel_source_codec_scan()

        current_paths = self._file_list.get_file_paths()
        self._file_codecs = {
            path: codec for path, codec in self._file_codecs.items() if path in current_paths
        }

        if not current_paths:
            self._refresh_source_codec_combo()
            self._update_source_filter_controls()
            return

        self._codec_probe_request_id += 1
        request_id = self._codec_probe_request_id
        self._set_source_codec_placeholder("Scanning file codecs...")
        self._update_source_filter_controls()

        worker = FFprobeWorker(
            current_paths,
            trash_zero_byte_files=False,
            parent=self,
        )
        self._codec_probe_worker = worker
        worker.completed.connect(
            lambda results, rid=request_id, active_worker=worker: self._on_source_codec_scan_completed(
                rid, active_worker, results
            )
        )
        worker.error.connect(
            lambda file_path, error, rid=request_id: self._on_source_codec_scan_error(
                rid, file_path, error
            )
        )
        worker.start()

    def _cancel_source_codec_scan(self) -> None:
        """Cancel any in-progress source codec probe."""
        if self._codec_probe_worker is not None:
            self._codec_probe_worker.cancel()
            self._codec_probe_worker.deleteLater()
            self._codec_probe_worker = None

    def _set_source_codec_placeholder(self, text: str) -> None:
        """Show a disabled placeholder entry in the source codec combo."""
        self._source_codec_combo.blockSignals(True)
        self._source_codec_combo.clear()
        self._source_codec_combo.addItem(text, None)
        self._source_codec_combo.setCurrentIndex(0)
        self._source_codec_combo.blockSignals(False)

    def _refresh_source_codec_combo(self) -> None:
        """Refresh the source codec combo from the latest probe results."""
        preferred_codec = self._normalize_source_codec(
            self._config_service.get("convert.source_codec_filter", "")
        )
        unique_codecs = sorted(set(self._file_codecs.values()))

        self._source_codec_combo.blockSignals(True)
        self._source_codec_combo.clear()
        for codec in unique_codecs:
            self._source_codec_combo.addItem(
                self._format_source_codec_label(codec), codec
            )

        if unique_codecs:
            index = self._source_codec_combo.findData(preferred_codec)
            self._source_codec_combo.setCurrentIndex(index if index >= 0 else 0)
        self._source_codec_combo.blockSignals(False)

    def _update_source_filter_controls(self) -> None:
        """Update enabled state for source filtering controls."""
        has_source_codecs = self._source_codec_combo.count() > 0 and (
            self._source_codec_combo.itemData(0) is not None
        )
        filter_supported = self._is_source_codec_filter_supported()
        can_enable_filter = filter_supported and has_source_codecs

        self._source_codec_filter_check.setEnabled(can_enable_filter)
        self._source_codec_combo.setEnabled(
            can_enable_filter and self._source_codec_filter_check.isChecked()
        )

    def _on_source_codec_scan_completed(
        self, request_id: int, worker: FFprobeWorker, results: List[object]
    ) -> None:
        """Handle completion of source codec probing."""
        worker.deleteLater()
        if request_id != self._codec_probe_request_id:
            return

        if self._codec_probe_worker is worker:
            self._codec_probe_worker = None

        current_paths = set(self._file_list.get_file_paths())
        self._file_codecs = {}
        for metadata in results:
            file_path = getattr(metadata, "file_path", None)
            codec = getattr(metadata, "codec", "")
            if file_path and file_path in current_paths and codec:
                self._file_codecs[file_path] = self._normalize_source_codec(codec)

        self._refresh_source_codec_combo()
        self._update_source_filter_controls()

    def _on_source_codec_scan_error(
        self, request_id: int, file_path: str, error: str
    ) -> None:
        """Log source codec scan failures without interrupting the UI."""
        if request_id != self._codec_probe_request_id:
            return
        logger.warning("Codec probe failed for %s: %s", file_path, error)

    def _build_config(self) -> ConversionConfig:
        """Build a ConversionConfig from the current UI state."""
        codec = self._get_selected_output_codec()
        hw_encoder = self._hw_combo.currentData()
        use_hw = hw_encoder is not None

        return ConversionConfig(
            output_codec=codec,
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
                build_conversion_output_name(input_path)
            )

        self._preview_tree.update_preview(preview)

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the page."""
        self._file_list.set_enabled(enabled)
        self._codec_combo.setEnabled(enabled)
        self._crf_slider.setEnabled(enabled)
        self._preset_combo.setEnabled(enabled)
        if enabled:
            self._hw_combo.setEnabled(self._hw_combo.count() > 1)
            self._update_source_filter_controls()
        else:
            self._hw_combo.setEnabled(False)
            self._source_codec_filter_check.setEnabled(False)
            self._source_codec_combo.setEnabled(False)
        self._output_input.setEnabled(enabled)
        self._output_browse_btn.setEnabled(enabled)
