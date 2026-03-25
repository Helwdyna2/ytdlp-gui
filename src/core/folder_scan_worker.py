"""Worker for scanning folders for video files in a background thread."""

import logging
from pathlib import Path
from typing import List

from PyQt6.QtCore import QThread, pyqtSignal

from ..utils.constants import SUPPORTED_VIDEO_EXTENSIONS
from ..utils.file_validation import cleanup_zero_byte_files

logger = logging.getLogger(__name__)


class FolderScanWorker(QThread):
    """
    QThread worker for scanning folders for video files.

    Prevents UI freezing when scanning large directories with many files.

    Signals:
        progress: Emits (current_count, message) during scan
        completed: Emits list of video file paths when done
        files_deleted: Emits (count, paths) when zero-byte files are moved to trash
        error: Emits error_message if scan fails
    """

    progress = pyqtSignal(int, str)  # count, message
    completed = pyqtSignal(list)  # List[str] of file paths
    files_deleted = pyqtSignal(int, list)  # count, paths of trashed files
    error = pyqtSignal(str)  # error_message

    def __init__(self, folder_path: str, recursive: bool = True, parent=None):
        """
        Initialize the folder scan worker.

        Args:
            folder_path: Path to folder to scan
            recursive: Whether to scan subdirectories
            parent: Parent QObject
        """
        super().__init__(parent)
        self._folder_path = folder_path
        self._recursive = recursive
        self._cancelled = False

    def cancel(self) -> None:
        """Request cancellation of the scan."""
        self._cancelled = True

    def run(self) -> None:
        """Execute the folder scan using single directory traversal."""
        try:
            folder = Path(self._folder_path)
            if not folder.is_dir():
                self.error.emit(f"Not a directory: {self._folder_path}")
                return

            video_files = []
            self.progress.emit(0, f"Scanning {folder.name}...")

            # Build set of supported extensions (normalized to lowercase)
            supported_exts = set()
            for ext in SUPPORTED_VIDEO_EXTENSIONS:
                supported_exts.add(ext.lower())

            # Single traversal: walk directory once and check each file
            if self._recursive:
                # Use rglob for recursive scan (single traversal)
                for file_path in folder.rglob("*"):
                    if self._cancelled:
                        logger.info("Folder scan cancelled")
                        return

                    # Check if it's a file with supported extension (case-insensitive)
                    if (
                        file_path.is_file()
                        and file_path.suffix.lower() in supported_exts
                        and not file_path.name.startswith("._")
                    ):
                        video_files.append(str(file_path))

                        # Emit progress every 10 files
                        if len(video_files) % 10 == 0:
                            self.progress.emit(
                                len(video_files), f"Found {len(video_files)} videos..."
                            )
            else:
                # Non-recursive: only scan immediate children
                for file_path in folder.iterdir():
                    if self._cancelled:
                        logger.info("Folder scan cancelled")
                        return

                    if (
                        file_path.is_file()
                        and file_path.suffix.lower() in supported_exts
                        and not file_path.name.startswith("._")
                    ):
                        video_files.append(str(file_path))

                        if len(video_files) % 10 == 0:
                            self.progress.emit(
                                len(video_files), f"Found {len(video_files)} videos..."
                            )

            # Sort files
            video_files = sorted(video_files)

            # Clean up zero-byte files
            valid_files, trashed_files = cleanup_zero_byte_files(video_files)

            if trashed_files:
                self.files_deleted.emit(len(trashed_files), trashed_files)

            logger.info(
                f"Found {len(valid_files)} valid video files in {self._folder_path}"
            )
            self.completed.emit(valid_files)

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"Folder scan error: {error_msg}")
            self.error.emit(error_msg)


def scan_folder_for_videos(folder_path: str, recursive: bool = True) -> List[str]:
    """
    Scan a folder for video files synchronously using single traversal.

    NOTE: This function blocks the calling thread. For UI applications,
    prefer using FolderScanWorker to scan in a background thread.

    Args:
        folder_path: Path to folder to scan
        recursive: Whether to scan subdirectories

    Returns:
        List of video file paths
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        return []

    video_files = []

    # Build set of supported extensions (normalized to lowercase)
    supported_exts = set()
    for ext in SUPPORTED_VIDEO_EXTENSIONS:
        supported_exts.add(ext.lower())

    # Single traversal
    if recursive:
        for file_path in folder.rglob("*"):
            if (
                file_path.is_file()
                and file_path.suffix.lower() in supported_exts
                and not file_path.name.startswith("._")
            ):
                video_files.append(str(file_path))
    else:
        for file_path in folder.iterdir():
            if (
                file_path.is_file()
                and file_path.suffix.lower() in supported_exts
                and not file_path.name.startswith("._")
            ):
                video_files.append(str(file_path))

    return sorted(video_files)
