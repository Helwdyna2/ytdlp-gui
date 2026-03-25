"""Tests for optimized FolderScanWorker single-traversal behavior."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtCore import QEventLoop

from src.core.folder_scan_worker import FolderScanWorker


@pytest.fixture
def temp_video_dir(tmp_path):
    """Create temp directory with mixed-case video files."""
    # Create test files with unique names to avoid case-insensitive filesystem issues
    (tmp_path / "video1.mp4").write_text("test")
    (tmp_path / "video2.MP4").write_text("test")
    (tmp_path / "video2b.Mp4").write_text("test")
    (tmp_path / "video3.mkv").write_text("test")
    (tmp_path / "video4.MKV").write_text("test")
    (tmp_path / "._video5.mp4").write_text("test")  # macOS resource fork
    (tmp_path / "readme.txt").write_text("test")  # non-video

    # Create subdirectory
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "nested1.avi").write_text("test")
    (subdir / "nested2.AVI").write_text("test")
    (subdir / "nested3.mP4").write_text("test")

    return tmp_path


def test_single_traversal_optimization_uses_rglob_once(temp_video_dir, qtbot):
    """Test that worker uses rglob only once, not per-extension."""
    worker = FolderScanWorker(str(temp_video_dir), recursive=True)

    # Mock Path.rglob to count how many times it's called
    original_rglob = Path.rglob
    rglob_calls = []

    def tracked_rglob(self, pattern):
        rglob_calls.append(pattern)
        return original_rglob(self, pattern)

    completed_files = []
    worker.completed.connect(lambda files: completed_files.extend(files))

    with patch.object(Path, "rglob", tracked_rglob):
        worker.start()
        qtbot.waitUntil(lambda: not worker.isRunning(), timeout=5000)

    # Should only call rglob once with "*" pattern (single traversal)
    assert len(rglob_calls) == 1
    assert rglob_calls[0] == "*"

    # But still find all files
    assert len(completed_files) == 8


def test_single_traversal_finds_all_extensions(temp_video_dir, qtbot):
    """Test that worker finds all extensions in a single traversal."""
    worker = FolderScanWorker(str(temp_video_dir), recursive=True)

    completed_files = []

    def on_completed(files):
        completed_files.extend(files)

    worker.completed.connect(on_completed)

    # Run worker
    worker.start()
    qtbot.waitUntil(lambda: not worker.isRunning(), timeout=5000)

    # Verify all video files found (mixed case, but not resource fork)
    assert len(completed_files) == 8

    filenames = [Path(f).name for f in completed_files]
    assert "video1.mp4" in filenames
    assert "video2.MP4" in filenames
    assert "video2b.Mp4" in filenames
    assert "video3.mkv" in filenames
    assert "video4.MKV" in filenames
    assert "nested1.avi" in filenames
    assert "nested2.AVI" in filenames
    assert "nested3.mP4" in filenames

    # Verify resource fork excluded
    assert "._video5.mp4" not in filenames

    # Verify non-video excluded
    assert "readme.txt" not in filenames


def test_single_traversal_skips_resource_forks(temp_video_dir, qtbot):
    """Test that macOS resource forks (._*) are skipped."""
    worker = FolderScanWorker(str(temp_video_dir), recursive=True)

    completed_files = []
    worker.completed.connect(lambda files: completed_files.extend(files))

    worker.start()
    qtbot.waitUntil(lambda: not worker.isRunning(), timeout=5000)

    # No file should start with ._
    for file_path in completed_files:
        assert not Path(file_path).name.startswith("._")


def test_non_recursive_scan_single_level(temp_video_dir, qtbot):
    """Test non-recursive scan only finds files in root level."""
    worker = FolderScanWorker(str(temp_video_dir), recursive=False)

    completed_files = []
    worker.completed.connect(lambda files: completed_files.extend(files))

    worker.start()
    qtbot.waitUntil(lambda: not worker.isRunning(), timeout=5000)

    # Should find root files but not nested ones
    assert len(completed_files) == 5

    filenames = [Path(f).name for f in completed_files]
    assert "nested1.avi" not in filenames
    assert "nested2.AVI" not in filenames
    assert "nested3.mP4" not in filenames


def test_worker_emits_progress_signals(temp_video_dir, qtbot):
    """Test that worker emits progress signals during scan."""
    worker = FolderScanWorker(str(temp_video_dir), recursive=True)

    progress_signals = []
    worker.progress.connect(lambda count, msg: progress_signals.append((count, msg)))

    worker.start()
    qtbot.waitUntil(lambda: not worker.isRunning(), timeout=5000)

    # Should have emitted at least the initial progress
    assert len(progress_signals) > 0
    assert progress_signals[0][1].startswith("Scanning")


def test_worker_cancellation(temp_video_dir, qtbot):
    """Test that worker can be cancelled mid-scan."""
    # Add many files so the scan doesn't finish before cancel takes effect
    bulk_dir = temp_video_dir / "bulk"
    bulk_dir.mkdir()
    for i in range(200):
        (bulk_dir / f"video_{i:04d}.mp4").write_text("test")

    worker = FolderScanWorker(str(temp_video_dir), recursive=True)

    completed_called = []
    worker.completed.connect(lambda files: completed_called.append(True))

    worker.start()
    worker.cancel()

    # Wait deterministically for worker to finish
    qtbot.waitUntil(lambda: not worker.isRunning(), timeout=5000)

    # Completed should not be called when cancelled
    assert len(completed_called) == 0
