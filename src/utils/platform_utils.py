"""Platform-specific utilities for portable application paths."""

import logging
import sys
import os
import subprocess
from pathlib import Path
from enum import Enum
from typing import Dict, Any

logger = logging.getLogger(__name__)


class Platform(Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"


def get_platform() -> Platform:
    """Detect current platform."""
    if sys.platform == "win32":
        return Platform.WINDOWS
    elif sys.platform == "darwin":
        return Platform.MACOS
    else:
        return Platform.LINUX


def get_subprocess_kwargs() -> Dict[str, Any]:
    """
    Get platform-specific subprocess kwargs to hide console windows.

    On Windows, this prevents black command prompt windows from flashing
    when running FFmpeg, ffprobe, or other subprocess calls.

    Returns:
        Dict of kwargs to pass to subprocess.run() or subprocess.Popen()
    """
    kwargs: Dict[str, Any] = {}

    if sys.platform == "win32":
        # Windows: Hide console window
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs["startupinfo"] = startupinfo
        # Also prevent new console window creation
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    return kwargs


def get_app_dir() -> Path:
    """
    Get application directory (portable).

    For packaged app: directory containing executable
    For development: project root (ytdlp-gui/)
    """
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle
        return Path(sys.executable).parent
    else:
        # Running from source - go up from utils/ to src/ to project root
        return Path(__file__).parent.parent.parent


def get_data_dir() -> Path:
    """Get data directory for database and config."""
    return get_app_dir() / "data"


def get_db_path() -> Path:
    """Get SQLite database path."""
    return get_data_dir() / "ytdlp_gui.db"


def get_config_path() -> Path:
    """Get config file path."""
    return get_data_dir() / "config.json"


def get_log_dir() -> Path:
    """Get log directory path."""
    return get_data_dir() / "logs"


def get_default_output_dir() -> Path:
    """Get default output directory based on platform."""
    platform = get_platform()

    if platform == Platform.WINDOWS:
        # Windows: User's Videos folder
        videos = Path(os.environ.get("USERPROFILE", "")) / "Videos" / "yt-dlp"
    elif platform == Platform.MACOS:
        # macOS: User's Movies folder
        videos = Path.home() / "Movies" / "yt-dlp"
    else:
        # Linux: User's Videos folder
        videos = Path.home() / "Videos" / "yt-dlp"

    return videos


def ensure_dirs():
    """Ensure all required directories exist."""
    dirs = [
        get_data_dir(),
        get_log_dir(),
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def quick_look_file(file_path: str) -> bool:
    """
    Open Quick Look preview for a file (macOS only for now).

    Uses AppleScript to reveal the file in Finder and trigger Quick Look
    via the spacebar shortcut, which is more reliable than qlmanage.

    Args:
        file_path: Path to the file to preview

    Returns:
        True if preview launched successfully, False otherwise
    """
    if not Path(file_path).exists():
        return False

    platform = get_platform()

    if platform == Platform.MACOS:
        # macOS: Use AppleScript to reveal in Finder and trigger Quick Look
        # This is more reliable than qlmanage -p which can crash
        try:
            # Escape the file path for AppleScript
            escaped_path = file_path.replace("\\", "\\\\").replace('"', '\\"')

            # AppleScript to:
            # 1. Tell Finder to reveal and select the file
            # 2. Activate Finder (bring to front)
            # 3. Tell System Events to press spacebar (triggers Quick Look)
            apple_script = f'''
                tell application "Finder"
                    reveal POSIX file "{escaped_path}"
                    activate
                end tell
                delay 0.3
                tell application "System Events"
                    keystroke space
                end tell
            '''

            subprocess.Popen(
                ["osascript", "-e", apple_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to open Quick Look: {e}")
            return False

    # Windows/Linux: Not supported yet (future enhancement)
    return False


def open_file_default_app(file_path: str) -> bool:
    """
    Open file with system's default application.

    Args:
        file_path: Path to the file to open

    Returns:
        True if opened successfully, False otherwise
    """
    if not Path(file_path).exists():
        return False

    platform = get_platform()

    try:
        if platform == Platform.MACOS:
            subprocess.Popen(["open", file_path])
        elif platform == Platform.WINDOWS:
            os.startfile(file_path)  # type: ignore[attr-defined] # Windows only
        elif platform == Platform.LINUX:
            subprocess.Popen(["xdg-open", file_path])
        return True
    except Exception as e:
        logger.error(f"Failed to open file with default app: {e}")
        return False
