"""QThread worker for individual yt-dlp downloads."""

import logging
import os
import re
import threading
import time
from typing import Any, Dict, Optional, Callable, Set

import yt_dlp
from yt_dlp.utils import parse_bytes
from PyQt6.QtCore import QThread, pyqtSignal

from ..data.models import OutputConfig, ProgressInfo
from ..services.config_service import ConfigService
from ..utils.constants import DEFAULT_FORMAT, VIDEO_ONLY_FORMAT, DEFAULT_MERGE_FORMAT
from ..utils.url_redaction import redact_url, redact_urls_in_text

logger = logging.getLogger(__name__)

# Force a consistent filename format across all sites.
# Uses yt-dlp's "fallback key" syntax: %(a,b,c)s picks the first non-empty field.
# Note: Sequential numbering is added in _build_outtmpl() method.
AUTHOR_ID_BASE = (
    "%(uploader,creator,channel,artist,uploader_id,channel_id,webpage_url_domain)s"
    " - %(id)s"
)

# Cache for directory listings to optimize sequence number generation
# Maps directory path to set of existing filenames
_dir_listing_cache: Dict[str, Set[str]] = {}
_dir_listing_cache_lock = threading.Lock()


def _get_cached_dir_listing(directory: str) -> Set[str]:
    """
    Get cached directory listing, populating cache if needed.

    Args:
        directory: Directory path to list

    Returns:
        Set of filenames in the directory
    """
    with _dir_listing_cache_lock:
        if directory not in _dir_listing_cache:
            if os.path.isdir(directory):
                try:
                    _dir_listing_cache[directory] = set(os.listdir(directory))
                except OSError:
                    _dir_listing_cache[directory] = set()
            else:
                _dir_listing_cache[directory] = set()
        return _dir_listing_cache[directory]


def clear_dir_listing_cache(directory: Optional[str] = None) -> None:
    """
    Clear the directory listing cache.

    Args:
        directory: Specific directory to clear, or None to clear all
    """
    global _dir_listing_cache
    with _dir_listing_cache_lock:
        if directory is None:
            _dir_listing_cache.clear()
        elif directory in _dir_listing_cache:
            del _dir_listing_cache[directory]


def _find_next_sequence_number(output_dir: str, base_pattern: str) -> int:
    """
    Find the next available sequence number for a file pattern.

    Uses cached directory listing for O(1) lookups instead of repeated
    filesystem calls. Optimized for large directories.

    Args:
        output_dir: Directory where files will be saved
        base_pattern: Base filename pattern without sequence number or extension
                      (e.g., "Author - video_id")

    Returns:
        Next available sequence number (starts at 1)
    """
    # Get cached directory listing for O(1) lookups
    existing_files = _get_cached_dir_listing(output_dir)

    if not existing_files:
        return 1

    # Build prefix to match: "base_pattern - "
    prefix = f"{base_pattern} - "

    # Extract sequence numbers from existing files matching the pattern
    # Pattern: "base_pattern - NNN.ext" where NNN is 3 digits
    max_seq = 0

    for filename in existing_files:
        # Fast prefix check before regex
        if not filename.startswith(prefix):
            continue

        # Extract sequence number using regex on the relevant part
        # Look for " - NNN." pattern near the end
        match = re.search(r" - (\d{3})\.[^.]+$", filename)
        if match:
            seq_num = int(match.group(1))
            max_seq = max(max_seq, seq_num)

    return max_seq + 1


def _build_retry_sleep_function(
    mode: str,
    start: float,
    end: float,
    step: float,
    base: float,
) -> Optional[Callable[[int], float]]:
    """Build a retry sleep function matching yt-dlp behavior."""
    if mode == "off" or start <= 0:
        return None

    limit = end if end > 0 else float("inf")

    if mode == "exp":
        base_value = base if base > 0 else 2.0

        def exp_func(n: int) -> float:
            return min(start * (base_value**n), limit)

        return exp_func

    step_value = step if step > 0 else start

    def linear_func(n: int) -> float:
        return min(start + step_value * n, limit)

    return linear_func


class DownloadWorker(QThread):
    """
    Worker thread for individual yt-dlp downloads.

    Each worker handles ONE URL to simplify cancellation and progress tracking.
    Progress is reported via Qt signals (thread-safe).
    """

    # Signals for communication with main thread
    progress = pyqtSignal(dict)  # Progress info dict
    completed = pyqtSignal(bool, str, dict)  # success, message, metadata
    log = pyqtSignal(str, str)  # level, message
    title_found = pyqtSignal(str)  # Video title

    def __init__(self, url: str, config: OutputConfig, parent=None):
        super().__init__(parent)
        self.url = url
        self.config = config
        self._is_cancelled = False
        self._current_title: Optional[str] = None
        self._current_filename: Optional[str] = None
        self._total_bytes: int = 0
        self._config_service = ConfigService()
        # Throttle progress signals to avoid UI jank (10Hz max)
        self._last_progress_time = 0
        self._progress_throttle_ms = 100  # 100ms = 10Hz

    def run(self):
        """Execute download in worker thread."""
        try:
            logger.info("Starting download: %s", redact_url(self.url))

            # First, extract info without downloading to get metadata
            extract_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
            }
            if self.config.cookies_path:
                extract_opts["cookiefile"] = self.config.cookies_path

            with yt_dlp.YoutubeDL(extract_opts) as ydl:
                # Check cancellation before starting
                if self._is_cancelled:
                    self.completed.emit(False, "Cancelled", {"url": self.url})
                    return

                # Extract info first to get title and metadata for filename
                info = None
                try:
                    info = ydl.extract_info(self.url, download=False)
                    if info:
                        self._current_title = info.get("title", self.url)
                        self.title_found.emit(self._current_title)
                        self.log.emit("info", f"Found: {self._current_title}")
                except Exception as e:
                    logger.warning(f"Could not extract info: {e}")
                    self._current_title = self.url

            # Check cancellation again
            if self._is_cancelled:
                self.completed.emit(False, "Cancelled", {"url": self.url})
                return

            # Build output template with sequence number
            outtmpl = self._build_outtmpl(info)

            # Build download options
            ydl_opts = self._build_options(outtmpl)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Perform download
                ydl.download([self.url])

            if not self._is_cancelled:
                completion_label = self._current_title or redact_url(self.url)
                self.log.emit("info", f"Completed: {completion_label}")
                self.completed.emit(
                    True,
                    "Success",
                    {
                        "title": self._current_title,
                        "url": self.url,
                        "filename": self._current_filename,
                        "total_bytes": self._total_bytes,
                    },
                )

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if "Cancelled" in error_msg:
                self.completed.emit(False, "Cancelled", {"url": self.url})
            else:
                redacted_url = redact_url(self.url)
                redacted_message = redact_urls_in_text(error_msg)
                logger.error("Download error for %s: %s", redacted_url, redacted_message)
                self.log.emit("error", f"Error: {redacted_message[:100]}")
                self.completed.emit(False, redacted_message, {"url": self.url})

        except Exception as e:
            redacted_url = redact_url(self.url)
            redacted_message = redact_urls_in_text(str(e))
            logger.exception(
                "Unexpected error downloading %s: %s", redacted_url, redacted_message
            )
            self.log.emit("error", f"Error: {redacted_message[:100]}")
            self.completed.emit(False, redacted_message, {"url": self.url})

    def cancel(self):
        """Request cancellation (called from main thread)."""
        logger.info("Cancellation requested for: %s", redact_url(self.url))
        self._is_cancelled = True

    def _progress_hook(self, d: Dict[str, Any]):
        """
        Called by yt-dlp during download (in worker thread).

        Raises DownloadError if cancelled.
        """
        if self._is_cancelled:
            raise yt_dlp.utils.DownloadError("Cancelled by user")

        status = d.get("status", "")

        if status == "downloading":
            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            speed = d.get("speed", 0) or 0
            eta = d.get("eta", 0) or 0

            # Calculate percentage
            if total > 0:
                percent = (downloaded / total) * 100
            else:
                percent = 0

            self._total_bytes = total
            self._current_filename = d.get("filename", "")

            # Throttle progress signals to avoid UI jank (10Hz max)
            # Always emit if this is the final progress (100%)
            now = time.time() * 1000  # Convert to milliseconds
            is_final = percent >= 100
            should_emit = (
                now - self._last_progress_time >= self._progress_throttle_ms or is_final
            )

            if should_emit:
                self._last_progress_time = now
                progress_info = {
                    "status": "downloading",
                    "percent": percent,
                    "speed": speed,
                    "downloaded": downloaded,
                    "total": total,
                    "eta": eta,
                    "filename": self._current_filename,
                }
                self.progress.emit(progress_info)

        elif status == "finished":
            self._current_filename = d.get("filename", "")
            self.progress.emit(
                {
                    "status": "finished",
                    "percent": 100,
                    "filename": self._current_filename,
                    "speed": 0,
                    "downloaded": self._total_bytes,
                    "total": self._total_bytes,
                    "eta": 0,
                }
            )

        elif status == "error":
            error_message = redact_urls_in_text(d.get("error", "Unknown error"))
            self.log.emit("error", f"Download error: {error_message}")

    def _postprocessor_hook(self, d: Dict[str, Any]):
        """Called by yt-dlp during post-processing."""
        if self._is_cancelled:
            raise yt_dlp.utils.DownloadError("Cancelled by user")

        status = d.get("status", "")
        if status == "started":
            postprocessor = d.get("postprocessor", "Processing")
            self.log.emit("info", f"Post-processing: {postprocessor}")

    def _build_outtmpl(self, info: Optional[Dict[str, Any]]) -> str:
        """
        Build output template with sequential numbering.

        Args:
            info: Extracted video info from yt-dlp (may be None)

        Returns:
            Output template path with sequence number
        """
        if info:
            # Get uploader using same fallback logic as yt-dlp template
            uploader = (
                info.get("uploader")
                or info.get("creator")
                or info.get("channel")
                or info.get("artist")
                or info.get("uploader_id")
                or info.get("channel_id")
                or info.get("webpage_url_domain")
                or "Unknown"
            )
            video_id = info.get("id", "unknown")

            # Build base filename pattern to search for existing files
            base_pattern = f"{uploader} - {video_id}"

            # Find next sequence number
            seq_num = _find_next_sequence_number(self.config.output_dir, base_pattern)

            # Build template with specific sequence number
            outtmpl = f"{base_pattern} - {seq_num:03d}.%(ext)s"
        else:
            # Fallback: use yt-dlp template variables with sequence placeholder
            # This shouldn't normally happen since we extract info first
            outtmpl = AUTHOR_ID_BASE + " - 001.%(ext)s"

        return os.path.join(self.config.output_dir, outtmpl)

    def _build_options(self, outtmpl: str) -> Dict[str, Any]:
        """
        Build yt-dlp options dictionary.

        Args:
            outtmpl: Output template path (from _build_outtmpl)
        """
        opts = {
            "outtmpl": outtmpl,
            "progress_hooks": [self._progress_hook],
            "postprocessor_hooks": [self._postprocessor_hook],
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "ignoreerrors": False,
            "no_color": True,
        }

        # Cookies file
        if self.config.cookies_path:
            opts["cookiefile"] = self.config.cookies_path

        # Overwrite existing files
        if self.config.force_overwrite:
            opts["overwrites"] = True
        else:
            opts["overwrites"] = False

        # Video format selection
        if self.config.video_only:
            opts["format"] = VIDEO_ONLY_FORMAT
        else:
            opts["format"] = DEFAULT_FORMAT
            opts["merge_output_format"] = DEFAULT_MERGE_FORMAT

        polite = self._config_service.get_section("download_polite")
        sleep_requests = float(polite.get("sleep_requests_seconds", 0.0))
        if sleep_requests > 0:
            opts["sleep_interval_requests"] = sleep_requests

        min_sleep = max(float(polite.get("min_sleep_interval_seconds", 0.0)), 0.0)
        max_sleep = max(float(polite.get("max_sleep_interval_seconds", 0.0)), 0.0)
        if max_sleep > 0 and min_sleep <= 0:
            min_sleep = max_sleep
        if max_sleep > 0 and max_sleep < min_sleep:
            max_sleep = min_sleep

        if min_sleep > 0:
            opts["sleep_interval"] = min_sleep
        if max_sleep > 0:
            opts["max_sleep_interval"] = max_sleep

        limit_rate = polite.get("limit_rate", "").strip()
        if limit_rate:
            parsed_rate = parse_bytes(limit_rate)
            if parsed_rate:
                opts["ratelimit"] = parsed_rate
            else:
                logger.warning(
                    "Invalid limit rate value ignored: %s", limit_rate
                )

        retries = polite.get("retries", None)
        if retries is not None:
            opts["retries"] = int(retries)

        retry_sleep_functions: Dict[str, Callable[[int], float]] = {}
        http_retry = polite.get("retry_sleep_http", {})
        http_func = _build_retry_sleep_function(
            http_retry.get("mode", "off"),
            float(http_retry.get("start", 0.0)),
            float(http_retry.get("end", 0.0)),
            float(http_retry.get("step", 1.0)),
            float(http_retry.get("base", 2.0)),
        )
        if http_func:
            retry_sleep_functions["http"] = http_func

        if polite.get("retry_sleep_fragment_enabled", False):
            fragment_retry = polite.get("retry_sleep_fragment", {})
            fragment_func = _build_retry_sleep_function(
                fragment_retry.get("mode", "off"),
                float(fragment_retry.get("start", 0.0)),
                float(fragment_retry.get("end", 0.0)),
                float(fragment_retry.get("step", 1.0)),
                float(fragment_retry.get("base", 2.0)),
            )
            if fragment_func:
                retry_sleep_functions["fragment"] = fragment_func

        if retry_sleep_functions:
            opts["retry_sleep_functions"] = retry_sleep_functions

        return opts


class DownloadResult:
    """Result of a download operation."""

    def __init__(
        self,
        url: str,
        success: bool,
        message: str = "",
        title: Optional[str] = None,
        filename: Optional[str] = None,
        file_size: Optional[int] = None,
    ):
        self.url = url
        self.success = success
        self.message = message
        self.title = title
        self.filename = filename
        self.file_size = file_size
