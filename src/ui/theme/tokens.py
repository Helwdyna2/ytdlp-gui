"""Digital Obsidian theme token dictionaries.

Tokens are string key-value pairs consumed by the QSS template engine.
Both DARK_TOKENS and LIGHT_TOKENS must have identical key sets.
"""

from typing import Dict, List

# ---------------------------------------------------------------------------
# Font stacks
# ---------------------------------------------------------------------------
FONT_HEADLINE: str = '"Manrope", "Segoe UI", sans-serif'
FONT_BODY: str = '"Inter", "Segoe UI", "Helvetica Neue", sans-serif'
FONT_DISPLAY: str = FONT_HEADLINE  # Alias for backward compat
FONT_MONO: str = '"SF Mono", "Cascadia Code", "Consolas", monospace'

# ---------------------------------------------------------------------------
# Required token keys (authoritative list)
# ---------------------------------------------------------------------------
REQUIRED_TOKEN_KEYS: List[str] = [
    # Surfaces
    "bg-void",
    "bg-surface",
    "bg-panel",
    "bg-cell",
    "bg-hover",
    "bg-selected",
    "surface-app",
    "surface-panel",
    "surface-canvas",
    "surface-container-low",
    "surface-container",
    "surface-container-high",
    "surface-container-highest",
    "surface-bright",
    "surface-container-lowest",
    "input-well",
    # Borders
    "border-hard",
    "border-soft",
    "border-focus",
    "border-bright",
    "ghost-border",
    # Colors
    "primary",
    "primary-container",
    "primary-dim",
    "secondary",
    "secondary-container",
    "on-surface",
    "on-surface-variant",
    "on-primary-container",
    "outline-variant",
    # Data colors (backward compat)
    "cyan",
    "cyan-dim",
    "cyan-glow",
    "orange",
    "orange-dim",
    "green",
    "green-dim",
    "red",
    "red-dim",
    "yellow",
    "yellow-dim",
    "purple",
    "accent-primary",
    "accent-muted",
    "error",
    "error-dim",
    # Text
    "text-bright",
    "text-primary",
    "text-dim",
    "text-muted",
    "text-on-cyan",
    "text-strong",
    # Spacing
    "sp-xs",
    "sp-s",
    "sp-m",
    "sp-l",
    "sp-xl",
    "sp-2xl",
    "sp-3xl",
    # Radii
    "r-none",
    "r-s",
    "r-m",
    "r-l",
    "r-xl",
]

# ---------------------------------------------------------------------------
# Dark theme — Digital Obsidian
# ---------------------------------------------------------------------------
DARK_TOKENS: Dict[str, str] = {
    # Surfaces
    "bg-void": "#0e0e10",
    "bg-surface": "#131315",
    "bg-panel": "#19191c",
    "bg-cell": "#1f1f22",
    "bg-hover": "#262528",
    "bg-selected": "#2c2c2f",
    "surface-app": "#0e0e10",
    "surface-panel": "#19191c",
    "surface-canvas": "#131315",
    "surface-container-low": "#131315",
    "surface-container": "#19191c",
    "surface-container-high": "#1f1f22",
    "surface-container-highest": "#262528",
    "surface-bright": "#2c2c2f",
    "surface-container-lowest": "#0e0e10",
    "input-well": "#000000",
    # Borders
    "border-hard": "rgba(72, 71, 74, 0.15)",
    "border-soft": "rgba(72, 71, 74, 0.10)",
    "border-focus": "rgba(197, 196, 255, 0.4)",
    "border-bright": "rgba(72, 71, 74, 0.25)",
    "ghost-border": "rgba(72, 71, 74, 0.15)",
    # Colors — primary violet, secondary teal
    "primary": "#c5c4ff",
    "primary-container": "#9c9bd3",
    "primary-dim": "#b8b6f0",
    "secondary": "#abefec",
    "secondary-container": "#075a58",
    "on-surface": "#f6f3f5",
    "on-surface-variant": "#acaaad",
    "on-primary-container": "#c5c4ff",
    "outline-variant": "rgba(72, 71, 74, 0.15)",
    # Data colors (backward compat mapped to new palette)
    "cyan": "#c5c4ff",
    "cyan-dim": "#9c9bd3",
    "cyan-glow": "#c5c4ff",
    "orange": "#eab308",
    "orange-dim": "#a16207",
    "green": "#abefec",
    "green-dim": "#075a58",
    "red": "#ff6e84",
    "red-dim": "#d73357",
    "yellow": "#eab308",
    "yellow-dim": "#a16207",
    "purple": "#c5c4ff",
    "accent-primary": "#c5c4ff",
    "accent-muted": "#48474a",
    "error": "#ff6e84",
    "error-dim": "#d73357",
    # Text
    "text-bright": "#f6f3f5",
    "text-primary": "#acaaad",
    "text-dim": "#767577",
    "text-muted": "#48474a",
    "text-on-cyan": "#0e0e10",
    "text-strong": "#f6f3f5",
    # Spacing
    "sp-xs": "4px",
    "sp-s": "8px",
    "sp-m": "12px",
    "sp-l": "16px",
    "sp-xl": "24px",
    "sp-2xl": "32px",
    "sp-3xl": "48px",
    # Radii
    "r-none": "0px",
    "r-s": "4px",
    "r-m": "8px",
    "r-l": "12px",
    "r-xl": "16px",
}

# ---------------------------------------------------------------------------
# Light theme — Digital Obsidian Light
# ---------------------------------------------------------------------------
LIGHT_TOKENS: Dict[str, str] = {
    # Surfaces
    "bg-void": "#f6f3f5",
    "bg-surface": "#eeeced",
    "bg-panel": "#ffffff",
    "bg-cell": "#e4e2e5",
    "bg-hover": "#d9d7da",
    "bg-selected": "#c5c3c6",
    "surface-app": "#f6f3f5",
    "surface-panel": "#ffffff",
    "surface-canvas": "#eeeced",
    "surface-container-low": "#eeeced",
    "surface-container": "#ffffff",
    "surface-container-high": "#e4e2e5",
    "surface-container-highest": "#d9d7da",
    "surface-bright": "#ffffff",
    "surface-container-lowest": "#f6f3f5",
    "input-well": "#ffffff",
    # Borders
    "border-hard": "rgba(72, 71, 74, 0.18)",
    "border-soft": "rgba(72, 71, 74, 0.10)",
    "border-focus": "rgba(100, 99, 180, 0.5)",
    "border-bright": "rgba(72, 71, 74, 0.25)",
    "ghost-border": "rgba(72, 71, 74, 0.12)",
    # Colors
    "primary": "#6461b3",
    "primary-container": "#7a78c9",
    "primary-dim": "#5553a0",
    "secondary": "#0d7371",
    "secondary-container": "#abefec",
    "on-surface": "#1a181b",
    "on-surface-variant": "#48474a",
    "on-primary-container": "#3d3b8e",
    "outline-variant": "rgba(72, 71, 74, 0.18)",
    # Data colors
    "cyan": "#6461b3",
    "cyan-dim": "#5553a0",
    "cyan-glow": "#6461b3",
    "orange": "#ca8a04",
    "orange-dim": "#a16207",
    "green": "#0d7371",
    "green-dim": "#075a58",
    "red": "#d73357",
    "red-dim": "#b91c1c",
    "yellow": "#ca8a04",
    "yellow-dim": "#a16207",
    "purple": "#6461b3",
    "accent-primary": "#6461b3",
    "accent-muted": "#767577",
    "error": "#d73357",
    "error-dim": "#b91c1c",
    # Text
    "text-bright": "#1a181b",
    "text-primary": "#48474a",
    "text-dim": "#767577",
    "text-muted": "#acaaad",
    "text-on-cyan": "#ffffff",
    "text-strong": "#1a181b",
    # Spacing
    "sp-xs": "4px",
    "sp-s": "8px",
    "sp-m": "12px",
    "sp-l": "16px",
    "sp-xl": "24px",
    "sp-2xl": "32px",
    "sp-3xl": "48px",
    # Radii
    "r-none": "0px",
    "r-s": "4px",
    "r-m": "8px",
    "r-l": "12px",
    "r-xl": "16px",
}
