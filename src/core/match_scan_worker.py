"""Worker for scanning and parsing video files for matching in a background thread."""

import logging
import os
from pathlib import Path
from typing import List

from PyQt6.QtCore import QThread, pyqtSignal

from ..data.models import MatchConfig, MatchResult, MatchStatus
from .filename_parser import FilenameParser

logger = logging.getLogger(__name__)

# Video file extensions to scan for (same as MatchManager)
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".wmv", ".mov", ".flv", ".webm", ".m4v"}


class MatchScanWorker(QThread):
    """
    QThread worker for scanning folders and parsing filenames for matching.

    Moves the folder scan and filename parsing logic off the UI thread.
    Reuses the same parsing/config behavior from MatchManager.scan_folder().

    Signals:
        progress: Emits (current, total) during scan
        completed: Emits List[MatchResult] when done
        error: Emits error_message if scan fails
    """

    progress = pyqtSignal(int, int)  # current, total
    completed = pyqtSignal(list)  # List[MatchResult]
    error = pyqtSignal(str)  # error_message

    def __init__(self, folder_path: str, config: MatchConfig, parent=None):
        """
        Initialize the match scan worker.

        Args:
            folder_path: Path to folder to scan
            config: MatchConfig with parsing settings
            parent: Parent QObject
        """
        super().__init__(parent)
        self._folder_path = folder_path
        self._config = config
        self._cancelled = False
        self._parser = FilenameParser(config.custom_studios, config.skip_keywords)

    def cancel(self) -> None:
        """Request cancellation of the scan."""
        self._cancelled = True

    def run(self) -> None:
        """Execute the folder scan and filename parsing."""
        try:
            folder = Path(self._folder_path)
            if not folder.is_dir():
                self.error.emit(f"Not a directory: {self._folder_path}")
                return

            # Find all video files (same logic as MatchManager.scan_folder)
            video_files = []
            for root, _dirs, files in os.walk(folder):
                if self._cancelled:
                    logger.info("Match scan cancelled")
                    return

                for file in files:
                    ext = Path(file).suffix.lower()
                    if ext in VIDEO_EXTENSIONS:
                        full_path = os.path.join(root, file)
                        video_files.append(full_path)

                # Emit discovery progress (total unknown during traversal)
                self.progress.emit(len(video_files), 0)

            logger.info(f"Found {len(video_files)} video file(s)")

            # Parse each filename
            results: List[MatchResult] = []
            for i, file_path in enumerate(video_files):
                if self._cancelled:
                    logger.info("Match scan cancelled during parsing")
                    return

                filename = Path(file_path).name

                # Check if file should be included
                if not self._config.include_already_named:
                    # Skip if file looks already named (has studio - performer - title format)
                    if self._looks_already_named(filename):
                        logger.debug(f"Skipping already-named file: {filename}")
                        result = MatchResult(
                            file_path=file_path,
                            original_filename=filename,
                            status=MatchStatus.SKIPPED,
                        )
                        results.append(result)
                        continue

                # Parse filename
                parsed = self._parser.parse(filename)

                # Create result
                result = MatchResult(
                    file_path=file_path,
                    original_filename=filename,
                    status=MatchStatus.PENDING,
                    parsed=parsed,
                )
                results.append(result)

                # Emit progress
                self.progress.emit(i + 1, len(video_files))

            logger.info(f"Parsed {len(results)} file(s)")
            self.completed.emit(results)

        except Exception as e:
            logger.exception(f"Error scanning folder for matching: {e}")
            self.error.emit(f"Error scanning folder: {e}")

    def _looks_already_named(self, filename: str) -> bool:
        """
        Check if filename looks already properly named.

        Heuristic: Contains at least 2 dashes (studio - performer - title format)

        Args:
            filename: Filename to check

        Returns:
            True if looks already named
        """
        # Remove extension
        name_no_ext = Path(filename).stem

        # Count dashes
        dash_count = name_no_ext.count(" - ")

        # If has at least 2 dashes in format " - ", likely already named
        return dash_count >= 2
