"""Tests for icon registry."""

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


def test_get_icon_returns_qicon(qapp):
    from src.ui.theme.icons import get_icon
    from PyQt6.QtGui import QIcon

    icon = get_icon("download")
    assert isinstance(icon, QIcon)
    assert not icon.isNull()


def test_get_icon_unknown_returns_fallback(qapp):
    from src.ui.theme.icons import get_icon
    from PyQt6.QtGui import QIcon

    icon = get_icon("nonexistent_icon_name")
    assert isinstance(icon, QIcon)


def test_nav_icons_all_exist(qapp):
    from src.ui.theme.icons import NAV_ICONS, get_icon

    for name in NAV_ICONS:
        icon = get_icon(name)
        assert not icon.isNull(), f"Nav icon '{name}' is null"


def test_stage_icons_exist(qapp):
    from src.ui.theme.icons import get_icon

    for name in ("ingest", "prepare", "organize", "export"):
        icon = get_icon(name)
        assert not icon.isNull(), f"Stage icon '{name}' is null"


def test_status_icons_all_exist(qapp):
    from src.ui.theme.icons import STATUS_ICONS, get_icon

    for name in STATUS_ICONS:
        icon = get_icon(name)
        assert not icon.isNull(), f"Status icon '{name}' is null"


def test_action_icons_all_exist(qapp):
    from src.ui.theme.icons import ACTION_ICONS, get_icon

    for name in ACTION_ICONS:
        icon = get_icon(name)
        assert not icon.isNull(), f"Action icon '{name}' is null"


def test_get_icon_with_color(qapp):
    from src.ui.theme.icons import get_icon
    from PyQt6.QtGui import QIcon

    icon = get_icon("download", color="#00d4ff")
    assert isinstance(icon, QIcon)
    assert not icon.isNull()
