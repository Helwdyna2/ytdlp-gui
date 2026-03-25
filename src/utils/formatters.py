"""Formatting utilities for sizes, speeds, and times."""


def format_size(bytes_val: int) -> str:
    """Format bytes to human-readable size string."""
    if bytes_val is None or bytes_val < 0:
        return "0 B"

    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024:
            if unit == 'B':
                return f"{int(bytes_val)} {unit}"
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024

    return f"{bytes_val:.1f} PB"


def format_speed(bytes_per_sec: float) -> str:
    """Format bytes/second to human-readable speed string."""
    if bytes_per_sec is None or bytes_per_sec <= 0:
        return "0 B/s"

    for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
        if bytes_per_sec < 1024:
            if unit == 'B/s':
                return f"{int(bytes_per_sec)} {unit}"
            return f"{bytes_per_sec:.1f} {unit}"
        bytes_per_sec /= 1024

    return f"{bytes_per_sec:.1f} TB/s"


def format_eta(seconds: int) -> str:
    """Format seconds to human-readable ETA string."""
    if seconds is None or seconds < 0:
        return "--:--"

    if seconds == 0:
        return "00:00"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def format_percent(fraction: float) -> str:
    """Format fraction (0-1) to percentage string."""
    if fraction is None or fraction < 0:
        return "0%"

    percent = min(fraction * 100, 100)
    return f"{percent:.1f}%"


def truncate_string(s: str, max_length: int = 60, suffix: str = "...") -> str:
    """Truncate a string to max_length, adding suffix if truncated."""
    if not s:
        return ""

    if len(s) <= max_length:
        return s

    return s[:max_length - len(suffix)] + suffix
