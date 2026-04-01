"""Tests for ConvertPage."""
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


def test_convert_page_creates(qapp):
    from src.ui.pages.convert_page import ConvertPage
    page = ConvertPage()
    assert page is not None


def test_convert_page_header_copy(qapp):
    from src.ui.pages.convert_page import ConvertPage
    page = ConvertPage()
    header = page.findChild(type(page._file_list).mro()[0].__class__)
    # Check via PageHeader
    from src.ui.components.page_header import PageHeader
    headers = page.findChildren(PageHeader)
    assert len(headers) == 1
    assert headers[0].title_label.text() == "Convert"


def test_convert_page_uses_split_layout(qapp):
    from src.ui.pages.convert_page import ConvertPage
    from src.ui.components.split_layout import SplitLayout
    page = ConvertPage()
    splits = page.findChildren(SplitLayout)
    assert len(splits) == 1, "Convert page should use SplitLayout"


def test_convert_page_quality_label_and_crf_tooltip(qapp):
    from src.ui.pages.convert_page import ConvertPage
    from PyQt6.QtWidgets import QLabel
    page = ConvertPage()
    labels = [lbl for lbl in page.findChildren(QLabel) if lbl.text() == "Quality"]
    assert len(labels) >= 1, "Should have a 'Quality' label"
    assert "CRF" in page._crf_slider.toolTip()


def test_convert_page_progress_in_left_panel(qapp):
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


def test_convert_page_one_primary_action(qapp):
    from src.ui.pages.convert_page import ConvertPage
    from PyQt6.QtWidgets import QPushButton
    page = ConvertPage()
    ctas = [
        btn for btn in page.findChildren(QPushButton)
        if btn.property("button_role") == "cta"
    ]
    assert len(ctas) == 1, f"Expected 1 CTA button, found {len(ctas)}"
    assert ctas[0].text() == "START CONVERT"


def test_convert_page_start_btn_role(qapp):
    from src.ui.pages.convert_page import ConvertPage
    page = ConvertPage()
    assert page._start_btn.property("button_role") == "cta"


def test_convert_page_cancel_btn_role(qapp):
    from src.ui.pages.convert_page import ConvertPage
    page = ConvertPage()
    assert page._cancel_btn.property("button_role") == "secondary"
