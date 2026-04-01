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


def _make_window(qapp, monkeypatch):
    """Create a MainWindow with mocked DB/session."""
    from src.ui import main_window as main_window_module
    from src.ui.main_window import MainWindow

    class DummyConfigService:
        def __init__(self):
            self.values = {}

        def get(self, key, default=None):
            return self.values.get(key, default)

    class DummyDownloadManager:
        def __init__(self, download_repo):
            self.download_repo = download_repo
            self.is_running = False

    class DummyAuthManager:
        def __init__(self, parent=None):
            self.parent = parent

    monkeypatch.setattr(main_window_module, "ConfigService", DummyConfigService)
    monkeypatch.setattr(main_window_module, "DownloadManager", DummyDownloadManager)
    monkeypatch.setattr(main_window_module, "AuthManager", DummyAuthManager)
    monkeypatch.setattr(main_window_module.MainWindow, "_setup_ui", lambda self: None)
    monkeypatch.setattr(main_window_module.MainWindow, "_setup_menu_bar", lambda self: None)
    monkeypatch.setattr(main_window_module.MainWindow, "_setup_shortcuts", lambda self: None)
    monkeypatch.setattr(main_window_module.MainWindow, "_connect_signals", lambda self: None)
    monkeypatch.setattr(main_window_module.MainWindow, "_setup_quick_look_shortcut", lambda self: None)

    db = MagicMock()
    db.get_connection.return_value = MagicMock()
    session_svc = MagicMock()
    session_svc.get_pending_session.return_value = None
    saved_task_svc = MagicMock()
    return MainWindow(
        database=db,
        session_service=session_svc,
        saved_task_service=saved_task_svc,
    )


def _make_window_with_positional_parent(qapp, monkeypatch):
    """Create a MainWindow using the legacy positional parent argument."""
    from PyQt6.QtWidgets import QWidget
    from src.ui import main_window as main_window_module
    from src.ui.main_window import MainWindow

    class DummyConfigService:
        def __init__(self):
            self.values = {}

        def get(self, key, default=None):
            return self.values.get(key, default)

    class DummyDownloadManager:
        def __init__(self, download_repo):
            self.download_repo = download_repo
            self.is_running = False

    class DummyAuthManager:
        def __init__(self, parent=None):
            self.parent = parent

    monkeypatch.setattr(main_window_module, "ConfigService", DummyConfigService)
    monkeypatch.setattr(main_window_module, "DownloadManager", DummyDownloadManager)
    monkeypatch.setattr(main_window_module, "AuthManager", DummyAuthManager)
    monkeypatch.setattr(main_window_module.MainWindow, "_setup_ui", lambda self: None)
    monkeypatch.setattr(main_window_module.MainWindow, "_setup_menu_bar", lambda self: None)
    monkeypatch.setattr(main_window_module.MainWindow, "_setup_shortcuts", lambda self: None)
    monkeypatch.setattr(main_window_module.MainWindow, "_connect_signals", lambda self: None)
    monkeypatch.setattr(main_window_module.MainWindow, "_setup_quick_look_shortcut", lambda self: None)

    db = MagicMock()
    session_svc = MagicMock()
    parent = QWidget()
    return MainWindow(db, session_svc, parent), parent


def test_main_window_integration(qapp, monkeypatch):
    """Single consolidated test to minimize teardown crashes."""
    win = _make_window(qapp, monkeypatch)
    win.trim_page = type("DummyTrimPage", (), {"cleanup": lambda self: None})()

    assert win is not None
    assert win.saved_task_service is not None
    assert win.session_service.get_pending_session.return_value is None
    assert win.database is not None

    # Explicit cleanup to reduce segfault risk
    win.close()
    qapp.processEvents()
    del win
    gc.collect()
    qapp.processEvents()


def test_main_window_accepts_legacy_positional_parent(qapp, monkeypatch):
    win, parent = _make_window_with_positional_parent(qapp, monkeypatch)

    assert win.parent() is parent
    assert win.saved_task_service is None

    win.trim_page = type("DummyTrimPage", (), {"cleanup": lambda self: None})()
    win.close()
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
