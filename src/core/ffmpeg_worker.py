"""Worker for video conversion using FFmpeg."""

import logging
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from ..data.models import ConversionConfig, ConversionJob, ConversionStatus
from ..utils.ffmpeg_utils import find_ffmpeg
from ..utils.hardware_accel import get_encoder_for_codec, get_cached_hardware_encoders
from ..utils.platform_utils import get_subprocess_kwargs

logger = logging.getLogger(__name__)


class FFmpegWorker(QThread):
    """
    QThread worker for video conversion using FFmpeg.

    Signals:
        progress: Emits (percent, speed, eta, current_time, total_duration)
        log: Emits (level, message) for logging
        completed: Emits (success, output_path, error_message)
    """

    progress = pyqtSignal(
        float, str, str, float, float
    )  # percent, speed, eta, current, total
    log = pyqtSignal(str, str)  # level, message
    completed = pyqtSignal(bool, str, str)  # success, output_path, error_message

    def __init__(
        self, input_path: str, output_path: str, config: ConversionConfig, parent=None
    ):
        """
        Initialize the FFmpeg worker.

        Args:
            input_path: Path to input video file
            output_path: Path for output video file
            config: Conversion configuration
            parent: Parent QObject
        """
        super().__init__(parent)
        self._input_path = input_path
        self._output_path = output_path
        self._config = config
        self._cancelled = False
        self._process: Optional[subprocess.Popen] = None
        self._duration: float = 0.0
        self._recent_output_lines: list[str] = []
        self._last_progress_emit_time: float = 0.0
        self._last_progress_percent_int: int = -1

    def cancel(self) -> None:
        """Request cancellation of the conversion."""
        self._cancelled = True
        if self._process:
            try:
                self._process.terminate()
            except Exception as e:
                logger.warning(f"Failed to terminate FFmpeg process: {e}")

    def run(self) -> None:
        """Execute the FFmpeg conversion."""
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            self.completed.emit(False, self._output_path, "FFmpeg not found")
            return

        try:
            Path(self._output_path).parent.mkdir(parents=True, exist_ok=True)

            # Build the FFmpeg command
            cmd = self._build_command(ffmpeg_path)
            self.log.emit("info", f"Starting conversion: {Path(self._input_path).name}")
            self.log.emit("debug", f"Command: {' '.join(cmd)}")

            # Start FFmpeg process with platform-specific settings
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Prevent deadlock if stderr pipe fills
                text=True,
                encoding="utf-8",
                errors="replace",  # Handle non-UTF8 characters gracefully
                **get_subprocess_kwargs(),
            )

            # Parse FFmpeg output for progress
            self._parse_output()

            # Wait for process to complete
            self._process.wait()

            if self._cancelled:
                self.log.emit("info", "Conversion cancelled")
                self.completed.emit(False, self._output_path, "Cancelled")
                self._cleanup_output()
                return

            if self._process.returncode == 0:
                self.log.emit(
                    "info", f"Conversion complete: {Path(self._output_path).name}"
                )
                self.completed.emit(True, self._output_path, "")
            else:
                error_msg = self._extract_error("\n".join(self._recent_output_lines))
                self.log.emit("error", f"Conversion failed: {error_msg}")
                self.completed.emit(False, self._output_path, error_msg)
                self._cleanup_output()

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"Conversion error: {error_msg}")
            self.log.emit("error", f"Conversion error: {error_msg}")
            self.completed.emit(False, self._output_path, error_msg)
            self._cleanup_output()

    def _build_command(self, ffmpeg_path: str) -> list:
        """
        Build the FFmpeg command with all options.

        Args:
            ffmpeg_path: Path to FFmpeg executable

        Returns:
            Command as list of strings
        """
        cmd = [
            ffmpeg_path,
            "-y",  # Overwrite output
            "-i",
            self._input_path,
        ]

        if self._config.output_codec in {"mp3", "aac", "flac"}:
            cmd.extend(["-vn"])
            cmd.extend(self._build_audio_only_args())
        else:
            encoder = self._resolve_video_encoder()
            cmd.extend(["-c:v", encoder])

            scale_filter = self._build_scale_filter()
            if scale_filter:
                cmd.extend(["-vf", scale_filter])

            cmd.extend(self._build_video_quality_args(encoder))
            cmd.extend(self._build_mux_audio_args())

        # Progress reporting
        cmd.extend(["-progress", "pipe:1"])

        # Output file
        cmd.append(self._output_path)

        return cmd

    def _resolve_video_encoder(self) -> str:
        """Resolve the requested video encoder for the selected output format."""
        if self._config.output_codec == "vp9":
            return "libvpx-vp9"

        hw_encoder = None
        if self._config.use_hardware_accel:
            encoders = get_cached_hardware_encoders()
            for enc in encoders:
                if (
                    self._config.hardware_encoder
                    and enc.name == self._config.hardware_encoder
                ):
                    hw_encoder = enc
                    break
            if not hw_encoder and encoders:
                hw_encoder = encoders[0]

        return get_encoder_for_codec(
            hw_encoder, self._config.output_codec, self._config.use_hardware_accel
        )

    def _build_video_quality_args(self, encoder: str) -> list[str]:
        """Build codec-specific quality arguments for video outputs."""
        if encoder == "libvpx-vp9":
            return ["-b:v", "0", "-crf", str(self._config.crf_value)]

        if "nvenc" in encoder:
            return [
                "-cq",
                str(self._config.crf_value),
                "-preset",
                self._nvenc_preset(self._config.preset),
            ]

        if "amf" in encoder:
            return [
                "-qp_i",
                str(self._config.crf_value),
                "-qp_p",
                str(self._config.crf_value),
            ]

        if "qsv" in encoder:
            return [
                "-global_quality",
                str(self._config.crf_value),
                "-preset",
                self._qsv_preset(self._config.preset),
            ]

        if "videotoolbox" in encoder:
            estimated_bitrate = self._estimate_bitrate_from_crf(self._config.crf_value)
            return ["-b:v", f"{estimated_bitrate}k"]

        return ["-crf", str(self._config.crf_value), "-preset", self._config.preset]

    def _build_mux_audio_args(self) -> list[str]:
        """Build audio arguments for video container outputs."""
        if self._config.output_codec == "vp9":
            return ["-c:a", "libopus", "-b:a", "192k"]
        return ["-c:a", "aac", "-b:a", "192k"]

    def _build_audio_only_args(self) -> list[str]:
        """Build audio codec arguments for audio-only outputs."""
        if self._config.output_codec == "mp3":
            return ["-c:a", "libmp3lame", "-b:a", "192k"]
        if self._config.output_codec == "flac":
            return ["-c:a", "flac"]
        return ["-c:a", "aac", "-b:a", "192k"]

    def _build_scale_filter(self) -> Optional[str]:
        """Build a scale/pad filter for the selected output resolution."""
        if self._config.output_codec not in {"h264", "hevc", "vp9"}:
            return None

        resolution = (self._config.output_resolution or "").strip().lower()
        if not resolution:
            return None

        match = re.fullmatch(r"(\d+)x(\d+)", resolution)
        if not match:
            logger.warning("Ignoring invalid output resolution: %s", resolution)
            return None

        width, height = match.groups()
        return (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease:"
            f"force_divisible_by=2,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
        )

    def _nvenc_preset(self, preset: str) -> str:
        """Map standard preset to NVENC preset."""
        preset_map = {
            "ultrafast": "p1",
            "superfast": "p2",
            "veryfast": "p3",
            "faster": "p4",
            "fast": "p5",
            "medium": "p5",
            "slow": "p6",
            "slower": "p7",
            "veryslow": "p7",
        }
        return preset_map.get(preset, "p5")

    def _qsv_preset(self, preset: str) -> str:
        """Map standard preset to QSV preset."""
        preset_map = {
            "ultrafast": "veryfast",
            "superfast": "veryfast",
            "veryfast": "veryfast",
            "faster": "faster",
            "fast": "fast",
            "medium": "medium",
            "slow": "slow",
            "slower": "slower",
            "veryslow": "veryslow",
        }
        return preset_map.get(preset, "medium")

    def _estimate_bitrate_from_crf(self, crf: int) -> int:
        """Estimate bitrate from CRF value for VideoToolbox."""
        # Rough estimation: CRF 23 ≈ 5000kbps, lower CRF = higher bitrate
        base_bitrate = 5000
        # Each CRF unit roughly doubles/halves the file size
        factor = 2 ** ((23 - crf) / 6)
        return int(base_bitrate * factor)

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

            elif line.startswith("total_size="):
                pass  # Could track output size

            elif line.startswith("speed="):
                try:
                    speed_str = line.split("=")[1].strip()
                    if self._duration > 0 and current_time > 0:
                        percent = (current_time / self._duration) * 100
                        percent = min(percent, 99.9)  # Cap at 99.9 until done

                        # Calculate ETA
                        eta_str = self._calculate_eta(current_time, speed_str)

                        now = time.time()
                        percent_int = int(percent)
                        if (
                            percent_int != self._last_progress_percent_int
                            or (now - self._last_progress_emit_time) >= 0.25
                        ):
                            self.progress.emit(
                                percent,
                                speed_str,
                                eta_str,
                                current_time,
                                self._duration,
                            )
                            self._last_progress_emit_time = now
                            self._last_progress_percent_int = percent_int
                except (ValueError, IndexError):
                    pass

            elif line.startswith("Duration:") or "Duration:" in line:
                # Parse duration from FFmpeg output
                match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", line)
                if match:
                    h, m, s = match.groups()
                    self._duration = int(h) * 3600 + int(m) * 60 + float(s)

    def _calculate_eta(self, current_time: float, speed_str: str) -> str:
        """Calculate ETA from current progress and speed."""
        from ..utils.ffmpeg_utils import calculate_ffmpeg_eta

        return calculate_ffmpeg_eta(self._duration, current_time, speed_str)

    def _extract_error(self, stderr: str) -> str:
        """Extract meaningful error message from FFmpeg stderr."""
        from ..utils.ffmpeg_utils import extract_ffmpeg_error

        return extract_ffmpeg_error(stderr, fallback="Conversion failed")

    def _cleanup_output(self) -> None:
        """Remove partial output file on failure/cancellation."""
        try:
            output_path = Path(self._output_path)
            if output_path.exists():
                output_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to cleanup output file: {e}")
