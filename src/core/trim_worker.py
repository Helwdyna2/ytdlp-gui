"""Worker for video trimming using FFmpeg."""

import logging
import re
import subprocess
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from ..data.models import TrimJob, TrimStatus
from ..utils.ffmpeg_utils import find_ffmpeg
from ..utils.platform_utils import get_subprocess_kwargs

logger = logging.getLogger(__name__)


class TrimWorker(QThread):
    """
    QThread worker for video trimming using FFmpeg.

    Signals:
        progress: Emits (percent, speed, eta) for progress updates
        log: Emits (level, message) for logging
        completed: Emits (success, output_path, error_message)
    """

    progress = pyqtSignal(float, str, str)  # percent, speed, eta
    log = pyqtSignal(str, str)  # level, message
    completed = pyqtSignal(bool, str, str)  # success, output_path, error_message

    def __init__(
        self,
        input_path: str,
        output_path: str,
        start_time: float,
        end_time: float,
        lossless: bool = True,
        parent=None,
    ):
        """
        Initialize the trim worker.

        Args:
            input_path: Path to input video file
            output_path: Path for output video file
            start_time: Start time in seconds
            end_time: End time in seconds
            lossless: If True, use stream copy (fast but keyframe-limited)
            parent: Parent QObject
        """
        super().__init__(parent)
        self._input_path = input_path
        self._output_path = output_path
        self._start_time = start_time
        self._end_time = end_time
        self._lossless = lossless
        self._cancelled = False
        self._process: Optional[subprocess.Popen] = None
        self._duration: float = end_time - start_time
        self._recent_output_lines: list[str] = []

    def cancel(self) -> None:
        """Request cancellation of the trim operation."""
        self._cancelled = True
        if self._process:
            try:
                self._process.terminate()
            except Exception as e:
                logger.warning(f"Failed to terminate FFmpeg process: {e}")

    def run(self) -> None:
        """Execute the FFmpeg trim operation."""
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            self.completed.emit(False, self._output_path, "FFmpeg not found")
            return

        try:
            # Ensure output directory exists
            output_dir = Path(self._output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)

            # Build the FFmpeg command
            cmd = self._build_command(ffmpeg_path)
            self.log.emit("info", f"Starting trim: {Path(self._input_path).name}")
            self.log.emit("debug", f"Command: {' '.join(cmd)}")

            # Start FFmpeg process
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                **get_subprocess_kwargs(),
            )

            # Parse FFmpeg output for progress
            self._parse_output()

            # Wait for process to complete
            self._process.wait()

            if self._cancelled:
                self.log.emit("info", "Trim cancelled")
                self.completed.emit(False, self._output_path, "Cancelled")
                self._cleanup_output()
                return

            if self._process.returncode == 0:
                self.log.emit("info", f"Trim complete: {Path(self._output_path).name}")
                self.completed.emit(True, self._output_path, "")
            else:
                error_msg = self._extract_error("\n".join(self._recent_output_lines))
                self.log.emit("error", f"Trim failed: {error_msg}")
                self.completed.emit(False, self._output_path, error_msg)
                self._cleanup_output()

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"Trim error: {error_msg}")
            self.log.emit("error", f"Trim error: {error_msg}")
            self.completed.emit(False, self._output_path, error_msg)
            self._cleanup_output()

    def _build_command(self, ffmpeg_path: str) -> list:
        """
        Build the FFmpeg command for trimming.

        For lossless trim, we use -c copy which is fast but can only cut
        at keyframes, so the actual trim point may vary slightly.

        For re-encoding, we get frame-accurate cuts but it's slower.

        Args:
            ffmpeg_path: Path to FFmpeg executable

        Returns:
            Command as list of strings
        """
        # Calculate duration of the segment to extract
        duration = self._end_time - self._start_time

        if self._lossless:
            # Lossless trim using stream copy
            # -ss before -i for faster seeking (input seeking)
            # -avoid_negative_ts make_zero helps with sync issues
            cmd = [
                ffmpeg_path,
                "-y",  # Overwrite output
                "-ss",
                str(self._start_time),  # Seek to start position
                "-i",
                self._input_path,
                "-t",
                str(duration),  # Duration to extract
                "-c",
                "copy",  # Copy streams without re-encoding
                "-avoid_negative_ts",
                "make_zero",
                "-progress",
                "pipe:1",  # Progress reporting
                self._output_path,
            ]
        else:
            # Re-encoding for frame-accurate cuts
            # -ss after -i for accurate seeking (output seeking)
            cmd = [
                ffmpeg_path,
                "-y",  # Overwrite output
                "-i",
                self._input_path,
                "-ss",
                str(self._start_time),  # Seek to start position
                "-to",
                str(self._end_time),  # End position
                "-c:v",
                "libx264",  # Re-encode video
                "-crf",
                "18",  # High quality
                "-preset",
                "fast",
                "-c:a",
                "aac",  # Re-encode audio
                "-b:a",
                "192k",
                "-progress",
                "pipe:1",  # Progress reporting
                self._output_path,
            ]

        return cmd

    def _parse_output(self) -> None:
        """Parse FFmpeg progress output."""
        if not self._process or not self._process.stdout:
            return

        current_time = 0.0

        for line in self._process.stdout:
            if self._cancelled:
                break

            line = line.strip()
            if line:
                self._recent_output_lines.append(line)
                if len(self._recent_output_lines) > 200:
                    self._recent_output_lines = self._recent_output_lines[-200:]

            # Parse progress info
            if line.startswith("out_time_ms="):
                try:
                    ms = int(line.split("=")[1])
                    current_time = ms / 1_000_000.0  # Convert to seconds
                except (ValueError, IndexError):
                    pass

            elif line.startswith("speed="):
                try:
                    speed_str = line.split("=")[1].strip()
                    if self._duration > 0 and current_time > 0:
                        percent = (current_time / self._duration) * 100
                        percent = min(percent, 99.9)  # Cap at 99.9 until done

                        # Calculate ETA
                        eta_str = self._calculate_eta(current_time, speed_str)

                        self.progress.emit(percent, speed_str, eta_str)
                except (ValueError, IndexError):
                    pass

    def _calculate_eta(self, current_time: float, speed_str: str) -> str:
        """Calculate ETA from current progress and speed."""
        from ..utils.ffmpeg_utils import calculate_ffmpeg_eta

        return calculate_ffmpeg_eta(self._duration, current_time, speed_str)

    def _extract_error(self, stderr: str) -> str:
        """Extract meaningful error message from FFmpeg stderr."""
        from ..utils.ffmpeg_utils import extract_ffmpeg_error

        return extract_ffmpeg_error(stderr, fallback="Trim failed")

    def _cleanup_output(self) -> None:
        """Remove partial output file on failure/cancellation."""
        try:
            output_path = Path(self._output_path)
            if output_path.exists():
                output_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to cleanup output file: {e}")
