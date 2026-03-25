"""Theme token dictionaries for Signal Deck dark and light themes.

Tokens are string key-value pairs consumed by the QSS template engine.
Both DARK_TOKENS and LIGHT_TOKENS must have identical key sets.
"""

from typing import Dict, List

# ---------------------------------------------------------------------------
# Font stacks
# ---------------------------------------------------------------------------
FONT_BODY: str = '"Segoe UI", "Helvetica Neue", "Helvetica", sans-serif'
FONT_DISPLAY: str = FONT_BODY  # Alias for backward compat, not passed to build_qss
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
    # Borders
    "border-hard",
    "border-soft",
    "border-focus",
    "border-bright",
    # Data colors
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
]

# ---------------------------------------------------------------------------
# Dark theme
# ---------------------------------------------------------------------------
DARK_TOKENS: Dict[str, str] = {
    # Surfaces
    "bg-void": "#09090b",
    "bg-surface": "#18181b",
    "bg-panel": "#27272a",
    "bg-cell": "#3f3f46",
    "bg-hover": "#3f3f46",
    "bg-selected": "#52525b",
    "surface-app": "#09090b",
    "surface-panel": "#18181b",
    "surface-canvas": "#27272a",
    # Borders
    "border-hard": "#3f3f46",
    "border-soft": "#27272a",
    "border-focus": "#71717a",
    "border-bright": "#a1a1aa",
    # Data colors
    "cyan": "#38bdf8",
    "cyan-dim": "#0ea5e9",
    "cyan-glow": "#7dd3fc",
    "orange": "#fb923c",
    "orange-dim": "#ea580c",
    "green": "#4ade80",
    "green-dim": "#16a34a",
    "red": "#f87171",
    "red-dim": "#dc2626",
    "yellow": "#facc15",
    "yellow-dim": "#ca8a04",
    "purple": "#c084fc",
    "accent-primary": "#38bdf8",
    "accent-muted": "#0ea5e9",
    # Text
    "text-bright": "#fafafa",
    "text-primary": "#e4e4e7",
    "text-dim": "#636369",
    "text-muted": "#8a8a94",
    "text-on-cyan": "#0c1017",
    "text-strong": "#ffffff",
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
    "r-l": "6px",
}

# ---------------------------------------------------------------------------
# Light theme
# ---------------------------------------------------------------------------
LIGHT_TOKENS: Dict[str, str] = {
    # Surfaces
    "bg-void": "#fafafa",
    "bg-surface": "#f4f4f5",
    "bg-panel": "#e4e4e7",
    "bg-cell": "#d4d4d8",
    "bg-hover": "#d4d4d8",
    "bg-selected": "#a1a1aa",
    "surface-app": "#fafafa",
    "surface-panel": "#f4f4f5",
    "surface-canvas": "#e4e4e7",
    # Borders
    "border-hard": "#d4d4d8",
    "border-soft": "#e4e4e7",
    "border-focus": "#71717a",
    "border-bright": "#52525b",
    # Data colors
    "cyan": "#0284c7",
    "cyan-dim": "#0369a1",
    "cyan-glow": "#38bdf8",
    "orange": "#ea580c",
    "orange-dim": "#c2410c",
    "green": "#16a34a",
    "green-dim": "#15803d",
    "red": "#dc2626",
    "red-dim": "#b91c1c",
    "yellow": "#ca8a04",
    "yellow-dim": "#a16207",
    "purple": "#9333ea",
    "accent-primary": "#0284c7",
    "accent-muted": "#0369a1",
    # Text
    "text-bright": "#09090b",
    "text-primary": "#18181b",
    "text-dim": "#71717a",
    "text-muted": "#52525b",
    "text-on-cyan": "#ffffff",
    "text-strong": "#000000",
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
    "r-l": "6px",
}
