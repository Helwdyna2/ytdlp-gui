"""Tests for RenamePage."""
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


def test_rename_page_creates(qapp):
    from src.ui.pages.rename_page import RenamePage
    page = RenamePage()
    assert page is not None


def test_rename_page_has_drag_handles(qapp):
    from src.ui.pages.rename_page import RenamePage
    from PyQt6.QtWidgets import QLabel
    page = RenamePage()
    handles = [lbl for lbl in page.findChildren(QLabel) if lbl.objectName() == "dragHandle"]
    assert len(handles) > 0, "Rename tokens should have visible drag handles"


def test_rename_page_one_primary_action(qapp):
    from src.ui.pages.rename_page import RenamePage
    from PyQt6.QtWidgets import QPushButton
    page = RenamePage()
    ctas = [
        btn for btn in page.findChildren(QPushButton)
        if btn.property("button_role") == "cta"
    ]
    assert len(ctas) == 1
    assert ctas[0].text() == "APPLY RENAME"
