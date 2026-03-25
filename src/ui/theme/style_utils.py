"""Theme-aware style utilities for widget property updates."""

_STATUS_COLOR_MAP = {
    "info": "cyan",
    "warning": "orange",
    "success": "green",
    "error": "red",
    "muted": "dim",
}


def set_status_color(widget, status_type: str) -> None:
    """Set dataColor property on a widget and force QSS re-evaluation.

    Args:
        widget: The QWidget to update.
        status_type: One of 'info', 'warning', 'success', 'error', 'muted'.
    """
    color = _STATUS_COLOR_MAP.get(status_type, "dim")
    widget.setProperty("dataColor", color)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
