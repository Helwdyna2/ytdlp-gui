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
    "bg-surface": "#0f0f12",
    "bg-panel": "#18181b",
    "bg-cell": "#1c1c21",
    "bg-hover": "#27272a",
    "bg-selected": "#52525b",
    "surface-app": "#09090b",
    "surface-panel": "#18181b",
    "surface-canvas": "#0f0f12",
    # Borders
    "border-hard": "#27272a",
    "border-soft": "#27272a",
    "border-focus": "#3b82f6",
    "border-bright": "#3f3f46",
    # Data colors
    "cyan": "#3b82f6",
    "cyan-dim": "#1e40af",
    "cyan-glow": "#3b82f6",
    "orange": "#eab308",
    "orange-dim": "#a16207",
    "green": "#22c55e",
    "green-dim": "#15803d",
    "red": "#ef4444",
    "red-dim": "#dc2626",
    "yellow": "#eab308",
    "yellow-dim": "#a16207",
    "purple": "#8b5cf6",
    "accent-primary": "#fafafa",
    "accent-muted": "#52525b",
    # Text
    "text-bright": "#fafafa",
    "text-primary": "#a1a1aa",
    "text-dim": "#636369",
    "text-muted": "#8a8a94",
    "text-on-cyan": "#09090b",
    "text-strong": "#fafafa",
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
    "bg-panel": "#ffffff",
    "bg-cell": "#e4e4e7",
    "bg-hover": "#d4d4d8",
    "bg-selected": "#a1a1aa",
    "surface-app": "#fafafa",
    "surface-panel": "#ffffff",
    "surface-canvas": "#f4f4f5",
    # Borders
    "border-hard": "#d4d4d8",
    "border-soft": "#e4e4e7",
    "border-focus": "#2563eb",
    "border-bright": "#a1a1aa",
    # Data colors
    "cyan": "#2563eb",
    "cyan-dim": "#1d4ed8",
    "cyan-glow": "#2563eb",
    "orange": "#ca8a04",
    "orange-dim": "#a16207",
    "green": "#16a34a",
    "green-dim": "#15803d",
    "red": "#dc2626",
    "red-dim": "#b91c1c",
    "yellow": "#ca8a04",
    "yellow-dim": "#a16207",
    "purple": "#7c3aed",
    "accent-primary": "#18181b",
    "accent-muted": "#52525b",
    # Text
    "text-bright": "#09090b",
    "text-primary": "#3f3f46",
    "text-dim": "#8a8a92",
    "text-muted": "#71717a",
    "text-on-cyan": "#ffffff",
    "text-strong": "#09090b",
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
