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
    assert "Queued" in header._stat_value_labels


def test_page_header_update_stat(qapp):
    from src.ui.components.page_header import PageHeader
    header = PageHeader(title="Test", description="Desc")
    header.add_stat("Active", "0")
    header.update_stat("Active", "3")
    assert header._stat_value_labels["Active"].text() == "3"


def test_page_header_add_stat_with_color_property(qapp):
    from src.ui.components.page_header import PageHeader
    header = PageHeader(title="Test", description="Desc")
    header.add_stat("Active", "2", color="cyan")
    lbl = header._stat_value_labels["Active"]
    # Color should be set via dataColor property, not inline stylesheet
    assert lbl.property("dataColor") == "cyan"


def test_page_header_update_stat_with_color_property(qapp):
    from src.ui.components.page_header import PageHeader
    header = PageHeader(title="Test", description="Desc")
    header.add_stat("Queued", "0")
    header.update_stat("Queued", "5", color="orange")
    lbl = header._stat_value_labels["Queued"]
    assert lbl.property("dataColor") == "orange"
