"""Tests for MatchPage."""
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


def test_match_page_creates(qapp):
    from src.ui.pages.match_page import MatchPage
    page = MatchPage()
    assert page is not None


def test_match_page_uses_split_layout(qapp):
    from src.ui.pages.match_page import MatchPage
    from src.ui.components.split_layout import SplitLayout
    page = MatchPage()
    splits = page.findChildren(SplitLayout)
    assert len(splits) == 1


def test_match_page_exclusion_copy(qapp):
    from src.ui.pages.match_page import MatchPage
    page = MatchPage()
    text = page.skip_keywords_button.text()
    assert "Exclude terms" in text, f"Expected 'Exclude terms…', got: {text}"


def test_match_page_scan_is_secondary(qapp):
    from src.ui.pages.match_page import MatchPage
    page = MatchPage()
    assert page.scan_button.property("button_role") == "secondary", \
        "Scan Folder should be secondary"


def test_match_page_start_matching_is_primary(qapp):
    from src.ui.pages.match_page import MatchPage
    page = MatchPage()
    assert page.match_button.property("button_role") == "primary"


def test_match_page_one_primary_action(qapp):
    from src.ui.pages.match_page import MatchPage
    from PyQt6.QtWidgets import QPushButton
    page = MatchPage()
    primaries = [
        btn for btn in page.findChildren(QPushButton)
        if btn.property("button_role") == "primary"
    ]
    assert len(primaries) == 1, f"Expected 1 primary button, found {len(primaries)}"
    assert primaries[0].text() == "Start Matching"


def test_match_page_auth_guidance_uses_add_urls(qapp):
    """Auth message should say 'Add URLs' not 'Download tab'."""
    from src.ui.pages.match_page import MatchPage
    import inspect
    source = inspect.getsource(MatchPage)
    assert "Download tab" not in source, \
        "Match page should reference 'Add URLs' not 'Download tab'"
