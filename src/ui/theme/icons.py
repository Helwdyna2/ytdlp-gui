"""Centralized icon registry using qtawesome."""

import logging
from typing import Optional

import qtawesome as qta
from PyQt6.QtGui import QIcon

logger = logging.getLogger(__name__)

# Navigation icons (sidebar)
NAV_ICONS = {
    # New sidebar tool keys
    "add_urls": "mdi6.link-plus",
    "extract_urls": "mdi6.web",
    "convert": "mdi6.swap-horizontal",
    "trim": "mdi6.content-cut",
    "metadata": "mdi6.information-outline",
    "sort": "mdi6.sort-variant",
    "rename": "mdi6.rename-box",
    "match": "mdi6.link-variant",
    "settings": "mdi6.cog-outline",
    # Legacy keys kept for backward compat
    "ingest": "mdi6.link-plus",
    "prepare": "mdi6.swap-horizontal",
    "organize": "mdi6.sort-variant",
    "export": "mdi6.cog-outline",
    "download": "mdi6.download",
    # Previously existing keys preserved
    "extract": "mdi6.link",
}

# Status icons
STATUS_ICONS = {
    "success": "mdi6.check-circle",
    "error": "mdi6.alert-circle",
    "warning": "mdi6.alert",
    "pending": "mdi6.clock-outline",
    "active": "mdi6.play-circle",
}

# Action icons (buttons)
ACTION_ICONS = {
    "browse": "mdi6.folder-open",
    "add": "mdi6.plus",
    "remove": "mdi6.delete-outline",
    "cancel": "mdi6.close",
    "refresh": "mdi6.refresh",
    "theme_dark": "mdi6.weather-night",
    "theme_light": "mdi6.weather-sunny",
}

# Combined lookup
_ALL_ICONS = {**NAV_ICONS, **STATUS_ICONS, **ACTION_ICONS}


def get_icon(name: str, color: Optional[str] = None) -> QIcon:
    """Get a QIcon by friendly name.

    Args:
        name: Friendly icon name (e.g., "download", "success", "browse")
        color: Optional hex color string (e.g., "#00d4ff")

    Returns:
        QIcon instance. Returns empty QIcon for unknown names.
    """
    icon_id = _ALL_ICONS.get(name)
    if icon_id is None:
        logger.warning(f"Unknown icon name: {name}")
        return QIcon()

    try:
        if color:
            return qta.icon(icon_id, color=color)
        return qta.icon(icon_id)
    except Exception as e:
        logger.error(f"Failed to load icon '{name}' ({icon_id}): {e}")
        return QIcon()
