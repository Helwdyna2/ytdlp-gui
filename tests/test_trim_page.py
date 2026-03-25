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
    primaries = [
        btn for btn in page.findChildren(QPushButton)
        if btn.property("button_role") == "primary"
    ]
    assert len(primaries) == 1, f"Expected 1 primary button, found {len(primaries)}"
    assert primaries[0].text() == "Trim Video"


def test_trim_page_trim_btn_role(qapp):
    from src.ui.pages.trim_page import TrimPage
    page = TrimPage()
    assert page._trim_btn.property("button_role") == "primary"


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
