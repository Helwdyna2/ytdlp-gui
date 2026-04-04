"""Tests for ConvertPage."""

import os
import sys

import pytest
from PyQt6.QtCore import QObject, pyqtSignal

pytest.importorskip("PyQt6.QtWidgets")


@pytest.fixture(autouse=True)
def reset_singleton():
    from src.ui.theme.theme_engine import ThemeEngine
    ThemeEngine._instance = None
    yield
    ThemeEngine._instance = None


@pytest.fixture
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def convert_page_module():
    import src.ui.pages.convert_page as convert_page_module

    return convert_page_module


@pytest.fixture
def fake_config_service(monkeypatch, convert_page_module):
    class FakeConfigService:
        next_values = {}

        def __init__(self):
            self.values = {
                "convert.codec": "h264",
                "convert.resolution": "source",
                "convert.crf": 23,
                "convert.preset": "medium",
                "convert.output_dir": "",
                "convert.use_hardware_accel": False,
                "convert.hardware_encoder": "",
                "convert.skip_matching_output_enabled": False,
            }
            self.values.update(type(self).next_values)

        def get(self, key, default=None):
            return self.values.get(key, default)

        def set(self, key, value):
            self.values[key] = value

    monkeypatch.setattr(convert_page_module, "ConfigService", FakeConfigService)
    monkeypatch.setattr(convert_page_module, "get_cached_hardware_encoders", lambda: [])
    FakeConfigService.next_values = {}
    return FakeConfigService


@pytest.fixture
def fake_ffprobe_worker(monkeypatch, convert_page_module):
    from src.data.models import VideoMetadata

    class FakeFFprobeWorker(QObject):
        progress = pyqtSignal(int, int, str)
        error = pyqtSignal(str, str)
        completed = pyqtSignal(list)

        results_by_path = {}
        auto_complete = True
        auto_complete_queue = []
        instances = []

        def __init__(
            self,
            file_paths,
            base_folder=None,
            max_workers=None,
            trash_zero_byte_files=True,
            parent=None,
        ):
            super().__init__(parent)
            self.file_paths = list(file_paths)
            self.trash_zero_byte_files = trash_zero_byte_files
            self.cancelled = False
            type(self).instances.append(self)

        def start(self):
            should_complete = type(self).auto_complete
            if type(self).auto_complete_queue:
                should_complete = type(self).auto_complete_queue.pop(0)

            if self.cancelled or not should_complete:
                return

            results = []
            for path in self.file_paths:
                metadata = type(self).results_by_path.get(path)
                if not metadata:
                    continue

                if isinstance(metadata, str):
                    metadata = {"codec": metadata}

                results.append(
                    VideoMetadata(
                        file_path=path,
                        codec=metadata.get("codec", ""),
                        width=metadata.get("width", 0),
                        height=metadata.get("height", 0),
                    )
                )
            self.completed.emit(results)

        def cancel(self):
            self.cancelled = True

    monkeypatch.setattr(convert_page_module, "FFprobeWorker", FakeFFprobeWorker)
    FakeFFprobeWorker.results_by_path = {}
    FakeFFprobeWorker.auto_complete = True
    FakeFFprobeWorker.auto_complete_queue = []
    FakeFFprobeWorker.instances = []
    return FakeFFprobeWorker


@pytest.fixture
def fake_folder_scan_worker(monkeypatch, convert_page_module):
    class FakeFolderScanWorker(QObject):
        progress = pyqtSignal(int, str)
        completed = pyqtSignal(list)
        error = pyqtSignal(str)

        instances = []

        def __init__(self, folder, recursive=True, parent=None):
            super().__init__(parent)
            self.folder = folder
            self.recursive = recursive
            self.started = False
            type(self).instances.append(self)

        def start(self):
            self.started = True

    monkeypatch.setattr(
        convert_page_module, "FolderScanWorker", FakeFolderScanWorker
    )
    FakeFolderScanWorker.instances = []
    return FakeFolderScanWorker


@pytest.fixture
def fake_conversion_manager(monkeypatch, convert_page_module):
    class FakeConversionManager(QObject):
        job_started = pyqtSignal(int)
        job_progress = pyqtSignal(int, float, str, str)
        job_completed = pyqtSignal(int, bool, str, str)
        queue_progress = pyqtSignal(int, int, int)
        all_completed = pyqtSignal()
        job_creation_progress = pyqtSignal(int, int)
        jobs_created = pyqtSignal(list)
        files_deleted = pyqtSignal(int, list)

        instances = []

        def __init__(self):
            super().__init__()
            self.config = None
            self.added_files = None
            self.added_output_dir = None
            self.added_output_paths = None
            self.started = False
            self.cancelled = False
            self.completed_count = 0
            self.failed_count = 0
            type(self).instances.append(self)

        def set_config(self, config):
            self.config = config

        def add_files_async(self, files, output_dir, output_paths=None):
            self.added_files = list(files)
            self.added_output_dir = output_dir
            self.added_output_paths = output_paths

        def start(self):
            self.started = True

        def cancel_all(self):
            self.cancelled = True

        def reset_counts(self):
            self.completed_count = 0
            self.failed_count = 0

    monkeypatch.setattr(convert_page_module, "ConversionManager", FakeConversionManager)
    FakeConversionManager.instances = []
    return FakeConversionManager


def _hardware_encoder(name, h264=True, hevc=True, display_name=None):
    from src.utils.hardware_accel import HardwareEncoder

    return HardwareEncoder(
        name=name,
        display_name=display_name or name.upper(),
        h264_encoder=f"h264_{name}",
        hevc_encoder=f"hevc_{name}",
        h264_available=h264,
        hevc_available=hevc,
    )


def _combo_items(combo):
    return [combo.itemText(i) for i in range(combo.count())]


def test_convert_page_creates(qapp, fake_config_service, fake_ffprobe_worker):
    from src.ui.pages.convert_page import ConvertPage
    page = ConvertPage()
    assert page is not None


def test_convert_page_header_copy(qapp, fake_config_service, fake_ffprobe_worker):
    from src.ui.pages.convert_page import ConvertPage
    page = ConvertPage()
    header = page.findChild(type(page._file_list).mro()[0].__class__)
    # Check via PageHeader
    from src.ui.components.page_header import PageHeader
    headers = page.findChildren(PageHeader)
    assert len(headers) == 1
    assert headers[0].title_label.text() == "Convert"


def test_convert_page_uses_split_layout(qapp, fake_config_service, fake_ffprobe_worker):
    from src.ui.pages.convert_page import ConvertPage
    from src.ui.components.split_layout import SplitLayout
    page = ConvertPage()
    splits = page.findChildren(SplitLayout)
    assert len(splits) == 1, "Convert page should use SplitLayout"


def test_convert_page_quality_label_and_crf_tooltip(
    qapp, fake_config_service, fake_ffprobe_worker
):
    from src.ui.pages.convert_page import ConvertPage
    from PyQt6.QtWidgets import QLabel
    page = ConvertPage()
    labels = [lbl for lbl in page.findChildren(QLabel) if lbl.text() == "Quality"]
    assert len(labels) >= 1, "Should have a 'Quality' label"
    assert "CRF" in page._crf_slider.toolTip()


def test_convert_page_progress_in_left_panel(
    qapp, fake_config_service, fake_ffprobe_worker
):
    from src.ui.pages.convert_page import ConvertPage
    from src.ui.components.split_layout import SplitLayout
    from PyQt6.QtWidgets import QProgressBar
    page = ConvertPage()
    # Progress bar should exist inside the left panel of the SplitLayout
    progress = page._overall_progress
    assert isinstance(progress, QProgressBar)
    splits = page.findChildren(SplitLayout)
    assert len(splits) == 1
    # Progress is now inside the left panel of the split layout (bento style)
    assert splits[0].isAncestorOf(progress), \
        "Progress bar should be inside the split layout left panel"


def test_convert_page_one_primary_action(
    qapp, fake_config_service, fake_ffprobe_worker
):
    from src.ui.pages.convert_page import ConvertPage
    from PyQt6.QtWidgets import QPushButton
    page = ConvertPage()
    ctas = [
        btn for btn in page.findChildren(QPushButton)
        if btn.property("button_role") == "cta"
    ]
    assert len(ctas) == 1, f"Expected 1 CTA button, found {len(ctas)}"
    assert ctas[0].text() == "START CONVERT"


def test_convert_page_start_btn_role(qapp, fake_config_service, fake_ffprobe_worker):
    from src.ui.pages.convert_page import ConvertPage
    page = ConvertPage()
    assert page._start_btn.property("button_role") == "cta"


def test_convert_page_cancel_btn_role(qapp, fake_config_service, fake_ffprobe_worker):
    from src.ui.pages.convert_page import ConvertPage
    page = ConvertPage()
    assert page._cancel_btn.property("button_role") == "secondary"


def test_convert_page_hw_combo_shows_only_compatible_options(
    qapp, monkeypatch, fake_config_service, fake_ffprobe_worker, convert_page_module
):
    from src.ui.pages.convert_page import ConvertPage

    monkeypatch.setattr(
        convert_page_module,
        "get_cached_hardware_encoders",
        lambda: [_hardware_encoder("videotoolbox", display_name="Apple VideoToolbox")],
    )

    page = ConvertPage()

    assert _combo_items(page._hw_combo) == ["None", "VideoToolbox"]
    assert "NVENC" not in _combo_items(page._hw_combo)
    assert "VAAPI" not in _combo_items(page._hw_combo)


def test_convert_page_hw_combo_refreshes_per_output_codec(
    qapp, monkeypatch, fake_config_service, fake_ffprobe_worker, convert_page_module
):
    from src.ui.pages.convert_page import ConvertPage

    monkeypatch.setattr(
        convert_page_module,
        "get_cached_hardware_encoders",
        lambda: [
            _hardware_encoder("videotoolbox", h264=True, hevc=False),
            _hardware_encoder("qsv", h264=False, hevc=True),
        ],
    )

    page = ConvertPage()
    assert _combo_items(page._hw_combo) == ["None", "VideoToolbox"]

    page._codec_combo.setCurrentIndex(1)
    assert _combo_items(page._hw_combo) == ["None", "Intel Quick Sync"]


def test_convert_page_hw_combo_disabled_for_unsupported_target(
    qapp, monkeypatch, fake_config_service, fake_ffprobe_worker, convert_page_module
):
    from src.ui.pages.convert_page import ConvertPage

    monkeypatch.setattr(
        convert_page_module,
        "get_cached_hardware_encoders",
        lambda: [_hardware_encoder("videotoolbox")],
    )

    page = ConvertPage()
    page._codec_combo.setCurrentIndex(2)

    assert _combo_items(page._hw_combo) == ["Not available for this format"]
    assert not page._hw_combo.isEnabled()
    assert page._source_codec_filter_check.isEnabled()
    assert "only available for H.264 and H.265" in page._hw_status_label.text()


def test_convert_page_hw_combo_explains_missing_hardware_detection(
    qapp, monkeypatch, fake_config_service, fake_ffprobe_worker, convert_page_module
):
    from src.ui.pages.convert_page import ConvertPage

    monkeypatch.setattr(convert_page_module, "get_cached_hardware_encoders", lambda: [])
    monkeypatch.setattr(
        convert_page_module,
        "get_hardware_detection_message",
        lambda codec: "FFmpeg found hardware encoders, but validation failed on this system.",
    )

    page = ConvertPage()

    assert _combo_items(page._hw_combo) == ["No hardware acceleration detected"]
    assert not page._hw_combo.isEnabled()
    assert "validation failed" in page._hw_status_label.text()
    assert page._hw_combo.toolTip() == page._hw_status_label.text()


def test_convert_page_ignores_saved_unsupported_hw_selection(
    qapp, monkeypatch, fake_config_service, fake_ffprobe_worker, convert_page_module
):
    from src.ui.pages.convert_page import ConvertPage

    fake_config_service.next_values = {
        "convert.use_hardware_accel": True,
        "convert.hardware_encoder": "nvenc",
    }
    monkeypatch.setattr(
        convert_page_module,
        "get_cached_hardware_encoders",
        lambda: [_hardware_encoder("videotoolbox")],
    )

    page = ConvertPage()

    assert page._hw_combo.currentData() == "videotoolbox"
    assert _combo_items(page._hw_combo) == ["None", "VideoToolbox"]


def test_convert_page_starts_disabled_until_preflight_completes(
    qapp, monkeypatch, fake_config_service, fake_ffprobe_worker, convert_page_module
):
    from src.ui.pages.convert_page import ConvertPage

    monkeypatch.setattr(convert_page_module, "get_cached_hardware_encoders", lambda: [])
    fake_ffprobe_worker.auto_complete = False
    fake_ffprobe_worker.results_by_path = {
        "/tmp/a.mp4": "h264",
    }

    page = ConvertPage()
    page._file_list._add_paths(["/tmp/a.mp4"])

    assert page._start_btn.isEnabled() is False

    worker = fake_ffprobe_worker.instances[-1]
    fake_ffprobe_worker.auto_complete = True
    worker.start()
    qapp.processEvents()

    assert page._start_btn.isEnabled() is True


def test_file_list_widget_emits_loading_state_when_folder_scan_starts(
    qapp,
    monkeypatch,
    fake_config_service,
    fake_ffprobe_worker,
    fake_folder_scan_worker,
    convert_page_module,
):
    from src.ui.pages.convert_page import FileListWidget

    states = []

    monkeypatch.setattr(
        convert_page_module.QFileDialog,
        "getExistingDirectory",
        lambda *args, **kwargs: "/tmp/library",
    )
    monkeypatch.setattr(
        convert_page_module, "update_dialog_last_dir", lambda *args, **kwargs: None
    )

    widget = FileListWidget()
    widget.loading_state_changed.connect(states.append)

    widget._on_add_folder()
    qapp.processEvents()

    assert states == [True]
    assert fake_folder_scan_worker.instances[-1].started is True


def test_convert_page_filter_off_queues_all_files(
    qapp,
    monkeypatch,
    fake_config_service,
    fake_ffprobe_worker,
    fake_conversion_manager,
    convert_page_module,
):
    from src.ui.pages.convert_page import ConvertPage

    monkeypatch.setattr(convert_page_module, "get_cached_hardware_encoders", lambda: [])
    fake_ffprobe_worker.results_by_path = {
        "/tmp/a.mp4": "h264",
        "/tmp/b.webm": "vp9",
    }

    page = ConvertPage()
    page._file_list._add_paths(list(fake_ffprobe_worker.results_by_path.keys()))
    qapp.processEvents()
    page._on_start()

    manager = fake_conversion_manager.instances[-1]
    assert manager.added_files == ["/tmp/a.mp4", "/tmp/b.webm"]


def test_convert_page_skip_status_refreshes_for_toggle_and_resolution(
    qapp, monkeypatch, fake_config_service, fake_ffprobe_worker, convert_page_module
):
    from src.ui.pages.convert_page import ConvertPage

    monkeypatch.setattr(convert_page_module, "get_cached_hardware_encoders", lambda: [])
    fake_ffprobe_worker.results_by_path = {
        "/tmp/a.mp4": {"codec": "h264", "width": 1920, "height": 1080},
    }

    page = ConvertPage()
    page._file_list._add_paths(["/tmp/a.mp4"])
    qapp.processEvents()

    assert page._preflight_status_label.text() == "Ready to convert 1 file(s)."

    page._source_codec_filter_check.setChecked(True)
    qapp.processEvents()

    assert "will be skipped" in page._preflight_status_label.text()

    resolution_index = page._resolution_combo.findText("1280x720")
    page._resolution_combo.setCurrentIndex(resolution_index)
    qapp.processEvents()

    assert page._preflight_status_label.text() == "Ready to convert 1 file(s)."


def test_convert_page_skip_matching_output_queues_only_non_matching_files(
    qapp,
    monkeypatch,
    fake_config_service,
    fake_ffprobe_worker,
    fake_conversion_manager,
    convert_page_module,
):
    from src.ui.pages.convert_page import ConvertPage

    messages = []

    monkeypatch.setattr(convert_page_module, "get_cached_hardware_encoders", lambda: [])
    monkeypatch.setattr(
        convert_page_module.QMessageBox,
        "information",
        lambda *args: messages.append(args[2]),
    )
    fake_ffprobe_worker.results_by_path = {
        "/tmp/a.mp4": "h264",
        "/tmp/b.webm": "vp9",
    }

    page = ConvertPage()
    page._file_list._add_paths(list(fake_ffprobe_worker.results_by_path.keys()))
    qapp.processEvents()
    page._source_codec_filter_check.setChecked(True)

    page._on_start()

    manager = fake_conversion_manager.instances[-1]
    assert manager.added_files == ["/tmp/b.webm"]
    assert any("Skipping 1 file(s)" in message for message in messages)


def test_convert_page_skip_matching_output_with_all_matches_shows_message(
    qapp,
    monkeypatch,
    fake_config_service,
    fake_ffprobe_worker,
    fake_conversion_manager,
    convert_page_module,
):
    from src.ui.pages.convert_page import ConvertPage

    messages = []

    monkeypatch.setattr(convert_page_module, "get_cached_hardware_encoders", lambda: [])
    monkeypatch.setattr(
        convert_page_module.QMessageBox,
        "information",
        lambda *args: messages.append((args[1], args[2])),
    )
    fake_ffprobe_worker.results_by_path = {
        "/tmp/a.mp4": "h264",
    }

    page = ConvertPage()
    page._file_list._add_paths(["/tmp/a.mp4"])
    qapp.processEvents()
    page._source_codec_filter_check.setChecked(True)

    page._on_start()

    assert fake_conversion_manager.instances == []
    assert (
        "Nothing To Convert",
        'All selected files already match "mp4 / H.264".',
    ) in messages


def test_convert_page_file_changes_restart_codec_scan(
    qapp, monkeypatch, fake_config_service, fake_ffprobe_worker, convert_page_module
):
    from src.ui.pages.convert_page import ConvertPage

    monkeypatch.setattr(convert_page_module, "get_cached_hardware_encoders", lambda: [])
    fake_ffprobe_worker.results_by_path = {
        "/tmp/a.mp4": "h264",
        "/tmp/b.webm": "vp9",
    }
    fake_ffprobe_worker.auto_complete_queue = [False, True]

    page = ConvertPage()
    page._file_list._add_paths(["/tmp/a.mp4"])
    qapp.processEvents()
    first_worker = fake_ffprobe_worker.instances[-1]

    page._file_list._add_paths(["/tmp/b.webm"])
    qapp.processEvents()

    assert first_worker.cancelled is True
    assert page._start_btn.isEnabled() is True


def test_convert_page_build_config_respects_hw_selection(
    qapp, monkeypatch, fake_config_service, fake_ffprobe_worker, convert_page_module
):
    from src.ui.pages.convert_page import ConvertPage

    monkeypatch.setattr(
        convert_page_module,
        "get_cached_hardware_encoders",
        lambda: [_hardware_encoder("videotoolbox")],
    )

    page = ConvertPage()
    page._hw_combo.setCurrentIndex(1)
    config = page._build_config()

    assert config.output_codec == "h264"
    assert config.use_hardware_accel is True
    assert config.hardware_encoder == "videotoolbox"


def test_convert_page_resolution_defaults_to_horizontal_presets(
    qapp, fake_config_service, fake_ffprobe_worker
):
    from src.ui.pages.convert_page import ConvertPage

    page = ConvertPage()

    assert page._resolution_combo.itemText(0) == "Same as source"
    assert page._resolution_combo.itemText(1) == "3840x2160"
    assert page._resolution_combo.itemText(4) == "1280x720"
    assert page._resolution_combo.itemText(6) == "2160x3840 (Vertical override)"


def test_convert_page_resolution_switches_to_vertical_when_source_is_vertical(
    qapp, fake_config_service, fake_ffprobe_worker
):
    from src.ui.pages.convert_page import ConvertPage

    fake_ffprobe_worker.results_by_path = {
        "/tmp/clip.mp4": {"codec": "h264", "width": 1080, "height": 1920},
    }

    page = ConvertPage()
    page._file_list._add_paths(["/tmp/clip.mp4"])
    qapp.processEvents()

    assert page._resolution_combo.itemText(1) == "2160x3840"
    assert page._resolution_combo.itemText(4) == "720x1280"
    assert page._resolution_combo.itemText(6) == "3840x2160 (Horizontal override)"


def test_convert_page_build_config_uses_selected_output_resolution(
    qapp, fake_config_service, fake_ffprobe_worker
):
    from src.ui.pages.convert_page import ConvertPage

    page = ConvertPage()
    index = page._resolution_combo.findText("1920x1080")
    page._resolution_combo.setCurrentIndex(index)

    config = page._build_config()

    assert config.output_resolution == "1920x1080"


def test_convert_page_shows_preview_tree_for_nested_folder_inputs(
    qapp, fake_config_service, fake_ffprobe_worker
):
    from src.ui.pages.convert_page import ConvertPage

    page = ConvertPage()
    page._file_list._add_paths(
        [
            "/tmp/library/Action/movie1.mp4",
            "/tmp/library/Drama/movie2.mp4",
            "/tmp/library/Drama/Sub/movie3.mp4",
        ],
        source_root="/tmp/library",
    )

    top_labels = [
        page._preview_tree.topLevelItem(i).text(0)
        for i in range(page._preview_tree.topLevelItemCount())
    ]

    assert "📁 Action" in top_labels
    assert "📁 Drama" in top_labels


def test_convert_page_folder_entries_keep_relative_labels(
    qapp, fake_config_service, fake_ffprobe_worker
):
    from src.ui.pages.convert_page import ConvertPage

    page = ConvertPage()
    page._file_list._add_paths(
        ["/tmp/library/Drama/Sub/movie3.mp4"], source_root="/tmp/library"
    )

    assert page._file_list._list_widget.item(0).text() == "Drama/Sub/movie3.mp4"


def test_convert_page_passes_nested_output_paths_for_folder_sources(
    qapp,
    monkeypatch,
    fake_config_service,
    fake_ffprobe_worker,
    fake_conversion_manager,
    convert_page_module,
):
    from src.ui.pages.convert_page import ConvertPage

    monkeypatch.setattr(convert_page_module, "get_cached_hardware_encoders", lambda: [])

    page = ConvertPage()
    page._file_list._add_paths(
        [
            "/tmp/library/Action/movie1.mp4",
            "/tmp/library/Drama/Sub/movie2.mp4",
        ],
        source_root="/tmp/library",
    )
    page._output_input.setText("/tmp/output")
    qapp.processEvents()

    page._on_start()

    manager = fake_conversion_manager.instances[-1]
    assert manager.added_output_paths == {
        "/tmp/library/Action/movie1.mp4": os.path.normpath(
            "/tmp/output/Action/movie1_converted.mp4"
        ),
        "/tmp/library/Drama/Sub/movie2.mp4": os.path.normpath(
            "/tmp/output/Drama/Sub/movie2_converted.mp4"
        ),
    }


def test_convert_page_preview_updates_output_extension(
    qapp, fake_config_service, fake_ffprobe_worker
):
    from src.ui.pages.convert_page import ConvertPage

    page = ConvertPage()
    page._file_list._add_paths(["/tmp/input.mp4"])
    qapp.processEvents()
    page._codec_combo.setCurrentIndex(page._codec_combo.findData("vp9"))

    root_item = page._preview_tree.invisibleRootItem()
    child_item = root_item.child(0) if root_item.childCount() else None

    assert child_item is not None
    assert child_item.text(0).endswith("input_converted.webm")


def test_convert_page_queue_status_text_updates_for_completed_job(
    qapp,
    monkeypatch,
    fake_config_service,
    fake_ffprobe_worker,
    fake_conversion_manager,
    convert_page_module,
):
    from src.data.models import ConversionJob
    from src.ui.pages.convert_page import ConvertPage

    monkeypatch.setattr(convert_page_module, "get_cached_hardware_encoders", lambda: [])

    page = ConvertPage()
    page._file_list._add_paths(["/tmp/a.mp4"])
    qapp.processEvents()

    assert page._queue_widget.status_text_for("/tmp/a.mp4") == "Pending"
    assert page._queue_widget.is_item_completed("/tmp/a.mp4") is False

    page._on_jobs_created(
        [
            ConversionJob(
                id=7,
                input_path="/tmp/a.mp4",
                output_path="/tmp/a_converted.mp4",
            )
        ]
    )
    page._on_job_started(7)
    page._on_job_completed(7, True, "/tmp/a_converted.mp4", "")

    assert page._queue_widget.status_text_for("/tmp/a.mp4") == "Complete"
    assert page._queue_widget.is_item_completed("/tmp/a.mp4") is True


def test_convert_page_prioritize_moves_item_to_front_of_queue(
    qapp,
    monkeypatch,
    fake_config_service,
    fake_ffprobe_worker,
    fake_conversion_manager,
    convert_page_module,
):
    from src.ui.pages.convert_page import ConvertPage

    monkeypatch.setattr(convert_page_module, "get_cached_hardware_encoders", lambda: [])

    paths = ["/tmp/a.mp4", "/tmp/b.mp4", "/tmp/c.mp4"]
    page = ConvertPage()
    page._file_list._add_paths(paths)
    qapp.processEvents()

    page._on_queue_prioritize_requested("/tmp/c.mp4")

    assert [item.input_path for item in page._queue_items] == [
        "/tmp/c.mp4",
        "/tmp/a.mp4",
        "/tmp/b.mp4",
    ]

    page._on_start()

    manager = fake_conversion_manager.instances[-1]
    assert manager.added_files == ["/tmp/c.mp4", "/tmp/a.mp4", "/tmp/b.mp4"]


def test_convert_page_skip_can_be_toggled_back_to_pending(
    qapp,
    monkeypatch,
    fake_config_service,
    fake_ffprobe_worker,
    convert_page_module,
):
    from src.core.convert_saved_task import ConvertQueueItemStatus
    from src.ui.pages.convert_page import ConvertPage

    monkeypatch.setattr(convert_page_module, "get_cached_hardware_encoders", lambda: [])

    page = ConvertPage()
    page._file_list._add_paths(["/tmp/a.mp4"])
    qapp.processEvents()

    page._on_queue_skip_requested("/tmp/a.mp4")
    assert page._queue_items[0].status is ConvertQueueItemStatus.SKIPPED
    assert page._start_btn.isEnabled() is False

    page._on_queue_skip_requested("/tmp/a.mp4")
    assert page._queue_items[0].status is ConvertQueueItemStatus.PENDING
    assert page._queue_widget.status_text_for("/tmp/a.mp4") == "Pending"
    assert page._start_btn.isEnabled() is True


def test_convert_page_cancel_marks_unstarted_rows_incomplete(
    qapp,
    monkeypatch,
    fake_config_service,
    fake_ffprobe_worker,
    fake_conversion_manager,
    convert_page_module,
):
    from src.data.models import ConversionJob
    from src.ui.pages.convert_page import ConvertPage
    from PyQt6.QtWidgets import QMessageBox

    monkeypatch.setattr(convert_page_module, "get_cached_hardware_encoders", lambda: [])
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *args, **kwargs: 0))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *args, **kwargs: 0))

    page = ConvertPage()
    page._file_list._add_paths(["/tmp/a.mp4", "/tmp/b.mp4"])
    qapp.processEvents()

    page._on_start()
    page._on_jobs_created(
        [
            ConversionJob(id=1, input_path="/tmp/a.mp4", output_path="/tmp/a_out.mp4"),
            ConversionJob(id=2, input_path="/tmp/b.mp4", output_path="/tmp/b_out.mp4"),
        ]
    )
    page._on_job_started(1)

    page._on_cancel()
    page._on_job_completed(1, False, "/tmp/a_out.mp4", "Cancelled by user")
    page._on_all_completed()

    assert page._queue_widget.status_text_for("/tmp/a.mp4") == "Cancelled by user"
    assert page._queue_widget.status_text_for("/tmp/b.mp4") == "Cancelled before start"


def test_convert_page_pause_marks_active_and_pending_rows_incomplete(
    qapp,
    monkeypatch,
    fake_config_service,
    fake_ffprobe_worker,
    fake_conversion_manager,
    convert_page_module,
):
    from src.data.models import ConversionJob
    from src.ui.pages.convert_page import ConvertPage

    monkeypatch.setattr(convert_page_module, "get_cached_hardware_encoders", lambda: [])

    page = ConvertPage()
    page._file_list._add_paths(["/tmp/a.mp4", "/tmp/b.mp4"])
    qapp.processEvents()

    page._on_start()
    page._on_jobs_created(
        [
            ConversionJob(id=1, input_path="/tmp/a.mp4", output_path="/tmp/a_out.mp4"),
            ConversionJob(id=2, input_path="/tmp/b.mp4", output_path="/tmp/b_out.mp4"),
        ]
    )
    page._on_job_started(1)
    page._on_job_progress(1, 47.0, "1x", "00:03")

    snapshot = page.pause_for_saved_task()

    manager = fake_conversion_manager.instances[-1]
    assert manager.cancelled is True
    assert snapshot["config"]["output_codec"] == "h264"
    assert [item["status"] for item in snapshot["items"]] == [
        "incomplete",
        "incomplete",
    ]
    assert snapshot["items"][0]["progress_percent"] == 0.0
    assert snapshot["items"][0]["detail"] == "Restart from beginning"
    assert snapshot["items"][1]["detail"] == "Paused before start"
    assert page._queue_widget.status_text_for("/tmp/a.mp4") == "Restart from beginning"
    assert page._queue_widget.status_text_for("/tmp/b.mp4") == "Paused before start"


def test_convert_page_restore_resumes_only_unfinished_items_in_queue_order(
    qapp,
    monkeypatch,
    fake_config_service,
    fake_ffprobe_worker,
    fake_conversion_manager,
    convert_page_module,
):
    from src.ui.pages.convert_page import ConvertPage

    monkeypatch.setattr(convert_page_module, "get_cached_hardware_encoders", lambda: [])

    page = ConvertPage()
    page.restore_saved_task(
        payload={
            "items": [
                {
                    "item_id": "done",
                    "input_path": "/tmp/done.mp4",
                    "output_path": "/tmp/out/done.mp4",
                    "display_name": "done.mp4",
                    "status": "completed",
                    "progress_percent": 100.0,
                    "detail": "Complete",
                },
                {
                    "item_id": "retry",
                    "input_path": "/tmp/retry.mp4",
                    "output_path": "/tmp/out/retry.mp4",
                    "display_name": "retry.mp4",
                    "status": "incomplete",
                    "progress_percent": 62.0,
                    "detail": "Cancelled",
                },
                {
                    "item_id": "pending",
                    "input_path": "/tmp/pending.mp4",
                    "output_path": "/tmp/out/pending.mp4",
                    "display_name": "pending.mp4",
                    "status": "pending",
                    "progress_percent": 0.0,
                    "detail": "Pending",
                },
            ]
        },
        config_payload={
            "output_codec": "h264",
            "output_dir": "/tmp/out",
            "crf_value": 23,
            "preset": "medium",
            "use_hardware_accel": False,
            "hardware_encoder": None,
        },
    )
    qapp.processEvents()

    assert [item.input_path for item in page._queue_items] == [
        "/tmp/done.mp4",
        "/tmp/retry.mp4",
        "/tmp/pending.mp4",
    ]
    assert page._queue_widget.status_text_for("/tmp/done.mp4") == "Complete"
    assert page._queue_widget.status_text_for("/tmp/retry.mp4") == "Restart from beginning"
    assert page._queue_widget.status_text_for("/tmp/pending.mp4") == "Pending"

    page._on_start()

    manager = fake_conversion_manager.instances[-1]
    assert manager.added_files == ["/tmp/retry.mp4", "/tmp/pending.mp4"]
    assert manager.added_output_paths == {
        "/tmp/retry.mp4": "/tmp/out/retry.mp4",
        "/tmp/pending.mp4": "/tmp/out/pending.mp4",
    }


def test_convert_page_restore_does_not_resume_failed_rows(
    qapp,
    monkeypatch,
    fake_config_service,
    fake_ffprobe_worker,
    fake_conversion_manager,
    convert_page_module,
):
    from src.ui.pages.convert_page import ConvertPage

    monkeypatch.setattr(convert_page_module, "get_cached_hardware_encoders", lambda: [])

    page = ConvertPage()
    page.restore_saved_task(
        payload={
            "items": [
                {
                    "item_id": "failed",
                    "input_path": "/tmp/failed.mp4",
                    "output_path": "/tmp/out/failed.mp4",
                    "display_name": "failed.mp4",
                    "status": "failed",
                    "detail": "Encoder error",
                    "error_message": "Encoder error",
                },
                {
                    "item_id": "retry",
                    "input_path": "/tmp/retry.mp4",
                    "output_path": "/tmp/out/retry.mp4",
                    "display_name": "retry.mp4",
                    "status": "incomplete",
                    "detail": "Cancelled",
                },
            ]
        },
        config_payload={
            "output_codec": "h264",
            "output_dir": "/tmp/out",
        },
    )
    qapp.processEvents()

    page._on_start()

    manager = fake_conversion_manager.instances[-1]
    assert manager.added_files == ["/tmp/retry.mp4"]
