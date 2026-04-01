"""Tests for AddUrlsPage."""
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


def test_add_urls_page_creates(qapp):
    from src.ui.pages.add_urls_page import AddUrlsPage
    page = AddUrlsPage()
    assert page is not None


def test_add_urls_page_header_stats(qapp):
    from src.ui.pages.add_urls_page import AddUrlsPage
    page = AddUrlsPage()
    # Should have exactly Queued, Active, Elapsed — no Done
    assert "Queued" in page._header._stat_value_labels
    assert "Active" in page._header._stat_value_labels
    assert "Elapsed" in page._header._stat_value_labels
    assert "Done" not in page._header._stat_value_labels


def test_add_urls_page_start_btn_is_primary(qapp):
    from src.ui.pages.add_urls_page import AddUrlsPage
    page = AddUrlsPage()
    assert page._start_btn.property("button_role") == "cta"


def test_add_urls_page_cancel_btn_is_secondary(qapp):
    from src.ui.pages.add_urls_page import AddUrlsPage
    page = AddUrlsPage()
    assert page._cancel_btn.property("button_role") == "secondary"


def test_add_urls_page_download_mode_hides_url_input(qapp):
    from src.ui.pages.add_urls_page import AddUrlsPage
    from src.ui.widgets.url_input_widget import UrlInputWidget
    url_input = UrlInputWidget()
    page = AddUrlsPage(url_input=url_input)
    page.set_download_mode(True)
    assert url_input.isHidden()
    page.set_download_mode(False)
    assert not url_input.isHidden()


def test_add_urls_auth_section_collapsible(qapp):
    from src.ui.pages.add_urls_page import AddUrlsPage
    from src.ui.widgets.auth_status_widget import AuthStatusWidget
    auth = AuthStatusWidget()
    page = AddUrlsPage(auth_status=auth)
    # Auth section should be inside a CollapsibleSection
    from src.ui.components.collapsible_section import CollapsibleSection
    sections = page.findChildren(CollapsibleSection)
    assert len(sections) >= 1, "Auth status should be in a CollapsibleSection"
