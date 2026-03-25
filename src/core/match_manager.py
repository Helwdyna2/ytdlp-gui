"""Match manager for orchestrating the video matching workflow."""

import logging
import os
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from ..data.models import (
    MatchConfig,
    MatchResult,
    MatchStatus,
    SceneMetadata,
    ParsedFilename,
)
from ..services.config_service import ConfigService
from .filename_parser import FilenameParser

logger = logging.getLogger(__name__)

# Video file extensions to scan for
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".wmv", ".mov", ".flv", ".webm", ".m4v"}


class MatchManager(QObject):
    """
    Orchestrates the video matching workflow.

    Signals:
        scan_started: Emitted when folder scan begins
        scan_progress: (current: int, total: int) Progress during scan
        scan_completed: (files: List[MatchResult]) Scan finished with file list
        match_started: Emitted when matching begins
        match_progress: (file_index: int, status: str, percent: float) Progress during matching
        match_result: (file_index: int, result: MatchResult) Individual file matched
        login_required: (database: str, url: str) User needs to login
        match_completed: Emitted when all matching is done
        rename_started: Emitted when renaming begins
        rename_progress: (current: int, total: int) Progress during rename
        rename_completed: (success: int, failed: int) Rename finished
        error: (message: str) Error occurred
    """

    # Signals
    scan_started = pyqtSignal()
    scan_progress = pyqtSignal(int, int)
    scan_completed = pyqtSignal(list)
    match_started = pyqtSignal()
    match_progress = pyqtSignal(int, str, float)
    match_result = pyqtSignal(int, object)
    login_required = pyqtSignal(str, str)
    match_completed = pyqtSignal()
    rename_started = pyqtSignal()
    rename_progress = pyqtSignal(int, int)
    rename_completed = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = MatchConfig()
        self._files: List[MatchResult] = []
        self._parser: Optional[FilenameParser] = None
        self._worker = None  # Will hold MatchWorker instance
        self._config_service = ConfigService()

    def set_config(self, config: MatchConfig) -> None:
        """
        Update configuration.

        Args:
            config: New MatchConfig to use
        """
        self._config = config
        self._parser = FilenameParser(config.custom_studios, config.skip_keywords)
        logger.info(f"Config updated: {config}")

    def scan_folder(self, folder_path: str) -> None:
        """
        Scan folder for video files and parse filenames.

        Populates self._files with MatchResult objects containing parsed data.

        Args:
            folder_path: Path to folder to scan
        """
        logger.info(f"Scanning folder: {folder_path}")
        self.scan_started.emit()

        try:
            # Ensure parser is initialized
            if self._parser is None:
                self._parser = FilenameParser(
                    self._config.custom_studios, self._config.skip_keywords
                )

            # Find all video files
            folder = Path(folder_path)
            video_files = []

            for root, dirs, files in os.walk(folder):
                for file in files:
                    ext = Path(file).suffix.lower()
                    if ext in VIDEO_EXTENSIONS:
                        full_path = os.path.join(root, file)
                        video_files.append(full_path)

                # Emit progress during scan
                self.scan_progress.emit(len(video_files), len(video_files))

            logger.info(f"Found {len(video_files)} video file(s)")

            # Parse each filename
            self._files = []
            for i, file_path in enumerate(video_files):
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
                        self._files.append(result)
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
                self._files.append(result)

                # Emit progress
                self.scan_progress.emit(i + 1, len(video_files))

            logger.info(f"Parsed {len(self._files)} file(s)")
            self.scan_completed.emit(self._files)

        except Exception as e:
            logger.exception(f"Error scanning folder: {e}")
            self.error.emit(f"Error scanning folder: {e}")

    def start_matching(self) -> None:
        """Start the matching process for scanned files."""
        if not self._files:
            self.error.emit("No files to match. Please scan a folder first.")
            return

        logger.info("Starting matching process")
        self.match_started.emit()

        try:
            # Import here to avoid circular dependency
            from .match_worker import MatchWorker

            # Use global Playwright profile directory
            cookies_dir = self._config_service.get("auth.profile_dir", "")
            if not cookies_dir:
                config_dir = Path(self._config_service.config_path).parent
                cookies_dir = str(config_dir / "browser_profiles" / "global")
                os.makedirs(cookies_dir, exist_ok=True)
                self._config_service.set("auth.profile_dir", cookies_dir, save=True)

            # Create worker
            self._worker = MatchWorker(
                files=self._files,
                config=self._config,
                cookies_dir=cookies_dir,
                parent=self,
            )

            # Connect signals
            self._worker.progress.connect(self._on_worker_progress)
            self._worker.match_found.connect(self._on_worker_match_found)
            self._worker.login_required.connect(self._on_worker_login_required)
            self._worker.login_completed.connect(self._on_worker_login_completed)
            self._worker.error.connect(self._on_worker_error)
            self._worker.completed.connect(self._on_worker_completed)

            # Start worker
            self._worker.start()

        except Exception as e:
            logger.exception(f"Error starting matching: {e}")
            self.error.emit(f"Error starting matching: {e}")

    def stop_matching(self) -> None:
        """Stop the matching process."""
        if self._worker:
            logger.info("Stopping matching process")
            self._worker.cancel()

    def confirm_login(self, database: str) -> None:
        """
        Confirm user has logged in to database.

        Args:
            database: Name of database ('porndb' or 'stashdb')
        """
        if self._worker:
            self._worker.confirm_login(database)

    def select_match(self, file_index: int, match: SceneMetadata) -> None:
        """
        Select a specific match for a file.

        Args:
            file_index: Index of file in self._files
            match: Selected SceneMetadata
        """
        if file_index < len(self._files):
            result = self._files[file_index]
            result.selected_match = match
            result.status = MatchStatus.MATCHED
            result.new_filename = self.generate_new_filename(result)

            logger.info(f"Selected match for {result.original_filename}: {match.title}")
            self.match_result.emit(file_index, result)

    def rename_files(self, file_indices: List[int]) -> None:
        """
        Rename selected files to matched names.

        Args:
            file_indices: List of indices in self._files to rename
        """
        logger.info(f"Renaming {len(file_indices)} file(s)")
        self.rename_started.emit()

        success = 0
        failed = 0

        for i, idx in enumerate(file_indices):
            if idx >= len(self._files):
                continue

            result = self._files[idx]

            # Skip if no match selected
            if not result.selected_match or not result.new_filename:
                logger.warning(
                    f"No match for {result.original_filename}, skipping rename"
                )
                failed += 1
                continue

            # Generate new path
            old_path = Path(result.file_path)
            new_path = old_path.parent / result.new_filename

            # Check if target already exists
            if new_path.exists():
                logger.error(f"Target file already exists: {new_path}")
                failed += 1
                continue

            # Rename file
            try:
                old_path.rename(new_path)
                result.file_path = str(new_path)
                result.status = MatchStatus.RENAMED
                success += 1
                logger.info(f"Renamed: {old_path.name} -> {new_path.name}")
            except Exception as e:
                logger.exception(f"Error renaming {old_path}: {e}")
                result.error_message = str(e)
                result.status = MatchStatus.FAILED
                failed += 1

            # Emit progress
            self.rename_progress.emit(i + 1, len(file_indices))
            self.match_result.emit(idx, result)

        logger.info(f"Rename complete: {success} succeeded, {failed} failed")
        self.rename_completed.emit(success, failed)

    def generate_new_filename(self, result: MatchResult) -> Optional[str]:
        """
        Generate new filename based on selected match and config.

        Format: {studio} - {performer} - {title} - {tags}.{ext}

        Args:
            result: MatchResult with selected_match

        Returns:
            New filename string or None if no match
        """
        if not result.selected_match:
            return None

        match = result.selected_match
        ext = Path(result.file_path).suffix

        # Build components
        studio = self._sanitize_filename(match.studio)
        performers = ", ".join(self._sanitize_filename(p) for p in match.performers)
        title = self._sanitize_filename(match.title)

        # Base name
        new_name = f"{studio} - {performers} - {title}"

        # Append preserved tags if enabled
        if (
            self._config.preserve_tags
            and result.parsed
            and result.parsed.preserved_tags
        ):
            # Join tags with commas
            tags = ", ".join(result.parsed.preserved_tags)
            new_name = f"{new_name} - {tags}"

        return f"{new_name}{ext}"

    def get_files(self) -> List[MatchResult]:
        """
        Get current file list.

        Returns:
            List of MatchResult objects
        """
        return self._files

    def set_scan_results(self, files: List[MatchResult]) -> None:
        """
        Set the file list from an external scan (e.g., MatchScanWorker).

        Args:
            files: List of MatchResult objects from the scan
        """
        self._files = files

    # === Private Methods ===

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

    def _sanitize_filename(self, text: str) -> str:
        """
        Remove/replace characters invalid in filenames.

        Args:
            text: Text to sanitize

        Returns:
            Sanitized text safe for filenames
        """
        # Remove: < > : " / \ | ? *
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            text = text.replace(char, "")
        return text.strip()

    # === Worker Signal Handlers ===

    def _on_worker_progress(self, file_index: int, status_message: str) -> None:
        """Handle progress from worker."""
        percent = (file_index + 1) / len(self._files)
        self.match_progress.emit(file_index, status_message, percent)

    def _on_worker_match_found(
        self, file_index: int, match_result: MatchResult
    ) -> None:
        """Handle match found by worker."""
        if file_index < len(self._files):
            self._files[file_index] = match_result

            # If single match found, auto-generate filename
            if (
                match_result.status == MatchStatus.MATCHED
                and match_result.selected_match
            ):
                match_result.new_filename = self.generate_new_filename(match_result)

            self.match_result.emit(file_index, match_result)

    def _on_worker_login_required(self, database_name: str, url: str) -> None:
        """Handle login required from worker."""
        self.login_required.emit(database_name, url)

    def _on_worker_login_completed(self, database_name: str) -> None:
        """Handle login completed from worker."""
        logger.info(f"Login completed for {database_name}")

    def _on_worker_error(self, file_index: int, error_message: str) -> None:
        """Handle error from worker."""
        if file_index < len(self._files):
            result = self._files[file_index]
            result.status = MatchStatus.FAILED
            result.error_message = error_message
            self.match_result.emit(file_index, result)

    def _on_worker_completed(self) -> None:
        """Handle worker completion."""
        logger.info("Matching worker completed")
        self.match_completed.emit()
        self._worker = None
