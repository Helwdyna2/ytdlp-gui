"""Tests for MetadataPage."""
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


def test_metadata_page_creates(qapp):
    from src.ui.pages.metadata_page import MetadataPage
    page = MetadataPage()
    assert page is not None


def test_metadata_page_uses_split_layout(qapp):
    from src.ui.pages.metadata_page import MetadataPage
    from src.ui.components.split_layout import SplitLayout
    page = MetadataPage()
    splits = page.findChildren(SplitLayout)
    assert len(splits) == 1


def test_metadata_page_one_primary_action(qapp):
    from src.ui.pages.metadata_page import MetadataPage
    from PyQt6.QtWidgets import QPushButton
    page = MetadataPage()
    primaries = [
        btn for btn in page.findChildren(QPushButton)
        if btn.property("button_role") == "primary"
    ]
    assert len(primaries) == 1
    assert primaries[0].text() == "Scan"
