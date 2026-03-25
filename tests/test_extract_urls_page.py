"""Tests for ExtractUrlsPage."""
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


def test_extract_urls_page_creates(qapp):
    from src.ui.pages.extract_urls_page import ExtractUrlsPage
    page = ExtractUrlsPage()
    assert page is not None


def test_extract_urls_page_status_copy(qapp):
    from src.ui.pages.extract_urls_page import ExtractUrlsPage
    page = ExtractUrlsPage()
    assert page.status_label.text() == "Ready to extract."
    assert page.results_label.text() == "No links found yet."


def test_extract_urls_primary_action_is_extract(qapp):
    from src.ui.pages.extract_urls_page import ExtractUrlsPage
    page = ExtractUrlsPage()
    assert page.extract_button.property("button_role") == "primary"


def test_extract_urls_stop_is_secondary(qapp):
    from src.ui.pages.extract_urls_page import ExtractUrlsPage
    page = ExtractUrlsPage()
    assert page.stop_button.property("button_role") == "secondary"


def test_extract_urls_auth_guidance_uses_add_urls(qapp):
    from src.ui.pages.extract_urls_page import ExtractUrlsPage
    from PyQt6.QtWidgets import QLabel
    page = ExtractUrlsPage()
    labels = [lbl for lbl in page.findChildren(QLabel) if lbl.objectName() == "dimLabel"]
    texts = [lbl.text() for lbl in labels]
    assert any("Sign in using Add URLs first" in t for t in texts), (
        f"Expected 'Add URLs' auth guidance, found: {texts}"
    )
