"""TrimPage — video trimming tool page."""

import logging
from pathlib import Path
from typing import Dict, Optional, Set

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

from ...core.editor import (
    EditorDiagnostics,
    EditorSession,
    ExportManager,
    ExportMode,
    ExportPlanner,
    KeyframeProbeWorker,
    ProjectStore,
    QuickSessionStore,
)
from ...core.trim_manager import TrimManager
from ...core.ffprobe_worker import FFprobeWorker
from ...data.models import TrimConfig
from ...services.config_service import ConfigService
from ...utils.constants import VIDEO_FILE_FILTER
from ...utils.dialog_utils import get_dialog_start_dir, update_dialog_last_dir
from ..components.activity_drawer import ActivityDrawer
from ..components.data_panel import DataPanel
from ..components.log_feed import LogFeed
from ..components.page_header import PageHeader
from ..components.split_layout import SplitLayout
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
        self._video_preview = video_preview or self._build_default_video_preview()
        self._trim_timeline = trim_timeline or TrimTimelineWidget()
        self._config_service = ConfigService()
        self._editor_session = EditorSession()
        self._export_planner = ExportPlanner()
        self._export_manager = ExportManager(self)
        self._project_store = ProjectStore()
        self._quick_session_store = QuickSessionStore()
        self._diagnostics = EditorDiagnostics(self)
        self._syncing_editor_ui = False
        self._is_running = False
        self._current_project_path: Optional[str] = None

        # Runtime state
        self._current_path: Optional[str] = None
        self._successfully_trimmed_originals: Set[str] = set()
        self._job_id_to_input_path: Dict[int, str] = {}
        self._ffprobe_worker = None
        self._keyframe_worker: Optional[KeyframeProbeWorker] = None
        self._source_metadata: dict = {}
        self._source_probe_payload: dict = {}
        self._keyframe_times: list[float] = []
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(600)

        self._setup_ui()
        self._connect_signals()
        self._load_settings()
        self._autosave_timer.timeout.connect(self._save_quick_session_now)
        self._restore_quick_session_if_enabled()

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

        self._load_project_btn = QPushButton("Load Project")
        self._load_project_btn.setObjectName("btnWire")
        mode_row.addWidget(self._load_project_btn)

        self._save_project_btn = QPushButton("Save Project")
        self._save_project_btn.setObjectName("btnWire")
        mode_row.addWidget(self._save_project_btn)

        main_layout.addLayout(mode_row)

        split = SplitLayout(right_width=460)
        main_layout.addWidget(split, stretch=1)

        left_layout = QVBoxLayout(split.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        right_layout = QVBoxLayout(split.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # 3. Preview panel
        self._preview_panel = DataPanel("Preview")
        self._preview_container = self._video_preview
        self._preview_panel.body_layout.addWidget(self._preview_container)
        left_layout.addWidget(self._preview_panel, stretch=5)

        # 4. Timeline panel
        self._timeline_panel = DataPanel("Timeline")
        self._timeline_container = self._trim_timeline
        self._timeline_panel.body_layout.addWidget(self._timeline_container)

        time_row = QHBoxLayout()
        time_row.setSpacing(12)

        time_row.addWidget(QLabel("Start:"))
        self._start_input = QLineEdit()
        self._start_input.setPlaceholderText("00:00:00.000")
        self._start_input.setFixedWidth(140)
        time_row.addWidget(self._start_input)

        self._set_start_btn = QPushButton("Set to Current")
        self._set_start_btn.setObjectName("btnWire")
        self._set_start_btn.setToolTip("Set start time to current playback position")
        time_row.addWidget(self._set_start_btn)

        time_row.addSpacing(24)

        time_row.addWidget(QLabel("End:"))
        self._end_input = QLineEdit()
        self._end_input.setPlaceholderText("00:00:00.000")
        self._end_input.setFixedWidth(140)
        time_row.addWidget(self._end_input)

        self._set_end_btn = QPushButton("Set to Current")
        self._set_end_btn.setObjectName("btnWire")
        self._set_end_btn.setToolTip("Set end time to current playback position")
        time_row.addWidget(self._set_end_btn)

        time_row.addStretch()
        self._timeline_panel.body_layout.addLayout(time_row)
        left_layout.addWidget(self._timeline_panel, stretch=2)

        # 5. Segments panel
        self._segment_panel = DataPanel("Segments")
        segment_actions = QHBoxLayout()
        segment_actions.setSpacing(8)

        self._split_btn = QPushButton("Split at Current")
        self._split_btn.setObjectName("btnWire")
        self._split_btn.setEnabled(False)
        segment_actions.addWidget(self._split_btn)

        self._toggle_segment_btn = QPushButton("Disable Segment")
        self._toggle_segment_btn.setObjectName("btnWire")
        self._toggle_segment_btn.setEnabled(False)
        segment_actions.addWidget(self._toggle_segment_btn)

        self._delete_segment_btn = QPushButton("Delete Segment")
        self._delete_segment_btn.setObjectName("btnDestructive")
        self._delete_segment_btn.setProperty("button_role", "destructive")
        self._delete_segment_btn.setEnabled(False)
        segment_actions.addWidget(self._delete_segment_btn)

        self._segment_panel.body_layout.addLayout(segment_actions)

        label_row = QHBoxLayout()
        label_row.setSpacing(8)
        label_row.addWidget(QLabel("Label"))
        self._segment_label_input = QLineEdit()
        self._segment_label_input.setPlaceholderText("Optional segment label")
        self._segment_label_input.setEnabled(False)
        label_row.addWidget(self._segment_label_input, stretch=1)
        self._segment_panel.body_layout.addLayout(label_row)

        tags_row = QHBoxLayout()
        tags_row.setSpacing(8)
        tags_row.addWidget(QLabel("Tags"))
        self._segment_tags_input = QLineEdit()
        self._segment_tags_input.setPlaceholderText("Comma-separated tags")
        self._segment_tags_input.setEnabled(False)
        tags_row.addWidget(self._segment_tags_input, stretch=1)
        self._segment_panel.body_layout.addLayout(tags_row)

        self._segment_list = SegmentListWidget()
        self._segment_list.setEnabled(False)
        self._segment_panel.body_layout.addWidget(self._segment_list, stretch=1)
        right_layout.addWidget(self._segment_panel, stretch=4)

        # 6. Export panel
        self._export_panel = DataPanel("Export")

        self._lossless_checkbox = QCheckBox(
            "Lossless export (fast, keyframe-limited)"
        )
        self._lossless_checkbox.setChecked(True)
        self._lossless_checkbox.setToolTip(
            "Copy streams without re-encoding. Very fast but cuts at keyframes only."
        )
        self._export_panel.body_layout.addWidget(self._lossless_checkbox)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        mode_row.addWidget(QLabel("Mode"))
        self._export_mode_combo = QComboBox()
        self._export_mode_combo.addItem("Separate Outputs", ExportMode.SEPARATE.value)
        self._export_mode_combo.addItem("Merged Output", ExportMode.MERGED.value)
        mode_row.addWidget(self._export_mode_combo, stretch=1)
        self._export_panel.body_layout.addLayout(mode_row)

        output_row = QHBoxLayout()
        output_row.setSpacing(8)
        output_row.addWidget(QLabel("Output"))

        self._output_input = QLineEdit()
        self._output_input.setPlaceholderText("Same as input (adds _trimmed suffix)")
        output_row.addWidget(self._output_input, stretch=1)

        self._output_browse_btn = QPushButton("Browse")
        self._output_browse_btn.setObjectName("btnWire")
        output_row.addWidget(self._output_browse_btn)
        self._export_panel.body_layout.addLayout(output_row)

        self._warning_label = QLabel("")
        self._warning_label.setObjectName("dimLabel")
        self._warning_label.setVisible(False)
        self._warning_label.setWordWrap(True)
        self._export_panel.body_layout.addWidget(self._warning_label)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("btnSecondary")
        self._cancel_btn.setProperty("button_role", "secondary")
        self._cancel_btn.setVisible(False)
        action_row.addWidget(self._cancel_btn)
        action_row.addStretch()

        self._trim_btn = QPushButton("Trim Video")
        self._trim_btn.setObjectName("btnPrimary")
        self._trim_btn.setProperty("button_role", "primary")
        self._trim_btn.setEnabled(False)
        self._trim_btn.setMinimumWidth(120)
        action_row.addWidget(self._trim_btn)
        self._export_panel.body_layout.addLayout(action_row)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        self._export_panel.body_layout.addWidget(self._progress_bar)

        self._status_label = QLabel("")
        self._status_label.setObjectName("dimLabel")
        self._status_label.setVisible(False)
        self._status_label.setWordWrap(True)
        self._export_panel.body_layout.addWidget(self._status_label)
        right_layout.addWidget(self._export_panel, stretch=2)

        self._activity_drawer = ActivityDrawer("Editor Activity")
        self._activity_log = LogFeed(max_entries=150)
        self._activity_drawer.set_content_widget(self._activity_log)
        right_layout.addWidget(self._activity_drawer, stretch=2)

    # ------------------------------------------------------------------ #
    #  Signal wiring                                                       #
    # ------------------------------------------------------------------ #

    def _connect_signals(self) -> None:
        """Wire up all signal connections."""
        # Mode selector
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)

        # Load video button
        self._load_video_btn.clicked.connect(self._on_load_video)
        self._load_project_btn.clicked.connect(self._on_load_project)
        self._save_project_btn.clicked.connect(self._on_save_project)

        # Time control buttons
        self._set_start_btn.clicked.connect(self._on_set_start)
        self._set_end_btn.clicked.connect(self._on_set_end)
        self._start_input.editingFinished.connect(self._sync_inputs_to_session)
        self._end_input.editingFinished.connect(self._sync_inputs_to_session)
        self._segment_tags_input.editingFinished.connect(self._on_segment_tags_edited)

        # Output browse
        self._output_browse_btn.clicked.connect(self._on_browse_output)

        # Action buttons
        self._trim_btn.clicked.connect(self._on_trim)
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._split_btn.clicked.connect(self._on_split_segment)
        self._toggle_segment_btn.clicked.connect(self._on_toggle_segment)
        self._delete_segment_btn.clicked.connect(self._on_delete_segment)
        self._segment_label_input.editingFinished.connect(
            self._on_segment_label_edited
        )

        # Persist settings on change
        self._lossless_checkbox.stateChanged.connect(self._save_settings)
        self._output_input.textChanged.connect(self._save_settings)
        self._lossless_checkbox.stateChanged.connect(self._schedule_autosave)
        self._output_input.textChanged.connect(self._schedule_autosave)
        self._export_mode_combo.currentIndexChanged.connect(self._on_export_mode_changed)

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

        self._export_manager.started.connect(self._on_export_started)
        self._export_manager.progress.connect(self._on_export_progress)
        self._export_manager.log.connect(self._on_export_log)
        self._export_manager.completed.connect(self._on_export_completed)

        self._diagnostics.entry_added.connect(
            lambda level, message: self._activity_log.add_entry(message, level)
        )
        self._diagnostics.entry_added.connect(lambda *_: self._update_activity_badge())
        self._diagnostics.cleared.connect(self._activity_log.clear)

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

    def _build_default_video_preview(self) -> Optional[VideoPreviewWidget]:
        """Return the default preview widget for the Trim page."""
        return VideoPreviewWidget()

    # ------------------------------------------------------------------ #
    #  Settings persistence                                                #
    # ------------------------------------------------------------------ #

    def _load_settings(self) -> None:
        """Load persisted settings."""
        lossless = self._config_service.get("trim.single_lossless", True)
        self._lossless_checkbox.setChecked(lossless)

        output_dir = self._config_service.get("trim.single_output_dir", "")
        self._output_input.setText(output_dir)

        export_mode = self._config_service.get("trim.single_export_mode", "separate")
        index = self._export_mode_combo.findData(export_mode)
        self._export_mode_combo.setCurrentIndex(max(index, 0))
        self._sync_output_placeholder()

    def _save_settings(self) -> None:
        """Persist current settings."""
        self._config_service.set(
            "trim.single_lossless", self._lossless_checkbox.isChecked()
        )
        self._config_service.set("trim.single_output_dir", self._output_input.text())
        self._config_service.set(
            "trim.single_export_mode",
            self._export_mode_combo.currentData(),
        )

    def _export_mode(self) -> ExportMode:
        value = self._export_mode_combo.currentData() or ExportMode.SEPARATE.value
        return ExportMode(value)

    def _sync_output_placeholder(self) -> None:
        if self._export_mode() == ExportMode.MERGED:
            self._output_input.setPlaceholderText(
                "Merged output file (defaults next to source)"
            )
        else:
            self._output_input.setPlaceholderText(
                "Output folder (defaults to source folder)"
            )

    # ------------------------------------------------------------------ #
    #  UI event handlers                                                   #
    # ------------------------------------------------------------------ #

    def _on_mode_changed(self, index: int) -> None:
        """Handle mode combo change."""
        is_single = index == self._MODE_SINGLE
        self._load_video_btn.setVisible(is_single)
        self._load_project_btn.setVisible(is_single)
        self._save_project_btn.setVisible(is_single)
        self._preview_panel.setVisible(is_single)
        self._timeline_panel.setVisible(is_single)
        self._segment_panel.setVisible(is_single)
        self._activity_drawer.setVisible(is_single)
        self._apply_editor_control_state()

    def _on_export_mode_changed(self, _index: int = 0) -> None:
        self._sync_output_placeholder()
        self._save_settings()
        self._schedule_autosave()

    def _on_load_video(self) -> None:
        """Open a file dialog and load the selected video."""
        start_dir = get_dialog_start_dir(fallback_config_key="trim.single_output_dir")
        file, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", start_dir, VIDEO_FILE_FILTER
        )
        if file:
            update_dialog_last_dir(file)
            self._load_video(file)

    def _on_load_project(self) -> None:
        """Restore a saved project JSON file."""
        start_dir = get_dialog_start_dir("", "dialogs.last_dir")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Trim Project",
            start_dir,
            "Trim Project (*.cutproj.json *.json);;All Files (*)",
        )
        if not file_path:
            return

        update_dialog_last_dir(file_path)
        try:
            payload = self._project_store.load(file_path)
            self._restore_snapshot(
                payload["session"],
                export_state=payload.get("export", {}),
                analysis=payload.get("analysis", {}),
                project_path=file_path,
            )
            self._diagnostics.record("info", f"Loaded project {Path(file_path).name}")
        except Exception as exc:
            QMessageBox.warning(self, "Project Load Failed", str(exc))
            self._diagnostics.record("error", f"Project load failed: {exc}")

    def _on_save_project(self) -> None:
        """Persist the current editor state as a project JSON file."""
        if not self._editor_session.has_source:
            QMessageBox.information(self, "No Project State", "Load a video before saving a project.")
            return

        start_dir = get_dialog_start_dir("", "dialogs.last_dir")
        suggested = (
            f"{Path(self._current_path).stem}.cutproj.json"
            if self._current_path
            else "trim-session.cutproj.json"
        )
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Trim Project",
            str(Path(start_dir) / suggested),
            "Trim Project (*.cutproj.json *.json);;All Files (*)",
        )
        if not file_path:
            return

        update_dialog_last_dir(file_path)
        try:
            self._project_store.save(
                file_path,
                self._editor_session,
                export_state=self._build_export_state(),
                analysis=self._build_analysis_state(),
            )
            self._current_project_path = file_path
            self._diagnostics.record("info", f"Saved project {Path(file_path).name}")
        except Exception as exc:
            QMessageBox.warning(self, "Project Save Failed", str(exc))
            self._diagnostics.record("error", f"Project save failed: {exc}")

    def _load_video(self, path: str) -> None:
        """Load a video file for preview and trimming."""
        self._cancel_analysis_jobs()
        self._current_path = path
        self._current_project_path = None
        self._editor_session.clear()
        self._source_metadata = {}
        self._source_probe_payload = {}
        self._keyframe_times = []
        self._warning_label.clear()
        self._warning_label.setVisible(False)
        self._refresh_editor_ui()

        # Reset time inputs and timeline
        self._start_input.setText(self._format_timestamp(0.0))
        self._end_input.setText(self._format_timestamp(0.0))
        self._trim_btn.setEnabled(False)
        self._status_label.setVisible(True)
        self._status_label.setText(f"Loading {Path(path).name}…")

        if self._trim_timeline is not None:
            self._trim_timeline.reset()

        self._probe_source_metadata(path)

        # Load into preview widget if available
        if self._video_preview is not None and self._video_preview.is_available():
            self._video_preview.load_video(path)
        else:
            self._diagnostics.record("warning", "Preview backend unavailable, using ffprobe duration only.")

        self._schedule_autosave()

    def _probe_source_metadata(self, path: str) -> None:
        """Probe metadata for the loaded source and start keyframe analysis."""
        self._ffprobe_worker = FFprobeWorker([path])
        self._ffprobe_worker.raw_metadata_ready.connect(self._on_raw_probe_ready)
        self._ffprobe_worker.completed.connect(self._on_probe_completed)
        self._ffprobe_worker.start()
        self._diagnostics.record("info", f"Probing metadata for {Path(path).name}")

    def _on_probe_completed(self, results: list) -> None:
        """Handle ffprobe duration probe completion."""
        if results:
            metadata = results[0]
            duration = metadata.duration
            self._source_metadata = {
                "codec": metadata.codec,
                "duration": metadata.duration,
                "width": metadata.width,
                "height": metadata.height,
                "fps": metadata.fps,
                "bitrate": metadata.bitrate,
            }
            if duration > 0:
                if not self._editor_session.has_source:
                    self._on_duration_loaded(duration)
                self._diagnostics.record(
                    "info",
                    f"Metadata ready: {metadata.codec or 'unknown codec'}, {metadata.width}x{metadata.height}",
                )
                self._start_keyframe_probe(self._current_path)
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

    def _on_raw_probe_ready(self, _file_path: str, raw_payload: dict) -> None:
        """Capture raw ffprobe JSON for later diagnostics/export planning."""
        self._source_probe_payload = raw_payload or {}

    def _start_keyframe_probe(self, path: Optional[str]) -> None:
        if not path:
            return
        self._keyframe_worker = KeyframeProbeWorker(path, self)
        self._keyframe_worker.completed.connect(self._on_keyframes_ready)
        self._keyframe_worker.failed.connect(self._on_keyframe_probe_failed)
        self._keyframe_worker.start()

    def _on_keyframes_ready(self, keyframe_times: list) -> None:
        self._keyframe_times = keyframe_times
        self._diagnostics.record(
            "info", f"Keyframe map ready ({len(keyframe_times)} positions)."
        )
        if self._keyframe_worker is not None:
            self._keyframe_worker.deleteLater()
            self._keyframe_worker = None
        self._schedule_autosave()

    def _on_keyframe_probe_failed(self, message: str) -> None:
        self._diagnostics.record("warning", f"Keyframe scan skipped: {message}")
        if self._keyframe_worker is not None:
            self._keyframe_worker.deleteLater()
            self._keyframe_worker = None

    def _on_duration_loaded(self, duration: float) -> None:
        """Handle video duration loaded from preview or ffprobe."""
        if self._current_path is None:
            return

        if (
            self._editor_session.source_path == self._current_path
            and self._editor_session.segments
        ):
            self._editor_session.duration = max(duration, self._editor_session.duration)
            self._refresh_editor_ui()
            return

        self._editor_session.load_source(self._current_path, duration)
        self._refresh_editor_ui()
        self._trim_btn.setEnabled(bool(self._editor_session.enabled_segments()))
        self._status_label.setText(f"Loaded {Path(self._current_path).name}")
        self._schedule_autosave()

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
        self._schedule_autosave()

    def _on_set_start(self) -> None:
        """Set start input to current playback position."""
        if self._video_preview is not None:
            pos = self._video_preview.get_position()
            self._start_input.setText(self._format_timestamp(pos))
            self._sync_inputs_to_session()

    def _on_set_end(self) -> None:
        """Set end input to current playback position."""
        if self._video_preview is not None:
            pos = self._video_preview.get_position()
            self._end_input.setText(self._format_timestamp(pos))
            self._sync_inputs_to_session()

    def _sync_inputs_to_session(self) -> None:
        """Push start/end text inputs into the selected segment."""
        if self._editor_session.selected_segment is None:
            return
        try:
            start = self._parse_time_input(self._start_input.text())
            end = self._parse_time_input(self._end_input.text())
        except ValueError:
            self._refresh_editor_ui()
            return

        self._editor_session.update_selected_range(start, end)
        self._refresh_editor_ui()
        self._schedule_autosave()

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
        self._schedule_autosave()

    def _on_toggle_segment(self) -> None:
        """Toggle the selected segment's enabled state."""
        segment = self._editor_session.toggle_segment_enabled()
        if segment is None:
            return
        self._refresh_editor_ui()
        self._schedule_autosave()

    def _on_segment_selected(self, segment_id: str) -> None:
        """Sync list selection into the editor session."""
        if self._editor_session.select_segment(segment_id) is None:
            return
        self._refresh_editor_ui()

    def _on_segment_toggled(self, segment_id: str, enabled: bool) -> None:
        """Handle enabled-state changes from the segment list."""
        self._editor_session.set_segment_enabled(segment_id, enabled)
        self._refresh_editor_ui()
        self._schedule_autosave()

    def _on_segment_label_changed(self, segment_id: str, label: str) -> None:
        """Handle inline label edits from the segment list."""
        self._editor_session.set_segment_label(segment_id, label)
        self._refresh_editor_ui()
        self._schedule_autosave()

    def _on_segment_label_edited(self) -> None:
        """Handle label edits from the inline inspector field."""
        segment = self._editor_session.selected_segment
        if segment is None:
            return
        self._editor_session.set_segment_label(
            segment.id, self._segment_label_input.text()
        )
        self._refresh_editor_ui()
        self._schedule_autosave()

    def _on_delete_segment(self) -> None:
        """Remove the selected segment from the current session."""
        removed = self._editor_session.delete_segment()
        if removed is None:
            return

        self._status_label.setVisible(True)
        self._status_label.setText("Segment deleted.")
        self._refresh_editor_ui()
        self._schedule_autosave()

    def _on_segment_tags_edited(self) -> None:
        """Handle comma-separated tag edits for the active segment."""
        segment = self._editor_session.selected_segment
        if segment is None:
            return
        tags = [tag.strip() for tag in self._segment_tags_input.text().split(",")]
        self._editor_session.set_segment_tags(segment.id, tags)
        self._refresh_editor_ui()
        self._schedule_autosave()

    def _on_timeline_seek_requested(self, position: float) -> None:
        """Seek the preview player when the timeline requests it."""
        if self._video_preview is not None:
            self._video_preview.seek(position)

    def _on_browse_output(self) -> None:
        """Browse for output folder or merged file path."""
        start_dir = get_dialog_start_dir(self._output_input.text(), "trim.single_output_dir")
        if self._export_mode() == ExportMode.MERGED:
            current_source = Path(self._current_path) if self._current_path else Path(start_dir) / "merged.mp4"
            suggested = self._output_input.text() or str(
                current_source.with_name(f"{current_source.stem}_merged{current_source.suffix}")
            )
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Select Merged Output",
                suggested,
                VIDEO_FILE_FILTER,
            )
            if file_path:
                update_dialog_last_dir(file_path)
                self._output_input.setText(file_path)
        else:
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
        if not Path(self._current_path).exists():
            QMessageBox.warning(
                self,
                "Source Missing",
                "The saved source file is missing. Load or relink the source media first.",
            )
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
        output_target = self._output_input.text().strip() or None

        try:
            plan = self._export_planner.build_plan(
                self._editor_session,
                mode=self._export_mode(),
                lossless=lossless,
                output_target=output_target,
                keyframe_times=self._keyframe_times,
                source_metadata=self._source_metadata,
            )
        except Exception as exc:
            QMessageBox.warning(self, "Cannot Export", str(exc))
            self._diagnostics.record("error", f"Export planning failed: {exc}")
            return

        self._present_plan_warnings(plan)
        if plan.requires_confirmation and not self._confirm_export(plan):
            self._diagnostics.record("warning", "Export cancelled after warning review.")
            return

        self._export_manager.start(plan)
        self.trim_requested.emit()
        self._schedule_autosave()

    def _start_trim(
        self,
        files,
        trim_ranges,
        lossless: bool,
        output_dir: Optional[str],
        output_path_overrides=None,
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

    def _present_plan_warnings(self, plan) -> None:
        if not plan.warnings:
            self._warning_label.clear()
            self._warning_label.setVisible(False)
            return

        warning_text = "\n".join(f"- {warning.message}" for warning in plan.warnings)
        self._warning_label.setText(warning_text)
        self._warning_label.setVisible(True)
        for warning in plan.warnings:
            self._diagnostics.record("warning", warning.message)

    def _confirm_export(self, plan) -> bool:
        warning_text = "\n\n".join(warning.message for warning in plan.warnings)
        result = QMessageBox.warning(
            self,
            "Review Export Warnings",
            f"{warning_text}\n\nContinue with this export?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return result == QMessageBox.StandardButton.Yes

    def _on_export_started(self) -> None:
        self._set_running(True)
        self._progress_bar.setVisible(True)
        self._status_label.setVisible(True)
        self._status_label.setText("Starting export…")

    def _on_export_progress(self, percent: float, speed: str, _eta: str) -> None:
        self._progress_bar.setValue(int(percent))
        speed_suffix = f" at {speed}" if speed else ""
        self._status_label.setText(f"Exporting… {percent:.0f}%{speed_suffix}")

    def _on_export_log(self, level: str, message: str) -> None:
        self._diagnostics.record(level, message)

    def _on_export_completed(self, success: bool, outputs: object, error: str) -> None:
        self._set_running(False)
        output_paths = outputs if isinstance(outputs, list) else []
        if success:
            count = len(output_paths)
            self._status_label.setText(f"Done. Exported {count} output(s).")
            self._diagnostics.record("info", f"Export complete: {count} output(s).")
            QMessageBox.information(
                self,
                "Export Complete",
                f"Successfully exported {count} output(s).",
            )
        else:
            status = "Cancelled" if "Cancelled" in error else "Failed"
            self._status_label.setText(f"{status}: {error}" if error else status)
            self._diagnostics.record("error", f"Export failed: {error or status}")
            if "Cancelled" not in error:
                QMessageBox.warning(
                    self,
                    "Export Failed",
                    error or "The export failed.",
                )

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
        self._export_manager.cancel()
        if self._trim_manager is not None:
            self._trim_manager.cancel_all()
        self._diagnostics.record("warning", "Export cancellation requested.")
        self.cancel_requested.emit()

    # ------------------------------------------------------------------ #
    #  Running state                                                       #
    # ------------------------------------------------------------------ #

    def _set_running(self, running: bool) -> None:
        """Toggle UI between idle and running states."""
        self._is_running = running
        self._trim_btn.setEnabled(not running)
        self._load_video_btn.setEnabled(not running)
        self._load_project_btn.setEnabled(not running)
        self._save_project_btn.setEnabled(not running)
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
        self._save_quick_session_now()
        self._cancel_analysis_jobs()
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
            self._segment_tags_input.setText(", ".join(segment.tags))
            self._toggle_segment_btn.setText(
                "Disable Segment" if segment.enabled else "Enable Segment"
            )
        else:
            self._update_time_inputs(0.0, 0.0)
            self._segment_label_input.clear()
            self._segment_tags_input.clear()
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
        self._start_input.setText(self._format_timestamp(start))
        self._end_input.setText(self._format_timestamp(end))
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
        source_exists = bool(self._current_path) and Path(self._current_path).exists()

        self._split_btn.setEnabled(is_interactive and has_selection)
        self._toggle_segment_btn.setEnabled(is_interactive and has_selection)
        self._delete_segment_btn.setEnabled(is_interactive and has_selection)
        self._segment_label_input.setEnabled(is_interactive and has_selection)
        self._segment_tags_input.setEnabled(is_interactive and has_selection)
        self._segment_list.setEnabled(is_interactive and has_segments)
        self._start_input.setEnabled(is_interactive and has_selection)
        self._end_input.setEnabled(is_interactive and has_selection)
        self._set_start_btn.setEnabled(is_interactive and has_selection)
        self._set_end_btn.setEnabled(is_interactive and has_selection)
        self._trim_btn.setEnabled(
            is_interactive and source_exists and has_enabled
        )

    def _format_timestamp(self, seconds: float) -> str:
        seconds = max(0.0, seconds)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        if millis >= 1000:
            millis -= 1000
            secs += 1
        if secs >= 60:
            secs -= 60
            minutes += 1
        if minutes >= 60:
            minutes -= 60
            hours += 1
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def _parse_time_input(self, value: str) -> float:
        text = value.strip()
        if not text:
            raise ValueError("Time value is empty")
        if ":" not in text:
            return float(text)

        parts = text.split(":")
        if len(parts) != 3:
            raise ValueError(f"Invalid timestamp: {value}")

        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return max(0.0, hours * 3600 + minutes * 60 + seconds)

    def _schedule_autosave(self, *_args) -> None:
        if not self._config_service.get("trim.quick_session_restore", True):
            return
        self._autosave_timer.start()

    def _save_quick_session_now(self) -> None:
        if self._editor_session.has_source:
            self._quick_session_store.save(
                self._editor_session,
                export_state=self._build_export_state(),
                analysis=self._build_analysis_state(),
            )
        else:
            self._quick_session_store.clear()

    def _restore_quick_session_if_enabled(self) -> None:
        if not self._config_service.get("trim.quick_session_restore", True):
            return
        snapshot = self._quick_session_store.load()
        if not snapshot:
            return

        session = snapshot.get("session")
        if session is None or not session.source_path:
            return

        self._restore_snapshot(
            session,
            export_state=snapshot.get("export", {}),
            analysis=snapshot.get("analysis", {}),
            project_path=None,
        )
        self._diagnostics.record("info", "Restored the previous Trim session.")

    def _restore_snapshot(
        self,
        session: EditorSession,
        *,
        export_state: dict,
        analysis: dict,
        project_path: Optional[str],
    ) -> None:
        self._editor_session = session
        self._current_path = session.source_path
        self._current_project_path = project_path
        self._source_metadata = analysis.get("source_metadata", {})
        self._source_probe_payload = analysis.get("source_probe_payload", {})
        self._keyframe_times = analysis.get("keyframe_times", []) or []

        self._lossless_checkbox.setChecked(export_state.get("lossless", True))
        self._output_input.setText(export_state.get("output_target", ""))
        mode_value = export_state.get("mode", ExportMode.SEPARATE.value)
        index = self._export_mode_combo.findData(mode_value)
        self._export_mode_combo.setCurrentIndex(max(index, 0))
        self._sync_output_placeholder()
        self._refresh_editor_ui()
        self._status_label.setVisible(True)

        if session.source_path and Path(session.source_path).exists():
            if self._video_preview is not None and self._video_preview.is_available():
                self._video_preview.load_video(session.source_path)
        else:
            self._status_label.setText("Saved source file is missing. Relink by loading the source again.")
            self._diagnostics.record(
                "warning",
                "Saved source file is missing. Load the original media again to restore preview/export.",
            )

    def _build_export_state(self) -> dict:
        return {
            "mode": self._export_mode().value,
            "lossless": self._lossless_checkbox.isChecked(),
            "output_target": self._output_input.text().strip(),
        }

    def _build_analysis_state(self) -> dict:
        return {
            "source_metadata": self._source_metadata,
            "source_probe_payload": self._source_probe_payload,
            "keyframe_times": self._keyframe_times,
        }

    def _update_activity_badge(self) -> None:
        warnings = self._diagnostics.warning_count()
        if warnings:
            self._activity_drawer.set_badge_text(f"{warnings} warnings")
        else:
            self._activity_drawer.set_badge_text(
                f"{len(self._diagnostics.entries())} events"
                if self._diagnostics.entries()
                else ""
            )

    def _cancel_analysis_jobs(self) -> None:
        if self._ffprobe_worker is not None and self._ffprobe_worker.isRunning():
            self._ffprobe_worker.cancel()
        if self._keyframe_worker is not None and self._keyframe_worker.isRunning():
            self._keyframe_worker.requestInterruption()
