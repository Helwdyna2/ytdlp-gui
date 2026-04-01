"""Tests for ConvertPage."""

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
                "convert.crf": 23,
                "convert.preset": "medium",
                "convert.output_dir": "",
                "convert.use_hardware_accel": False,
                "convert.hardware_encoder": "",
                "convert.source_codec_filter_enabled": False,
                "convert.source_codec_filter": "",
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
                codec = type(self).results_by_path.get(path)
                if codec:
                    results.append(VideoMetadata(file_path=path, codec=codec))
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
            type(self).instances.append(self)

        def set_config(self, config):
            self.config = config

        def add_files_async(self, files, output_dir):
            self.added_files = list(files)
            self.added_output_dir = output_dir

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

    assert _combo_items(page._hw_combo) == ["None"]
    assert not page._hw_combo.isEnabled()
    assert not page._source_codec_filter_check.isEnabled()


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


def test_convert_page_populates_unique_source_codecs(
    qapp, monkeypatch, fake_config_service, fake_ffprobe_worker, convert_page_module
):
    from src.ui.pages.convert_page import ConvertPage

    monkeypatch.setattr(convert_page_module, "get_cached_hardware_encoders", lambda: [])
    fake_ffprobe_worker.results_by_path = {
        "/tmp/a.mp4": "h264",
        "/tmp/b.webm": "vp9",
        "/tmp/c.mp4": "h264",
    }

    page = ConvertPage()
    page._file_list._add_paths(list(fake_ffprobe_worker.results_by_path.keys()))
    qapp.processEvents()

    assert _combo_items(page._source_codec_combo) == ["H.264", "VP9"]


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


def test_convert_page_filter_on_queues_only_matching_files(
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
    page._source_codec_combo.setCurrentIndex(page._source_codec_combo.findData("vp9"))

    page._on_start()

    manager = fake_conversion_manager.instances[-1]
    assert manager.added_files == ["/tmp/b.webm"]
    assert any("Skipping 1 file(s)" in message for message in messages)


def test_convert_page_filter_on_with_no_matches_shows_message(
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
    page._source_codec_combo.setCurrentIndex(0)
    page._source_codec_combo.setItemData(0, "vp9")
    page._source_codec_combo.setItemText(0, "VP9")

    page._on_start()

    assert fake_conversion_manager.instances == []
    assert ("No Matching Files", 'No files match the selected source codec "VP9".') in messages


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
    assert _combo_items(page._source_codec_combo) == ["H.264", "VP9"]


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
