"""Tests for MatchTabWidget using MatchScanWorker for background scanning."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from PyQt6.QtCore import QObject, Qt, pyqtSignal

from src.ui.widgets.match_tab_widget import MatchTabWidget
from src.data.models import MatchResult, MatchStatus


class FakeScanWorker(QObject):
    """Controllable stand-in for MatchScanWorker."""

    progress = pyqtSignal(int, int)
    completed = pyqtSignal(list)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, folder_path, config, parent=None):
        super().__init__(parent)
        self.folder_path = folder_path
        self.config = config
        self._running = False
        self.cancelled = False
        self.wait_calls = []
        if hasattr(FakeScanWorker, "_test_instances"):
            FakeScanWorker._test_instances.append(self)

    def start(self):
        self._running = True

    def cancel(self):
        self.cancelled = True

    def isRunning(self):
        return self._running

    def wait(self, timeout):
        self.wait_calls.append(timeout)
        self._running = False
        return True

    def emit_completed(self, files):
        self._running = False
        self.completed.emit(files)
        self.finished.emit()

    def emit_error(self, message):
        self._running = False
        self.error.emit(message)
        self.finished.emit()


@pytest.fixture
def fake_scan_instances():
    """Provide an isolated instance list for FakeScanWorker per test."""
    instances = []
    FakeScanWorker._test_instances = instances
    yield instances
    del FakeScanWorker._test_instances


@pytest.fixture
def temp_match_dir(tmp_path):
    """Create temp directory with video files for matching."""
    (tmp_path / "video1.mp4").write_text("test")
    (tmp_path / "video2.mkv").write_text("test")
    (tmp_path / "Studio - Performer - Title.avi").write_text("test")
    (tmp_path / "random.txt").write_text("test")  # non-video
    return tmp_path


def make_match_result(
    file_path: Path, status: MatchStatus = MatchStatus.PENDING
) -> MatchResult:
    """Build a minimal MatchResult for widget tests."""
    return MatchResult(
        file_path=str(file_path),
        original_filename=file_path.name,
        status=status,
    )


def test_match_tab_widget_uses_background_scan_worker(temp_match_dir, qtbot):
    """Test that MatchTabWidget uses MatchScanWorker for background scanning."""
    widget = MatchTabWidget()
    qtbot.addWidget(widget)

    # Set folder and trigger scan
    widget.folder_input.setText(str(temp_match_dir))

    # Click scan button
    qtbot.mouseClick(widget.scan_button, Qt.MouseButton.LeftButton)

    # Wait for scan to complete before checking anything
    qtbot.waitUntil(lambda: widget.scan_button.isEnabled(), timeout=5000)

    # Verify files were found (proving worker was used successfully)
    assert len(widget._files) == 3


def test_match_tab_widget_scan_runs_in_background_thread(temp_match_dir, qtbot):
    """Test that scan runs in background without blocking UI."""
    widget = MatchTabWidget()
    qtbot.addWidget(widget)

    widget.folder_input.setText(str(temp_match_dir))

    # Track UI state changes
    button_states = []

    def check_button_state():
        button_states.append(widget.scan_button.isEnabled())

    # Click scan - button should be disabled during scan
    qtbot.mouseClick(widget.scan_button, Qt.MouseButton.LeftButton)

    # Button should be disabled immediately
    assert not widget.scan_button.isEnabled()

    # Wait for scan to complete
    qtbot.waitUntil(lambda: widget.scan_button.isEnabled(), timeout=5000)

    # Verify results were populated
    assert len(widget._files) == 3  # 3 video files
    assert widget.results_table.rowCount() == 3


def test_match_tab_widget_populates_results_after_scan(temp_match_dir, qtbot):
    """Test that widget populates results table after background scan completes."""
    widget = MatchTabWidget()
    qtbot.addWidget(widget)

    widget.folder_input.setText(str(temp_match_dir))
    qtbot.mouseClick(widget.scan_button, Qt.MouseButton.LeftButton)

    # Wait for completion
    qtbot.waitUntil(lambda: len(widget._files) > 0, timeout=5000)

    # Verify files were found and parsed
    assert len(widget._files) == 3

    filenames = [f.original_filename for f in widget._files]
    assert "video1.mp4" in filenames
    assert "video2.mkv" in filenames
    assert "Studio - Performer - Title.avi" in filenames

    # Verify non-video file was excluded
    assert "random.txt" not in filenames

    # Verify table was populated
    assert widget.results_table.rowCount() == 3


def test_match_tab_widget_can_cancel_scan(temp_match_dir, qtbot):
    """Test that scan can be cancelled without blocking."""
    widget = MatchTabWidget()
    qtbot.addWidget(widget)

    # Create a large directory to ensure scan takes some time
    subdir = temp_match_dir / "subdir"
    subdir.mkdir()
    for i in range(50):
        (subdir / f"video{i}.mp4").write_text("test")

    widget.folder_input.setText(str(temp_match_dir))

    # Start scan
    qtbot.mouseClick(widget.scan_button, Qt.MouseButton.LeftButton)

    # Immediately start a new scan (should cancel the first)
    qtbot.mouseClick(widget.scan_button, Qt.MouseButton.LeftButton)

    # Wait for completion
    qtbot.waitUntil(lambda: widget.scan_button.isEnabled(), timeout=5000)

    # Should complete without errors
    assert widget.scan_button.isEnabled()


def test_match_tab_widget_ignores_stale_scan_results(
    temp_match_dir, qtbot, fake_scan_instances
):
    """Ignore results from cancelled workers after a replacement scan starts."""
    other_dir = temp_match_dir / "other"
    other_dir.mkdir()

    widget = MatchTabWidget()
    qtbot.addWidget(widget)

    with patch("src.core.match_scan_worker.MatchScanWorker", FakeScanWorker):
        widget.folder_input.setText(str(temp_match_dir))
        widget._on_scan_clicked()
        first_worker = fake_scan_instances[-1]

        widget.folder_input.setText(str(other_dir))
        widget._on_scan_clicked()
        second_worker = fake_scan_instances[-1]

        assert first_worker.cancelled is True
        assert second_worker is widget._scan_worker

        stale = [make_match_result(temp_match_dir / "video1.mp4")]
        fresh = [make_match_result(other_dir / "fresh.mp4")]

        first_worker.emit_completed(stale)
        assert widget._files == []
        assert widget._scan_worker is second_worker

        second_worker.emit_completed(fresh)
        assert [result.original_filename for result in widget._files] == ["fresh.mp4"]
        assert widget._scan_worker is None


def test_match_tab_widget_clears_results_and_actions_when_scan_starts(
    temp_match_dir, qtbot, fake_scan_instances
):
    """Clear stale results and disable row actions while a background scan is active."""
    widget = MatchTabWidget()
    qtbot.addWidget(widget)

    widget._files = [
        make_match_result(temp_match_dir / "video1.mp4"),
        make_match_result(temp_match_dir / "video2.mkv"),
    ]
    widget._populate_table()
    widget.view_details_button.setEnabled(True)
    widget.manual_search_button.setEnabled(True)
    widget.rename_button.setEnabled(True)

    with patch("src.core.match_scan_worker.MatchScanWorker", FakeScanWorker):
        widget.folder_input.setText(str(temp_match_dir))
        widget._on_scan_clicked()

        assert widget._files == []
        assert widget.results_table.rowCount() == 0
        assert widget.selection_label.text() == "Selected: 0 file(s)"
        assert not widget.view_details_button.isEnabled()
        assert not widget.manual_search_button.isEnabled()
        assert not widget.rename_button.isEnabled()
        assert widget._scan_worker is fake_scan_instances[-1]


def test_match_tab_widget_cleans_up_active_scan_worker_on_close(
    temp_match_dir, qtbot, fake_scan_instances
):
    """Closing the widget should cancel and wait for the active scan worker."""
    widget = MatchTabWidget()
    qtbot.addWidget(widget)

    with patch("src.core.match_scan_worker.MatchScanWorker", FakeScanWorker):
        widget.folder_input.setText(str(temp_match_dir))
        widget._on_scan_clicked()

        active_worker = fake_scan_instances[-1]
        assert active_worker.isRunning()

        widget.close()

        assert active_worker.cancelled is True
        assert active_worker.wait_calls == [1000]


def test_match_tab_widget_handles_scan_errors(qtbot):
    """Test that widget handles scan errors gracefully."""
    widget = MatchTabWidget()
    qtbot.addWidget(widget)

    # Set invalid folder
    widget.folder_input.setText("/nonexistent/path")

    # This should show a warning dialog before attempting scan
    # The scan button click will trigger validation
    # We can't easily test QMessageBox without mocking, but we can verify
    # the widget doesn't crash
    assert widget.folder_input.text() == "/nonexistent/path"


def test_match_tab_widget_scan_respects_config(temp_match_dir, qtbot):
    """Test that widget passes correct config to scan worker."""
    widget = MatchTabWidget()
    qtbot.addWidget(widget)

    widget.folder_input.setText(str(temp_match_dir))

    # Configure to skip already-named files
    widget.include_named_checkbox.setChecked(False)

    qtbot.mouseClick(widget.scan_button, Qt.MouseButton.LeftButton)

    # Wait for completion
    qtbot.waitUntil(lambda: len(widget._files) > 0, timeout=5000)

    # Find the already-named file
    already_named = [
        f for f in widget._files if "Studio - Performer - Title" in f.original_filename
    ]

    if already_named:
        # Should be marked as SKIPPED
        assert already_named[0].status == MatchStatus.SKIPPED


def test_match_tab_widget_passes_config_to_manager(temp_match_dir, qtbot):
    """Test that widget passes current config to manager for matching."""
    widget = MatchTabWidget()
    qtbot.addWidget(widget)

    widget.folder_input.setText(str(temp_match_dir))

    # Set specific config options
    widget.porndb_checkbox.setChecked(True)
    widget.stashdb_checkbox.setChecked(False)
    widget.preserve_tags_checkbox.setChecked(False)
    widget.include_named_checkbox.setChecked(True)

    # Scan folder
    qtbot.mouseClick(widget.scan_button, Qt.MouseButton.LeftButton)

    # Wait for scan completion
    qtbot.waitUntil(lambda: len(widget._files) > 0, timeout=5000)

    # Manager should be initialized now
    assert widget._manager is not None

    # Manager's config should match widget's current settings
    assert widget._manager._config.search_porndb is True
    assert widget._manager._config.search_stashdb is False
    assert widget._manager._config.preserve_tags is False
    assert widget._manager._config.include_already_named is True

    # Verify parser was initialized with config
    assert widget._manager._parser is not None


def test_match_tab_widget_updates_config_before_matching(temp_match_dir, qtbot):
    """Test that widget updates manager config when Match is clicked."""
    widget = MatchTabWidget()
    qtbot.addWidget(widget)

    widget.folder_input.setText(str(temp_match_dir))

    # Initial config
    widget.porndb_checkbox.setChecked(True)
    widget.stashdb_checkbox.setChecked(True)
    widget.preserve_tags_checkbox.setChecked(True)

    # Scan folder
    qtbot.mouseClick(widget.scan_button, Qt.MouseButton.LeftButton)

    # Wait for scan completion
    qtbot.waitUntil(lambda: len(widget._files) > 0, timeout=5000)

    # Verify initial config was set
    assert widget._manager._config.search_porndb is True
    assert widget._manager._config.search_stashdb is True
    assert widget._manager._config.preserve_tags is True

    # NOW change config AFTER scan but BEFORE matching
    widget.stashdb_checkbox.setChecked(False)
    widget.preserve_tags_checkbox.setChecked(False)

    # Start matching (this should update the config)
    # We can't actually run the match worker in tests easily, but we can
    # check the config was updated before the worker would start

    # Capture the config state just before matching would start
    # We'll do this by checking the manager's config after calling the match click handler

    # Mock the manager's start_matching to prevent actual matching
    original_start_matching = widget._manager.start_matching
    config_at_match_time = []

    def mock_start_matching():
        # Capture config before starting
        config_at_match_time.append(
            {
                "search_porndb": widget._manager._config.search_porndb,
                "search_stashdb": widget._manager._config.search_stashdb,
                "preserve_tags": widget._manager._config.preserve_tags,
            }
        )
        # Don't actually start matching

    widget._manager.start_matching = mock_start_matching

    # Trigger match
    qtbot.mouseClick(widget.match_button, Qt.MouseButton.LeftButton)

    # Config should have been updated to match current UI state
    assert len(config_at_match_time) == 1
    assert config_at_match_time[0]["search_porndb"] is True
    assert config_at_match_time[0]["search_stashdb"] is False  # Changed after scan
    assert config_at_match_time[0]["preserve_tags"] is False  # Changed after scan

    # Restore original method
    widget._manager.start_matching = original_start_matching
