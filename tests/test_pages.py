"""Basic instantiation tests for all page widgets."""
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


def test_import_all_pages():
    from src.ui.pages import (
        add_urls_page,
        extract_urls_page,
        convert_page,
        trim_page,
        metadata_page,
        sort_page,
        rename_page,
        match_page,
        settings_page,
    )
    # All modules should import without error
    assert add_urls_page is not None
    assert extract_urls_page is not None
    assert convert_page is not None
    assert trim_page is not None
    assert metadata_page is not None
    assert sort_page is not None
    assert rename_page is not None
    assert match_page is not None
    assert settings_page is not None


def test_add_urls_page_creates(qapp):
    from src.ui.pages.add_urls_page import AddUrlsPage
    page = AddUrlsPage()
    assert page is not None


def test_extract_urls_page_creates(qapp):
    from src.ui.pages.extract_urls_page import ExtractUrlsPage
    page = ExtractUrlsPage()
    assert page is not None


def test_convert_page_creates(qapp):
    from src.ui.pages.convert_page import ConvertPage
    page = ConvertPage()
    assert page is not None


def test_trim_page_creates(qapp):
    from src.ui.pages.trim_page import TrimPage
    page = TrimPage()
    assert page is not None


def test_metadata_page_creates(qapp):
    from src.ui.pages.metadata_page import MetadataPage
    page = MetadataPage()
    assert page is not None


def test_sort_page_creates(qapp):
    from src.ui.pages.sort_page import SortPage
    page = SortPage()
    assert page is not None


def test_rename_page_creates(qapp):
    from src.ui.pages.rename_page import RenamePage
    page = RenamePage()
    assert page is not None


def test_match_page_creates(qapp):
    from src.ui.pages.match_page import MatchPage
    page = MatchPage()
    assert page is not None


def test_settings_page_creates(qapp):
    from src.ui.pages.settings_page import SettingsPage
    page = SettingsPage()
    assert page is not None
