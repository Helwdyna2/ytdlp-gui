"""Worker for extracting video metadata using ffprobe."""

import json
import logging
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import List, Optional, Tuple

from PyQt6.QtCore import QThread, pyqtSignal

from ..data.models import VideoMetadata
from ..utils.ffmpeg_utils import find_ffprobe
from ..utils.constants import SUPPORTED_VIDEO_EXTENSIONS
from ..utils.platform_utils import get_subprocess_kwargs

logger = logging.getLogger(__name__)

# Hardware-optimized defaults
# For AMD 9950X3D (24 cores/48 threads) + NVMe: use high concurrency
# ffprobe is I/O-bound, so we can use more workers than CPU cores
DEFAULT_MAX_WORKERS = min(32, (os.cpu_count() or 4) * 2)
# Batch size for progress updates to reduce signal overhead
PROGRESS_BATCH_SIZE = 8


class FFprobeWorker(QThread):
    """
    QThread worker for extracting video metadata from files.

    Optimized for high-end hardware with concurrent ffprobe execution.
    Uses ThreadPoolExecutor for parallel metadata extraction.

    Signals:
        progress: Emits (current_index, total_files, file_path) during scan
        metadata_ready: Emits VideoMetadata for each successfully probed file
        error: Emits (file_path, error_message) for failures
        completed: Emits list of all successfully extracted VideoMetadata
    """

    progress = pyqtSignal(int, int, str)  # current, total, file_path
    metadata_ready = pyqtSignal(object)  # VideoMetadata
    raw_metadata_ready = pyqtSignal(str, object)  # file_path, raw ffprobe JSON
    error = pyqtSignal(str, str)  # file_path, error_message
    completed = pyqtSignal(list)  # List[VideoMetadata]

    def __init__(
        self,
        file_paths: List[str],
        base_folder: Optional[str] = None,
        max_workers: Optional[int] = None,
        parent=None,
    ):
        """
        Initialize the ffprobe worker.

        Args:
            file_paths: List of video file paths to probe
            base_folder: Base folder for calculating relative paths (optional)
            max_workers: Number of concurrent ffprobe processes (default: auto-detect based on CPU)
            parent: Parent QObject
        """
        super().__init__(parent)
        self._file_paths = file_paths
        self._base_folder = Path(base_folder) if base_folder else None
        self._max_workers = max_workers or DEFAULT_MAX_WORKERS
        self._cancelled = False
        self._progress_lock = Lock()
        self._completed_count = 0

    def cancel(self) -> None:
        """Request cancellation of the probe operation."""
        self._cancelled = True

    def run(self) -> None:
        """Execute the ffprobe operations with parallel processing."""
        ffprobe_path = find_ffprobe()
        if not ffprobe_path:
            self.error.emit("", "ffprobe not found")
            self.completed.emit([])
            return

        results: List[VideoMetadata] = []
        results_lock = Lock()
        total = len(self._file_paths)

        if total == 0:
            self.completed.emit([])
            return

        # Use concurrent processing for large file sets
        # For small sets (<= 4 files), sequential is faster due to overhead
        if total <= 4:
            results = self._run_sequential(ffprobe_path, total)
        else:
            results = self._run_concurrent(ffprobe_path, total)

        self.completed.emit(results)

    def _run_sequential(self, ffprobe_path: str, total: int) -> List[VideoMetadata]:
        """Run ffprobe sequentially for small file sets."""
        results: List[VideoMetadata] = []

        for i, file_path in enumerate(self._file_paths):
            if self._cancelled:
                logger.info("FFprobe worker cancelled")
                break

            self.progress.emit(i + 1, total, file_path)

            try:
                metadata, raw_data = self._probe_file(ffprobe_path, file_path)
                self.raw_metadata_ready.emit(file_path, raw_data)
                if metadata:
                    results.append(metadata)
                    self.metadata_ready.emit(metadata)
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Failed to probe {file_path}: {error_msg}")
                self.error.emit(file_path, error_msg)

        return results

    def _run_concurrent(self, ffprobe_path: str, total: int) -> List[VideoMetadata]:
        """Run ffprobe concurrently for large file sets."""
        results: List[VideoMetadata] = []
        results_lock = Lock()

        def probe_with_result(
            file_path: str,
        ) -> Tuple[Optional[VideoMetadata], Optional[dict], Optional[str]]:
            """Probe a file and return (metadata, raw_data, error_msg)."""
            if self._cancelled:
                return None, None, None

            try:
                metadata, raw_data = self._probe_file(ffprobe_path, file_path)
                return metadata, raw_data, None
            except Exception as e:
                return None, None, str(e)

        # Use ThreadPoolExecutor for concurrent I/O-bound operations
        # Optimal for NVMe storage with high IOPS
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(probe_with_result, path): path
                for path in self._file_paths
            }

            # Process results as they complete
            for future in as_completed(future_to_path):
                if self._cancelled:
                    # Cancel remaining futures
                    for f in future_to_path:
                        f.cancel()
                    logger.info("FFprobe worker cancelled")
                    break

                file_path = future_to_path[future]

                # Update progress
                with self._progress_lock:
                    self._completed_count += 1
                    current = self._completed_count

                self.progress.emit(current, total, file_path)

                try:
                    metadata, raw_data, error_msg = future.result()

                    if error_msg:
                        logger.warning(f"Failed to probe {file_path}: {error_msg}")
                        self.error.emit(file_path, error_msg)
                    else:
                        if raw_data is not None:
                            self.raw_metadata_ready.emit(file_path, raw_data)
                        if metadata:
                            with results_lock:
                                results.append(metadata)
                            self.metadata_ready.emit(metadata)

                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"Failed to probe {file_path}: {error_msg}")
                    self.error.emit(file_path, error_msg)

        return results

    def _probe_file(
        self, ffprobe_path: str, file_path: str
    ) -> Tuple[Optional[VideoMetadata], dict]:
        """
        Probe a single file for metadata.

        Args:
            ffprobe_path: Path to ffprobe executable
            file_path: Path to video file

        Returns:
            Tuple of parsed VideoMetadata and raw ffprobe JSON
        """
        from ..utils.file_validation import is_zero_byte_file, move_to_trash

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check for zero-byte files and move to trash
        if is_zero_byte_file(file_path):
            logger.warning(f"Zero-byte file detected: {file_path}")
            if move_to_trash(file_path):
                logger.info(f"Moved zero-byte file to trash: {file_path}")
                raise ValueError(f"Zero-byte file moved to trash: {file_path}")
            else:
                logger.error(f"Failed to move zero-byte file to trash: {file_path}")
                raise ValueError(f"Cannot process zero-byte file: {file_path}")

        # Run ffprobe with JSON output
        cmd = [
            ffprobe_path,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",  # Handle non-UTF8 characters gracefully
            timeout=30,
            **get_subprocess_kwargs(),
        )

        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")

        if not result.stdout:
            raise RuntimeError("ffprobe returned empty output")

        data = json.loads(result.stdout)
        return self._parse_ffprobe_output(file_path, data), data

    def _parse_ffprobe_output(
        self, file_path: str, data: dict
    ) -> Optional[VideoMetadata]:
        """
        Parse ffprobe JSON output into VideoMetadata.

        Args:
            file_path: Original file path
            data: Parsed JSON from ffprobe

        Returns:
            VideoMetadata object
        """
        # Find the video stream
        video_stream = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                video_stream = stream
                break

        if not video_stream:
            return None

        # Extract dimensions
        width = video_stream.get("width", 0)
        height = video_stream.get("height", 0)

        # Extract FPS - prefer avg_frame_rate for accuracy
        # r_frame_rate is the container's declared rate, which may not match actual content
        # avg_frame_rate is calculated from actual frames and is what tools like Topaz use
        # Example: r_frame_rate="30/1" but avg_frame_rate="1223680/40791" = 29.998774 fps
        fps = 0.0

        # Try avg_frame_rate first (more accurate for variable/non-standard frame rates)
        avg_fps_str = video_stream.get("avg_frame_rate", "0/0")
        if "/" in avg_fps_str:
            num, den = avg_fps_str.split("/")
            if int(den) > 0:
                fps = float(num) / float(den)

        # Fall back to r_frame_rate if avg_frame_rate is invalid/zero
        if fps == 0.0:
            fps_str = video_stream.get("r_frame_rate", "0/1")
            if "/" in fps_str:
                num, den = fps_str.split("/")
                if int(den) > 0:
                    fps = float(num) / float(den)
            else:
                fps = float(fps_str)

        # Extract codec
        codec = video_stream.get("codec_name", "unknown")

        # Extract bitrate (from format or stream)
        bitrate = 0
        if "bit_rate" in video_stream:
            bitrate = int(video_stream["bit_rate"])
        elif "format" in data and "bit_rate" in data["format"]:
            bitrate = int(data["format"]["bit_rate"])

        # Extract duration
        duration = 0.0
        if "duration" in video_stream:
            duration = float(video_stream["duration"])
        elif "format" in data and "duration" in data["format"]:
            duration = float(data["format"]["duration"])

        # Get file size
        file_size = Path(file_path).stat().st_size

        # Calculate relative subfolder path from base
        original_subfolder = ""
        if self._base_folder:
            try:
                file_obj = Path(file_path)
                rel_path = file_obj.parent.relative_to(self._base_folder)
                original_subfolder = str(rel_path) if str(rel_path) != "." else ""
            except ValueError:
                # File is not relative to base folder
                pass

        return VideoMetadata(
            file_path=file_path,
            width=width,
            height=height,
            fps=fps,
            codec=codec,
            bitrate=bitrate,
            duration=duration,
            file_size=file_size,
            original_subfolder=original_subfolder,
        )


def delete_macos_dotfiles(
    folder_path: str, recursive: bool = True
) -> Tuple[int, List[str]]:
    """
    Delete macOS dotfiles (AppleDouble resource fork files starting with '._').

    These files are created by macOS when copying files to non-HFS+ volumes
    and are typically unwanted clutter on other operating systems.

    Args:
        folder_path: Path to folder to clean
        recursive: Whether to clean subdirectories

    Returns:
        Tuple of (deleted_count, list of deleted file paths)
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        return 0, []

    deleted_files = []
    pattern = "**/._*" if recursive else "._*"

    for file_path in folder.glob(pattern):
        if file_path.is_file() and file_path.name.startswith("._"):
            try:
                file_path.unlink()
                deleted_files.append(str(file_path))
                logger.debug(f"Deleted macOS dotfile: {file_path}")
            except OSError as e:
                logger.warning(f"Failed to delete dotfile {file_path}: {e}")

    if deleted_files:
        logger.info(f"Deleted {len(deleted_files)} macOS dotfiles from {folder_path}")

    return len(deleted_files), deleted_files


def scan_folder_for_videos(folder_path: str, recursive: bool = True) -> List[str]:
    """
    Scan a folder for video files.

    DEPRECATED: This function blocks the calling thread. For UI applications,
    prefer using FolderScanWorker from folder_scan_worker.py to scan in a background thread.

    This function is kept for backward compatibility with existing code.

    Args:
        folder_path: Path to folder to scan
        recursive: Whether to scan subdirectories

    Returns:
        List of video file paths
    """
    from .folder_scan_worker import scan_folder_for_videos as _scan

    return _scan(folder_path, recursive)
