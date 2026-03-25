"""Manager for sorting video files into organized folder structures."""

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import QObject, QThread, pyqtSignal, QMutex, QMutexLocker

from ..data.models import VideoMetadata, SortCriterion

logger = logging.getLogger(__name__)


@dataclass
class SortResult:
    """Result of a sort operation."""

    source_path: str
    destination_path: str
    success: bool
    error_message: Optional[str] = None
    is_duplicate: bool = False


@dataclass
class FolderStructure:
    """Represents a proposed folder structure for sorting."""

    name: str
    children: Dict[str, "FolderStructure"] = field(default_factory=dict)
    files: List[str] = field(default_factory=list)

    def add_file(self, path_parts: List[str], file_path: str) -> None:
        """
        Add a file to the folder structure.

        Args:
            path_parts: List of folder names leading to this file
            file_path: The original file path
        """
        if not path_parts:
            self.files.append(file_path)
            return

        folder_name = path_parts[0]
        if folder_name not in self.children:
            self.children[folder_name] = FolderStructure(name=folder_name)

        self.children[folder_name].add_file(path_parts[1:], file_path)

    def get_flat_structure(self, prefix: str = "") -> List[Tuple[str, str]]:
        """
        Get a flat list of (relative_path, file_path) tuples.

        Args:
            prefix: Current path prefix

        Returns:
            List of (destination_relative_path, source_file_path) tuples
        """
        result = []
        current_path = f"{prefix}/{self.name}" if prefix else self.name

        for file_path in self.files:
            result.append((current_path, file_path))

        for child in self.children.values():
            result.extend(child.get_flat_structure(current_path))

        return result


class SortManager(QObject):
    """
    Manager for sorting video files into folder hierarchies.

    Signals:
        progress: Emits (current, total, file_path) during sort operation
        file_sorted: Emits SortResult for each file
        completed: Emits (success_count, failure_count, duplicate_count)
        error: Emits (error_message)
    """

    progress = pyqtSignal(int, int, str)  # current, total, file_path
    file_sorted = pyqtSignal(object)  # SortResult
    completed = pyqtSignal(
        int, int, int
    )  # success_count, failure_count, duplicate_count
    error = pyqtSignal(str)  # error_message

    def __init__(self, parent=None):
        """Initialize the sort manager."""
        super().__init__(parent)
        self._mutex = QMutex()
        self._cancelled = False

    def cancel(self) -> None:
        """Cancel the current sort operation."""
        with QMutexLocker(self._mutex):
            self._cancelled = True

    def build_folder_structure(
        self,
        metadata_list: List[VideoMetadata],
        criteria: List[SortCriterion],
        enabled_criteria: Dict[SortCriterion, bool],
        preserve_subfolders: bool = True,
    ) -> FolderStructure:
        """
        Build a proposed folder structure based on metadata and criteria.

        Args:
            metadata_list: List of VideoMetadata for files to sort
            criteria: Ordered list of sort criteria
            enabled_criteria: Dict mapping criteria to enabled state

        Returns:
            FolderStructure representing the proposed organization
        """
        root = FolderStructure(name="")

        for metadata in metadata_list:
            path_parts = []

            # Preserve original subfolder if enabled
            if preserve_subfolders and metadata.original_subfolder:
                # Add original subfolder parts first (handle both / and \ separators)
                import os

                subfolder_parts = (
                    metadata.original_subfolder.replace("/", os.sep)
                    .replace("\\", os.sep)
                    .split(os.sep)
                )
                path_parts.extend(subfolder_parts)

            for criterion in criteria:
                if not enabled_criteria.get(criterion, False):
                    continue

                folder_name = self._get_folder_name(metadata, criterion)
                if folder_name:
                    path_parts.append(folder_name)

            root.add_file(path_parts, metadata.file_path)

        return root

    def _get_folder_name(
        self, metadata: VideoMetadata, criterion: SortCriterion
    ) -> str:
        """
        Get the folder name for a file based on a criterion.

        Args:
            metadata: Video metadata
            criterion: Sort criterion

        Returns:
            Folder name string
        """
        if criterion == SortCriterion.FPS:
            return metadata.fps_label
        elif criterion == SortCriterion.RESOLUTION:
            return metadata.resolution
        elif criterion == SortCriterion.ORIENTATION:
            return metadata.orientation
        elif criterion == SortCriterion.CODEC:
            return metadata.codec.upper() if metadata.codec else "unknown"
        elif criterion == SortCriterion.BITRATE:
            return metadata.bitrate_label
        else:
            return ""

    def execute_sort(
        self,
        folder_structure: FolderStructure,
        destination_root: str,
        move_files: bool = True,
    ) -> Tuple[int, int, int]:
        """
        Execute the sort operation, moving/copying files.

        Args:
            folder_structure: The proposed folder structure
            destination_root: Root directory for sorted files
            move_files: If True, move files; if False, copy them

        Returns:
            Tuple of (success_count, failure_count, duplicate_count)
        """
        with QMutexLocker(self._mutex):
            self._cancelled = False

        flat_structure = folder_structure.get_flat_structure()
        total = len(flat_structure)
        success_count = 0
        failure_count = 0
        duplicate_count = 0

        for i, (rel_path, source_path) in enumerate(flat_structure):
            # Check cancellation
            with QMutexLocker(self._mutex):
                if self._cancelled:
                    logger.info("Sort operation cancelled")
                    break

            self.progress.emit(i + 1, total, source_path)

            try:
                # Build destination path
                source = Path(source_path)
                dest_dir = Path(destination_root) / rel_path
                dest_path = dest_dir / source.name

                # Create destination directory
                dest_dir.mkdir(parents=True, exist_ok=True)

                # Handle collision (duplicate detection)
                resolved_path = self._handle_collision(source, dest_path)

                if resolved_path is None:
                    # Duplicate detected -- delete source file
                    logger.info(
                        f"Deleted duplicate: {source_path} (matches {dest_path})"
                    )
                    if move_files:
                        source.unlink()
                    result = SortResult(
                        source_path=source_path,
                        destination_path=str(dest_path),
                        success=True,
                        is_duplicate=True,
                    )
                    duplicate_count += 1
                else:
                    # Move or copy the file
                    if move_files:
                        shutil.move(str(source), str(resolved_path))
                    else:
                        shutil.copy2(str(source), str(resolved_path))

                    result = SortResult(
                        source_path=source_path,
                        destination_path=str(resolved_path),
                        success=True,
                    )
                    success_count += 1

            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Failed to sort {source_path}: {error_msg}")
                result = SortResult(
                    source_path=source_path,
                    destination_path="",
                    success=False,
                    error_message=error_msg,
                )
                failure_count += 1

            self.file_sorted.emit(result)

        self.completed.emit(success_count, failure_count, duplicate_count)
        return success_count, failure_count, duplicate_count

    def _handle_collision(self, source: Path, dest: Path) -> Optional[Path]:
        """
        Handle a filename collision at the destination.

        Determines whether the collision is a true duplicate (same name + size)
        or a different file that happens to share a name.

        Args:
            source: Source file path
            dest: Desired destination path

        Returns:
            - dest unchanged if no collision exists
            - None if dest is a duplicate of source (same name + size) -- caller should delete source
            - A renamed path (e.g., video_1.mp4) if dest exists but has different size
        """
        if not dest.exists():
            return dest

        # Compare file sizes to determine if this is a true duplicate
        try:
            source_size = source.stat().st_size
            dest_size = dest.stat().st_size
        except OSError as e:
            logger.warning(f"Could not stat files for duplicate check: {e}")
            # Fall through to rename logic as safety measure
            source_size = -1
            dest_size = -2

        if source_size == dest_size:
            # Same filename + same size = duplicate -- signal caller to delete source
            return None

        # Different sizes -- these are different files with the same name.
        # Use _N suffix rename strategy.
        stem = dest.stem
        suffix = dest.suffix
        parent = dest.parent
        counter = 1

        while True:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1

            if counter > 1000:
                raise RuntimeError(f"Too many conflicting files for {dest}")

    def preview_structure(
        self,
        metadata_list: List[VideoMetadata],
        criteria: List[SortCriterion],
        enabled_criteria: Dict[SortCriterion, bool],
        preserve_subfolders: bool = True,
    ) -> Dict[str, List[str]]:
        """
        Generate a preview of the folder structure.

        Args:
            metadata_list: List of VideoMetadata
            criteria: Ordered list of criteria
            enabled_criteria: Dict of enabled states

        Returns:
            Dict mapping folder paths to lists of filenames
        """
        structure = self.build_folder_structure(
            metadata_list, criteria, enabled_criteria, preserve_subfolders
        )
        flat = structure.get_flat_structure()

        preview: Dict[str, List[str]] = {}
        for rel_path, source_path in flat:
            if rel_path not in preview:
                preview[rel_path] = []
            preview[rel_path].append(Path(source_path).name)

        return preview

    def build_unsort_structure(
        self, metadata_list: List[VideoMetadata], source_root: str
    ) -> Dict[str, str]:
        """
        Build a mapping for unsorting files back to their first-level parent folder.

        For each file, extracts the first subfolder under source_root and maps
        the file to be moved there.

        Example:
            source_root: H:\\Stuffy\\Instagram
            file: H:\\Stuffy\\Instagram\\Account1\\30fps\\1080p\\video.mp4
            result: video.mp4 -> H:\\Stuffy\\Instagram\\Account1\\video.mp4

        Args:
            metadata_list: List of VideoMetadata for files to unsort
            source_root: The root folder that was scanned

        Returns:
            Dict mapping source_path -> destination_path
        """
        source_root_path = Path(source_root)
        unsort_map: Dict[str, str] = {}

        for metadata in metadata_list:
            file_path = Path(metadata.file_path)

            try:
                # Get path relative to source root
                rel_path = file_path.relative_to(source_root_path)
                parts = rel_path.parts

                if len(parts) <= 1:
                    # File is already at root or first level, skip
                    continue

                # First part is the immediate subfolder, rest is nested structure
                first_subfolder = parts[0]
                filename = parts[-1]

                # Destination is source_root / first_subfolder / filename
                dest_path = source_root_path / first_subfolder / filename

                # Only add if file needs to move (not already at destination)
                if file_path != dest_path:
                    unsort_map[str(file_path)] = str(dest_path)

            except ValueError:
                # File is not under source_root, skip
                logger.warning(f"File {file_path} is not under {source_root_path}")
                continue

        return unsort_map

    def preview_unsort(
        self, metadata_list: List[VideoMetadata], source_root: str
    ) -> Dict[str, List[str]]:
        """
        Generate a preview of the unsort operation.

        Args:
            metadata_list: List of VideoMetadata
            source_root: The root folder that was scanned

        Returns:
            Dict mapping folder paths to lists of filenames that will be there
        """
        unsort_map = self.build_unsort_structure(metadata_list, source_root)
        source_root_path = Path(source_root)

        preview: Dict[str, List[str]] = {}
        for source_path, dest_path in unsort_map.items():
            dest = Path(dest_path)
            # Get relative path from source root for display
            try:
                rel_folder = str(dest.parent.relative_to(source_root_path))
            except ValueError:
                rel_folder = str(dest.parent)

            if rel_folder not in preview:
                preview[rel_folder] = []
            preview[rel_folder].append(dest.name)

        return preview

    def execute_unsort(
        self,
        unsort_map: Dict[str, str],
        move_files: bool = True,
        source_root: Optional[str] = None,
    ) -> Tuple[int, int, int]:
        """
        Execute the unsort operation, moving/copying files to their first-level folders.

        Args:
            unsort_map: Dict mapping source_path -> destination_path
            move_files: If True, move files; if False, copy them
            source_root: Root folder to clean up empty directories from (only used if move_files=True)

        Returns:
            Tuple of (success_count, failure_count, duplicate_count)
        """
        with QMutexLocker(self._mutex):
            self._cancelled = False

        total = len(unsort_map)
        success_count = 0
        failure_count = 0
        duplicate_count = 0

        for i, (source_path, dest_path) in enumerate(unsort_map.items()):
            # Check cancellation
            with QMutexLocker(self._mutex):
                if self._cancelled:
                    logger.info("Unsort operation cancelled")
                    break

            self.progress.emit(i + 1, total, source_path)

            try:
                source = Path(source_path)
                dest = Path(dest_path)

                # Ensure destination directory exists
                dest.parent.mkdir(parents=True, exist_ok=True)

                # Handle collision (duplicate detection)
                resolved_path = self._handle_collision(source, dest)

                if resolved_path is None:
                    # Duplicate detected -- delete source file
                    logger.info(
                        f"Deleted duplicate: {source_path} (matches {dest_path})"
                    )
                    if move_files:
                        source.unlink()
                    result = SortResult(
                        source_path=source_path,
                        destination_path=str(dest),
                        success=True,
                        is_duplicate=True,
                    )
                    duplicate_count += 1
                else:
                    # Move or copy the file
                    if move_files:
                        shutil.move(str(source), str(resolved_path))
                    else:
                        shutil.copy2(str(source), str(resolved_path))

                    result = SortResult(
                        source_path=source_path,
                        destination_path=str(resolved_path),
                        success=True,
                    )
                    success_count += 1

            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Failed to unsort {source_path}: {error_msg}")
                result = SortResult(
                    source_path=source_path,
                    destination_path="",
                    success=False,
                    error_message=error_msg,
                )
                failure_count += 1

            self.file_sorted.emit(result)

        # Clean up empty folders after moving files
        if move_files and source_root and (success_count > 0 or duplicate_count > 0):
            deleted_count = self._delete_empty_folders(source_root)
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} empty folders")

        self.completed.emit(success_count, failure_count, duplicate_count)
        return success_count, failure_count, duplicate_count

    def _delete_empty_folders(self, root_path: str) -> int:
        """
        Recursively delete empty folders under root_path.

        Walks the tree bottom-up to handle nested empty folders.
        Only deletes folders that are completely empty (no files, no subfolders).

        Args:
            root_path: Root directory to clean up

        Returns:
            Number of folders deleted
        """
        root = Path(root_path)
        deleted_count = 0

        # Walk bottom-up so we delete deepest empty folders first
        # This allows parent folders to become empty and be deleted too
        for dirpath in sorted(
            root.rglob("*"), key=lambda p: len(p.parts), reverse=True
        ):
            if not dirpath.is_dir():
                continue

            # Check if directory is empty
            try:
                # Use iterdir to check if empty (more efficient than listdir)
                if not any(dirpath.iterdir()):
                    dirpath.rmdir()
                    deleted_count += 1
                    logger.debug(f"Deleted empty folder: {dirpath}")
            except OSError as e:
                # Directory not empty or permission error
                logger.debug(f"Could not delete {dirpath}: {e}")
                continue

        return deleted_count


class SortWorker(QThread):
    """
    QThread worker for running sort/unsort operations off the main thread.

    Wraps SortManager.execute_sort() or execute_unsort() in a background thread.
    Progress and completion are communicated via the SortManager's existing signals.
    """

    def __init__(
        self,
        manager: SortManager,
        mode: str,
        parent=None,
        # Sort mode params
        folder_structure: Optional[FolderStructure] = None,
        destination_root: str = "",
        move_files: bool = True,
        # Unsort mode params
        unsort_map: Optional[Dict[str, str]] = None,
        source_root: Optional[str] = None,
    ):
        """
        Initialize the sort worker.

        Args:
            manager: SortManager instance (signals will be emitted from this)
            mode: "sort" or "unsort"
            folder_structure: Required for sort mode
            destination_root: Required for sort mode
            move_files: Whether to move (True) or copy (False) files
            unsort_map: Required for unsort mode
            source_root: Optional root for empty folder cleanup in unsort mode
        """
        super().__init__(parent)
        self._manager = manager
        self._mode = mode
        self._folder_structure = folder_structure
        self._destination_root = destination_root
        self._move_files = move_files
        self._unsort_map = unsort_map
        self._source_root = source_root

    def run(self) -> None:
        """Execute the sort or unsort operation in background thread."""
        try:
            if self._mode == "sort" and self._folder_structure is not None:
                self._manager.execute_sort(
                    self._folder_structure,
                    self._destination_root,
                    self._move_files,
                )
            elif self._mode == "unsort" and self._unsort_map is not None:
                self._manager.execute_unsort(
                    self._unsort_map,
                    self._move_files,
                    source_root=self._source_root,
                )
            else:
                self._manager.error.emit(f"Invalid sort worker mode: {self._mode}")
        except Exception as e:
            logger.exception(f"Sort worker error: {e}")
            self._manager.error.emit(str(e))
