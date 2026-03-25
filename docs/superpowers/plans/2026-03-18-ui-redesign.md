# UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the entire UI layer with a monochrome zinc design featuring flat sidebar navigation, per-tool layouts, and WCAG-compliant contrast.

**Architecture:** The backend (`src/core/`, `src/data/`, `src/services/`) is untouched. We rewrite `src/ui/` bottom-up: tokens first, then QSS, then shell/sidebar, then each tool page. Old stage widgets are replaced by standalone page widgets. The `ThemeEngine` API is preserved; only token values and QSS change.

**Tech Stack:** PyQt6, qtawesome (icons), existing backend managers/workers/models.

**Spec:** `docs/superpowers/specs/2026-03-18-ui-redesign-design.md`

---

## File Structure

### Theme Layer (rewrite in place)
- `src/ui/theme/tokens.py` — New REQUIRED_TOKEN_KEYS, DARK_TOKENS, LIGHT_TOKENS, font stacks
- `src/ui/theme/qss_builder.py` — Complete QSS rewrite for zinc design
- `src/ui/theme/icons.py` — Add sidebar-specific icon entries
- `src/ui/theme/theme_engine.py` — Update `apply_theme()` signature (drop FONT_CONDENSED)

### Shell Layer (rewrite)
- `src/ui/components/sidebar.py` — **New.** Flat nav with sections, icons, badges
- `src/ui/shell.py` — Rewrite: Sidebar + QStackedWidget (replaces Grid+StageRail+AppHeader+Footer)
- `src/ui/main_window.py` — Rewire to register 9 tool pages instead of 4 stages

### Components (modify/remove/add)
- `src/ui/components/config_bar.py` — **New.** Compact horizontal settings row
- `src/ui/components/page_header.py` — **New.** Reusable header with title + description + stats
- `src/ui/components/split_layout.py` — **New.** Reusable left/right split (fixed + flex panels) used by Convert, Metadata, Sort, Rename, Match pages
- Keep: `data_panel.py`, `log_feed.py`, `activity_drawer.py` (restyle via QSS)
- Keep: `collapsible_section.py`, `source_folder_bar.py`, `empty_state.py` (reused by new pages)
- Remove: `stage_context_strip.py`, `inspector_panel.py`, `workspace_surface.py`, `stage_rail.py`, `app_header.py`, `data_cell.py`, `status_tag.py`, `facility_bar.py`, `footer_bar.py`

### Page Widgets (new files replacing old stage/tab widgets)
- `src/ui/pages/add_urls_page.py` — Replaces ingest_stage_widget + url_input_widget layout
- `src/ui/pages/extract_urls_page.py` — Replaces extract_urls_tab_widget layout
- `src/ui/pages/convert_page.py` — Replaces convert_tab_widget layout
- `src/ui/pages/trim_page.py` — Replaces trim_tab_widget layout
- `src/ui/pages/metadata_page.py` — Replaces metadata_viewer_widget layout
- `src/ui/pages/sort_page.py` — Replaces sort_tab_widget layout
- `src/ui/pages/rename_page.py` — Replaces rename_tab_widget layout
- `src/ui/pages/match_page.py` — Replaces match_tab_widget layout
- `src/ui/pages/settings_page.py` — Replaces settings_tab_widget layout
- `src/ui/pages/__init__.py` — Package init

### Dialog Widgets (keep, restyle via QSS)
- `src/ui/widgets/match_detail_dialog.py` — Used by MatchPage
- `src/ui/widgets/match_skip_keywords_dialog.py` — Used by MatchPage
- `src/ui/widgets/metadata_compare_dialog.py` — Used by MetadataPage

### Shared Widgets (restyle, keep logic)
- `src/ui/widgets/url_input_widget.py` — Update placeholder text, remove old styling
- `src/ui/widgets/auth_status_widget.py` — Restyle as collapsible section
- `src/ui/widgets/file_picker_widget.py` — Restyle
- `src/ui/widgets/output_config_widget.py` — Restyle
- `src/ui/widgets/progress_widget.py` — Restyle (blue progress bars)
- `src/ui/widgets/queue_progress_widget.py` — Restyle
- `src/ui/widgets/download_log_widget.py` — Restyle
- `src/ui/widgets/video_preview_widget.py` — Keep (used by trim)
- `src/ui/widgets/trim_timeline_widget.py` — Keep (used by trim)

### Tests (rewrite to match new structure)
- `tests/test_theme_tokens.py` — Update font stack assertions, keep key-set tests
- `tests/test_qss_builder.py` — Update signature, selector assertions
- `tests/test_shell.py` — Rewrite for Sidebar-based shell
- `tests/test_sidebar.py` — **New.** Test sidebar nav creation, switching, badges
- Remove: `test_stage_rail.py`, `test_stage_context_strip.py`, `test_workspace_surface.py`, `test_app_header.py`, `test_footer_bar.py`
- Update: `test_main_window_workbench.py`, `test_ingest_stage_widget.py`, `test_export_stage_widget.py`, `test_prepare_stage_widget.py`, `test_organize_stage_widget.py`
- Check: `test_activity_drawer.py`, `test_log_feed.py`, `test_data_panel.py` — may need updates if QSS restyle changes object names

---

## Task 1: Theme Tokens

**Files:**
- Modify: `src/ui/theme/tokens.py`
- Modify: `tests/test_theme_tokens.py`

- [ ] **Step 1: Update test_theme_tokens.py for new font stacks**

Replace the `test_font_stacks_defined` test to expect the new system font stack instead of Chakra Petch / IBM Plex Mono / Barlow Condensed. Keep all key-set tests unchanged — they will validate our token rewrite.

```python
def test_font_stacks_defined():
    from src.ui.theme.tokens import FONT_DISPLAY, FONT_BODY
    assert "Segoe UI" in FONT_DISPLAY or "Helvetica" in FONT_DISPLAY
    assert "Segoe UI" in FONT_BODY or "Helvetica" in FONT_BODY
    # FONT_CONDENSED is dropped
```

Run: `pytest tests/test_theme_tokens.py -v`
Expected: `test_font_stacks_defined` FAILS (still has old fonts), other tests pass.

- [ ] **Step 2: Rewrite tokens.py with zinc palette**

Replace `FONT_DISPLAY`, `FONT_BODY`, remove `FONT_CONDENSED`. Replace all values in `DARK_TOKENS` and `LIGHT_TOKENS` with the zinc palette from the spec. Keep `REQUIRED_TOKEN_KEYS` identical (same key names — values change, keys don't), **plus add `r-l` (6px radius for buttons)** to `REQUIRED_TOKEN_KEYS`. This is critical: the key set stays the same so all existing QSS references still resolve.

Add `"r-l"` to REQUIRED_TOKEN_KEYS after `"r-m"`:
```python
    # Radii
    "r-none",
    "r-s",
    "r-m",
    "r-l",  # NEW — 6px button radius per spec
]
```

And in both DARK_TOKENS and LIGHT_TOKENS, add:
```python
    "r-l": "6px",
```

Exact color values are in spec section "Dark Theme Tokens" and "Light Theme Tokens".

Font stacks (FONT_DISPLAY is kept as an alias of FONT_BODY for backward compat — both use the same value. The QSS builder only uses FONT_BODY and FONT_MONO):
```python
FONT_BODY: str = '"Segoe UI", "Helvetica Neue", "Helvetica", sans-serif'
FONT_DISPLAY: str = FONT_BODY  # Alias for backward compat, not passed to build_qss
FONT_MONO: str = '"SF Mono", "Cascadia Code", "Consolas", monospace'
# FONT_CONDENSED is removed entirely
```

- [ ] **Step 3: Run token tests**

Run: `pytest tests/test_theme_tokens.py -v`
Expected: ALL PASS. Key-set invariant holds, font stacks match, values are strings.

- [ ] **Step 4: Commit**

```bash
git add src/ui/theme/tokens.py tests/test_theme_tokens.py
git commit -m "feat(theme): replace token values with monochrome zinc palette"
```

---

## Task 2: QSS Builder Rewrite

**Files:**
- Modify: `src/ui/theme/qss_builder.py` (complete rewrite)
- Modify: `src/ui/theme/theme_engine.py` (update apply_theme signature)
- Modify: `tests/test_qss_builder.py`
- Modify: `tests/test_theme_engine.py`

- [ ] **Step 1: Update test_qss_builder.py**

The new QSS builder will have a simpler signature: `build_qss(tokens, font_body, font_mono)`. Update tests:
- Remove references to `FONT_DISPLAY`, `FONT_CONDENSED`
- Update selector assertions: remove `QWidget#appHeader`, `QWidget#stageRail`, `QWidget#stageContextStrip`, `QWidget#workspaceSurface`. Add `QWidget#sidebar`, `QPushButton#sidebarItem`.
- Keep: `QPushButton`, `QLineEdit`, `QProgressBar`, `QTableWidget`, `QCheckBox`, `QComboBox`, `QScrollBar` assertions.
- Update `test_build_qss_includes_object_name_rules`: expect `btnPrimary`, `btnSecondary`, `btnDestructive` instead of `btnCyan`, `btnDanger`.
- Update `test_build_qss_uses_token_colors`: check new token values are present.

Run: `pytest tests/test_qss_builder.py -v`
Expected: FAIL (old builder still in place).

- [ ] **Step 2: Rewrite qss_builder.py**

Complete rewrite. The new `build_qss(tokens, font_body, font_mono)` generates QSS for:

1. **Global base** (`QWidget`): `bg-void` background, `text-primary` color, `font_body` font, 12px
2. **QPushButton**: default secondary style (`transparent` bg, `border-hard` border, `text-primary` color, 6px radius). Plus `#btnPrimary` (`accent-primary` bg, `text-on-cyan` color), `#btnDestructive` (`transparent` bg, `red` color).
3. **Focus states**: `:focus` on all interactive widgets → `2px solid {border-focus}`
4. **Inputs** (QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox): `bg-surface` bg, `border-hard` border, `text-primary` color, 8px radius
5. **QCheckBox/QRadioButton**: `text-primary` color, indicator with `border-bright` border
6. **QSlider**: groove `bg-surface`, handle `accent-primary`
7. **QProgressBar**: `bg-surface` bg, chunk `cyan` color
8. **Tables** (QTableWidget, QTreeWidget, QHeaderView): `bg-void` bg, `border-hard` grid, `bg-hover` on hover, `bg-selected` on selected
9. **QScrollBar**: minimal style, `bg-surface` bg, `bg-hover` handle
10. **QToolTip**: `bg-panel` bg, `text-bright` color, `border-hard` border
11. **Sidebar** (`QWidget#sidebar`): `bg-surface` bg, fixed width
12. **Sidebar items** (`QPushButton#sidebarItem`): transparent, left-aligned, `text-dim` color. `checked` state: `bg-cell` bg, `text-bright` color, 2px `cyan` left border.
13. **Sidebar section headers** (`QLabel#sidebarSection`): 9px, uppercase, `text-dim`, letter-spacing
14. **Page headers**: `text-bright` color, 18px, weight 600
15. **LogFeed** (`QWidget#logFeed`): Keep existing styling pattern, update colors
16. **ActivityDrawer** (`QWidget#activityDrawer`): Keep existing, update colors
17. **DataPanel** (`QWidget#dpanel`): Update to `bg-surface` bg, `border-hard` border

- [ ] **Step 3: Update theme_engine.py**

Change `apply_theme` to use new signature:
```python
from .tokens import DARK_TOKENS, LIGHT_TOKENS, FONT_BODY, FONT_MONO
# ...
def apply_theme(self, app: QApplication) -> None:
    tokens = self._tokens[self._current_theme]
    qss = build_qss(tokens, FONT_BODY, FONT_MONO)
    app.setStyleSheet(qss)
```

Update import line. Remove `FONT_DISPLAY`, `FONT_CONDENSED` imports.

- [ ] **Step 4: Update test_theme_engine.py**

This file hardcodes 4 old color values that will break with new zinc tokens:
- `"#08090d"` in `test_theme_engine_apply_produces_qss` (old `bg-void` dark)
- `"#5a8aaa"` in `test_theme_engine_get_color` (old `cyan`)
- `"#08090d"` in `test_theme_engine_get_color` (old `bg-void`)
- `"#f0f0f2"` in `test_theme_engine_get_color_light` (old `bg-void` light)

Replace all hardcoded values with the new zinc palette values from the spec. Also update any references to `FONT_CONDENSED` or the old `build_qss` signature.

```python
def test_theme_engine_apply_produces_qss(qapp):
    from src.ui.theme.theme_engine import ThemeEngine
    engine = ThemeEngine()
    engine.apply_theme(qapp)
    qss = qapp.styleSheet()
    assert len(qss) > 100
    # Check for new zinc bg-void dark token instead of old #08090d
    from src.ui.theme.tokens import DARK_TOKENS
    assert DARK_TOKENS["bg-void"] in qss

def test_theme_engine_get_color(qapp):
    from src.ui.theme.theme_engine import ThemeEngine
    from src.ui.theme.tokens import DARK_TOKENS
    engine = ThemeEngine()
    assert engine.get_color("cyan") == DARK_TOKENS["cyan"]
    assert engine.get_color("bg-void") == DARK_TOKENS["bg-void"]

def test_theme_engine_get_color_light(qapp):
    from src.ui.theme.theme_engine import ThemeEngine
    from src.ui.theme.tokens import LIGHT_TOKENS
    engine = ThemeEngine()
    engine.set_theme("light")
    assert engine.get_color("bg-void") == LIGHT_TOKENS["bg-void"]
```

- [ ] **Step 5: Run all theme tests**

Run: `pytest tests/test_qss_builder.py tests/test_theme_tokens.py tests/test_theme_engine.py -v`
Expected: ALL PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ui/theme/qss_builder.py src/ui/theme/theme_engine.py tests/test_qss_builder.py tests/test_theme_engine.py
git commit -m "feat(theme): rewrite QSS builder for monochrome zinc design system"
```

---

## Task 3: Icons Update

**Files:**
- Modify: `src/ui/theme/icons.py`
- Modify: `tests/test_icons.py`

- [ ] **Step 1: Update icons.py NAV_ICONS for flat sidebar**

Add/update entries for all 9 sidebar tools:
```python
NAV_ICONS = {
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
}
```

- [ ] **Step 2: Update test_icons.py if it asserts specific icon names**

Run: `pytest tests/test_icons.py -v`
Expected: PASS. Fix any assertions that reference removed keys.

- [ ] **Step 3: Commit**

```bash
git add src/ui/theme/icons.py tests/test_icons.py
git commit -m "feat(icons): update nav icons for flat sidebar tools"
```

---

## Task 4: Sidebar Component

**Files:**
- Create: `src/ui/components/sidebar.py`
- Create: `tests/test_sidebar.py`

- [ ] **Step 1: Write test_sidebar.py**

```python
"""Tests for Sidebar component."""
import pytest, sys
pytest.importorskip("PyQt6.QtWidgets")

@pytest.fixture(autouse=True)
def reset_singleton():
    from src.ui.theme.theme_engine import ThemeEngine
    ThemeEngine._instance = None
    yield
    ThemeEngine._instance = None

@pytest.fixture
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app

def test_sidebar_creates(qapp):
    from src.ui.components.sidebar import Sidebar
    sb = Sidebar()
    assert sb is not None

def test_sidebar_has_nav_items(qapp):
    from src.ui.components.sidebar import Sidebar
    sb = Sidebar()
    # Should have 9 tool items + settings
    assert sb.item_count() >= 9

def test_sidebar_emits_tool_selected(qapp):
    from src.ui.components.sidebar import Sidebar
    sb = Sidebar()
    received = []
    sb.tool_selected.connect(lambda key: received.append(key))
    sb.select_tool("convert")
    assert received == ["convert"]

def test_sidebar_set_badge(qapp):
    from src.ui.components.sidebar import Sidebar
    sb = Sidebar()
    sb.set_badge("add_urls", 3)
    # Should not crash; badge is visual
```

Run: `pytest tests/test_sidebar.py -v`
Expected: FAIL (sidebar.py doesn't exist yet).

- [ ] **Step 2: Implement sidebar.py**

Create `src/ui/components/sidebar.py`:
- Class `Sidebar(QWidget)` with signal `tool_selected = pyqtSignal(str)`
- Constructor builds a QVBoxLayout with:
  - App title label ("yt-dlp GUI") + subtitle ("Download, convert, organize")
  - Three section groups (DOWNLOAD, PROCESS, ORGANIZE) each with a QLabel section header and QPushButton items
  - QButtonGroup for exclusive selection (checkable buttons)
  - Settings item at bottom, separated by a line
- Each nav button gets: `setObjectName("sidebarItem")`, `setCheckable(True)`, icon via `get_icon()`, text label
- Active item: `setChecked(True)` → QSS handles visual state
- Methods: `select_tool(key)`, `set_badge(key, count)`, `item_count()`, `active_tool()`
- Badge: QLabel overlay on the button, styled as blue pill
- Fixed width: `setFixedWidth(190)`

The nav items and their keys:
```python
SECTIONS = [
    ("DOWNLOAD", [("add_urls", "Add URLs"), ("extract_urls", "Extract URLs")]),
    ("PROCESS", [("convert", "Convert"), ("trim", "Trim"), ("metadata", "Metadata")]),
    ("ORGANIZE", [("sort", "Sort"), ("rename", "Rename"), ("match", "Match")]),
]
```

- [ ] **Step 3: Run sidebar tests**

Run: `pytest tests/test_sidebar.py -v`
Expected: ALL PASS.

- [ ] **Step 4: Commit**

```bash
git add src/ui/components/sidebar.py tests/test_sidebar.py
git commit -m "feat(ui): add Sidebar component with flat nav and sections"
```

---

## Task 5: Page Header & Config Bar Components

**Files:**
- Create: `src/ui/components/page_header.py`
- Create: `src/ui/components/config_bar.py`

- [ ] **Step 1: Write tests for PageHeader and ConfigBar**

Create `tests/test_page_header.py` and `tests/test_config_bar.py`:

```python
# tests/test_page_header.py
import pytest, sys
pytest.importorskip("PyQt6.QtWidgets")

@pytest.fixture(autouse=True)
def reset_singleton():
    from src.ui.theme.theme_engine import ThemeEngine
    ThemeEngine._instance = None
    yield
    ThemeEngine._instance = None

@pytest.fixture
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app

def test_page_header_creates(qapp):
    from src.ui.components.page_header import PageHeader
    header = PageHeader(title="Test", description="Desc")
    assert header is not None

def test_page_header_set_title(qapp):
    from src.ui.components.page_header import PageHeader
    header = PageHeader(title="Test", description="Desc")
    header.set_title("New Title")
    assert header.title_label.text() == "New Title"

def test_page_header_add_stat(qapp):
    from src.ui.components.page_header import PageHeader
    header = PageHeader(title="Test", description="Desc")
    header.add_stat("Queued", "5")
    # Should not crash; stat is visual
```

```python
# tests/test_config_bar.py
import pytest, sys
pytest.importorskip("PyQt6.QtWidgets")

@pytest.fixture(autouse=True)
def reset_singleton():
    from src.ui.theme.theme_engine import ThemeEngine
    ThemeEngine._instance = None
    yield
    ThemeEngine._instance = None

@pytest.fixture
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app

def test_config_bar_creates(qapp):
    from src.ui.components.config_bar import ConfigBar
    bar = ConfigBar()
    assert bar is not None

def test_config_bar_add_field(qapp):
    from PyQt6.QtWidgets import QLineEdit
    from src.ui.components.config_bar import ConfigBar
    bar = ConfigBar()
    bar.add_field("Label", QLineEdit())
    # Should not crash
```

Run: `pytest tests/test_page_header.py tests/test_config_bar.py -v`
Expected: FAIL (files don't exist yet).

- [ ] **Step 2: Implement page_header.py**

Simple reusable header widget:
- `PageHeader(QWidget)` with `title_label: QLabel` (18px, `text-bright`), `description: QLabel` (12px, `text-muted`)
- Optional right-side stats area (QHBoxLayout) for stat counters
- Methods: `set_title(text)`, `set_description(text)`, `add_stat(label, value, color=None)`, `update_stat(label, value, color=None)`
- `setObjectName("pageHeader")`

- [ ] **Step 3: Implement config_bar.py**

Compact horizontal config row:
- `ConfigBar(QWidget)` — single-row QHBoxLayout
- Methods: `add_field(label, widget)`, `add_separator()`
- Styled: `bg-surface` background, `border-hard` border, 8px radius, 12px padding
- `setObjectName("configBar")`

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_page_header.py tests/test_config_bar.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Implement split_layout.py**

Reusable split layout used by 5 pages (Convert, Metadata, Sort, Rename, Match):
- `SplitLayout(QWidget)` — QHBoxLayout with left (flex) and right (fixed-width) panels
- Constructor: `SplitLayout(right_width=320)`
- Properties: `left_panel` (QWidget), `right_panel` (QWidget) — consumers add children to these
- Right panel gets `setFixedWidth(right_width)`, left panel stretches
- `setObjectName("splitLayout")`

Add a basic test in `tests/test_split_layout.py`:
```python
import pytest, sys
pytest.importorskip("PyQt6.QtWidgets")

@pytest.fixture(autouse=True)
def reset_singleton():
    from src.ui.theme.theme_engine import ThemeEngine
    ThemeEngine._instance = None
    yield
    ThemeEngine._instance = None

@pytest.fixture
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app

def test_split_layout_creates(qapp):
    from src.ui.components.split_layout import SplitLayout
    sl = SplitLayout()
    assert sl.left_panel is not None
    assert sl.right_panel is not None

def test_split_layout_right_width(qapp):
    from src.ui.components.split_layout import SplitLayout
    sl = SplitLayout(right_width=260)
    assert sl.right_panel.maximumWidth() == 260
```

- [ ] **Step 6: Run all component tests**

Run: `pytest tests/test_page_header.py tests/test_config_bar.py tests/test_split_layout.py -v`
Expected: ALL PASS.

- [ ] **Step 7: Commit**

```bash
git add src/ui/components/page_header.py src/ui/components/config_bar.py src/ui/components/split_layout.py tests/test_page_header.py tests/test_config_bar.py tests/test_split_layout.py
git commit -m "feat(ui): add PageHeader, ConfigBar, and SplitLayout reusable components"
```

---

## Task 6: Shell Rewrite

**Files:**
- Modify: `src/ui/shell.py` (complete rewrite)
- Modify: `tests/test_shell.py` (rewrite tests)
- Remove references to: `StageRail`, `AppHeader`, `FooterBar`

- [ ] **Step 1: Rewrite test_shell.py**

New tests for sidebar-based shell:
```python
def test_shell_creates(qapp):
    from src.ui.shell import Shell
    shell = Shell()
    assert shell is not None

def test_shell_has_sidebar(qapp):
    from src.ui.shell import Shell
    shell = Shell()
    assert shell.sidebar is not None
    assert shell.content_stack is not None

def test_shell_register_tool(qapp):
    from src.ui.shell import Shell
    from src.ui.stage_definitions import StageDefinition
    from PyQt6.QtWidgets import QWidget
    shell = Shell()
    shell.register_stage(StageDefinition("prepare", "Prepare"), QWidget())
    assert shell.content_stack.count() >= 1

def test_shell_switch_to_tool(qapp):
    from src.ui.shell import Shell
    from src.ui.stage_definitions import StageDefinition
    from PyQt6.QtWidgets import QWidget
    shell = Shell()
    shell.register_stage(StageDefinition("ingest", "Ingest"), QWidget())
    shell.register_stage(StageDefinition("prepare", "Prepare"), QWidget())
    shell.switch_to_stage("prepare")
    assert shell.active_stage() == "prepare"
```

Run: `pytest tests/test_shell.py -v`
Expected: FAIL.

- [ ] **Step 2: Rewrite shell.py**

Replace the Grid+StageRail+AppHeader+Footer with:
```python
class Shell(QWidget):
    stage_changed = pyqtSignal(str)

    def __init__(self):
        self.stage_rail = StageRail()
        self.content_stack = QStackedWidget()
        # Grid layout: header | stage rail | content | footer
        self.stage_rail.stage_selected.connect(self.switch_to_stage)

    def register_stage(self, definition, widget): ...
    def switch_to_stage(self, key): ...
    def active_stage(self): ...
    def set_stage_status(self, key, status): ...
```

Keep the public stage API stable throughout the migration. Preserve `stage_definitions.py` and the external stage keys `ingest`, `prepare`, `organize`, and `export`. If internal tool-level pages are introduced, map them behind the shell/stage layer rather than exposing tool keys to callers.

- [ ] **Step 3: Run shell tests**

Run: `pytest tests/test_shell.py -v`
Expected: ALL PASS.

- [ ] **Step 4: Commit**

```bash
git add src/ui/shell.py tests/test_shell.py
git commit -m "feat(shell): rewrite shell with flat sidebar navigation"
```

---

## Task 7: Pages Package & Add URLs Page

**Files:**
- Create: `src/ui/pages/__init__.py`
- Create: `src/ui/pages/add_urls_page.py`

This is the most important page — it's the landing screen. It replaces `ingest_stage_widget.py`'s "Add Media" tab.

- [ ] **Step 1: Create pages package**

Create `src/ui/pages/__init__.py` (empty).

- [ ] **Step 2: Implement add_urls_page.py**

`AddUrlsPage(QWidget)` — full-width layout:
- `PageHeader` with title "Add URLs", description "Paste video links, sign in if needed, then download."
- Right-side stats: Queued, Active, Done (optional), Elapsed — using `PageHeader.add_stat()`
- `UrlInputWidget` (injected) — placeholder text updated
- Status row: "{n} links ready" / "No links added yet" + Clear button
- `ConfigBar` with: output folder (injected `OutputConfigWidget`), concurrent slider, filename format display
- Collapsible auth section (injected `AuthStatusWidget`)
- Action bar: [Load from file] left, [Cancel] [Start Download] right
- Download progress area (injected `QueueProgressWidget`, `ProgressWidget`, `DownloadLogWidget`) — shown when downloads active

Constructor takes all injected widgets as parameters (same pattern as current `IngestStageWidget`).

Public API:
- `set_queue_stats(queued, active, done, elapsed)` — update header stats with colors
- `set_download_mode(active: bool)` — switch between URL input view and download progress view

- [ ] **Step 3: Commit**

```bash
git add src/ui/pages/__init__.py src/ui/pages/add_urls_page.py
git commit -m "feat(pages): add AddUrlsPage as landing screen"
```

---

## Task 8: Extract URLs Page

**Files:**
- Create: `src/ui/pages/extract_urls_page.py`

- [ ] **Step 1: Implement extract_urls_page.py**

`ExtractUrlsPage(QWidget)` — full-width layout. Restructure `extract_urls_tab_widget.py` content:
- PageHeader: "Extract URLs" / "Extract links from web pages."
- URL input for page URLs
- Auto-scroll options inline (collapsible)
- Output folder selection
- Status line: "No links found yet." / "Ready to extract."
- Action bar: [Stop] [Extract]

Preserve all `ExtractUrlsManager` signal connections from the original widget. The business logic stays; only the layout changes.

UX copy changes:
- Playwright profile text → "Sign in using the Download tab first to access private content."
- "Found: 0 URLs" → "No links found yet."
- "Ready." → "Ready to extract."

- [ ] **Step 2: Commit**

```bash
git add src/ui/pages/extract_urls_page.py
git commit -m "feat(pages): add ExtractUrlsPage"
```

---

## Task 9: Convert Page

**Files:**
- Create: `src/ui/pages/convert_page.py`

- [ ] **Step 1: Implement convert_page.py**

`ConvertPage(QWidget)` — uses `SplitLayout` (file list left, settings right):
- PageHeader: "Convert" / "Transcode video files to different formats."
- Left panel (flex): File list with Add Files/Add Folder buttons
- Right panel (fixed ~320px): Codec dropdown, Quality slider (tooltip: "CRF — lower values mean higher quality"), Preset, Hardware acceleration (combined label), Output folder
- Below split: Progress section with job list
- Primary button: "Start Convert"

Preserve all `ConversionManager`, `FFprobeWorker`, `FolderScanWorker` connections from `convert_tab_widget.py`. Move the `FileListWidget` inner class as-is.

UX copy: "Quality (CRF):" → "Quality:" with tooltip. Hardware accel: combine into single label.

- [ ] **Step 2: Commit**

```bash
git add src/ui/pages/convert_page.py
git commit -m "feat(pages): add ConvertPage with split layout"
```

---

## Task 10: Trim Page

**Files:**
- Create: `src/ui/pages/trim_page.py`

- [ ] **Step 1: Implement trim_page.py**

`TrimPage(QWidget)` — full-width with internal structure:
- PageHeader: "Trim" / "Cut segments from video files."
- Mode selector (Single Video / Batch Trim)
- Video preview area (reuse `VideoPreviewWidget`)
- Timeline (reuse `TrimTimelineWidget`)
- Start/End time fields with Set to Current buttons
- Lossless checkbox: "Lossless (fast — may shift to nearest keyframe)"
- Output folder
- Action bar: [Cancel] [Trim Video]
- Progress section below

Preserve all `TrimManager`, `VideoPreviewWidget`, `TrimTimelineWidget` integration. This is the most complex page — keep all existing business logic, state management, and worker connections from `trim_tab_widget.py`.

- [ ] **Step 2: Commit**

```bash
git add src/ui/pages/trim_page.py
git commit -m "feat(pages): add TrimPage preserving video preview integration"
```

---

## Task 11: Metadata Page

**Files:**
- Create: `src/ui/pages/metadata_page.py`

- [ ] **Step 1: Implement metadata_page.py**

`MetadataPage(QWidget)` — uses `SplitLayout`:
- PageHeader: "Metadata" / "Inspect media file properties."
- Left: File list with source folder browse + scan
- Right: Metadata detail table (Basic Info / Raw FFprobe tabs)
- Bottom: [Compare] [Export to CSV] buttons

Preserve all `FFprobeWorker` integration from `metadata_viewer_widget.py`.

- [ ] **Step 2: Commit**

```bash
git add src/ui/pages/metadata_page.py
git commit -m "feat(pages): add MetadataPage with split layout"
```

---

## Task 12: Sort Page

**Files:**
- Create: `src/ui/pages/sort_page.py`

- [ ] **Step 1: Implement sort_page.py**

`SortPage(QWidget)` — uses `SplitLayout`:
- PageHeader: "Sort" / "Organize media into folder structures."
- Source bar: folder path + [Browse] + [Scan]
- Left: Sort criteria (drag-reorderable list with visible grip handles + up/down arrow buttons)
- Right: Proposed structure tree preview with [Expand All] [Collapse All]
- Destination section: output folder, Move/Copy radio, checkboxes
- UX copy: "Remove hidden macOS files (._*) during scan", "Undo sort (move files back)"

Preserve all `SortManager`, `SortWorker` connections from `sort_tab_widget.py`.

- [ ] **Step 2: Commit**

```bash
git add src/ui/pages/sort_page.py
git commit -m "feat(pages): add SortPage with split layout"
```

---

## Task 13: Rename Page

**Files:**
- Create: `src/ui/pages/rename_page.py`

- [ ] **Step 1: Implement rename_page.py**

`RenamePage(QWidget)` — uses `SplitLayout` per mockup:
- PageHeader: "Rename" / "Build a filename pattern from tokens, then preview and apply."
- Source bar: folder + [Browse] + [Scan]
- Left panel (260px fixed): "Pattern Tokens" section (active, with blue dots + drag handles) and "Available" section. Separator field, Custom text field, Index Start/Padding, Date Format, Remove chars.
- Right panel: Preview table with checkbox selection, Original → New Name columns, alternating row shading
- Bottom: "{n} of {m} selected" + [Refresh Preview] + [Apply Rename]

Active tokens get blue dot indicator and `bg-cell` background. Available tokens get `bg-surface` background and `text-dim` text.

Preserve `RenameTokenWidget` inner class and all rename logic from `rename_tab_widget.py`.

- [ ] **Step 2: Commit**

```bash
git add src/ui/pages/rename_page.py
git commit -m "feat(pages): add RenamePage with token builder and preview"
```

---

## Task 14: Match Page

**Files:**
- Create: `src/ui/pages/match_page.py`

- [ ] **Step 1: Implement match_page.py**

`MatchPage(QWidget)` — uses `SplitLayout`:
- PageHeader: "Match" / "Match files against scene databases."
- Left panel: Source folder, database checkboxes (properly spaced), position tags, include already-named, "Exclude terms..." field, [Scan Folder] + [Start Matching] buttons
- Right panel: Results table (Select, Status, Confidence, Original Name, Matched Name)
- Bottom: [View Match Details] [Manual Search...] + [Stop]

UX copy: "Search exclusions..." → "Exclude terms..."

Preserve all `MatchManager` connections from `match_tab_widget.py`.

- [ ] **Step 2: Commit**

```bash
git add src/ui/pages/match_page.py
git commit -m "feat(pages): add MatchPage with split layout"
```

---

## Task 15: Settings Page

**Files:**
- Create: `src/ui/pages/settings_page.py`

- [ ] **Step 1: Implement settings_page.py**

`SettingsPage(QWidget)` — full-width with collapsible sections:
- PageHeader: "Settings" / "Configure app-wide preferences."
- Sections (each a collapsible QGroupBox or details-like widget):
  - Appearance (theme toggle)
  - Browser & Authentication (was "Browser && Auth")
  - Download Defaults (Force Overwrite with tooltip, Video Only)
  - Rate Limiting
  - Retry Logic
  - Advanced Download Options (was "Fragment Settings")

UX copy: "Browser && Auth" → "Browser & Authentication", "Fragment Settings" → "Advanced Download Options". Add tooltip to Force Overwrite: "Replace existing files instead of skipping them".

Preserve all settings persistence logic from `settings_tab_widget.py`.

- [ ] **Step 2: Commit**

```bash
git add src/ui/pages/settings_page.py
git commit -m "feat(pages): add SettingsPage with collapsible sections"
```

---

## Task 16: Main Window Rewire

**Files:**
- Modify: `src/ui/main_window.py` (major rewrite)

This is the integration task — connecting all pages to the shell and wiring up all backend signals.

- [ ] **Step 1: Update main_window.py imports**

Replace imports of old stage widgets with new page imports:
```python
from src.ui.pages.add_urls_page import AddUrlsPage
from src.ui.pages.extract_urls_page import ExtractUrlsPage
from src.ui.pages.convert_page import ConvertPage
from src.ui.pages.trim_page import TrimPage
from src.ui.pages.metadata_page import MetadataPage
from src.ui.pages.sort_page import SortPage
from src.ui.pages.rename_page import RenamePage
from src.ui.pages.match_page import MatchPage
from src.ui.pages.settings_page import SettingsPage
```

- [ ] **Step 2: Rewrite _setup_ui()**

Replace the 4-stage registration with 9-tool registration:
```python
def _setup_ui(self):
    # Create shared widgets (same as before)
    self.url_input = UrlInputWidget()
    self.auth_status = AuthStatusWidget(...)
    # ... etc

    # Create pages
    self.add_urls_page = AddUrlsPage(url_input=self.url_input, ...)
    self.extract_urls_page = ExtractUrlsPage(...)
    self.convert_page = ConvertPage(...)
    # ... etc

    # Register tools with shell
    self.shell.register_tool("add_urls", self.add_urls_page)
    self.shell.register_tool("extract_urls", self.extract_urls_page)
    self.shell.register_tool("convert", self.convert_page)
    self.shell.register_tool("trim", self.trim_page)
    self.shell.register_tool("metadata", self.metadata_page)
    self.shell.register_tool("sort", self.sort_page)
    self.shell.register_tool("rename", self.rename_page)
    self.shell.register_tool("match", self.match_page)
    self.shell.register_tool("settings", self.settings_page)
```

- [ ] **Step 3: Rewire _connect_signals()**

Map all existing download manager signals to the new `AddUrlsPage` methods. Map conversion signals to `ConvertPage`, trim signals to `TrimPage`, etc. The signal names from the managers haven't changed — only the UI widgets receiving them.

Key connections:
- `download_manager.download_progress` → `add_urls_page` progress update
- `download_manager.queue_progress` → `add_urls_page.set_queue_stats()`
- `download_manager.all_completed` → `add_urls_page.set_download_mode(False)`
- Badge updates: `download_manager.queue_progress` → `shell.set_badge("add_urls", active_count)`

- [ ] **Step 4: Update minimum window size**

```python
self.setMinimumSize(1000, 650)
```

- [ ] **Step 5: Remove old stage widget imports and stage definitions**

Delete imports for `IngestStageWidget`, `PrepareStageWidget`, `OrganizeStageWidget`, `ExportStageWidget`, `StageDefinition`.

- [ ] **Step 6: Commit**

```bash
git add src/ui/main_window.py
git commit -m "feat(main): rewire main window for 9-tool flat navigation"
```

---

## Task 17: UX Copy Updates in Shared Widgets

**Files:**
- Modify: `src/ui/widgets/url_input_widget.py`
- Modify: `src/ui/widgets/auth_status_widget.py`
- Modify: `src/ui/widgets/output_config_widget.py`

- [ ] **Step 1: Update url_input_widget.py strings**

- Placeholder: "Paste video links here — one per line, or mixed with other text"
- Helper text: "Links are automatically extracted, validated, sorted, and deduplicated."
- Zero state: "No links added yet"
- Non-zero: "{n} links ready"

- [ ] **Step 2: Update auth_status_widget.py**

Replace any Playwright-mentioning user-visible text with: "Sign in using the Download tab first to access private content."

- [ ] **Step 3: Commit**

```bash
git add src/ui/widgets/url_input_widget.py src/ui/widgets/auth_status_widget.py src/ui/widgets/output_config_widget.py
git commit -m "fix(copy): update UX copy across shared widgets"
```

---

## Task 18: Clean Up Old Files

**Files:**
- Remove: `src/ui/components/stage_context_strip.py`
- Remove: `src/ui/components/inspector_panel.py`
- Remove: `src/ui/components/workspace_surface.py`
- Remove: `src/ui/components/stage_rail.py`
- Remove: `src/ui/components/app_header.py`
- Remove: `src/ui/components/data_cell.py`
- Remove: `src/ui/components/status_tag.py`
- Remove: `src/ui/components/facility_bar.py`
- Remove: `src/ui/components/footer_bar.py` (imported by old shell.py)
- Remove: `src/ui/widgets/ingest_stage_widget.py`
- Remove: `src/ui/widgets/prepare_stage_widget.py`
- Remove: `src/ui/widgets/organize_stage_widget.py`
- Remove: `src/ui/widgets/export_stage_widget.py`
- Remove: `src/ui/widgets/convert_tab_widget.py`
- Remove: `src/ui/widgets/trim_tab_widget.py`
- Remove: `src/ui/widgets/sort_tab_widget.py`
- Remove: `src/ui/widgets/rename_tab_widget.py`
- Remove: `src/ui/widgets/match_tab_widget.py`
- Remove: `src/ui/widgets/settings_tab_widget.py`
- Remove: `src/ui/widgets/metadata_viewer_widget.py`
- Remove: `src/ui/widgets/extract_urls_tab_widget.py`
- Preserve: `src/ui/stage_definitions.py` so the stable external stage keys `ingest`, `prepare`, `organize`, and `export` remain part of the shell contract
- Modify: `src/ui/widgets/__init__.py` — Remove re-exports of deleted widget classes
- Modify: `src/ui/components/__init__.py` — Remove re-exports of deleted component classes, add new components
- Remove old tests: `tests/test_stage_rail.py`, `tests/test_stage_context_strip.py`, `tests/test_workspace_surface.py`, `tests/test_app_header.py`, `tests/test_footer_bar.py`

- [ ] **Step 1: Remove old component files**

Only remove files that are no longer imported anywhere. Run a quick grep for each file's class name before deleting to confirm nothing still imports it.

- [ ] **Step 2: Remove old widget files**

Same approach — grep for the class name, confirm no remaining imports, then delete. Don't forget `extract_urls_tab_widget.py`.

- [ ] **Step 3: Update __init__.py files**

- `src/ui/widgets/__init__.py`: Remove re-exports of all deleted widget classes (IngestStageWidget, PrepareStageWidget, OrganizeStageWidget, ExportStageWidget, ConvertTabWidget, TrimTabWidget, SortTabWidget, RenameTabWidget, MatchTabWidget, SettingsTabWidget, MetadataViewerWidget, ExtractUrlsTabWidget).
- `src/ui/components/__init__.py`: Remove re-exports of deleted components (StageContextStrip, InspectorPanel, WorkspaceSurface, StageRail, AppHeader, DataCell, StatusTag, FacilityBar, FooterBar). Add imports for new components (Sidebar, PageHeader, ConfigBar, SplitLayout).

- [ ] **Step 4: Remove old test files**

Delete tests for removed components.

Note: Do NOT delete `tests/test_data_panel.py` — `data_panel.py` is kept and restyled.

- [ ] **Step 5: Run full test suite**

Run: `pytest -q`
Expected: ALL PASS (or identify remaining failures from import references).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: remove old stage widgets, components, and tests"
```

---

## Task 19: Update Remaining Tests

**Files:**
- Modify: `tests/test_main_window_workbench.py`
- Modify: `tests/test_ingest_stage_widget.py` → rename/rewrite or delete
- Modify: `tests/test_export_stage_widget.py` → delete
- Modify: `tests/test_prepare_stage_widget.py` → delete
- Modify: `tests/test_organize_stage_widget.py` → delete
- Modify: `tests/test_components.py`

- [ ] **Step 1: Update test_main_window_workbench.py**

This test creates a MainWindow and verifies it starts up. Update to expect the new shell structure (sidebar, content_stack, 9 tools instead of 4 stages).

- [ ] **Step 2: Delete obsolete stage widget tests**

Delete `test_ingest_stage_widget.py`, `test_export_stage_widget.py`, `test_prepare_stage_widget.py`, `test_organize_stage_widget.py` (the old stage containers are gone).

- [ ] **Step 3: Update test_components.py**

Remove references to deleted components. Add basic import tests for new components (Sidebar, PageHeader, ConfigBar, SplitLayout).

- [ ] **Step 4: Create basic instantiation tests for all 9 page widgets**

Create `tests/test_pages.py` with one test per page that verifies the class can be imported and instantiated without crashing. These are smoke tests — they catch import errors and constructor issues:

```python
"""Basic instantiation tests for all page widgets."""
import pytest, sys
pytest.importorskip("PyQt6.QtWidgets")

@pytest.fixture(autouse=True)
def reset_singleton():
    from src.ui.theme.theme_engine import ThemeEngine
    ThemeEngine._instance = None
    yield
    ThemeEngine._instance = None

@pytest.fixture
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app

def test_import_all_pages(qapp):
    from src.ui.pages import (
        add_urls_page, extract_urls_page, convert_page, trim_page,
        metadata_page, sort_page, rename_page, match_page, settings_page,
    )
    # All modules should import without error
```

Note: Pages that require injected widgets (AddUrlsPage needs UrlInputWidget, etc.) may need factory fixtures — add those as needed based on each page's constructor.

- [ ] **Step 5: Run full test suite**

Run: `pytest -q`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "test: update test suite for new UI architecture"
```

---

## Task 20: Final Verification

- [ ] **Step 1: Visual smoke test**

Run: `source .venv/bin/activate && python run.py`

Verify:
1. App opens with sidebar visible on the left
2. "Add URLs" is selected by default
3. Click each of the 9 sidebar items — correct page loads
4. Enter a URL and click Start Download — progress appears
5. Sidebar badge shows active download count
6. Navigate to Rename — split layout with token list and preview table
7. Navigate to Settings — collapsible sections render

- [ ] **Step 2: String audit**

Run: `grep -r "Browser && Auth" src/` — should find 0 matches
Run: `grep -r "Summary And Utilities" src/` — should find 0 matches
Run: `grep -r "QUEUE" src/ui/` — should find 0 matches (as standalone label)
Run: `grep -r "Unified media workbench" src/` — should find 0 matches
Run: `grep -r "Fragment Settings" src/` — should find 0 matches

- [ ] **Step 3: Token invariant check**

Run: `python -c "from src.ui.theme.tokens import DARK_TOKENS, LIGHT_TOKENS; assert set(DARK_TOKENS.keys()) == set(LIGHT_TOKENS.keys()); print('OK')"` — should print OK

- [ ] **Step 4: Full test suite**

Run: `pytest -q`
Expected: ALL PASS.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete UI redesign - monochrome zinc with flat navigation"
```
