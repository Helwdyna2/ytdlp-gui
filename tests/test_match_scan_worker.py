"""Tests for MatchScanWorker background scanning and parsing."""

import pytest
from pathlib import Path
from PyQt6.QtCore import QEventLoop

from src.core.match_scan_worker import MatchScanWorker
from src.data.models import MatchConfig, MatchStatus


@pytest.fixture
def temp_match_dir(tmp_path):
    """Create temp directory with video files for matching."""
    # Create video files with various naming patterns
    (tmp_path / "Brazzers.23.04.15.Jane.Doe.XXX.1080p.mp4").write_text("test")
    (tmp_path / "RealityKings - Lisa Ann - Hot Scene.mp4").write_text("test")
    (tmp_path / "random_video.mkv").write_text("test")
    (tmp_path / "Studio - Performer - Title.avi").write_text("test")  # already named
    (tmp_path / "video.txt").write_text("test")  # non-video

    return tmp_path


def test_match_scan_worker_runs_in_background(temp_match_dir, qtbot):
    """Test that MatchScanWorker runs in a background thread."""
    config = MatchConfig(
        source_dir=str(temp_match_dir),
        search_porndb=True,
        search_stashdb=True,
    )

    worker = MatchScanWorker(str(temp_match_dir), config)

    # Verify worker is a QThread
    assert hasattr(worker, "start")
    assert hasattr(worker, "isRunning")

    completed_files = []
    worker.completed.connect(lambda files: completed_files.extend(files))

    worker.start()

    # Worker should run asynchronously
    assert worker.isRunning() or len(completed_files) > 0

    qtbot.waitUntil(lambda: not worker.isRunning(), timeout=5000)

    # Should have found and parsed video files
    assert len(completed_files) > 0


def test_match_scan_worker_parses_filenames(temp_match_dir, qtbot):
    """Test that worker parses filenames and creates MatchResult objects."""
    config = MatchConfig(
        source_dir=str(temp_match_dir),
        search_porndb=True,
        search_stashdb=True,
    )

    worker = MatchScanWorker(str(temp_match_dir), config)

    completed_files = []
    worker.completed.connect(lambda files: completed_files.extend(files))

    worker.start()
    qtbot.waitUntil(lambda: not worker.isRunning(), timeout=5000)

    # All results should have file_path, original_filename, status
    for result in completed_files:
        assert result.file_path
        assert result.original_filename
        assert result.status in [MatchStatus.PENDING, MatchStatus.SKIPPED]

        # If status is PENDING, should have parsed data
        if result.status == MatchStatus.PENDING:
            assert result.parsed is not None


def test_match_scan_worker_skips_already_named(temp_match_dir, qtbot):
    """Test that worker skips already-named files when configured."""
    config = MatchConfig(
        source_dir=str(temp_match_dir),
        search_porndb=True,
        search_stashdb=True,
        include_already_named=False,  # Skip already-named files
    )

    worker = MatchScanWorker(str(temp_match_dir), config)

    completed_files = []
    worker.completed.connect(lambda files: completed_files.extend(files))

    worker.start()
    qtbot.waitUntil(lambda: not worker.isRunning(), timeout=5000)

    # Find the already-named file
    already_named = [
        r
        for r in completed_files
        if "Studio - Performer - Title" in r.original_filename
    ]

    if already_named:
        # Should be marked as SKIPPED
        assert already_named[0].status == MatchStatus.SKIPPED


def test_match_scan_worker_includes_already_named_when_configured(
    temp_match_dir, qtbot
):
    """Test that worker includes already-named files when configured."""
    config = MatchConfig(
        source_dir=str(temp_match_dir),
        search_porndb=True,
        search_stashdb=True,
        include_already_named=True,  # Include already-named files
    )

    worker = MatchScanWorker(str(temp_match_dir), config)

    completed_files = []
    worker.completed.connect(lambda files: completed_files.extend(files))

    worker.start()
    qtbot.waitUntil(lambda: not worker.isRunning(), timeout=5000)

    # Find the already-named file
    already_named = [
        r
        for r in completed_files
        if "Studio - Performer - Title" in r.original_filename
    ]

    if already_named:
        # Should be marked as PENDING, not SKIPPED
        assert already_named[0].status == MatchStatus.PENDING


def test_match_scan_worker_emits_progress(temp_match_dir, qtbot):
    """Test that worker emits progress signals during scan."""
    config = MatchConfig(source_dir=str(temp_match_dir))

    worker = MatchScanWorker(str(temp_match_dir), config)

    progress_signals = []
    worker.progress.connect(
        lambda current, total: progress_signals.append((current, total))
    )

    worker.start()
    qtbot.waitUntil(lambda: not worker.isRunning(), timeout=5000)

    # Should have emitted progress
    assert len(progress_signals) > 0


def test_match_scan_worker_handles_errors(qtbot):
    """Test that worker emits error signal for invalid directory."""
    config = MatchConfig(source_dir="/nonexistent/path")

    worker = MatchScanWorker("/nonexistent/path", config)

    error_messages = []
    worker.error.connect(lambda msg: error_messages.append(msg))

    worker.start()
    qtbot.waitUntil(lambda: not worker.isRunning(), timeout=5000)

    # Should have emitted error
    assert len(error_messages) > 0
    assert (
        "directory" in error_messages[0].lower() or "not" in error_messages[0].lower()
    )


def test_match_scan_worker_can_be_cancelled(temp_match_dir, qtbot):
    """Test that worker can be cancelled mid-scan."""
    # Add many files so the scan doesn't finish before cancel takes effect
    bulk_dir = temp_match_dir / "bulk"
    bulk_dir.mkdir()
    for i in range(200):
        (bulk_dir / f"video_{i:04d}.mp4").write_text("test")

    config = MatchConfig(source_dir=str(temp_match_dir))
    worker = MatchScanWorker(str(temp_match_dir), config)

    completed_called = []
    worker.completed.connect(lambda files: completed_called.append(True))

    worker.start()
    worker.cancel()

    # Wait deterministically for worker to finish
    qtbot.waitUntil(lambda: not worker.isRunning(), timeout=5000)

    # Completed should not be called when cancelled
    assert len(completed_called) == 0


def test_match_scan_worker_only_scans_video_extensions(temp_match_dir, qtbot):
    """Test that worker only scans video file extensions."""
    config = MatchConfig(source_dir=str(temp_match_dir))

    worker = MatchScanWorker(str(temp_match_dir), config)

    completed_files = []
    worker.completed.connect(lambda files: completed_files.extend(files))

    worker.start()
    qtbot.waitUntil(lambda: not worker.isRunning(), timeout=5000)

    # Should not include .txt file
    filenames = [r.original_filename for r in completed_files]
    assert "video.txt" not in filenames

    # Should only include video files
    for result in completed_files:
        ext = Path(result.file_path).suffix.lower()
        assert ext in [".mp4", ".mkv", ".avi", ".wmv", ".mov", ".flv", ".webm", ".m4v"]
