"""Helpers for computing conversion output names and locations."""

from pathlib import Path
from typing import Optional


OUTPUT_EXTENSION_BY_CODEC = {
    "h264": ".mp4",
    "hevc": ".mp4",
    "vp9": ".webm",
    "mp3": ".mp3",
    "aac": ".aac",
    "flac": ".flac",
}


def get_conversion_output_extension(output_codec: str) -> str:
    """Resolve the file extension for the selected conversion format."""
    normalized_codec = (output_codec or "h264").strip().lower()
    return OUTPUT_EXTENSION_BY_CODEC.get(normalized_codec, ".mp4")


def build_conversion_output_name(input_path: str, output_codec: str = "h264") -> str:
    """Build the converted filename for an input path."""
    extension = get_conversion_output_extension(output_codec)
    return f"{Path(input_path).stem}_converted{extension}"


def build_conversion_output_path(
    input_path: str,
    output_dir: Optional[str] = None,
    source_root: Optional[str] = None,
    output_codec: str = "h264",
) -> str:
    """Build the full output path for a conversion job."""
    target_dir = resolve_conversion_output_dir(
        input_path, output_dir=output_dir, source_root=source_root
    )
    return str(
        target_dir / build_conversion_output_name(input_path, output_codec=output_codec)
    )


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
