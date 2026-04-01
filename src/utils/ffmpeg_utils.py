"""FFmpeg and ffprobe utility functions."""

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

from .platform_utils import get_subprocess_kwargs

logger = logging.getLogger(__name__)


HARDWARE_PROBE_SOURCE = "testsrc2=size=320x240:rate=30:duration=1"


def _windows_ffmpeg_candidates(executable_name: str) -> list[str]:
    """Return likely Windows install paths, including winget-managed locations."""
    candidates = [
        rf"C:\ffmpeg\bin\{executable_name}",
        rf"C:\Program Files\ffmpeg\bin\{executable_name}",
        rf"C:\Program Files (x86)\ffmpeg\bin\{executable_name}",
    ]

    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return candidates

    winget_root = Path(local_app_data) / "Microsoft" / "WinGet"
    candidates.append(str(winget_root / "Links" / executable_name))

    packages_root = winget_root / "Packages"
    if packages_root.is_dir():
        for path in sorted(packages_root.glob(f"**/{executable_name}"), reverse=True):
            candidates.append(str(path))

    return candidates


def find_ffmpeg() -> Optional[str]:
    """
    Find the FFmpeg executable path.

    Returns:
        Path to ffmpeg executable, or None if not found.
    """
    # Check if ffmpeg is in PATH
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path

    # Check common installation locations
    common_paths = []

    if sys.platform == "darwin":  # macOS
        common_paths = [
            "/usr/local/bin/ffmpeg",
            "/opt/homebrew/bin/ffmpeg",
            "/opt/local/bin/ffmpeg",
        ]
    elif sys.platform == "win32":  # Windows
        common_paths = _windows_ffmpeg_candidates("ffmpeg.exe")
    else:  # Linux
        common_paths = [
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
        ]

    for path in common_paths:
        if Path(path).is_file():
            return path

    return None


def find_ffprobe() -> Optional[str]:
    """
    Find the ffprobe executable path.

    Returns:
        Path to ffprobe executable, or None if not found.
    """
    # Check if ffprobe is in PATH
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path:
        return ffprobe_path

    # Check common installation locations
    common_paths = []

    if sys.platform == "darwin":  # macOS
        common_paths = [
            "/usr/local/bin/ffprobe",
            "/opt/homebrew/bin/ffprobe",
            "/opt/local/bin/ffprobe",
        ]
    elif sys.platform == "win32":  # Windows
        common_paths = _windows_ffmpeg_candidates("ffprobe.exe")
    else:  # Linux
        common_paths = [
            "/usr/bin/ffprobe",
            "/usr/local/bin/ffprobe",
        ]

    for path in common_paths:
        if Path(path).is_file():
            return path

    return None


def check_ffmpeg_available() -> Tuple[bool, bool]:
    """
    Check if FFmpeg and ffprobe are available.

    Returns:
        Tuple of (ffmpeg_available, ffprobe_available)
    """
    ffmpeg_available = find_ffmpeg() is not None
    ffprobe_available = find_ffprobe() is not None
    return ffmpeg_available, ffprobe_available


def get_ffmpeg_version() -> Optional[str]:
    """
    Get the installed FFmpeg version string.

    Returns:
        Version string, or None if FFmpeg not found.
    """
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        return None

    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            **get_subprocess_kwargs(),
        )
        if result.returncode == 0:
            # First line contains version info
            first_line = result.stdout.split("\n")[0]
            return first_line
    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        logger.warning(f"Failed to get FFmpeg version: {e}")

    return None


def get_available_encoders() -> list[str]:
    """
    Get list of available video encoders from FFmpeg.

    Returns:
        List of encoder names (e.g., ['libx264', 'h264_nvenc', ...])
    """
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        return []

    try:
        result = subprocess.run(
            [ffmpeg_path, "-encoders"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            **get_subprocess_kwargs(),
        )
        if result.returncode == 0:
            encoders = []
            lines = result.stdout.split("\n")
            for line in lines:
                # Encoder lines start with format like " V..... libx264"
                if line.startswith(" V"):
                    parts = line.split()
                    if len(parts) >= 2:
                        encoders.append(parts[1])
            return encoders
    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        logger.warning(f"Failed to get encoders: {e}")

    return []


def _summarize_probe_failure(output: str) -> str:
    """Extract a concise, user-facing reason from FFmpeg probe output."""
    keywords = (
        "initializeencoder failed",
        "error while opening encoder",
        "failed to create hardware device context",
        "failed to open",
        "not supported",
        "conversion failed",
        "device",
        "error",
        "failed",
    )
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    for line in lines:
        lowered = line.lower()
        if any(keyword in lowered for keyword in keywords):
            return line
    if lines:
        return lines[-1]
    return "Unknown FFmpeg error"


def probe_hardware_encoder(encoder_name: str) -> tuple[bool, Optional[str]]:
    """
    Check whether a hardware encoder is listed and can complete a minimal encode.

    Args:
        encoder_name: Name of the encoder (e.g., 'h264_nvenc')

    Returns:
        Tuple of (is_available, failure_reason).
    """
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        return False, "FFmpeg not found"

    encoders = get_available_encoders()
    if encoder_name not in encoders:
        return False, "Encoder not listed by FFmpeg"

    try:
        result = subprocess.run(
            [
                ffmpeg_path,
                "-y",
                "-f",
                "lavfi",
                "-i",
                HARDWARE_PROBE_SOURCE,
                "-frames:v",
                "1",
                "-c:v",
                encoder_name,
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            **get_subprocess_kwargs(),
        )
        if result.returncode == 0:
            return True, None

        failure_output = result.stderr or result.stdout
        return False, _summarize_probe_failure(failure_output)
    except subprocess.TimeoutExpired:
        return False, "Probe timed out"
    except subprocess.SubprocessError as e:
        logger.debug(f"Hardware encoder {encoder_name} test failed: {e}")
        return False, str(e)


def is_hardware_encoder_available(encoder_name: str) -> bool:
    """
    Check if a specific hardware encoder is available.

    Args:
        encoder_name: Name of the encoder (e.g., 'h264_nvenc')

    Returns:
        True if the encoder is available and working.
    """
    is_available, _ = probe_hardware_encoder(encoder_name)
    return is_available


def calculate_ffmpeg_eta(duration: float, current_time: float, speed_str: str) -> str:
    """
    Calculate ETA from FFmpeg progress info.

    Args:
        duration: Total duration in seconds
        current_time: Current processed time in seconds
        speed_str: Speed string from FFmpeg (e.g., "1.5x")

    Returns:
        Human-readable ETA string (e.g., "5m 30s") or "N/A"
    """
    if not speed_str or speed_str == "N/A":
        return "N/A"

    try:
        speed = float(speed_str.rstrip("x"))
        if speed <= 0:
            return "N/A"

        remaining_time = (duration - current_time) / speed

        if remaining_time < 60:
            return f"{int(remaining_time)}s"
        elif remaining_time < 3600:
            mins = int(remaining_time // 60)
            secs = int(remaining_time % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(remaining_time // 3600)
            mins = int((remaining_time % 3600) // 60)
            return f"{hours}h {mins}m"
    except (ValueError, ZeroDivisionError):
        return "N/A"


def extract_ffmpeg_error(output: str, fallback: str = "Unknown error") -> str:
    """
    Extract a meaningful error message from FFmpeg output.

    Args:
        output: FFmpeg stdout/stderr output
        fallback: Default message when no error found

    Returns:
        Error message string
    """
    if not output:
        return fallback

    lines = output.split("\n")
    for line in reversed(lines):
        if "Error" in line or "Invalid" in line or "No such" in line:
            return line.strip()

    # Return last non-empty line
    for line in reversed(lines):
        if line.strip():
            return line.strip()[:200]

    return fallback
