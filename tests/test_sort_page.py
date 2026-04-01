"""Tests for SortPage."""
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


def test_sort_page_creates(qapp):
    from src.ui.pages.sort_page import SortPage
    page = SortPage()
    assert page is not None


def test_sort_page_uses_split_layout(qapp):
    from src.ui.pages.sort_page import SortPage
    from src.ui.components.split_layout import SplitLayout
    page = SortPage()
    splits = page.findChildren(SplitLayout)
    assert len(splits) == 1


def test_sort_page_has_drag_handles(qapp):
    from src.ui.pages.sort_page import SortPage
    from PyQt6.QtWidgets import QLabel
    page = SortPage()
    handles = [lbl for lbl in page.findChildren(QLabel) if lbl.objectName() == "dragHandle"]
    assert len(handles) > 0, "Sort criteria should have visible drag handles"


def test_sort_page_has_keyboard_reorder(qapp):
    from src.ui.pages.sort_page import SortPage
    page = SortPage()
    assert page._move_up_btn is not None
    assert page._move_down_btn is not None


def test_sort_page_one_primary_action(qapp):
    from src.ui.pages.sort_page import SortPage
    from PyQt6.QtWidgets import QPushButton
    page = SortPage()
    ctas = [
        btn for btn in page.findChildren(QPushButton)
        if btn.property("button_role") == "cta"
    ]
    assert len(ctas) == 1
    assert ctas[0].text() == "SORT FILES"
