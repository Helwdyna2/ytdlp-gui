"""MetadataPage — inspect media file properties using SplitLayout."""

import csv
import json
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
    QProgressBar,
    QMessageBox,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QHeaderView,
    QTextEdit,
)

from ...core.ffprobe_worker import FFprobeWorker
from ...core.folder_scan_worker import FolderScanWorker
from ...data.models import VideoMetadata
from ...services.config_service import ConfigService
from ...utils.dialog_utils import get_dialog_start_dir, update_dialog_last_dir
from ...utils.formatters import format_size
from ..components.page_header import PageHeader
from ..components.split_layout import SplitLayout
from ..widgets.metadata_compare_dialog import MetadataCompareDialog

logger = logging.getLogger(__name__)


class MetadataPage(QWidget):
    """
    Metadata page — inspect media file properties.

    Uses SplitLayout: file list on the left, metadata detail tabs on the right.
    Preserves all business logic from MetadataViewerTabWidget.
    """

    scan_started = pyqtSignal()
    scan_completed = pyqtSignal(int)  # file count

    def __init__(self, ffprobe_worker=None, parent=None):
        super().__init__(parent)
        self._metadata_list: List[VideoMetadata] = []
        self._metadata_map: Dict[str, VideoMetadata] = {}
        self._raw_metadata_map: Dict[str, dict] = {}
        self._ffprobe_worker: Optional[FFprobeWorker] = ffprobe_worker
        self._folder_scan_worker: Optional[FolderScanWorker] = None
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
                title="Metadata",
                description="Inspect media file properties.",
            )
        )

        # 2. Source bar (horizontal): Folder label + path input + Browse + Scan
        source_row = QHBoxLayout()
        source_row.addWidget(QLabel("Folder:"))

        self._folder_input = QLineEdit()
        self._folder_input.setPlaceholderText("Select a folder to scan…")
        source_row.addWidget(self._folder_input, stretch=1)

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

        # Scan progress row (hidden while idle)
        progress_row = QHBoxLayout()
        self._scan_progress = QProgressBar()
        self._scan_progress.setVisible(False)
        self._scan_status = QLabel("")
        self._scan_status.setVisible(False)
        self._scan_cancel_btn = QPushButton("Cancel")
        self._scan_cancel_btn.setObjectName("btnDestructive")
        self._scan_cancel_btn.setProperty("button_role", "destructive")
        self._scan_cancel_btn.setVisible(False)
        progress_row.addWidget(self._scan_progress)
        progress_row.addWidget(self._scan_status)
        progress_row.addWidget(self._scan_cancel_btn)
        root.addLayout(progress_row)

        # 3. SplitLayout — file list left, detail tabs right
        split = SplitLayout(right_width=400, gap=20)

        # --- LEFT panel: file count label + list ---
        left_layout = QVBoxLayout(split.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        self._file_count_label = QLabel("No files scanned")
        left_layout.addWidget(self._file_count_label)

        self._file_list = QListWidget()
        self._file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        left_layout.addWidget(self._file_list)

        # --- RIGHT panel: tab widget ---
        right_layout = QVBoxLayout(split.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._tabs = QTabWidget()

        # Tab 1: Basic Info (tree widget)
        basic_widget = QWidget()
        basic_layout = QVBoxLayout(basic_widget)
        basic_layout.setContentsMargins(0, 0, 0, 0)

        self._info_tree = QTreeWidget()
        self._info_tree.setHeaderLabels(["Property", "Value"])
        self._info_tree.setColumnCount(2)
        header = self._info_tree.header()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._info_tree.setRootIsDecorated(True)
        basic_layout.addWidget(self._info_tree)
        self._tabs.addTab(basic_widget, "Basic Info")

        # Tab 2: Raw FFprobe
        raw_widget = QWidget()
        raw_layout = QVBoxLayout(raw_widget)
        raw_layout.setContentsMargins(0, 0, 0, 0)

        self._raw_text = QTextEdit()
        self._raw_text.setReadOnly(True)
        self._raw_text.setObjectName("monoText")
        raw_layout.addWidget(self._raw_text)
        self._tabs.addTab(raw_widget, "Raw FFprobe")

        right_layout.addWidget(self._tabs)

        root.addWidget(split, stretch=1)

        # 4. Action bar
        action_row = QHBoxLayout()
        action_row.addStretch()

        self._compare_btn = QPushButton("Compare")
        self._compare_btn.setObjectName("btnSecondary")
        self._compare_btn.setProperty("button_role", "secondary")
        self._compare_btn.setEnabled(False)
        self._compare_btn.setToolTip("Compare 2–4 selected files side-by-side")

        self._export_csv_btn = QPushButton("Export to CSV")
        self._export_csv_btn.setObjectName("btnSecondary")
        self._export_csv_btn.setProperty("button_role", "secondary")
        self._export_csv_btn.setEnabled(False)

        action_row.addWidget(self._compare_btn)
        action_row.addWidget(self._export_csv_btn)
        root.addLayout(action_row)

    def _connect_signals(self) -> None:
        """Wire up all signal connections."""
        self._folder_input.textChanged.connect(self._on_source_changed)
        self._browse_btn.clicked.connect(self._on_browse)
        self._scan_btn.clicked.connect(self._on_scan)
        self._scan_cancel_btn.clicked.connect(self._on_cancel_scan)

        self._file_list.itemSelectionChanged.connect(self._on_selection_changed)
        self._file_list.itemSelectionChanged.connect(self._update_compare_button_state)

        self._compare_btn.clicked.connect(self._on_compare)
        self._export_csv_btn.clicked.connect(self._on_export_csv)

    def _load_settings(self) -> None:
        """Load saved settings from config."""
        source = self._config.get("metadata_viewer.source_folder", "")
        if source:
            self._folder_input.setText(source)

    def _save_settings(self) -> None:
        """Persist current settings."""
        self._config.set(
            "metadata_viewer.source_folder", self._folder_input.text(), save=False
        )
        self._config.save()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_browse_start_dir(self) -> str:
        return get_dialog_start_dir(
            self._folder_input.text(), "metadata_viewer.source_folder"
        )

    def _add_tree_property(
        self, parent: QTreeWidgetItem, name: str, value: str
    ) -> None:
        """Add a property row to the info tree."""
        QTreeWidgetItem(parent, [name, value])

    # ------------------------------------------------------------------
    # Event handlers — source / browse / scan
    # ------------------------------------------------------------------

    def _on_source_changed(self, text: str) -> None:
        """Enable Scan button only when path is a valid directory."""
        self._scan_btn.setEnabled(bool(text and Path(text).is_dir()))

    def _on_browse(self) -> None:
        """Open folder picker."""
        start_dir = self._get_browse_start_dir()
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder", start_dir
        )
        if folder:
            update_dialog_last_dir(folder)
            self._folder_input.setText(folder)
            self._save_settings()

    def _on_scan(self) -> None:
        """Start scanning the source folder."""
        source_path = self._folder_input.text()
        if not source_path or not Path(source_path).is_dir():
            QMessageBox.warning(self, "Invalid Folder", "Please select a valid folder.")
            return

        # Reset UI
        self._scan_progress.setVisible(True)
        self._scan_progress.setMaximum(0)
        self._scan_progress.setValue(0)
        self._scan_status.setVisible(True)
        self._scan_status.setText("Finding video files…")
        self._scan_btn.setEnabled(False)
        self._browse_btn.setEnabled(False)
        self._folder_input.setEnabled(False)

        # Clear previous data
        self._metadata_list.clear()
        self._metadata_map.clear()
        self._raw_metadata_map.clear()
        self._info_tree.clear()
        self._raw_text.clear()
        self._file_list.clear()

        self.scan_started.emit()

        # Start background folder scan
        self._folder_scan_worker = FolderScanWorker(source_path, recursive=True)
        self._folder_scan_worker.progress.connect(self._on_folder_scan_progress)
        self._folder_scan_worker.completed.connect(self._on_folder_scan_completed)
        self._folder_scan_worker.error.connect(self._on_folder_scan_error)
        self._folder_scan_worker.files_deleted.connect(self._on_files_deleted)
        self._folder_scan_worker.start()

    def _on_folder_scan_progress(self, count: int, message: str) -> None:
        self._scan_status.setText(message)

    def _on_folder_scan_completed(self, video_files: List[str]) -> None:
        """Handle folder scan completion — start FFprobe worker."""
        if self._folder_scan_worker:
            self._folder_scan_worker.deleteLater()
            self._folder_scan_worker = None

        if not video_files:
            QMessageBox.information(
                self, "No Videos Found", "No video files found in the selected folder."
            )
            self._reset_scan_ui()
            return

        source_path = self._folder_input.text()
        self._ffprobe_worker = FFprobeWorker(video_files, base_folder=source_path)
        self._ffprobe_worker.progress.connect(self._on_scan_progress)
        self._ffprobe_worker.metadata_ready.connect(self._on_metadata_ready)
        self._ffprobe_worker.raw_metadata_ready.connect(self._on_raw_metadata_ready)
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
        self._reset_scan_ui()

    def _on_cancel_scan(self) -> None:
        if self._ffprobe_worker:
            self._ffprobe_worker.cancel()

    def _on_scan_progress(self, current: int, total: int, file_path: str) -> None:
        self._scan_progress.setValue(current)
        self._scan_status.setText(f"Scanning: {Path(file_path).name}")

    def _on_metadata_ready(self, metadata: VideoMetadata) -> None:
        self._metadata_list.append(metadata)
        self._metadata_map[metadata.file_path] = metadata

    def _on_raw_metadata_ready(self, file_path: str, raw_data: dict) -> None:
        self._raw_metadata_map[file_path] = raw_data

    def _on_scan_completed(self, results: List[VideoMetadata]) -> None:
        """Handle FFprobe scan completion."""
        self._reset_scan_ui()

        self._metadata_list = sorted(
            results, key=lambda m: Path(m.file_path).name.lower()
        )

        # Populate file list
        self._file_list.clear()
        for metadata in self._metadata_list:
            name = Path(metadata.file_path).name
            size_str = format_size(metadata.file_size)
            item = QListWidgetItem(f"{name} ({size_str})")
            item.setData(Qt.ItemDataRole.UserRole, metadata.file_path)
            self._file_list.addItem(item)

        self._file_count_label.setText(f"{len(self._metadata_list)} file(s) found")

        has_files = len(self._metadata_list) > 0
        self._export_csv_btn.setEnabled(has_files)

        if self._metadata_list:
            self._file_list.setCurrentRow(0)

        self._save_settings()
        self.scan_completed.emit(len(self._metadata_list))
        logger.info("Metadata scan completed: %d files", len(self._metadata_list))

    def _reset_scan_ui(self) -> None:
        """Re-enable controls after scan completes or errors out."""
        self._scan_progress.setVisible(False)
        self._scan_status.setVisible(False)
        self._scan_cancel_btn.setVisible(False)
        self._scan_btn.setEnabled(
            bool(self._folder_input.text() and Path(self._folder_input.text()).is_dir())
        )
        self._browse_btn.setEnabled(True)
        self._folder_input.setEnabled(True)

    # ------------------------------------------------------------------
    # Event handlers — file selection / metadata display
    # ------------------------------------------------------------------

    def _on_selection_changed(self) -> None:
        """Display metadata for the first selected file."""
        items = self._file_list.selectedItems()
        if not items:
            return
        file_path = items[0].data(Qt.ItemDataRole.UserRole)
        metadata = self._metadata_map.get(file_path)
        raw_data = self._raw_metadata_map.get(file_path)
        if metadata:
            self._display_metadata(metadata, raw_data)

    def _display_metadata(
        self, metadata: VideoMetadata, raw_data: Optional[dict]
    ) -> None:
        """Populate the Basic Info tree and Raw FFprobe text area."""
        self._info_tree.clear()

        # File information
        file_section = QTreeWidgetItem(["FILE INFORMATION"])
        self._info_tree.addTopLevelItem(file_section)
        file_path = Path(metadata.file_path)
        self._add_tree_property(file_section, "Filename", file_path.name)
        self._add_tree_property(file_section, "Directory", str(file_path.parent))
        self._add_tree_property(file_section, "File Size", format_size(metadata.file_size))
        self._add_tree_property(file_section, "Extension", file_path.suffix.upper())

        # Video information
        video_section = QTreeWidgetItem(["VIDEO INFORMATION"])
        self._info_tree.addTopLevelItem(video_section)
        self._add_tree_property(
            video_section, "Resolution", f"{metadata.width}\u00d7{metadata.height}"
        )
        self._add_tree_property(
            video_section, "Resolution Category", metadata.resolution_category
        )
        self._add_tree_property(
            video_section, "Orientation", metadata.orientation.title()
        )
        self._add_tree_property(
            video_section, "Frame Rate", f"{metadata.fps:.3f} fps"
        )
        self._add_tree_property(
            video_section, "Frame Rate Category", metadata.fps_category
        )
        self._add_tree_property(video_section, "Video Codec", metadata.codec.upper())
        self._add_tree_property(video_section, "Bitrate", metadata.bitrate_label)
        if metadata.bitrate > 0:
            self._add_tree_property(
                video_section,
                "Bitrate (kbps)",
                f"{metadata.bitrate / 1000:,.0f}",
            )

        # Duration
        duration_section = QTreeWidgetItem(["DURATION"])
        self._info_tree.addTopLevelItem(duration_section)
        hours = int(metadata.duration // 3600)
        minutes = int((metadata.duration % 3600) // 60)
        seconds = metadata.duration % 60
        if hours > 0:
            duration_str = f"{hours}h {minutes}m {seconds:.2f}s"
        elif minutes > 0:
            duration_str = f"{minutes}m {seconds:.2f}s"
        else:
            duration_str = f"{seconds:.2f}s"
        self._add_tree_property(duration_section, "Duration", duration_str)
        self._add_tree_property(
            duration_section, "Total Seconds", f"{metadata.duration:.3f}"
        )
        if metadata.fps > 0:
            total_frames = int(metadata.duration * metadata.fps)
            self._add_tree_property(
                duration_section, "Estimated Frames", f"{total_frames:,}"
            )

        # Audio streams (from raw data)
        if raw_data:
            audio_streams = [
                s
                for s in raw_data.get("streams", [])
                if s.get("codec_type") == "audio"
            ]
            if audio_streams:
                label = (
                    f"AUDIO ({len(audio_streams)} stream"
                    + ("s" if len(audio_streams) > 1 else "")
                    + ")"
                )
                audio_section = QTreeWidgetItem([label])
                self._info_tree.addTopLevelItem(audio_section)
                for i, stream in enumerate(audio_streams):
                    stream_item = QTreeWidgetItem([f"Stream {i + 1}"])
                    audio_section.addChild(stream_item)
                    codec = stream.get("codec_name", "unknown")
                    self._add_tree_property(stream_item, "Codec", codec.upper())
                    sample_rate = stream.get("sample_rate", "")
                    if sample_rate:
                        self._add_tree_property(
                            stream_item, "Sample Rate", f"{int(sample_rate):,} Hz"
                        )
                    channels = stream.get("channels", 0)
                    channel_layout = stream.get("channel_layout", "")
                    if channels:
                        channel_str = (
                            f"{channels} ({channel_layout})"
                            if channel_layout
                            else str(channels)
                        )
                        self._add_tree_property(stream_item, "Channels", channel_str)
                    bit_rate = stream.get("bit_rate", "")
                    if bit_rate:
                        self._add_tree_property(
                            stream_item, "Bitrate", f"{int(bit_rate) / 1000:.0f} kbps"
                        )

            # Container / format info
            format_info = raw_data.get("format", {})
            if format_info:
                format_section = QTreeWidgetItem(["CONTAINER FORMAT"])
                self._info_tree.addTopLevelItem(format_section)
                format_name = format_info.get("format_name", "")
                if format_name:
                    self._add_tree_property(format_section, "Format", format_name)
                format_long = format_info.get("format_long_name", "")
                if format_long:
                    self._add_tree_property(format_section, "Format Name", format_long)
                nb_streams = format_info.get("nb_streams", 0)
                if nb_streams:
                    self._add_tree_property(
                        format_section, "Total Streams", str(nb_streams)
                    )
                tags = format_info.get("tags", {})
                if tags:
                    tags_section = QTreeWidgetItem(["METADATA TAGS"])
                    self._info_tree.addTopLevelItem(tags_section)
                    for key, value in sorted(tags.items()):
                        self._add_tree_property(tags_section, key, str(value))

        self._info_tree.expandAll()

        # Raw FFprobe tab
        if raw_data:
            self._raw_text.setPlainText(json.dumps(raw_data, indent=2))
        else:
            self._raw_text.setPlainText(
                "Raw metadata not available.\n"
                "Re-scan the folder to load detailed information."
            )

    # ------------------------------------------------------------------
    # Compare / export
    # ------------------------------------------------------------------

    def _update_compare_button_state(self) -> None:
        """Enable Compare only when 2–4 files are selected."""
        count = len(self._file_list.selectedItems())
        self._compare_btn.setEnabled(2 <= count <= 4 and bool(self._metadata_list))

    def _on_compare(self) -> None:
        """Open comparison dialog for selected files."""
        paths = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self._file_list.selectedItems()
        ]
        if not (2 <= len(paths) <= 4):
            return
        metadata_list = [
            self._metadata_map[p] for p in paths if p in self._metadata_map
        ]
        if len(metadata_list) < 2:
            return
        dialog = MetadataCompareDialog(
            metadata_list, self._raw_metadata_map, parent=self
        )
        dialog.show()

    def _on_export_csv(self) -> None:
        """Export metadata to CSV file."""
        if not self._metadata_list:
            return

        selected = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self._file_list.selectedItems()
        ]
        if not selected:
            selected = [
                self._file_list.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self._file_list.count())
                if self._file_list.item(i) is not None
            ]

        start_dir = get_dialog_start_dir("", "dialogs.last_dir")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export to CSV",
            str(Path(start_dir) / "video_metadata.csv"),
            "CSV Files (*.csv)",
        )
        if not file_path:
            return

        update_dialog_last_dir(file_path)

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Filename",
                        "Directory",
                        "File Size (bytes)",
                        "File Size",
                        "Width",
                        "Height",
                        "Resolution",
                        "Resolution Category",
                        "Orientation",
                        "FPS",
                        "FPS Category",
                        "Codec",
                        "Bitrate (bps)",
                        "Bitrate",
                        "Duration (s)",
                        "Duration",
                    ]
                )
                for path in selected:
                    metadata = self._metadata_map.get(path)
                    if metadata:
                        file_p = Path(metadata.file_path)
                        hours = int(metadata.duration // 3600)
                        minutes = int((metadata.duration % 3600) // 60)
                        seconds = metadata.duration % 60
                        if hours > 0:
                            duration_str = f"{hours}h {minutes}m {seconds:.2f}s"
                        elif minutes > 0:
                            duration_str = f"{minutes}m {seconds:.2f}s"
                        else:
                            duration_str = f"{seconds:.2f}s"
                        writer.writerow(
                            [
                                file_p.name,
                                str(file_p.parent),
                                metadata.file_size,
                                format_size(metadata.file_size),
                                metadata.width,
                                metadata.height,
                                metadata.resolution,
                                metadata.resolution_category,
                                metadata.orientation,
                                f"{metadata.fps:.3f}",
                                metadata.fps_category,
                                metadata.codec,
                                metadata.bitrate,
                                metadata.bitrate_label,
                                f"{metadata.duration:.3f}",
                                duration_str,
                            ]
                        )
            QMessageBox.information(
                self,
                "Export Complete",
                f"Successfully exported {len(selected)} file(s) to CSV.",
            )
            logger.info("Exported metadata to CSV: %s", file_path)
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export CSV: {e}")
            logger.error("Failed to export CSV: %s", e)

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
        """Enable or disable the page."""
        self._folder_input.setEnabled(enabled)
        self._browse_btn.setEnabled(enabled)
        self._scan_btn.setEnabled(
            enabled
            and bool(
                self._folder_input.text()
                and Path(self._folder_input.text()).is_dir()
            )
        )
        self._file_list.setEnabled(enabled)
        self._export_csv_btn.setEnabled(enabled and bool(self._metadata_list))
        count = len(self._file_list.selectedItems())
        self._compare_btn.setEnabled(
            enabled and bool(self._metadata_list) and 2 <= count <= 4
        )
