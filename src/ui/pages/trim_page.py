"""TrimPage — video trimming tool page."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

from send2trash import send2trash

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QCheckBox,
    QMessageBox,
    QProgressBar,
    QComboBox,
    QSizePolicy,
)

from ...core.editor import EditorSession
from ...core.trim_manager import TrimManager
from ...core.ffprobe_worker import FFprobeWorker
from ...data.models import TrimConfig
from ...services.config_service import ConfigService
from ...utils.constants import VIDEO_FILE_FILTER
from ...utils.dialog_utils import get_dialog_start_dir, update_dialog_last_dir
from ..components.page_header import PageHeader
from ..widgets.segment_list_widget import SegmentListWidget
from ..widgets.trim_timeline_widget import TrimTimelineWidget
from ..widgets.video_preview_widget import VideoPreviewWidget

logger = logging.getLogger(__name__)


class TrimPage(QWidget):
    """
    Full-width Trim page for video trimming.

    Supports single video and batch trim modes with injected
    VideoPreviewWidget and TrimTimelineWidget.

    Signals:
        trim_requested: Emitted when a trim operation is started
        cancel_requested: Emitted when the user requests cancellation
    """

    trim_requested = pyqtSignal()
    cancel_requested = pyqtSignal()

    _MODE_SINGLE = 0
    _MODE_BATCH = 1

    def __init__(
        self,
        trim_manager=None,
        video_preview=None,
        trim_timeline=None,
        parent=None,
    ):
        super().__init__(parent)
        self._trim_manager: Optional[TrimManager] = trim_manager
        self._video_preview = video_preview or VideoPreviewWidget()
        self._trim_timeline = trim_timeline or TrimTimelineWidget()
        self._config_service = ConfigService()
        self._editor_session = EditorSession()
        self._syncing_editor_ui = False
        self._is_running = False

        # Runtime state
        self._current_path: Optional[str] = None
        self._successfully_trimmed_originals: Set[str] = set()
        self._job_id_to_input_path: Dict[int, str] = {}
        self._ffprobe_worker = None

        self._setup_ui()
        self._connect_signals()
        self._load_settings()

    # ------------------------------------------------------------------ #
    #  UI construction                                                     #
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        """Build the page layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # 1. Page header
        header = PageHeader(
            title="Trim",
            description="Cut segments from video files.",
        )
        main_layout.addWidget(header)

        # 2. Mode selector row
        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        mode_label = QLabel("Mode:")
        mode_row.addWidget(mode_label)

        self._mode_combo = QComboBox()
        self._mode_combo.addItem("Single Video")
        self._mode_combo.addItem("Batch Trim")
        self._mode_combo.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        mode_row.addWidget(self._mode_combo)
        mode_row.addStretch()

        # Load video button (single mode only)
        self._load_video_btn = QPushButton("Load Video")
        self._load_video_btn.setObjectName("btnWire")
        mode_row.addWidget(self._load_video_btn)

        main_layout.addLayout(mode_row)

        # 3. Video preview
        self._preview_container = self._video_preview
        main_layout.addWidget(self._preview_container, stretch=3)

        # 4. Timeline
        self._timeline_container = self._trim_timeline
        main_layout.addWidget(self._timeline_container)

        # 4b. Segment editor controls
        segment_row = QHBoxLayout()
        segment_row.setSpacing(8)

        self._split_btn = QPushButton("Split at Current")
        self._split_btn.setObjectName("btnWire")
        self._split_btn.setEnabled(False)
        segment_row.addWidget(self._split_btn)

        self._toggle_segment_btn = QPushButton("Disable Segment")
        self._toggle_segment_btn.setObjectName("btnWire")
        self._toggle_segment_btn.setEnabled(False)
        segment_row.addWidget(self._toggle_segment_btn)

        segment_row.addWidget(QLabel("Label:"))
        self._segment_label_input = QLineEdit()
        self._segment_label_input.setPlaceholderText("Optional segment label")
        self._segment_label_input.setEnabled(False)
        segment_row.addWidget(self._segment_label_input, stretch=1)

        main_layout.addLayout(segment_row)

        self._segment_list = SegmentListWidget()
        self._segment_list.setEnabled(False)
        main_layout.addWidget(self._segment_list)

        # 5. Time controls row
        time_row = QHBoxLayout()
        time_row.setSpacing(12)

        time_row.addWidget(QLabel("Start:"))
        self._start_input = QLineEdit()
        self._start_input.setPlaceholderText("0.000")
        self._start_input.setFixedWidth(100)
        time_row.addWidget(self._start_input)

        self._set_start_btn = QPushButton("Set to Current")
        self._set_start_btn.setObjectName("btnWire")
        self._set_start_btn.setToolTip("Set start time to current playback position")
        time_row.addWidget(self._set_start_btn)

        time_row.addSpacing(24)

        time_row.addWidget(QLabel("End:"))
        self._end_input = QLineEdit()
        self._end_input.setPlaceholderText("0.000")
        self._end_input.setFixedWidth(100)
        time_row.addWidget(self._end_input)

        self._set_end_btn = QPushButton("Set to Current")
        self._set_end_btn.setObjectName("btnWire")
        self._set_end_btn.setToolTip("Set end time to current playback position")
        time_row.addWidget(self._set_end_btn)

        time_row.addStretch()
        main_layout.addLayout(time_row)

        # 6. Options row
        options_row = QHBoxLayout()
        options_row.setSpacing(12)

        self._lossless_checkbox = QCheckBox(
            "Lossless (fast \u2014 may shift to nearest keyframe)"
        )
        self._lossless_checkbox.setChecked(True)
        self._lossless_checkbox.setToolTip(
            "Copy streams without re-encoding. Very fast but cuts at keyframes only."
        )
        options_row.addWidget(self._lossless_checkbox)
        options_row.addStretch()
        main_layout.addLayout(options_row)

        # 7. Output folder row
        output_row = QHBoxLayout()
        output_row.setSpacing(8)

        output_row.addWidget(QLabel("Output folder:"))

        self._output_input = QLineEdit()
        self._output_input.setPlaceholderText("Same as input (adds _trimmed suffix)")
        output_row.addWidget(self._output_input, stretch=1)

        self._output_browse_btn = QPushButton("Browse")
        self._output_browse_btn.setObjectName("btnWire")
        output_row.addWidget(self._output_browse_btn)

        main_layout.addLayout(output_row)

        # 8. Action bar
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("btnSecondary")
        self._cancel_btn.setProperty("button_role", "secondary")
        self._cancel_btn.setVisible(False)
        action_row.addWidget(self._cancel_btn)

        action_row.addStretch()

        self._trim_btn = QPushButton("TRIM VIDEO")
        self._trim_btn.setObjectName("btnPrimary")
        self._trim_btn.setProperty("button_role", "cta")
        self._trim_btn.setEnabled(False)
        self._trim_btn.setMinimumWidth(140)
        action_row.addWidget(self._trim_btn)

        main_layout.addLayout(action_row)

        # 9. Progress section
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        main_layout.addWidget(self._progress_bar)

        self._status_label = QLabel("")
        self._status_label.setObjectName("dimLabel")
        self._status_label.setVisible(False)
        main_layout.addWidget(self._status_label)

        main_layout.addStretch()

    # ------------------------------------------------------------------ #
    #  Signal wiring                                                       #
    # ------------------------------------------------------------------ #

    def _connect_signals(self) -> None:
        """Wire up all signal connections."""
        # Mode selector
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)

        # Load video button
        self._load_video_btn.clicked.connect(self._on_load_video)

        # Time control buttons
        self._set_start_btn.clicked.connect(self._on_set_start)
        self._set_end_btn.clicked.connect(self._on_set_end)
        self._start_input.editingFinished.connect(self._sync_inputs_to_session)
        self._end_input.editingFinished.connect(self._sync_inputs_to_session)

        # Output browse
        self._output_browse_btn.clicked.connect(self._on_browse_output)

        # Action buttons
        self._trim_btn.clicked.connect(self._on_trim)
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._split_btn.clicked.connect(self._on_split_segment)
        self._toggle_segment_btn.clicked.connect(self._on_toggle_segment)
        self._segment_label_input.editingFinished.connect(
            self._on_segment_label_edited
        )

        # Persist settings on change
        self._lossless_checkbox.stateChanged.connect(self._save_settings)
        self._output_input.textChanged.connect(self._save_settings)

        # Wire injected preview widget
        if self._video_preview is not None:
            self._video_preview.duration_loaded.connect(self._on_duration_loaded)
            self._video_preview.position_changed.connect(self._on_position_changed)

        # Wire injected timeline widget
        if self._trim_timeline is not None:
            self._trim_timeline.range_changed.connect(self._on_range_changed)
            self._trim_timeline.seek_requested.connect(self._on_timeline_seek_requested)

        self._segment_list.segment_selected.connect(self._on_segment_selected)
        self._segment_list.segment_toggled.connect(self._on_segment_toggled)
        self._segment_list.segment_label_changed.connect(self._on_segment_label_changed)

        # Wire injected TrimManager if provided at construction
        if self._trim_manager is not None:
            self._connect_trim_manager(self._trim_manager)

    def _connect_trim_manager(self, manager: TrimManager) -> None:
        """Connect all TrimManager signals."""
        manager.job_started.connect(self._on_job_started)
        manager.job_progress.connect(self._on_job_progress)
        manager.job_completed.connect(self._on_job_completed)
        manager.queue_progress.connect(self._on_queue_progress)
        manager.all_completed.connect(self._on_all_completed)

    # ------------------------------------------------------------------ #
    #  Settings persistence                                                #
    # ------------------------------------------------------------------ #

    def _load_settings(self) -> None:
        """Load persisted settings."""
        lossless = self._config_service.get("trim.single_lossless", True)
        self._lossless_checkbox.setChecked(lossless)

        output_dir = self._config_service.get("trim.single_output_dir", "")
        self._output_input.setText(output_dir)

    def _save_settings(self) -> None:
        """Persist current settings."""
        self._config_service.set(
            "trim.single_lossless", self._lossless_checkbox.isChecked()
        )
        self._config_service.set("trim.single_output_dir", self._output_input.text())

    # ------------------------------------------------------------------ #
    #  UI event handlers                                                   #
    # ------------------------------------------------------------------ #

    def _on_mode_changed(self, index: int) -> None:
        """Handle mode combo change."""
        is_single = index == self._MODE_SINGLE
        self._load_video_btn.setVisible(is_single)
        # Preview + timeline only shown in single mode
        self._preview_container.setVisible(is_single)
        self._timeline_container.setVisible(is_single)
        self._split_btn.setVisible(is_single)
        self._toggle_segment_btn.setVisible(is_single)
        self._segment_label_input.setVisible(is_single)
        self._segment_list.setVisible(is_single)
        self._apply_editor_control_state()

    def _on_load_video(self) -> None:
        """Open a file dialog and load the selected video."""
        start_dir = get_dialog_start_dir(fallback_config_key="trim.single_output_dir")
        file, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", start_dir, VIDEO_FILE_FILTER
        )
        if file:
            update_dialog_last_dir(file)
            self._load_video(file)

    def _load_video(self, path: str) -> None:
        """Load a video file for preview and trimming."""
        self._current_path = path
        self._editor_session.clear()
        self._refresh_editor_ui()

        # Reset time inputs and timeline
        self._start_input.setText("0.000")
        self._end_input.setText("0.000")
        self._trim_btn.setEnabled(False)

        if self._trim_timeline is not None:
            self._trim_timeline.reset()

        # Load into preview widget if available
        if self._video_preview is not None and self._video_preview.is_available():
            self._video_preview.load_video(path)
        else:
            # Fall back to ffprobe for duration
            self._probe_duration(path)

    def _probe_duration(self, path: str) -> None:
        """Get video duration via ffprobe when mpv is not available."""
        self._ffprobe_worker = FFprobeWorker([path])
        self._ffprobe_worker.completed.connect(self._on_probe_completed)
        self._ffprobe_worker.start()

    def _on_probe_completed(self, results: list) -> None:
        """Handle ffprobe duration probe completion."""
        if results:
            metadata = results[0]
            duration = metadata.duration
            if duration > 0:
                self._on_duration_loaded(duration)
            else:
                QMessageBox.warning(
                    self, "Cannot Load Video", "Failed to read video duration."
                )
        else:
            QMessageBox.warning(
                self, "Cannot Load Video", "Failed to read video metadata."
            )

        if self._ffprobe_worker is not None:
            self._ffprobe_worker.deleteLater()
            self._ffprobe_worker = None

    def _on_duration_loaded(self, duration: float) -> None:
        """Handle video duration loaded from preview or ffprobe."""
        if self._current_path is None:
            return

        self._editor_session.load_source(self._current_path, duration)
        self._refresh_editor_ui()
        self._trim_btn.setEnabled(bool(self._editor_session.enabled_segments()))

    def _on_position_changed(self, position: float) -> None:
        """Handle playback position change from preview widget."""
        if self._trim_timeline is not None:
            self._trim_timeline.set_current_position(position)

    def _on_range_changed(self, start: float, end: float) -> None:
        """Handle timeline range change — sync into text inputs."""
        if self._syncing_editor_ui:
            return

        if self._editor_session.selected_segment is None:
            self._update_time_inputs(start, end)
            return

        self._editor_session.update_selected_range(start, end)
        self._refresh_editor_ui()

    def _on_set_start(self) -> None:
        """Set start input to current playback position."""
        if self._video_preview is not None:
            pos = self._video_preview.get_position()
            self._start_input.setText(f"{pos:.3f}")
            self._sync_inputs_to_session()

    def _on_set_end(self) -> None:
        """Set end input to current playback position."""
        if self._video_preview is not None:
            pos = self._video_preview.get_position()
            self._end_input.setText(f"{pos:.3f}")
            self._sync_inputs_to_session()

    def _sync_inputs_to_session(self) -> None:
        """Push start/end text inputs into the selected segment."""
        if self._editor_session.selected_segment is None:
            return
        try:
            start = float(self._start_input.text())
            end = float(self._end_input.text())
        except ValueError:
            self._refresh_editor_ui()
            return

        self._editor_session.update_selected_range(start, end)
        self._refresh_editor_ui()

    def _on_split_segment(self) -> None:
        """Split the active segment at the current playhead position."""
        if self._video_preview is None:
            return

        position = self._video_preview.get_position()
        if self._editor_session.split_at(position) is None:
            self._status_label.setVisible(True)
            self._status_label.setText("Move away from the segment edge before splitting.")
            return

        self._status_label.setVisible(True)
        self._status_label.setText("Segment split at current position.")
        self._refresh_editor_ui()

    def _on_toggle_segment(self) -> None:
        """Toggle the selected segment's enabled state."""
        segment = self._editor_session.toggle_segment_enabled()
        if segment is None:
            return
        self._refresh_editor_ui()

    def _on_segment_selected(self, segment_id: str) -> None:
        """Sync list selection into the editor session."""
        if self._editor_session.select_segment(segment_id) is None:
            return
        self._refresh_editor_ui()

    def _on_segment_toggled(self, segment_id: str, enabled: bool) -> None:
        """Handle enabled-state changes from the segment list."""
        self._editor_session.set_segment_enabled(segment_id, enabled)
        self._refresh_editor_ui()

    def _on_segment_label_changed(self, segment_id: str, label: str) -> None:
        """Handle inline label edits from the segment list."""
        self._editor_session.set_segment_label(segment_id, label)
        self._refresh_editor_ui()

    def _on_segment_label_edited(self) -> None:
        """Handle label edits from the inline inspector field."""
        segment = self._editor_session.selected_segment
        if segment is None:
            return
        self._editor_session.set_segment_label(
            segment.id, self._segment_label_input.text()
        )
        self._refresh_editor_ui()

    def _on_timeline_seek_requested(self, position: float) -> None:
        """Seek the preview player when the timeline requests it."""
        if self._video_preview is not None:
            self._video_preview.seek(position)

    def _on_browse_output(self) -> None:
        """Browse for output directory."""
        start_dir = get_dialog_start_dir(
            self._output_input.text(), "trim.single_output_dir"
        )
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", start_dir
        )
        if folder:
            update_dialog_last_dir(folder)
            self._output_input.setText(folder)

    def _on_trim(self) -> None:
        """Validate inputs and start trim operation."""
        if not self._current_path:
            QMessageBox.warning(self, "No Video", "Please load a video file first.")
            return

        enabled_segments = self._editor_session.enabled_segments()
        if not enabled_segments:
            QMessageBox.warning(
                self,
                "No Segments Selected",
                "Enable at least one segment before exporting.",
            )
            return

        lossless = self._lossless_checkbox.isChecked()
        output_dir = self._output_input.text() or None
        duration = self._editor_session.duration or (
            self._trim_timeline.get_duration() if self._trim_timeline is not None else 0.0
        )

        trim_ranges = [
            (segment.start_time, segment.end_time, duration)
            for segment in enabled_segments
        ]
        output_path_overrides = self._build_output_paths(
            self._current_path,
            output_dir,
            len(trim_ranges),
        )

        self._start_trim(
            files=[self._current_path] * len(trim_ranges),
            trim_ranges=trim_ranges,
            lossless=lossless,
            output_dir=output_dir,
            output_path_overrides=output_path_overrides,
        )

    def _start_trim(
        self,
        files: List[str],
        trim_ranges: List[tuple],
        lossless: bool,
        output_dir: Optional[str],
        output_path_overrides: Optional[List[str]] = None,
    ) -> None:
        """Create a TrimManager, add jobs, and start processing."""
        # Reset delete-originals tracking
        self._successfully_trimmed_originals.clear()
        self._job_id_to_input_path.clear()

        # Create a fresh TrimManager for this run
        self._trim_manager = TrimManager()

        config = TrimConfig(
            lossless=lossless,
            output_dir=output_dir,
        )
        self._trim_manager.set_config(config)

        # Connect TrimManager signals
        self._connect_trim_manager(self._trim_manager)

        # Add jobs
        overrides = output_path_overrides or [None] * len(trim_ranges)
        for path, (start, end, dur), output_path_override in zip(
            files, trim_ranges, overrides
        ):
            job = self._trim_manager.add_job(
                path,
                start,
                end,
                dur,
                output_path_override=output_path_override,
            )
            if job and job.id is not None:
                self._job_id_to_input_path[job.id] = path

        # Update UI to running state
        self._set_running(True)
        self.trim_requested.emit()

        # Start
        self._trim_manager.start()

    # ------------------------------------------------------------------ #
    #  TrimManager signal handlers                                         #
    # ------------------------------------------------------------------ #

    def _on_job_started(self, job_id: int) -> None:
        """Handle individual job start."""
        path = self._job_id_to_input_path.get(job_id, "")
        name = Path(path).name if path else f"Job {job_id}"
        self._status_label.setText(f"Trimming {name}…")

    def _on_job_progress(self, job_id: int, percent: float, speed: str = "", eta: str = "") -> None:
        """Handle job progress update."""
        self._progress_bar.setValue(int(percent))

    def _on_job_completed(
        self, job_id: int, success: bool, output_path: str, error: str
    ) -> None:
        """Handle single job completion."""
        if success:
            if job_id in self._job_id_to_input_path:
                self._successfully_trimmed_originals.add(
                    self._job_id_to_input_path[job_id]
                )
        else:
            status = "Cancelled" if "Cancelled" in error else "Failed"
            self._status_label.setText(f"{status}: {error}" if error else status)

    def _on_queue_progress(self, completed: int, total: int, in_progress: int) -> None:
        """Handle queue-level progress update."""
        if total > 0:
            self._progress_bar.setValue(int((completed / total) * 100))
        self._status_label.setText(f"{completed} / {total} complete")

    def _on_all_completed(self) -> None:
        """Handle all jobs finished."""
        self._set_running(False)

        if self._trim_manager is None:
            return

        completed = self._trim_manager.completed_count
        failed = self._trim_manager.failed_count
        self.trim_requested.emit()  # re-use signal to notify shell of state change

        if failed == 0:
            self._status_label.setText(f"Done — {completed} file(s) trimmed.")
            QMessageBox.information(
                self,
                "Trim Complete",
                f"Successfully trimmed {completed} file(s).",
            )
        else:
            self._status_label.setText(
                f"Done — {completed} succeeded, {failed} failed."
            )
            QMessageBox.warning(
                self,
                "Trim Complete",
                f"Trimmed {completed} file(s).\n{failed} file(s) failed.",
            )

    # ------------------------------------------------------------------ #
    #  Cancel                                                              #
    # ------------------------------------------------------------------ #

    def _on_cancel(self) -> None:
        """Cancel all running trim jobs."""
        if self._trim_manager is not None:
            self._trim_manager.cancel_all()
        self.cancel_requested.emit()

    # ------------------------------------------------------------------ #
    #  Running state                                                       #
    # ------------------------------------------------------------------ #

    def _set_running(self, running: bool) -> None:
        """Toggle UI between idle and running states."""
        self._is_running = running
        self._trim_btn.setEnabled(not running)
        self._load_video_btn.setEnabled(not running)
        self._cancel_btn.setVisible(running)
        self._progress_bar.setVisible(running or not running)  # always show after start
        self._status_label.setVisible(True)

        if running:
            self._progress_bar.setValue(0)
            self._status_label.setText("Starting…")
            self._mode_combo.setEnabled(False)
        else:
            self._mode_combo.setEnabled(True)

        self._apply_editor_control_state()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def set_video_preview(self, widget) -> None:
        """Replace the video preview widget after construction."""
        self._video_preview = widget

    def set_trim_timeline(self, widget) -> None:
        """Replace the trim timeline widget after construction."""
        self._trim_timeline = widget

    def cleanup(self) -> None:
        """Release resources (call before closing)."""
        if self._video_preview is not None:
            self._video_preview.cleanup()
        if self._ffprobe_worker is not None:
            self._ffprobe_worker.deleteLater()
            self._ffprobe_worker = None

    def _refresh_editor_ui(self) -> None:
        """Re-sync editor controls from the in-memory session."""
        self._syncing_editor_ui = True
        segment = self._editor_session.selected_segment

        if self._trim_timeline is not None:
            if self._editor_session.duration > 0:
                self._trim_timeline.set_duration(self._editor_session.duration)
            if segment is not None:
                self._trim_timeline.set_range(segment.start_time, segment.end_time)
            else:
                self._trim_timeline.reset()

        if segment is not None:
            self._update_time_inputs(segment.start_time, segment.end_time)
            self._segment_label_input.setText(segment.label)
            self._toggle_segment_btn.setText(
                "Disable Segment" if segment.enabled else "Enable Segment"
            )
        else:
            self._update_time_inputs(0.0, 0.0)
            self._segment_label_input.clear()
            self._toggle_segment_btn.setText("Disable Segment")

        self._segment_list.set_session(
            self._editor_session if self._editor_session.segments else None
        )
        self._syncing_editor_ui = False
        self._apply_editor_control_state()

    def _update_time_inputs(self, start: float, end: float) -> None:
        """Update start/end text fields without re-triggering sync."""
        self._start_input.blockSignals(True)
        self._end_input.blockSignals(True)
        self._start_input.setText(f"{start:.3f}")
        self._end_input.setText(f"{end:.3f}")
        self._start_input.blockSignals(False)
        self._end_input.blockSignals(False)

    def _build_output_paths(
        self, input_path: str, output_dir: Optional[str], count: int
    ) -> List[str]:
        """Build separate output paths for enabled segments."""
        input_file = Path(input_path)
        base_dir = Path(output_dir) if output_dir else input_file.parent

        if count == 1:
            return [str(base_dir / f"{input_file.stem}_trimmed{input_file.suffix}")]

        return [
            str(base_dir / f"{input_file.stem}_trimmed_{index + 1:03d}{input_file.suffix}")
            for index in range(count)
        ]

    def _apply_editor_control_state(self) -> None:
        """Update editor controls from selection and running state."""
        is_single_mode = self._mode_combo.currentIndex() == self._MODE_SINGLE
        has_selection = self._editor_session.selected_segment is not None
        has_segments = bool(self._editor_session.segments)
        has_enabled = bool(self._editor_session.enabled_segments())
        is_interactive = not self._is_running and is_single_mode

        self._split_btn.setEnabled(is_interactive and has_selection)
        self._toggle_segment_btn.setEnabled(is_interactive and has_selection)
        self._segment_label_input.setEnabled(is_interactive and has_selection)
        self._segment_list.setEnabled(is_interactive and has_segments)
        self._start_input.setEnabled(is_interactive and has_selection)
        self._end_input.setEnabled(is_interactive and has_selection)
        self._set_start_btn.setEnabled(is_interactive and has_selection)
        self._set_end_btn.setEnabled(is_interactive and has_selection)
        self._trim_btn.setEnabled(
            is_interactive and bool(self._current_path) and has_enabled
        )
