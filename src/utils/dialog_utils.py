"""Utilities for file dialog directory management."""

from pathlib import Path
from typing import Optional

from ..services.config_service import ConfigService


def get_dialog_start_dir(
    field_value: Optional[str] = None,
    fallback_config_key: Optional[str] = None,
) -> str:
    """
    Get the best starting directory for a file dialog.

    Priority order:
    1. field_value - Current value in the associated field (if valid directory)
    2. fallback_config_key - A specific config key to check (e.g., "sort.last_source_folder")
    3. dialogs.last_dir - Global last directory from config
    4. Path.home() - User's home directory as final fallback

    Args:
        field_value: Current value from the UI field (path string or None)
        fallback_config_key: Optional specific config key to check before global last_dir

    Returns:
        String path to use as starting directory
    """
    config = ConfigService()

    # 1. Try field value if it's a valid existing directory
    if field_value:
        field_path = Path(field_value)
        # If it's a file, use parent directory
        if field_path.is_file():
            return str(field_path.parent)
        # If it's a directory, use it
        if field_path.is_dir():
            return str(field_path)
        # If path doesn't exist but parent does, use parent
        if field_path.parent.is_dir():
            return str(field_path.parent)

    # 2. Try fallback config key if provided
    if fallback_config_key:
        fallback_path = config.get(fallback_config_key, "")
        if fallback_path:
            fb_path = Path(fallback_path)
            if fb_path.is_file():
                return str(fb_path.parent)
            if fb_path.is_dir():
                return str(fb_path)
            if fb_path.parent.is_dir():
                return str(fb_path.parent)

    # 3. Try global last directory
    last_dir = config.get("dialogs.last_dir", "")
    if last_dir:
        last_path = Path(last_dir)
        if last_path.is_dir():
            return str(last_path)
        if last_path.parent.is_dir():
            return str(last_path.parent)

    # 4. Final fallback: home directory
    return str(Path.home())


def update_dialog_last_dir(selected_path: str) -> None:
    """
    Update the global last directory after user selects a path.

    Args:
        selected_path: The path selected by the user in the dialog
    """
    if not selected_path:
        return

    config = ConfigService()
    path = Path(selected_path)

    # Store the directory (parent if file was selected)
    if path.is_file():
        dir_to_store = str(path.parent)
    elif path.is_dir():
        dir_to_store = str(path)
    else:
        # Path doesn't exist yet (e.g., save dialog), use parent
        dir_to_store = str(path.parent) if path.parent.exists() else str(Path.home())

    config.set("dialogs.last_dir", dir_to_store)
