"""Dialog for comparing metadata of multiple video files side-by-side."""

import logging
from pathlib import Path
from typing import Dict, List

import send2trash

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget,
    QMessageBox,
    QCheckBox,
)

from ...data.models import VideoMetadata
from ...data.database import Database
from ...utils.formatters import format_size
from ...utils.constants import SUPPORTED_VIDEO_EXTENSIONS
from ...utils.platform_utils import (
    quick_look_file,
    open_file_default_app,
    get_platform,
    Platform,
)

logger = logging.getLogger(__name__)


class MetadataCompareDialog(QDialog):
    """
    Dialog for comparing metadata of 2-4 video files side-by-side.

    Features:
    - Side-by-side column layout with one column per file
    - Grouped sections matching the detail view (File, Video, Duration, Audio, Container)
    - Highlighting of differing values across files
    - Scrollable content for many properties
    - Non-modal and resizable
    """

    def __init__(
        self,
        metadata_list: List[VideoMetadata],
        raw_metadata_map: Dict[str, dict],
        parent=None,
    ):
        super().__init__(parent)
        self._metadata_list = metadata_list
        self._raw_metadata_map = raw_metadata_map
        self._db = Database()

        self._setup_ui()
        self._build_comparison_grid()

    def _setup_ui(self) -> None:
        """Build the dialog UI layout."""
        self.setWindowTitle(f"Compare Metadata ({len(self._metadata_list)} files)")
        self.setMinimumSize(750, 450)
        self.resize(900, 600)

        # Make non-modal
        self.setModal(False)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # Scroll area for the comparison grid
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Container widget for the grid
        self._grid_widget = QWidget()
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setSpacing(2)
        self._grid_layout.setContentsMargins(6, 6, 6, 6)

        scroll_area.setWidget(self._grid_widget)
        layout.addWidget(scroll_area, stretch=1)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setObjectName("btnWire")
        close_btn.clicked.connect(self.close)
        close_btn.setMinimumWidth(100)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _build_comparison_grid(self) -> None:
        """Build the comparison grid with all metadata."""
        row = 0
        num_files = len(self._metadata_list)

        # Header row with filenames
        row = self._add_header_row(row)

        # File Information section
        file_props = self._get_file_properties()
        row = self._add_section(row, "FILE INFORMATION", file_props)

        # Video Information section
        video_props = self._get_video_properties()
        row = self._add_section(row, "VIDEO INFORMATION", video_props)

        # Duration section
        duration_props = self._get_duration_properties()
        row = self._add_section(row, "DURATION", duration_props)

        # Audio section (from raw metadata)
        audio_props = self._get_audio_properties()
        if audio_props:
            row = self._add_section(row, "AUDIO", audio_props)

        # Container Format section (from raw metadata)
        container_props = self._get_container_properties()
        if container_props:
            row = self._add_section(row, "CONTAINER FORMAT", container_props)

        # Add stretch at the bottom
        self._grid_layout.setRowStretch(row, 1)

        # Set column stretches - property name column fixed, file columns stretch equally
        self._grid_layout.setColumnStretch(0, 0)
        for col in range(1, num_files + 1):
            self._grid_layout.setColumnStretch(col, 1)

    def _add_header_row(self, row: int) -> int:
        """Add the header row with file names and action buttons."""
        # Empty cell for property column
        header_label = QLabel("Property")
        header_label.setObjectName("boldLabel")
        self._grid_layout.addWidget(header_label, row, 0)

        # File name headers
        for col, metadata in enumerate(self._metadata_list, start=1):
            filename = Path(metadata.file_path).name
            # Truncate long filenames
            display_name = filename if len(filename) <= 30 else filename[:27] + "..."

            label = QLabel(display_name)
            label.setObjectName("boldLabel")
            label.setToolTip(filename)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._grid_layout.addWidget(label, row, col)

        row += 1

        # Action buttons row
        actions_label = QLabel("Actions")
        actions_label.setObjectName("dimLabel")
        self._grid_layout.addWidget(actions_label, row, 0)

        for col, metadata in enumerate(self._metadata_list, start=1):
            # Create horizontal layout for buttons
            button_layout = QHBoxLayout()
            button_layout.setSpacing(4)
            button_layout.setContentsMargins(0, 0, 0, 0)

            # Delete button (always shown)
            delete_btn = QPushButton("\U0001f5d1")
            delete_btn.setObjectName("btnWire")
            delete_btn.setToolTip("Delete file (move to trash)")
            delete_btn.setFixedSize(30, 24)
            delete_btn.clicked.connect(
                lambda checked, path=metadata.file_path: self._on_delete_file(path)
            )
            button_layout.addWidget(delete_btn)

            # Preview button (only for video files)
            file_ext = Path(metadata.file_path).suffix.lower()
            if file_ext in SUPPORTED_VIDEO_EXTENSIONS:
                preview_btn = QPushButton("\u25b6\ufe0f")
                preview_btn.setObjectName("btnWire")
                preview_btn.setToolTip("Preview video")
                preview_btn.setFixedSize(30, 24)
                preview_btn.clicked.connect(
                    lambda checked, path=metadata.file_path: self._on_preview_file(path)
                )
                button_layout.addWidget(preview_btn)

            button_layout.addStretch()

            # Add button container to grid
            button_widget = QWidget()
            button_widget.setLayout(button_layout)
            self._grid_layout.addWidget(
                button_widget, row, col, Qt.AlignmentFlag.AlignCenter
            )

        return row + 1

    def _add_section(self, row: int, title: str, properties: List[tuple]) -> int:
        """
        Add a section with title and properties.

        Args:
            row: Starting row
            title: Section title (e.g., "FILE INFORMATION")
            properties: List of (property_name, [values...]) tuples

        Returns:
            Next available row
        """
        if not properties:
            return row

        num_files = len(self._metadata_list)

        # Section header spanning all columns
        section_label = QLabel(title)
        section_label.setObjectName("boldLabel")
        self._grid_layout.addWidget(section_label, row, 0, 1, num_files + 1)
        row += 1

        # Property rows
        for prop_name, values in properties:
            self._add_property_row(row, prop_name, values)
            row += 1

        # Add spacing after section
        spacer = QWidget()
        spacer.setFixedHeight(6)
        self._grid_layout.addWidget(spacer, row, 0, 1, num_files + 1)
        row += 1

        return row

    def _add_property_row(self, row: int, name: str, values: List[str]) -> None:
        """Add a single property row with values for each file."""
        # Property name
        name_label = QLabel(name)
        name_label.setObjectName("dimLabel")
        self._grid_layout.addWidget(name_label, row, 0)

        # Check if values differ
        differs = self._values_differ(values)

        # Value cells
        for col, value in enumerate(values, start=1):
            value_label = QLabel(str(value))
            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )

            if differs:
                value_label.setObjectName("diffHighlight")

            self._grid_layout.addWidget(value_label, row, col)

    def _values_differ(self, values: List[str]) -> bool:
        """Check if any values in the list differ from each other."""
        if not values:
            return False

        # Normalize values for comparison (strip whitespace, handle empty)
        normalized = [str(v).strip().lower() for v in values]
        return len(set(normalized)) > 1

    def _get_file_properties(self) -> List[tuple]:
        """Get file information properties for all files."""
        properties = []

        # Filename
        filenames = [Path(m.file_path).name for m in self._metadata_list]
        properties.append(("Filename", filenames))

        # Directory
        directories = [str(Path(m.file_path).parent) for m in self._metadata_list]
        properties.append(("Directory", directories))

        # File Size
        sizes = [format_size(m.file_size) for m in self._metadata_list]
        properties.append(("File Size", sizes))

        # Extension
        extensions = [Path(m.file_path).suffix.upper() for m in self._metadata_list]
        properties.append(("Extension", extensions))

        return properties

    def _get_video_properties(self) -> List[tuple]:
        """Get video information properties for all files."""
        properties = []

        # Resolution
        resolutions = [f"{m.width}x{m.height}" for m in self._metadata_list]
        properties.append(("Resolution", resolutions))

        # Resolution Category
        categories = [m.resolution_category for m in self._metadata_list]
        properties.append(("Resolution Category", categories))

        # Orientation
        orientations = [m.orientation.title() for m in self._metadata_list]
        properties.append(("Orientation", orientations))

        # Frame Rate
        fps_values = [f"{m.fps:.3f} fps" for m in self._metadata_list]
        properties.append(("Frame Rate", fps_values))

        # FPS Category
        fps_cats = [m.fps_category for m in self._metadata_list]
        properties.append(("FPS Category", fps_cats))

        # Video Codec
        codecs = [
            m.codec.upper() if m.codec else "Unknown" for m in self._metadata_list
        ]
        properties.append(("Video Codec", codecs))

        # Bitrate
        bitrates = [m.bitrate_label for m in self._metadata_list]
        properties.append(("Bitrate", bitrates))

        return properties

    def _get_duration_properties(self) -> List[tuple]:
        """Get duration properties for all files."""
        properties = []

        # Duration (formatted)
        durations = [self._format_duration(m.duration) for m in self._metadata_list]
        properties.append(("Duration", durations))

        # Total Seconds
        seconds = [f"{m.duration:.3f}" for m in self._metadata_list]
        properties.append(("Total Seconds", seconds))

        # Estimated Frames
        frames = []
        for m in self._metadata_list:
            if m.fps > 0:
                total_frames = int(m.duration * m.fps)
                frames.append(f"{total_frames:,}")
            else:
                frames.append("N/A")
        properties.append(("Estimated Frames", frames))

        return properties

    def _get_audio_properties(self) -> List[tuple]:
        """Get audio properties from raw metadata for all files."""
        properties = []

        # Collect audio info for each file
        audio_codecs = []
        sample_rates = []
        channels_list = []
        audio_bitrates = []

        for metadata in self._metadata_list:
            raw_data = self._raw_metadata_map.get(metadata.file_path, {})
            audio_streams = [
                s for s in raw_data.get("streams", []) if s.get("codec_type") == "audio"
            ]

            if audio_streams:
                # Use first audio stream
                stream = audio_streams[0]

                codec = stream.get("codec_name", "unknown").upper()
                audio_codecs.append(codec)

                sample_rate = stream.get("sample_rate", "")
                if sample_rate:
                    sample_rates.append(f"{int(sample_rate):,} Hz")
                else:
                    sample_rates.append("N/A")

                ch = stream.get("channels", 0)
                ch_layout = stream.get("channel_layout", "")
                if ch:
                    ch_str = f"{ch} ({ch_layout})" if ch_layout else str(ch)
                    channels_list.append(ch_str)
                else:
                    channels_list.append("N/A")

                bit_rate = stream.get("bit_rate", "")
                if bit_rate:
                    kbps = int(bit_rate) / 1000
                    audio_bitrates.append(f"{kbps:.0f} kbps")
                else:
                    audio_bitrates.append("N/A")
            else:
                audio_codecs.append("No Audio")
                sample_rates.append("N/A")
                channels_list.append("N/A")
                audio_bitrates.append("N/A")

        # Only add properties if at least one file has audio
        if any(c != "No Audio" for c in audio_codecs):
            properties.append(("Audio Codec", audio_codecs))
            properties.append(("Sample Rate", sample_rates))
            properties.append(("Channels", channels_list))
            properties.append(("Audio Bitrate", audio_bitrates))

        return properties

    def _get_container_properties(self) -> List[tuple]:
        """Get container format properties from raw metadata for all files."""
        properties = []

        formats = []
        format_names = []
        stream_counts = []

        for metadata in self._metadata_list:
            raw_data = self._raw_metadata_map.get(metadata.file_path, {})
            format_info = raw_data.get("format", {})

            fmt = format_info.get("format_name", "Unknown")
            formats.append(fmt)

            fmt_long = format_info.get("format_long_name", "Unknown")
            format_names.append(fmt_long)

            nb_streams = format_info.get("nb_streams", 0)
            stream_counts.append(str(nb_streams) if nb_streams else "N/A")

        # Only add if we have data
        if any(f != "Unknown" for f in formats):
            properties.append(("Format", formats))
            properties.append(("Format Name", format_names))
            properties.append(("Total Streams", stream_counts))

        return properties

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {secs:.2f}s"
        elif minutes > 0:
            return f"{minutes}m {secs:.2f}s"
        else:
            return f"{secs:.2f}s"

    def _on_delete_file(self, file_path: str) -> None:
        """Handle file deletion with confirmation."""
        filename = Path(file_path).name

        # Create confirmation dialog
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Delete")
        msg_box.setText(f"Delete this file?\n\n{filename}")
        msg_box.setInformativeText("The file will be moved to Trash.")
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)

        # Add checkbox for database cleanup
        cleanup_checkbox = QCheckBox("Also remove from database history")
        cleanup_checkbox.setChecked(True)
        msg_box.setCheckBox(cleanup_checkbox)

        result = msg_box.exec()

        if result != QMessageBox.StandardButton.Yes:
            return

        # Attempt to delete file
        try:
            send2trash.send2trash(file_path)
            logger.info(f"Moved file to trash: {file_path}")

            # Clean up database if requested
            if cleanup_checkbox.isChecked():
                self._cleanup_database_records(file_path)

            # Remove from comparison
            self._remove_file_column(file_path)

        except Exception as e:
            logger.exception(f"Failed to delete file: {file_path}")
            QMessageBox.critical(
                self,
                "Delete Failed",
                f"Could not delete file:\n{filename}\n\nError: {str(e)}",
            )

    def _cleanup_database_records(self, file_path: str) -> None:
        """Remove database records for deleted file."""
        deleted_count = 0

        # Delete from downloads table
        cursor = self._db.execute(
            "DELETE FROM downloads WHERE output_path = ?",
            (file_path,),
        )
        deleted_count += cursor.rowcount

        # Delete from conversion_jobs table
        cursor = self._db.execute(
            "DELETE FROM conversion_jobs WHERE output_path = ?",
            (file_path,),
        )
        deleted_count += cursor.rowcount

        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} database record(s) for {file_path}")

    def _remove_file_column(self, file_path: str) -> None:
        """Remove a file from comparison and rebuild the grid."""
        # Find and remove from metadata list
        self._metadata_list = [
            m for m in self._metadata_list if m.file_path != file_path
        ]

        # Remove from raw metadata map
        if file_path in self._raw_metadata_map:
            del self._raw_metadata_map[file_path]

        # Update window title
        num_files = len(self._metadata_list)
        self.setWindowTitle(f"Compare Metadata ({num_files} files)")

        # Check if comparison is still valid
        if num_files < 2:
            QMessageBox.information(
                self,
                "Comparison Ended",
                "Only 1 file remains. Closing comparison view.",
            )
            self.close()
            return

        # Clear and rebuild the grid
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        # Rebuild comparison
        self._build_comparison_grid()

    def _on_preview_file(self, file_path: str) -> None:
        """Open Quick Look preview (macOS) or default app for video file."""
        filename = Path(file_path).name
        platform = get_platform()

        if platform == Platform.MACOS:
            # Try Quick Look first
            if quick_look_file(file_path):
                return

            # Quick Look failed, ask user about fallback
            result = QMessageBox.question(
                self,
                "Quick Look Failed",
                f"Could not open Quick Look preview for:\n{filename}\n\n"
                "Would you like to open it with the default video player instead?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

            if result == QMessageBox.StandardButton.Yes:
                if not open_file_default_app(file_path):
                    QMessageBox.warning(
                        self,
                        "Open Failed",
                        f"Could not open file:\n{filename}",
                    )
        else:
            # Windows/Linux: Ask before opening with default app
            msg = f"Open this video file?\n\n{filename}"
            if platform == Platform.WINDOWS:
                msg += "\n\nTip: Install QuickLook from Microsoft Store for quick previews."

            result = QMessageBox.question(
                self,
                "Open Video",
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

            if result == QMessageBox.StandardButton.Yes:
                if not open_file_default_app(file_path):
                    QMessageBox.warning(
                        self,
                        "Open Failed",
                        f"Could not open file:\n{filename}",
                    )
