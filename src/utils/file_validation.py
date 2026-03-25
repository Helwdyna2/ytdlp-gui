"""File validation utilities for detecting and handling invalid video files."""

import logging
from pathlib import Path
from typing import List, Tuple

import send2trash

logger = logging.getLogger(__name__)


def is_zero_byte_file(file_path: str) -> bool:
    """
    Check if a file is exactly 0 bytes.

    Args:
        file_path: Path to file to check

    Returns:
        True if file exists and is 0 bytes, False otherwise
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return False

        file_size = path.stat().st_size
        return file_size == 0

    except (OSError, PermissionError) as e:
        logger.warning(f"Could not check file size for {file_path}: {e}")
        return False


def move_to_trash(file_path: str) -> bool:
    """
    Move a file to system trash/recycle bin.

    Args:
        file_path: Path to file to move to trash

    Returns:
        True if successful, False if failed
    """
    try:
        send2trash.send2trash(file_path)
        logger.info(f"Moved file to trash: {file_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to move file to trash: {file_path} - {e}")
        return False


def cleanup_zero_byte_files(file_paths: List[str]) -> Tuple[List[str], List[str]]:
    """
    Filter out and move zero-byte files to trash.

    Checks each file in the list, moves zero-byte files to trash,
    and returns separate lists of valid and trashed files.

    Args:
        file_paths: List of file paths to validate

    Returns:
        Tuple of (valid_files, trashed_files)
        - valid_files: List of files that are > 0 bytes
        - trashed_files: List of files that were moved to trash
    """
    valid_files = []
    trashed_files = []

    for file_path in file_paths:
        if is_zero_byte_file(file_path):
            logger.warning(f"Zero-byte file detected: {file_path}")
            if move_to_trash(file_path):
                trashed_files.append(file_path)
            else:
                # If we can't trash it, treat it as invalid but don't add to valid list
                logger.error(
                    f"Could not move zero-byte file to trash, excluding from results: {file_path}"
                )
        else:
            valid_files.append(file_path)

    if trashed_files:
        logger.info(
            f"Cleanup complete: {len(trashed_files)} zero-byte files moved to trash, {len(valid_files)} valid files"
        )

    return valid_files, trashed_files
