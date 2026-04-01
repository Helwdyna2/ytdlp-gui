"""Helpers for computing conversion output names and locations."""

from pathlib import Path
from typing import Optional


def build_conversion_output_name(input_path: str) -> str:
    """Build the converted filename for an input path."""
    return f"{Path(input_path).stem}_converted.mp4"


def build_conversion_output_path(
    input_path: str,
    output_dir: Optional[str] = None,
    source_root: Optional[str] = None,
) -> str:
    """Build the full output path for a conversion job."""
    target_dir = resolve_conversion_output_dir(
        input_path, output_dir=output_dir, source_root=source_root
    )
    return str(target_dir / build_conversion_output_name(input_path))


def get_conversion_preview_folder(
    input_path: str,
    output_dir: Optional[str] = None,
    source_root: Optional[str] = None,
) -> str:
    """Build the folder label shown in the Convert preview tree."""
    if output_dir:
        relative_parent = _relative_parent(Path(input_path).parent, source_root)
        if relative_parent is None or relative_parent == Path("."):
            return ""
        return relative_parent.as_posix()

    if source_root:
        relative_parent = _relative_parent(Path(input_path).parent, source_root)
        if relative_parent is None or relative_parent == Path("."):
            return ""
        return relative_parent.as_posix()

    return ""


def resolve_conversion_output_dir(
    input_path: str,
    output_dir: Optional[str] = None,
    source_root: Optional[str] = None,
) -> Path:
    """Resolve the destination directory for a converted file."""
    input_parent = Path(input_path).parent
    if not output_dir:
        return input_parent

    relative_parent = _relative_parent(input_parent, source_root)
    if relative_parent is None or relative_parent == Path("."):
        return Path(output_dir)

    return Path(output_dir) / relative_parent


def _relative_parent(
    input_parent: Path, source_root: Optional[str]
) -> Optional[Path]:
    """Return the input parent relative to the selected source root, if possible."""
    if not source_root:
        return None

    try:
        return input_parent.relative_to(Path(source_root))
    except ValueError:
        return None
