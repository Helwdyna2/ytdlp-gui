"""Integration tests for MainWindow — tool registration, default selection, badges.

NOTE: MainWindow teardown may segfault during Python 3.14 + PyQt6 GC.
This is a known environment issue (see AGENTS.md). The tests themselves
pass; the crash occurs during object cleanup after the test completes.
"""
import gc
import pytest
import sys
from unittest.mock import MagicMock

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


def _make_window(qapp):
    """Create a MainWindow with mocked DB/session."""
    from src.ui.main_window import MainWindow
    db = MagicMock()
    db.get_connection.return_value = MagicMock()
    session_svc = MagicMock()
    session_svc.get_pending_session.return_value = None
    return MainWindow(database=db, session_service=session_svc)


def test_main_window_integration(qapp):
    """Single consolidated test to minimize teardown crashes."""
    win = _make_window(qapp)

    # Creates successfully
    assert win is not None

    # Nine pages registered
    assert win.shell.content_stack.count() == 9

    # Default is add_urls
    assert win.shell.active_tool() == "add_urls"

    # All tool keys present
    expected = [
        "add_urls", "extract_urls", "convert", "trim",
        "metadata", "sort", "rename", "match", "settings",
    ]
    for key in expected:
        assert key in win.shell._tool_widgets, f"Tool '{key}' not registered"

    # Badge update doesn't crash
    win.shell.set_badge("add_urls", 3)
    win.shell.set_badge("add_urls", 0)

    # Explicit cleanup to reduce segfault risk
    win.close()
    qapp.processEvents()
    del win
    gc.collect()
    qapp.processEvents()


def test_page_imports_succeed():
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
    assert all([
        add_urls_page, extract_urls_page, convert_page, trim_page,
        metadata_page, sort_page, rename_page, match_page, settings_page,
    ])
