"""Tests for TrimPage."""
import pytest
import sys

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


def test_trim_page_creates(qapp):
    from src.ui.pages.trim_page import TrimPage
    page = TrimPage()
    assert page is not None


def test_trim_page_header_copy(qapp):
    from src.ui.pages.trim_page import TrimPage
    from src.ui.components.page_header import PageHeader
    page = TrimPage()
    headers = page.findChildren(PageHeader)
    assert len(headers) == 1
    assert headers[0].title_label.text() == "Trim"


def test_trim_page_lossless_label(qapp):
    from src.ui.pages.trim_page import TrimPage
    page = TrimPage()
    text = page._lossless_checkbox.text()
    assert "keyframe" in text.lower(), f"Expected keyframe info, got: {text}"
    assert page._lossless_checkbox.toolTip() != ""


def test_trim_page_one_primary_action(qapp):
    from src.ui.pages.trim_page import TrimPage
    from PyQt6.QtWidgets import QPushButton
    page = TrimPage()
    ctas = [
        btn for btn in page.findChildren(QPushButton)
        if btn.property("button_role") == "cta"
    ]
    assert len(ctas) == 1, f"Expected 1 CTA button, found {len(ctas)}"
    assert ctas[0].text() == "TRIM VIDEO"


def test_trim_page_trim_btn_role(qapp):
    from src.ui.pages.trim_page import TrimPage
    page = TrimPage()
    assert page._trim_btn.property("button_role") == "cta"


def test_trim_page_cancel_btn_role(qapp):
    from src.ui.pages.trim_page import TrimPage
    page = TrimPage()
    assert page._cancel_btn.property("button_role") == "secondary"


def test_trim_page_preview_and_timeline_instantiate(qapp):
    from src.ui.pages.trim_page import TrimPage
    page = TrimPage()
    # Preview and timeline containers should exist (placeholders when not injected)
    assert page._preview_container is not None
    assert page._timeline_container is not None


def test_trim_page_output_section_exists(qapp):
    from src.ui.pages.trim_page import TrimPage
    page = TrimPage()
    assert page._output_input is not None
    assert page._output_browse_btn is not None


def test_trim_page_progress_section_exists(qapp):
    from src.ui.pages.trim_page import TrimPage
    from PyQt6.QtWidgets import QProgressBar
    page = TrimPage()
    assert isinstance(page._progress_bar, QProgressBar)


def test_trim_page_cleanup_waits_for_analysis_workers(qapp, monkeypatch):
    from src.ui.pages.trim_page import TrimPage

    class _FakePreview:
        def __init__(self):
            self.cleanup_calls = 0

        def cleanup(self):
            self.cleanup_calls += 1

    class _FakeWorker:
        def __init__(self, running=True):
            self.running = running
            self.cancel_calls = 0
            self.interruption_calls = 0
            self.wait_calls = []
            self.delete_later_calls = 0

        def isRunning(self):
            return self.running

        def cancel(self):
            self.cancel_calls += 1

        def requestInterruption(self):
            self.interruption_calls += 1
            self.running = False

        def wait(self, timeout):
            self.wait_calls.append(timeout)
            self.running = False
            return True

        def deleteLater(self):
            self.delete_later_calls += 1

    page = TrimPage()
    preview = _FakePreview()
    ffprobe_worker = _FakeWorker()
    keyframe_worker = _FakeWorker()

    page._video_preview = preview
    page._ffprobe_worker = ffprobe_worker
    page._keyframe_worker = keyframe_worker
    monkeypatch.setattr(page, "_save_quick_session_now", lambda: None)

    page.cleanup()

    assert preview.cleanup_calls == 1
    assert ffprobe_worker.cancel_calls == 1
    assert ffprobe_worker.wait_calls == [5000]
    assert ffprobe_worker.delete_later_calls == 1
    assert keyframe_worker.interruption_calls == 1
    assert keyframe_worker.wait_calls == [5000]
    assert keyframe_worker.delete_later_calls == 1
    assert page._ffprobe_worker is None
    assert page._keyframe_worker is None
