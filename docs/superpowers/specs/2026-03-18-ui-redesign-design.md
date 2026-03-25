# UI Redesign — Complete Visual Overhaul

## Context

The current UI suffers from scattered layouts, poor contrast (multiple WCAG failures), inconsistent hierarchy, dead space, jargon-heavy copy, and a generally undefined visual feel. A previous fix attempt (GUI_FIX_PROMPT.md) did not deliver meaningful results. The user wants a complete UI refactor — not patches to the existing design, but a fresh UI built from scratch on top of the existing backend.

**What stays**: All business logic (`src/core/`, `src/data/`, `src/services/`, `src/utils/`), all managers/workers, all models, the signal/slot integration pattern.

**What's replaced**: Everything in `src/ui/` — theme tokens, QSS builder, shell, main window, all components, all widget layouts and styling.

---

## Design Decisions (User-Approved)

| Decision | Choice |
|----------|--------|
| **Visual direction** | Monochrome Zinc — zinc grays + white, color only for status |
| **Navigation** | Flat sidebar with section headers, all tools one click away |
| **Content layout** | Per-tool — each tool decides its own layout |
| **Color usage** | Monochrome default. Blue=active, Green=done, Yellow=queued, Red=error |
| **Icons** | Sidebar items have icons. Active item has blue left-border accent |
| **Button hierarchy** | White filled=primary, outlined=secondary, red text=destructive |

---

## Theme System — Monochrome Zinc Tokens

> **Breaking change**: The token key vocabulary is completely replaced. `REQUIRED_TOKEN_KEYS` is rewritten. The old naming convention (where `text-primary` was mid-range and `text-bright` was brightest) is inverted: `text-primary` is now the brightest text. The old `ThemeEngine.get_color()` API is preserved but all keys change. No code outside `src/ui/` calls `get_color()` — confirmed by codebase audit.

### Token Key Mapping (Old → New)

| Old Key | New Key | Notes |
|---------|---------|-------|
| `bg-void` | `bg-void` | Kept, renamed value |
| `bg-surface` | `bg-surface` | Kept, new value |
| `bg-panel` | `bg-panel` | Kept, new value |
| `bg-cell` | `bg-cell` | Kept, new value |
| `bg-hover` | `bg-hover` | Kept, new value |
| `bg-selected` | `bg-selected` | Kept, new value |
| `surface-app` | `surface-app` | Alias for bg-void |
| `surface-panel` | `surface-panel` | Alias for bg-panel |
| `surface-canvas` | `surface-canvas` | Alias for bg-surface |
| `border-hard` | `border-hard` | Kept, new value |
| `border-focus` | `border-focus` | Kept, changed to blue |
| `border-bright` | `border-bright` | Kept, new value |
| `cyan` | `cyan` | Now blue (#3b82f6) |
| `cyan-dim` | `cyan-dim` | Semi-transparent blue |
| `cyan-glow` | `cyan-glow` | Faint blue glow |
| `orange` | `orange` | Kept for compat, maps to yellow (#eab308) |
| `orange-dim` | `orange-dim` | Semi-transparent yellow |
| `green` | `green` | New value |
| `green-dim` | `green-dim` | Semi-transparent green |
| `red` | `red` | New value |
| `red-dim` | `red-dim` | Semi-transparent red |
| `yellow` | `yellow` | New value |
| `yellow-dim` | `yellow-dim` | Semi-transparent |
| `purple` | `purple` | Kept for compat |
| `accent-primary` | `accent-primary` | Now white (#fafafa) |
| `accent-muted` | `accent-muted` | Semi-transparent white |
| `text-bright` | `text-bright` | Now #fafafa (same role) |
| `text-primary` | `text-primary` | Now #a1a1aa (body text) |
| `text-dim` | `text-dim` | Now #636369 (placeholder) |
| `text-muted` | `text-muted` | Now #8a8a94 (disabled) |
| `text-on-cyan` | `text-on-cyan` | Dark text on bright bg |
| `text-strong` | `text-strong` | Now #fafafa (headings) |
| `r-none` | `r-none` | Kept (0px) |

### Dark Theme Tokens

#### Surfaces
| Token | Value | Usage |
|-------|-------|-------|
| `bg-void` | `#09090b` | App background, deepest layer |
| `bg-surface` | `#0f0f12` | Sidebar, input backgrounds, cards |
| `bg-panel` | `#18181b` | Slightly raised elements, table alt rows |
| `bg-cell` | `#1c1c21` | Active sidebar item, active token |
| `bg-hover` | `#27272a` | Hover states |
| `bg-selected` | `rgba(59, 130, 246, 0.08)` | Selected row highlight |
| `surface-app` | `#09090b` | Alias for bg-void |
| `surface-panel` | `#18181b` | Alias for bg-panel |
| `surface-canvas` | `#0f0f12` | Alias for bg-surface |

#### Borders
| Token | Value | Usage |
|-------|-------|-------|
| `border-hard` | `#27272a` | Standard borders (inputs, cards, dividers) |
| `border-focus` | `#3b82f6` | Focus ring for keyboard navigation |
| `border-bright` | `#3f3f46` | Emphasized borders (buttons, active elements) |

#### Text
| Token | Value | Ratio on bg-void | Usage |
|-------|-------|-------------------|-------|
| `text-bright` | `#fafafa` | 19.4:1 | Headings, active labels |
| `text-primary` | `#a1a1aa` | 7.53:1 | Body text, values (passes 4.5:1) |
| `text-dim` | `#636369` | 3.22:1 | Placeholder, inactive labels (passes 3:1 large text) |
| `text-muted` | `#8a8a94` | 5.05:1 | Helper text, descriptions (passes 4.5:1) |
| `text-on-cyan` | `#09090b` | — | Dark text on bright backgrounds |
| `text-strong` | `#fafafa` | 19.4:1 | Emphasis text, same as text-bright |

> **Note on text-dim and text-muted**: In the old system, `text-muted` was dimmer than `text-dim`. In the new system, `text-muted` (#8a8a94) is brighter than `text-dim` (#636369) because `text-muted` is used for helper text that must pass 4.5:1, while `text-dim` is only for large/uppercase decorative text at 3:1.

#### Status Colors
| Token | Value | Usage |
|-------|-------|-------|
| `cyan` | `#3b82f6` | Active/in-progress, focus, sidebar accent |
| `cyan-dim` | `rgba(59, 130, 246, 0.30)` | Semi-transparent blue |
| `cyan-glow` | `rgba(59, 130, 246, 0.12)` | Faint blue glow |
| `orange` | `#eab308` | Queued, warning |
| `orange-dim` | `rgba(234, 179, 8, 0.30)` | Semi-transparent yellow |
| `green` | `#22c55e` | Success, completed |
| `green-dim` | `rgba(34, 197, 94, 0.30)` | Semi-transparent green |
| `red` | `#ef4444` | Error, destructive actions |
| `red-dim` | `rgba(239, 68, 68, 0.30)` | Semi-transparent red |
| `yellow` | `#eab308` | Same as orange in zinc theme |
| `yellow-dim` | `rgba(234, 179, 8, 0.30)` | Semi-transparent |
| `purple` | `#8b5cf6` | Reserved |
| `accent-primary` | `#fafafa` | Primary action color (white) |
| `accent-muted` | `rgba(250, 250, 250, 0.12)` | Subtle highlight |

#### Spacing (unchanged from current)
| Token | Value |
|-------|-------|
| `sp-xs` | `4` |
| `sp-s` | `8` |
| `sp-m` | `12` |
| `sp-l` | `16` |
| `sp-xl` | `24` |
| `sp-2xl` | `32` |
| `sp-3xl` | `40` |

#### Radii
| Token | Value |
|-------|-------|
| `r-none` | `0` |
| `r-s` | `3` |
| `r-m` | `5` |

### Light Theme Tokens

The light theme preserves the zinc aesthetic with inverted luminance:

| Token | Dark Value | Light Value |
|-------|-----------|-------------|
| `bg-void` | `#09090b` | `#fafafa` |
| `bg-surface` | `#0f0f12` | `#f4f4f5` |
| `bg-panel` | `#18181b` | `#ffffff` |
| `bg-cell` | `#1c1c21` | `#e4e4e7` |
| `bg-hover` | `#27272a` | `#d4d4d8` |
| `bg-selected` | `rgba(59,130,246,0.08)` | `rgba(37,99,235,0.08)` |
| `surface-app` | `#09090b` | `#fafafa` |
| `surface-panel` | `#18181b` | `#ffffff` |
| `surface-canvas` | `#0f0f12` | `#f4f4f5` |
| `border-hard` | `#27272a` | `#d4d4d8` |
| `border-focus` | `#3b82f6` | `#2563eb` |
| `border-bright` | `#3f3f46` | `#a1a1aa` |
| `cyan` | `#3b82f6` | `#2563eb` |
| `cyan-dim` | `rgba(59,130,246,0.30)` | `rgba(37,99,235,0.15)` |
| `cyan-glow` | `rgba(59,130,246,0.12)` | `rgba(37,99,235,0.08)` |
| `orange` | `#eab308` | `#ca8a04` |
| `orange-dim` | `rgba(234,179,8,0.30)` | `rgba(202,138,4,0.15)` |
| `green` | `#22c55e` | `#16a34a` |
| `green-dim` | `rgba(34,197,94,0.30)` | `rgba(22,163,74,0.15)` |
| `red` | `#ef4444` | `#dc2626` |
| `red-dim` | `rgba(239,68,68,0.30)` | `rgba(220,38,38,0.15)` |
| `yellow` | `#eab308` | `#ca8a04` |
| `yellow-dim` | `rgba(234,179,8,0.30)` | `rgba(202,138,4,0.15)` |
| `purple` | `#8b5cf6` | `#7c3aed` |
| `accent-primary` | `#fafafa` | `#18181b` |
| `accent-muted` | `rgba(250,250,250,0.12)` | `rgba(24,24,27,0.08)` |
| `text-bright` | `#fafafa` | `#09090b` |
| `text-primary` | `#a1a1aa` | `#3f3f46` |
| `text-dim` | `#636369` | `#a1a1aa` |
| `text-muted` | `#8a8a94` | `#71717a` |
| `text-on-cyan` | `#09090b` | `#ffffff` |
| `text-strong` | `#fafafa` | `#09090b` |

Spacing and radii tokens are shared between themes (identical values).

### Typography

- **Primary font**: `"Segoe UI", "Helvetica Neue", "Helvetica", sans-serif` — Qt-compatible system font stack (Qt does not support `-apple-system`/`BlinkMacSystemFont` CSS keywords)
- **Monospace**: `"SF Mono", "Cascadia Code", "Consolas", monospace` — for file paths, format strings
- **Font stacks**: `FONT_DISPLAY` and `FONT_BODY` both use the system font stack. `FONT_CONDENSED` is dropped (section headers use the system font at small size with letter-spacing instead).
- **Heading**: 18px, weight 600, `text-bright`
- **Body**: 12px, `text-primary`
- **Label/Helper**: 11px, `text-muted`
- **Section header**: 9px uppercase, letter-spacing 1.2px, weight 600, `text-dim`

---

## Navigation — Flat Sidebar

### Structure
```
┌─────────────────────────────────┐
│ yt-dlp GUI                      │
│ Download, convert, organize     │
│                                 │
│ DOWNLOAD                        │
│ 🔗 Add URLs              [2]   │  ← badge when active downloads
│ 🌐 Extract URLs                │
│                                 │
│ PROCESS                         │
│ ⚙️ Convert                      │
│ ✂️ Trim                         │
│ 📄 Metadata                     │
│                                 │
│ ORGANIZE                        │
│ 📁 Sort                         │
│ ✏️ Rename                       │
│ 🔍 Match                        │
│                                 │
│ ─────────────────               │
│ ⚙ Settings                      │
└─────────────────────────────────┘
```

### Sidebar behavior
- **Width**: 190px fixed
- **Active item**: `bg-active` background + 2px `blue` left border + `text-primary` text
- **Inactive item**: transparent background + `text-dim` text
- **Section headers**: 9px uppercase, `text-faint`, not clickable
- **Badge**: Blue pill on active item when there are active operations (download count, conversion progress, etc.)
- **Settings**: Separated at bottom by a `border-default` divider
- **Icons**: qtawesome icons (not emoji — emoji rendering is inconsistent across platforms), 14px, dimmed when inactive

### Stage key mapping (backend compatibility)
The backend uses stage keys `ingest`, `prepare`, `organize`, `export`. The new nav maps to individual tools but the stage system is preserved internally:

| Sidebar Item | Backend Stage | Tool/Tab |
|-------------|---------------|----------|
| Add URLs | ingest | add_media |
| Extract URLs | ingest | extract_urls |
| Convert | prepare | convert |
| Trim | prepare | trim |
| Metadata | prepare | metadata |
| Sort | organize | sort |
| Rename | organize | rename |
| Match | organize | match |
| Settings | export | settings |

> **Note**: The `export` stage key is retained purely for backend compatibility. Its only remaining purpose is to host the Settings page. The old Summary tab is removed — download stats are shown inline on the Add URLs page header. If future work removes the stage-key concept from the backend, `export` can be dropped.

---

## Per-Tool Layouts

### Full-width tools

**Add URLs** (landing page)
```
┌────────────────────────────────────────────────────┐
│ Add URLs                    Queued:0 Active:0  0:00│
│ Paste video links, sign in if needed, download.    │
│                                                    │
│ ┌────────────────────────────────────────────────┐ │
│ │ Paste video links here — one per line...       │ │
│ │                                                │ │
│ │ Links are automatically extracted, validated,  │ │
│ │ sorted, and deduplicated.                      │ │
│ └────────────────────────────────────────────────┘ │
│ No links added yet                        [Clear]  │
│                                                    │
│ ┌ Output: ~/Movies/yt-dlp [Browse] │ Concurrent: 3│
│ │ Format: author - id.ext                        │ │
│ └────────────────────────────────────────────────┘ │
│                                                    │
│ ▶ Login status               Not signed in         │
│                                                    │
│ [Load from file]         [Cancel] [Start Download] │
└────────────────────────────────────────────────────┘
```

- Queue stats in header (right-aligned), colored when active
- URL input fills available space
- Config bar: output + concurrent + format in one compact row
- Login status: collapsible detail
- Active state: download items with progress bars replace the URL input area

**Extract URLs** — Full-width. URL input + auto-scroll options inline + output folder + extract button.

**Settings** — Full-width. Grouped sections (Appearance, Browser & Auth, Download Defaults, Rate Limiting, Retry Logic, Advanced Download Options). Each section collapsible.

**Metadata** — Full-width split: file list left, metadata table right (similar to current but cleaner).

### Split-layout tools

**Rename**
```
┌──────────────────────────────────────────────────────┐
│ Rename                                  12 files     │
│ Build a filename pattern, preview and apply.         │
│ Source: /path/to/folder     [Browse] [Scan]          │
│ ┌──────────────┬─────────────────────────────────┐   │
│ │ PATTERN      │ PREVIEW                         │   │
│ │              │ ☑ Select all           12 files  │   │
│ │ ☰ ● OrigName│ ┌───────────────────────────────┐│   │
│ │ ☰ ● Resolut.│ │ Original    →    New Name     ││   │
│ │ ☰ ● Codec   │ │ beach.mp4   → beach_1080.mp4 ││   │
│ │              │ │ drone.mp4   → drone_4k.mp4   ││   │
│ │ AVAILABLE    │ │ ...                           ││   │
│ │ ☰ Index     │ └───────────────────────────────┘│   │
│ │ ☰ Date      │                                   │   │
│ │ ☰ FPS       │ 3 of 12 selected                  │   │
│ │              │    [Refresh Preview] [Apply Rename]│  │
│ │ Sep: [_]     │                                   │   │
│ └──────────────┴─────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

**Sort** — Same split: criteria list (left, drag-reorderable) + folder tree preview (right).

**Match** — Same split: options/checkboxes/exclusions (left) + results table with status/confidence (right).

**Convert** — Same split: file list (left) + codec/quality/preset settings (right) + progress below.

**Trim** — Full-width with internal structure:
```
┌──────────────────────────────────────────────────────┐
│ Trim                                                 │
│ Cut segments from video files.                       │
│                                                      │
│ Mode: (● Single Video) (○ Batch Trim)                │
│ ┌──────────────────────────────────────────────────┐ │
│ │           [Video Preview Area]                   │ │
│ │              (QVideoWidget)                      │ │
│ └──────────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────────┐ │
│ │ [===|=======●===========|===] 00:01:23 / 00:05:00│
│ │ Start: 00:00:15.000  [Set]  End: 00:02:30.000[Set]│
│ └──────────────────────────────────────────────────┘ │
│ ☐ Lossless (fast — may shift to nearest keyframe)    │
│ Output: Same folder (adds _trimmed)  [Browse]        │
│                                                      │
│                            [Cancel]  [Trim Video]    │
│──────────────────────────────────────────────────────│
│ Progress                                       0 / 0 │
└──────────────────────────────────────────────────────┘
```
Video preview uses the existing `VideoPreviewWidget`/`TrimTimelineWidget` — layout is rewritten but the player integration stays.

---

## Button Hierarchy

| Role | Style | Examples |
|------|-------|----------|
| **Primary** | `bg: #fafafa`, `color: #09090b`, `font-weight: 600`, no border | Start Download, Apply Rename, Scan, Extract, Trim Video, Start Matching |
| **Secondary** | `bg: transparent`, `border: 1px solid #27272a`, `color: #a1a1aa` | Browse, Clear, Cancel, Load, Refresh Preview, Compare, Export to CSV |
| **Destructive** | `bg: transparent`, `border: 1px solid #27272a`, `color: #ef4444` | Stop All, Remove, Clear History |

- One primary button per view maximum
- Border-radius: `r-l` (6px) on all buttons
- Padding: 5px 14px (secondary), 5px 18px (primary)

---

## UX Copy Changes

All string replacements from `GUI_AUDIT.md` and `GUI_FIX_PROMPT.md` apply:

| Old | New |
|-----|-----|
| "Unified media workbench" | "Download, convert, and organize" |
| "QUEUE —" / "ACTIVE —" / "CLOCK —" | "Queued: 0" / "Active: 0" / "Elapsed: 0:00" |
| "Summary And Utilities" | (Removed — Settings is its own sidebar item) |
| "Check summary or adjust settings" | (Removed) |
| "Browser && Auth" | "Browser & Authentication" |
| "Fragment Settings" | "Advanced Download Options" |
| "Paste URLs here (one per line or mixed with text)..." | "Paste video links here — one per line, or mixed with other text" |
| "0 URLs ready" | "No links added yet" |
| "{n} URLs ready" | "{n} links ready" |
| Helper bullet list | "Links are automatically extracted, validated, sorted, and deduplicated." |
| "Quality (CRF):" | "Quality:" + tooltip |
| "Lossless (fast, keyframe-limited)" | "Lossless (fast — may shift to nearest keyframe)" |
| "Delete macOS dotfiles (.__*)" | "Remove hidden macOS files (._*) during scan" |
| "Unsort (Flatten)" | "Undo sort (move files back)" |
| "Search exclusions..." | "Exclude terms..." |
| Playwright profile text | "Sign in using the Download tab first to access private content." |
| "Found: 0 URLs" | "No links found yet." |
| "Ready." | "Ready to extract." |

---

## Accessibility

### Contrast
All text tokens pass WCAG 2.1 AA (ratios measured against `bg-void` #09090b):
- `text-bright` (#fafafa): 19.4:1 — passes (normal text)
- `text-primary` (#a1a1aa): 7.53:1 — passes 4.5:1 (normal text)
- `text-muted` (#8a8a94): 5.05:1 — passes 4.5:1 (normal text, used for helper/description text)
- `text-dim` (#636369): 3.22:1 — passes 3:1 (used only for large/uppercase decorative text like section headers)
- `border-hard` (#27272a) on `bg-surface` (#0f0f12): ~1.6:1 — supplemented by spatial cues, not relied on alone for meaning

### Focus indicators
All interactive elements get: `border: 2px solid #3b82f6` on `:focus`. QSS rules for QPushButton, QComboBox, QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QSlider, QCheckBox, QRadioButton.

### Keyboard
- Drag-reorderable lists (Sort criteria, Rename tokens) get small up/down arrow buttons appended to each row (visible on hover or focus). Keyboard: focus a row with Tab, then use Up/Down arrows to reorder.
- All controls reachable via Tab
- Minimum window size: 1000x650 (190px sidebar + 810px min content). Split-layout tools have a minimum left panel of 240px.

---

## Component Architecture

### Shell (replaces current `shell.py`)
```
QMainWindow
└── Central Widget (QHBoxLayout)
    ├── Sidebar (QWidget, 190px fixed)
    │   ├── App title
    │   ├── Section groups with nav items
    │   └── Settings (bottom, separated)
    └── Content Stack (QStackedWidget)
        └── One widget per tool (9 total)
```

The 4-stage StageRail + QStackedWidget model is replaced by a flat sidebar + QStackedWidget with 9 pages (one per tool) plus Settings.

### Components to keep (redesigned)
- `DataPanel` → simplified card container
- `LogFeed` → download log display
- `ActivityDrawer` → collapsible log section (used on Add URLs page)

### Components to remove
- `StageContextStrip` → replaced by in-page header
- `InspectorPanel` → removed (per-tool layouts instead)
- `WorkspaceSurface` → removed (content goes directly in tool widget)
- `StageRail` → replaced by Sidebar
- `AppHeader` → replaced by Sidebar title + per-page stats
- `FooterBar` → simplified to a minimal status bar or removed
- `DataCell` → replaced by inline stat display in page headers

### New components
- `Sidebar` — flat nav with sections, icons, badges
- `ConfigBar` — compact horizontal settings row (used on Add URLs)
- `SplitLayout` — reusable left/right split container for tools that need it

---

## Files to Modify

### Theme layer (complete rewrite)
- `src/ui/theme/tokens.py` — Replace DARK_TOKENS/LIGHT_TOKENS with Zinc palette
- `src/ui/theme/qss_builder.py` — Rewrite QSS for new design system
- `src/ui/theme/icons.py` — Update icon set for new nav items

### Shell layer (complete rewrite)
- `src/ui/shell.py` — Replace with Sidebar + QStackedWidget
- `src/ui/main_window.py` — Rewire to flat nav, 9 tool pages instead of 4 stages

### Components (rewrite/replace)
- `src/ui/components/` — Remove StageContextStrip, InspectorPanel, WorkspaceSurface, StageRail, AppHeader. Add Sidebar, ConfigBar, SplitLayout.

### Widget layouts (rewrite layouts, preserve business logic)
- `src/ui/widgets/ingest_stage_widget.py` → becomes two widgets: `add_urls_page.py`, `extract_urls_page.py`
- `src/ui/widgets/prepare_stage_widget.py` → removed (tools are standalone pages)
- `src/ui/widgets/organize_stage_widget.py` → removed
- `src/ui/widgets/export_stage_widget.py` → removed (Summary stats move to header area, Settings becomes own page)
- `src/ui/widgets/convert_tab_widget.py` → `convert_page.py` (layout rewrite, preserve ConversionManager integration)
- `src/ui/widgets/trim_tab_widget.py` → `trim_page.py` (layout rewrite, preserve TrimManager integration)
- `src/ui/widgets/sort_tab_widget.py` → `sort_page.py` (layout rewrite)
- `src/ui/widgets/rename_tab_widget.py` → `rename_page.py` (layout rewrite)
- `src/ui/widgets/match_tab_widget.py` → `match_page.py` (layout rewrite)
- `src/ui/widgets/settings_tab_widget.py` → `settings_page.py` (layout rewrite)
- `src/ui/widgets/metadata_viewer_widget.py` → `metadata_page.py` (layout rewrite)
- `src/ui/widgets/url_input_widget.py` — Restyle only, logic preserved
- `src/ui/widgets/extract_urls_tab_widget.py` — Restyle + restructure as standalone page

### Shared widgets (restyle)
- `src/ui/widgets/auth_status_widget.py` — Restyle as collapsible inline section
- `src/ui/widgets/file_picker_widget.py` — Restyle
- `src/ui/widgets/output_config_widget.py` — Restyle as compact ConfigBar row
- `src/ui/widgets/progress_widget.py` — Restyle with blue progress bars
- `src/ui/widgets/queue_progress_widget.py` — Restyle, integrate into page header
- `src/ui/widgets/download_log_widget.py` — Restyle

---

## Verification

1. **Visual**: Run `python run.py`, verify each of the 9 tool pages renders correctly
2. **Contrast**: Verify all text meets WCAG 2.1 AA using the token values
3. **Navigation**: Click every sidebar item, verify correct page loads
4. **Focus**: Tab through all controls, verify visible focus ring
5. **Downloads**: Test a download, verify progress bars, status colors, badge count
6. **Split layouts**: Verify Rename, Sort, Match, Convert show correct split
7. **Collapsibles**: Login status, Auth sections expand/collapse
8. **Tests**: Run `pytest -q`, fix any failures from renamed widgets/changed strings
9. **Token invariant**: Verify DARK_TOKENS and LIGHT_TOKENS have identical key sets
10. **String audit**: Grep for old strings ("Browser && Auth", "Summary And Utilities", "QUEUE", "Unified media workbench") — should find zero matches
