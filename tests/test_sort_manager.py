"""Tests for sort manager duplicate detection."""

import os
import shutil
import tempfile
from pathlib import Path

from src.core.sort_manager import SortResult


def test_sort_result_default_not_duplicate():
    """SortResult defaults to not being a duplicate."""
    result = SortResult(source_path="/a.mp4", destination_path="/b.mp4", success=True)
    assert result.is_duplicate is False


def test_sort_result_duplicate_flag():
    """SortResult can be marked as a duplicate."""
    result = SortResult(
        source_path="/a.mp4",
        destination_path="/b.mp4",
        success=True,
        is_duplicate=True,
    )
    assert result.is_duplicate is True


from src.core.sort_manager import SortManager


class TestHandleCollision:
    """Tests for SortManager._handle_collision()."""

    def setup_method(self):
        """Create temp directory for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = SortManager()

    def teardown_method(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_no_collision_returns_path_unchanged(self):
        """When destination doesn't exist, return it as-is."""
        dest = Path(self.temp_dir) / "video.mp4"
        source = Path(self.temp_dir) / "source.mp4"
        source.write_bytes(b"x" * 100)

        result = self.manager._handle_collision(source, dest)
        assert result == dest

    def test_same_name_same_size_returns_none(self):
        """When destination exists with same size, return None (duplicate)."""
        content = b"x" * 100
        source = Path(self.temp_dir) / "source" / "video.mp4"
        source.parent.mkdir(parents=True)
        source.write_bytes(content)

        dest = Path(self.temp_dir) / "dest" / "video.mp4"
        dest.parent.mkdir(parents=True)
        dest.write_bytes(content)

        result = self.manager._handle_collision(source, dest)
        assert result is None

    def test_same_name_different_size_renames(self):
        """When destination exists with different size, rename with _N suffix."""
        source = Path(self.temp_dir) / "source" / "video.mp4"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"x" * 100)

        dest = Path(self.temp_dir) / "dest" / "video.mp4"
        dest.parent.mkdir(parents=True)
        dest.write_bytes(b"y" * 200)  # Different size

        result = self.manager._handle_collision(source, dest)
        assert result is not None
        assert result != dest
        assert result.stem == "video_1"
        assert result.suffix == ".mp4"

    def test_rename_increments_counter(self):
        """When multiple collisions exist, counter increments."""
        source = Path(self.temp_dir) / "source" / "video.mp4"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"x" * 100)

        dest_dir = Path(self.temp_dir) / "dest"
        dest_dir.mkdir(parents=True)
        (dest_dir / "video.mp4").write_bytes(b"y" * 200)
        (dest_dir / "video_1.mp4").write_bytes(b"z" * 300)

        result = self.manager._handle_collision(source, dest_dir / "video.mp4")
        assert result.name == "video_2.mp4"


from src.core.sort_manager import FolderStructure


class TestExecuteSortDuplicates:
    """Tests for duplicate handling during sort execution."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = SortManager()
        self.results: list = []
        self.manager.file_sorted.connect(self.results.append)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sort_deletes_duplicate_and_reports(self):
        """When sorting would create a duplicate, delete source and report it."""
        source_dir = Path(self.temp_dir) / "source"
        source_dir.mkdir()
        dest_dir = Path(self.temp_dir) / "dest"
        dest_dir.mkdir()

        # Create source file
        source_file = source_dir / "video.mp4"
        source_file.write_bytes(b"x" * 100)

        # Create identical file already at destination root
        dest_file = dest_dir / "video.mp4"
        dest_file.write_bytes(b"x" * 100)

        # Build a trivial folder structure: no criteria = files go to root
        structure = FolderStructure(name="")
        structure.files.append(str(source_file))

        success, failures, duplicates = self.manager.execute_sort(
            structure, str(dest_dir), move_files=True
        )

        assert duplicates == 1
        assert success == 0
        assert failures == 0
        assert not source_file.exists(), "Source duplicate should be deleted"
        assert dest_file.exists(), "Destination file should remain"
        assert len(self.results) == 1
        assert self.results[0].is_duplicate is True
