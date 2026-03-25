"""Tests for DataPanel component."""

import pytest
import sys

pytest.importorskip("PyQt6.QtWidgets")


@pytest.fixture
def qapp():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def test_data_panel_creates(qapp):
    from src.ui.components.data_panel import DataPanel

    panel = DataPanel("Test Panel")
    assert panel is not None


def test_data_panel_has_title(qapp):
    from src.ui.components.data_panel import DataPanel

    panel = DataPanel("MY PANEL")
    assert panel._title_label.text() == "My Panel"


def test_data_panel_body_layout(qapp):
    from src.ui.components.data_panel import DataPanel
    from PyQt6.QtWidgets import QLabel

    panel = DataPanel("Test")
    label = QLabel("Content")
    panel.body_layout.addWidget(label)
    assert panel.body_layout.count() == 1


def test_data_panel_set_header_tag(qapp):
    from src.ui.components.data_panel import DataPanel

    panel = DataPanel("Test")
    panel.set_header_tag("ACTIVE", "cyan")
    assert panel._header_tag is not None
