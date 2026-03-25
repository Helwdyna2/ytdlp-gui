"""ConvertPage — video conversion tool page using SplitLayout."""

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
    QListWidget,
    QListWidgetItem,
    QComboBox,
    QSlider,
    QCheckBox,
    QProgressBar,
    QMessageBox,
    QFrame,
    QScrollArea,
    QSizePolicy,
)

from ...core.conversion_manager import ConversionManager
from ...core.folder_scan_worker import FolderScanWorker
from ...data.models import ConversionConfig, ConversionJob, ConversionStatus
from ...services.config_service import ConfigService
from ...utils.constants import (
    DEFAULT_CRF,
    MIN_CRF,
    MAX_CRF,
    DEFAULT_PRESET,
    CONVERSION_PRESETS,
    OUTPUT_CODECS,
    VIDEO_FILE_FILTER,
)
from ...utils.dialog_utils import get_dialog_start_dir, update_dialog_last_dir
from ...utils.hardware_accel import get_cached_hardware_encoders, HardwareEncoder
from ..theme.style_utils import set_status_color
from ..components.page_header import PageHeader
from ..components.split_layout import SplitLayout

logger = logging.getLogger(__name__)


class FileListWidget(QWidget):
    """Widget for managing the list of files to convert."""

    files_changed = pyqtSignal()  # Emitted when files are added/removed

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scan_worker: Optional[FolderScanWorker] = None
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
        self._remove_btn.setObjectName("btnDanger")
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
        self._add_paths(video_files)

        # Re-enable buttons
        self._add_files_btn.setEnabled(True)
        self._add_folder_btn.setEnabled(True)
        self._add_folder_btn.setText("Add Folder")

        # Clean up worker
        if self._scan_worker:
            self._scan_worker.deleteLater()
            self._scan_worker = None

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

    def _add_paths(self, paths: List[str]) -> None:
        """Add file paths to the list, skipping duplicates."""
        existing = set(self.get_file_paths())
        for path in paths:
            if path not in existing:
                item = QListWidgetItem(Path(path).name)
                item.setData(Qt.ItemDataRole.UserRole, path)
                item.setToolTip(path)
                self._list_widget.addItem(item)
        self.files_changed.emit()

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
                paths.append(item.data(Qt.ItemDataRole.UserRole))
        return paths

    def get_selected_file_path(self) -> Optional[str]:
        """Get the first selected file path, or None if no selection."""
        items = self._list_widget.selectedItems()
        if items:
            return items[0].data(Qt.ItemDataRole.UserRole)
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
        self._pending_job_widgets: Dict[int, str] = {}  # job_id -> filename
        self._done_count: int = 0
        self._failed_count: int = 0
        self._config_service = ConfigService()
        self._hardware_encoders: List[HardwareEncoder] = []

        self._setup_ui()
        self._connect_signals()
        self._load_settings()
        self._detect_hardware()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Build the full page layout."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # 1. Page header
        header = PageHeader(
            title="Convert",
            description="Transcode video files to different formats.",
        )
        root.addWidget(header)

        # 2. Split layout: file list left, settings right
        split = SplitLayout(right_width=320)

        # --- LEFT panel: toolbar + file list ---
        left_layout = QVBoxLayout(split.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        self._file_list = FileListWidget()
        left_layout.addWidget(self._file_list)

        # --- RIGHT panel: settings ---
        right_layout = QVBoxLayout(split.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # Output Format
        right_layout.addWidget(QLabel("Output Format"))
        self._codec_combo = QComboBox()
        self._codec_combo.addItems([
            "mp4 / H.264",
            "mp4 / H.265 (HEVC)",
            "webm / VP9",
            "mp3",
            "aac",
            "flac",
        ])
        right_layout.addWidget(self._codec_combo)

        # Quality
        right_layout.addWidget(QLabel("Quality"))
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
        right_layout.addLayout(quality_row)

        # Preset
        right_layout.addWidget(QLabel("Preset"))
        self._preset_combo = QComboBox()
        self._preset_combo.addItems(CONVERSION_PRESETS)
        self._preset_combo.setCurrentText(DEFAULT_PRESET)
        right_layout.addWidget(self._preset_combo)

        # Hardware Acceleration
        right_layout.addWidget(QLabel("Hardware Acceleration"))
        self._hw_combo = QComboBox()
        self._hw_combo.addItems(["None", "NVENC", "VideoToolbox", "VAAPI"])
        right_layout.addWidget(self._hw_combo)

        # Output Folder
        right_layout.addWidget(QLabel("Output Folder"))
        output_row = QHBoxLayout()
        self._output_input = QLineEdit()
        self._output_input.setPlaceholderText("Same as input (adds _converted suffix)")
        self._output_browse_btn = QPushButton("Browse")
        self._output_browse_btn.setObjectName("btnWire")
        self._output_browse_btn.setProperty("button_role", "secondary")
        output_row.addWidget(self._output_input)
        output_row.addWidget(self._output_browse_btn)
        right_layout.addLayout(output_row)

        right_layout.addStretch()

        root.addWidget(split, stretch=1)

        # 3. Progress section
        jobs_header = QLabel("Jobs")
        jobs_header.setObjectName("dpanelTitle")
        root.addWidget(jobs_header)

        self._jobs_list = QListWidget()
        self._jobs_list.setMaximumHeight(160)
        root.addWidget(self._jobs_list)

        self._overall_progress = QProgressBar()
        root.addWidget(self._overall_progress)

        # 4. Action bar
        action_row = QHBoxLayout()
        action_row.addStretch()

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("btnSecondary")
        self._cancel_btn.setProperty("button_role", "secondary")
        self._cancel_btn.setVisible(False)

        self._start_btn = QPushButton("Start Convert")
        self._start_btn.setObjectName("btnPrimary")
        self._start_btn.setProperty("button_role", "primary")
        self._start_btn.setEnabled(False)

        action_row.addWidget(self._cancel_btn)
        action_row.addWidget(self._start_btn)
        root.addLayout(action_row)

    def _connect_signals(self) -> None:
        """Wire up all signal connections."""
        self._file_list.files_changed.connect(self._on_files_changed)
        self._start_btn.clicked.connect(self._on_start)
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._crf_slider.valueChanged.connect(self._on_crf_changed)
        self._codec_combo.currentIndexChanged.connect(self._on_settings_changed)
        self._preset_combo.currentIndexChanged.connect(self._on_settings_changed)
        self._hw_combo.currentIndexChanged.connect(self._on_settings_changed)
        self._output_input.textChanged.connect(self._on_settings_changed)
        self._output_browse_btn.clicked.connect(self._on_browse_output)

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _load_settings(self) -> None:
        """Load settings from config service."""
        codec = self._config_service.get("convert.codec", "libx264")
        # Map libx264/libx265 -> combo index (0 = H.264, 1 = H.265)
        self._codec_combo.setCurrentIndex(1 if codec == "libx265" else 0)

        crf = self._config_service.get("convert.crf", DEFAULT_CRF)
        self._crf_slider.setValue(crf)
        self._crf_label.setText(str(crf))

        preset = self._config_service.get("convert.preset", DEFAULT_PRESET)
        idx = self._preset_combo.findText(preset)
        if idx >= 0:
            self._preset_combo.setCurrentIndex(idx)

        output_dir = self._config_service.get("convert.output_dir", "")
        self._output_input.setText(output_dir)

    def _save_settings(self) -> None:
        """Save current settings to config service."""
        idx = self._codec_combo.currentIndex()
        codec = "libx265" if idx == 1 else "libx264"
        self._config_service.set("convert.codec", codec)
        self._config_service.set("convert.crf", self._crf_slider.value())
        self._config_service.set("convert.preset", self._preset_combo.currentText())
        self._config_service.set("convert.output_dir", self._output_input.text())

    def _detect_hardware(self) -> None:
        """Detect available hardware encoders and configure combo."""
        try:
            self._hardware_encoders = get_cached_hardware_encoders()
            if self._hardware_encoders:
                # Pre-select first available encoder in the combo
                first = self._hardware_encoders[0]
                name_map = {
                    "nvenc": "NVENC",
                    "videotoolbox": "VideoToolbox",
                    "vaapi": "VAAPI",
                }
                display = name_map.get(first.name.lower(), first.display_name)
                idx = self._hw_combo.findText(display)
                if idx >= 0:
                    self._hw_combo.setCurrentIndex(idx)
        except Exception as e:
            logger.warning("Hardware detection failed: %s", e)

    def _on_crf_changed(self, value: int) -> None:
        """Update CRF label and save."""
        self._crf_label.setText(str(value))
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

    def _on_start(self) -> None:
        """Start conversion."""
        files = self._file_list.get_file_paths()
        if not files:
            return

        config = self._build_config()

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
        self._overall_progress.setMaximum(len(files))
        self._overall_progress.setValue(0)

        self.start_requested.emit()

        # Start async job creation (non-blocking)
        self._conversion_manager.add_files_async(files, config.output_dir)

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

    def _build_config(self) -> ConversionConfig:
        """Build a ConversionConfig from the current UI state."""
        idx = self._codec_combo.currentIndex()
        # Indices: 0=H.264, 1=H.265, 2=VP9/webm, 3=mp3, 4=aac, 5=flac
        codec_map = {
            0: "h264",
            1: "hevc",
            2: "vp9",
            3: "mp3",
            4: "aac",
            5: "flac",
        }
        codec = codec_map.get(idx, "h264")

        hw_text = self._hw_combo.currentText()
        hw_name_map = {
            "NVENC": "nvenc",
            "VideoToolbox": "videotoolbox",
            "VAAPI": "vaapi",
        }
        hw_encoder = hw_name_map.get(hw_text) if hw_text != "None" else None
        use_hw = hw_encoder is not None

        return ConversionConfig(
            output_codec=codec,
            crf_value=self._crf_slider.value(),
            preset=self._preset_combo.currentText(),
            use_hardware_accel=use_hw,
            hardware_encoder=hw_encoder,
            output_dir=self._output_input.text() or None,
        )

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the page."""
        self._file_list.set_enabled(enabled)
        self._codec_combo.setEnabled(enabled)
        self._crf_slider.setEnabled(enabled)
        self._preset_combo.setEnabled(enabled)
        self._hw_combo.setEnabled(enabled)
        self._output_input.setEnabled(enabled)
        self._output_browse_btn.setEnabled(enabled)
