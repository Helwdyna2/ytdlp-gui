"""Integration tests for MainWindow workbench wiring."""

import gc
import sys
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PyQt6.QtWidgets")

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.data.database import Database
from src.data.models import OutputConfig, SavedTask, SavedTaskStatus


@pytest.fixture(autouse=True)
def reset_singleton():
    from src.ui.theme.theme_engine import ThemeEngine

    ThemeEngine._instance = None
    yield
    ThemeEngine._instance = None


@pytest.fixture(autouse=True)
def reset_database():
    Database.reset_instance()
    yield
    Database.reset_instance()


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


class DummyConfigService:
    def __init__(self):
        self.values = {}

    def get(self, key, default=None):
        return self.values.get(key, default)


class DummyDownloadManager(QObject):
    download_started = pyqtSignal(str, str)
    download_progress = pyqtSignal(str, dict)
    download_completed = pyqtSignal(str, bool, str)
    download_title_found = pyqtSignal(str, str)
    queue_progress = pyqtSignal(int, int, int, int)
    aggregate_speed = pyqtSignal(float)
    log_message = pyqtSignal(str, str)
    all_completed = pyqtSignal()
    downloads_started = pyqtSignal()
    download_cancelling = pyqtSignal(str)
    download_force_terminated = pyqtSignal(str)

    def __init__(self, download_repo):
        super().__init__()
        self.download_repo = download_repo
        self.is_running = False

    def start_downloads(self, urls, config):
        self.is_running = True

    def cancel_all(self):
        self.is_running = False

    def get_remaining_urls(self):
        return []


class DummyAuthManager(QObject):
    login_finished = pyqtSignal(str, str)
    cookies_export_started = pyqtSignal()
    cookies_exported = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def export_cookies(self):
        self.cookies_export_started.emit()

    def get_cookies_file_path(self):
        return ""

    def open_login(self, start_url, target_cookie_suffixes=None):
        return None


class DummyUrlInputWidget(QWidget):
    urls_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.text_edit = QLineEdit(self)
        layout.addWidget(self.text_edit)
        self.urls = []

    def focus_input(self):
        self.text_edit.setFocus()

    def add_urls(self, urls):
        self.urls.extend(urls)
        self.urls_changed.emit(list(self.urls))

    def set_urls(self, urls):
        self.urls = list(urls)
        self.urls_changed.emit(list(self.urls))

    def set_enabled(self, enabled):
        self.setEnabled(enabled)


class DummyFilePickerWidget(QWidget):
    urls_loaded = pyqtSignal(list)

    def _browse_url_file(self):
        return None

    def set_enabled(self, enabled):
        self.setEnabled(enabled)


class DummyOutputConfigWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.output_dir = ""
        self._config = OutputConfig(output_dir="")

    def get_config(self):
        return OutputConfig(
            output_dir=self.output_dir,
            concurrent_limit=self._config.concurrent_limit,
            force_overwrite=self._config.force_overwrite,
            video_only=self._config.video_only,
            cookies_path=self._config.cookies_path,
        )

    def set_config(self, values):
        self.output_dir = values.get("output_dir", self.output_dir)

    def set_enabled(self, enabled):
        self.setEnabled(enabled)


class DummyQueueProgressWidget(QWidget):
    start_clicked = pyqtSignal()
    cancel_clicked = pyqtSignal()
    clear_history_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.start_btn = QPushButton("Start", self)
        self.cancel_btn = QPushButton("Cancel", self)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.cancel_btn)

    def set_url_count(self, count):
        return None

    def set_running(self, running):
        return None

    def update_progress(self, completed, failed, cancelled, total):
        return None

    def update_speed(self, speed):
        return None


class DummyProgressWidget(QWidget):
    def add_download(self, url):
        return None

    def update_progress(self, url, progress):
        return None

    def set_title(self, url, title):
        return None

    def set_completed(self, url, success, message, cancelled=False):
        return None

    def set_cancelling(self, url):
        return None

    def clear_completed(self):
        return None


class DummyDownloadLogWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.entries = []

    def clear(self):
        self.entries.clear()

    def add_info(self, message):
        self.entries.append(("info", message))

    def add_entry(self, level, message):
        self.entries.append((level, message))


class DummyAuthStatusWidget(QWidget):
    authenticate_requested = pyqtSignal(str)

    def set_urls(self, urls):
        return None

    def refresh_status(self):
        return None


class DummyAddUrlsPage(QWidget):
    start_download = pyqtSignal()
    cancel_download = pyqtSignal()
    load_from_file = pyqtSignal()
    clear_urls = pyqtSignal()

    def __init__(self, **kwargs):
        parent = kwargs.get("parent")
        super().__init__(parent)
        self.download_mode = False
        self.queue_stats = None

    def set_download_mode(self, active):
        self.download_mode = active

    def set_queue_stats(self, queued, active, elapsed):
        self.queue_stats = (queued, active, elapsed)


class DummyPage(QWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)


class DummyConvertPage(DummyPage):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.restore_calls = []

    def restore_saved_task(
        self,
        payload,
        config_payload=None,
        *,
        saved_task_id=None,
    ):
        self.restore_calls.append(
            {
                "payload": payload,
                "config_payload": config_payload,
                "saved_task_id": saved_task_id,
            }
        )


class DummyTrimPage(DummyPage):
    def cleanup(self):
        return None


class DummySettingsPage(DummyPage):
    def reload_settings(self):
        return None


def _patch_lightweight_main_window_components(monkeypatch):
    from src.ui import main_window as main_window_module

    monkeypatch.setattr(main_window_module, "ConfigService", DummyConfigService)
    monkeypatch.setattr(main_window_module, "DownloadManager", DummyDownloadManager)
    monkeypatch.setattr(main_window_module, "AuthManager", DummyAuthManager)
    monkeypatch.setattr(main_window_module, "UrlInputWidget", DummyUrlInputWidget)
    monkeypatch.setattr(main_window_module, "FilePickerWidget", DummyFilePickerWidget)
    monkeypatch.setattr(main_window_module, "OutputConfigWidget", DummyOutputConfigWidget)
    monkeypatch.setattr(main_window_module, "QueueProgressWidget", DummyQueueProgressWidget)
    monkeypatch.setattr(main_window_module, "ProgressWidget", DummyProgressWidget)
    monkeypatch.setattr(main_window_module, "DownloadLogWidget", DummyDownloadLogWidget)
    monkeypatch.setattr(main_window_module, "AuthStatusWidget", DummyAuthStatusWidget)
    monkeypatch.setattr(main_window_module, "AddUrlsPage", DummyAddUrlsPage)
    monkeypatch.setattr(main_window_module, "ExtractUrlsPage", DummyPage)
    monkeypatch.setattr(main_window_module, "ConvertPage", DummyConvertPage)
    monkeypatch.setattr(main_window_module, "TrimPage", DummyTrimPage)
    monkeypatch.setattr(main_window_module, "MetadataPage", DummyPage)
    monkeypatch.setattr(main_window_module, "SortPage", DummyPage)
    monkeypatch.setattr(main_window_module, "RenamePage", DummyPage)
    monkeypatch.setattr(main_window_module, "MatchPage", DummyPage)
    monkeypatch.setattr(main_window_module, "SettingsPage", DummySettingsPage)


def _make_window(monkeypatch, *, saved_task_service=None, parent=None):
    from src.ui.main_window import MainWindow

    _patch_lightweight_main_window_components(monkeypatch)

    db = MagicMock()
    db.get_connection.return_value = MagicMock()
    session_svc = MagicMock()
    session_svc.get_pending_session.return_value = None
    session_svc.stop_auto_save.return_value = None

    return MainWindow(
        db,
        session_svc,
        parent,
        saved_task_service=saved_task_service,
    )


def test_main_window_integration(qapp, monkeypatch):
    win = _make_window(monkeypatch, saved_task_service=MagicMock())

    assert win is not None
    assert win.shell.content_stack.count() == 9
    assert win.shell.active_tool() == "add_urls"

    expected = [
        "add_urls",
        "extract_urls",
        "convert",
        "trim",
        "metadata",
        "sort",
        "rename",
        "match",
        "settings",
    ]
    for key in expected:
        assert key in win.shell._tool_widgets, f"Tool '{key}' not registered"

    win.shell.set_badge("add_urls", 3)
    win.shell.set_badge("add_urls", 0)

    win.close()
    qapp.processEvents()
    del win
    gc.collect()
    qapp.processEvents()


def test_main_window_accepts_legacy_positional_parent(qapp, monkeypatch):
    parent = QWidget()
    win = _make_window(monkeypatch, parent=parent)

    assert win.parent() is parent
    assert win.saved_task_service is None
    assert win.shell.active_tool() == "add_urls"
    assert "trim" in win.shell._tool_widgets

    win.close()
    qapp.processEvents()


def test_file_menu_exposes_saved_tasks_action(qapp, monkeypatch):
    win = _make_window(monkeypatch, saved_task_service=MagicMock())

    file_menu = win.menuBar().actions()[0].menu()
    action_texts = [
        action.text()
        for action in file_menu.actions()
        if isinstance(action, QAction) and not action.isSeparator()
    ]

    assert "Saved Tasks..." in action_texts

    win.close()
    qapp.processEvents()


def test_restore_saved_convert_task_routes_to_convert_page(qapp, monkeypatch):
    win = _make_window(monkeypatch, saved_task_service=MagicMock())
    task = SavedTask(
        id=42,
        task_type="convert",
        title="Resume convert",
        status=SavedTaskStatus.PAUSED,
        payload={
            "config": {"audio_codec": "copy"},
            "items": [{"input_path": "/tmp/example.mp4"}],
        },
        summary={"title": "Resume convert"},
    )

    win.restore_saved_task(task)

    assert win.shell.active_tool() == "convert"
    assert win.convert_page.restore_calls == [
        {
            "payload": task.payload,
            "config_payload": {"audio_codec": "copy"},
            "saved_task_id": 42,
        }
    ]

    win.close()
    qapp.processEvents()


def test_saved_tasks_menu_action_opens_dialog_and_restores_selection(qapp, monkeypatch):
    from src.ui import main_window as main_window_module

    selected_task = SavedTask(
        id=7,
        task_type="convert",
        title="Queued convert",
        status=SavedTaskStatus.ACTIVE,
        payload={
            "config": {"video_codec": "h264"},
            "items": [{"input_path": "/tmp/input.mov"}],
        },
        summary={"title": "Queued convert"},
    )

    class DummySavedTasksDialog:
        instances = []

        def __init__(self, saved_task_service, parent=None):
            self.saved_task_service = saved_task_service
            self.parent = parent
            DummySavedTasksDialog.instances.append(self)

        def exec(self):
            return 1

        def selected_action(self):
            return "restore"

        def selected_task(self):
            return selected_task

    saved_task_service = MagicMock()
    monkeypatch.setattr(main_window_module, "SavedTasksDialog", DummySavedTasksDialog)
    win = _make_window(monkeypatch, saved_task_service=saved_task_service)

    file_menu = win.menuBar().actions()[0].menu()
    saved_tasks_action = next(
        action for action in file_menu.actions() if action.text() == "Saved Tasks..."
    )

    saved_tasks_action.trigger()

    assert DummySavedTasksDialog.instances
    assert DummySavedTasksDialog.instances[0].saved_task_service is saved_task_service
    assert win.shell.active_tool() == "convert"
    assert win.convert_page.restore_calls == [
        {
            "payload": selected_task.payload,
            "config_payload": {"video_codec": "h264"},
            "saved_task_id": 7,
        }
    ]

    win.close()
    qapp.processEvents()


def test_startup_prompt_restores_latest_saved_task(qapp, monkeypatch):
    latest_task = SavedTask(
        id=9,
        task_type="convert",
        title="Latest convert",
        status=SavedTaskStatus.PAUSED,
        payload={
            "config": {"output_codec": "h264"},
            "items": [{"input_path": "/tmp/latest.mp4"}],
        },
    )

    saved_task_service = MagicMock()
    saved_task_service.get_latest_recoverable_task.return_value = latest_task
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Yes),
    )

    win = _make_window(monkeypatch, saved_task_service=saved_task_service)
    win.prompt_restore_latest_saved_task()

    assert win.shell.active_tool() == "convert"
    assert win.convert_page.restore_calls == [
        {
            "payload": latest_task.payload,
            "config_payload": {"output_codec": "h264"},
            "saved_task_id": 9,
        }
    ]

    win.close()
    qapp.processEvents()


def test_startup_prompt_ignores_unrestorable_task_types(qapp, monkeypatch):
    latest_task = SavedTask(
        id=10,
        task_type="trim",
        title="Trim draft",
        status=SavedTaskStatus.PAUSED,
        payload={"project_path": "/tmp/test.cutproj.json"},
    )

    saved_task_service = MagicMock()
    saved_task_service.get_latest_recoverable_task.return_value = latest_task
    question_calls = []
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: question_calls.append(True)),
    )

    win = _make_window(monkeypatch, saved_task_service=saved_task_service)
    win.prompt_restore_latest_saved_task()

    assert question_calls == []
    assert win.shell.active_tool() == "add_urls"
    assert win.convert_page.restore_calls == []

    win.close()
    qapp.processEvents()


def test_build_startup_services_includes_saved_task_service(monkeypatch, tmp_path):
    import src.main as main_module

    monkeypatch.setattr(main_module, "ConfigService", DummyConfigService)

    database = Database(db_path=str(tmp_path / "startup.sqlite3"))
    services = main_module.build_startup_services(database)

    assert services["saved_task_service"].repository.db is database
    assert services["session_service"].session_repo.db is database
    assert services["saved_task_repo"].db is database


def test_page_imports_succeed():
    from src.ui.pages import (
        add_urls_page,
        convert_page,
        extract_urls_page,
        match_page,
        metadata_page,
        rename_page,
        settings_page,
        sort_page,
        trim_page,
    )

    assert all(
        [
            add_urls_page,
            extract_urls_page,
            convert_page,
            trim_page,
            metadata_page,
            sort_page,
            rename_page,
            match_page,
            settings_page,
        ]
    )
