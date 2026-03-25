"""Tests for ActivityDrawer component."""

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


def test_activity_drawer_starts_collapsed(qapp):
    from src.ui.components.activity_drawer import ActivityDrawer

    drawer = ActivityDrawer("Recent Activity")
    assert drawer.is_expanded() is False


def test_activity_drawer_toggles_expansion(qapp):
    from src.ui.components.activity_drawer import ActivityDrawer

    drawer = ActivityDrawer("Recent Activity")
    drawer.set_expanded(True)
    assert drawer.is_expanded() is True
