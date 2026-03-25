"""Tests for PageHeader component."""
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


def test_page_header_creates(qapp):
    from src.ui.components.page_header import PageHeader
    header = PageHeader(title="Test", description="Desc")
    assert header is not None


def test_page_header_set_title(qapp):
    from src.ui.components.page_header import PageHeader
    header = PageHeader(title="Test", description="Desc")
    header.set_title("New Title")
    assert header.title_label.text() == "New Title"


def test_page_header_add_stat(qapp):
    from src.ui.components.page_header import PageHeader
    header = PageHeader(title="Test", description="Desc")
    header.add_stat("Queued", "5")
    # Should not crash; stat is visual
