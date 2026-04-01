# Digital Obsidian UI Redesign Plan

## Overview

Redesign the yt-dlp GUI from the current "Signal Deck" zinc monochrome theme to the "Digital Obsidian" design system: a charcoal-base palette with muted violet (`#c5c4ff`) and teal (`#abefec`) accents, Manrope + Inter typography, tonal layering instead of visible borders, gradient CTA buttons, and a more structured shell with a top header bar, refined sidebar, and bottom status bar.

The work is split into five phases so the app can remain functional and testable throughout. Foundational token and QSS changes come first, then shell/layout changes, shared component refinements, page-level redesigns, and finally polish plus light-theme cleanup.

---

## Phase 1: Foundation — Tokens, Fonts, and QSS

**Goal:** Replace the design tokens, bundle fonts, and rewrite core QSS so the app’s visual language changes before structural layout work begins.

### 1A. Bundle fonts

**Files to create:**
- `src/ui/theme/fonts/`
- Bundle Manrope (`ExtraBold`, `Bold`, `SemiBold`, optionally `Regular`) and Inter (`Regular`, `Medium`, `SemiBold`, `Bold`) `.ttf` files

**Files to modify:**
- `src/ui/theme/theme_engine.py`
- `src/ui/theme/__init__.py`

**Implementation notes:**
- Add a `_load_fonts()` helper in `theme_engine.py`
- Load fonts with `QFontDatabase.addApplicationFont()`
- Resolve the font directory via `Path(__file__).parent / "fonts"`
- Log or warn on failures so the app falls back gracefully to system fonts
- Export `FONT_HEADLINE` from `src/ui/theme/__init__.py`

### 1B. Rewrite `tokens.py`

**File to modify:** `src/ui/theme/tokens.py`

**Typography:**
- `FONT_HEADLINE = '"Manrope", "Segoe UI", sans-serif'`
- `FONT_BODY = '"Inter", "Segoe UI", "Helvetica Neue", sans-serif'`
- Keep `FONT_MONO` as-is

**Core dark palette:**
- `bg-void = #0e0e10`
- `bg-surface = #131315`
- `bg-panel = #19191c`
- `bg-cell = #1f1f22`
- `bg-hover = #262528`
- `bg-selected = #2c2c2f`
- `input-well` or equivalent lowest surface = `#000000`
- `primary = #c5c4ff`
- `primary-container = #9c9bd3`
- `primary-dim = #b8b6f0`
- `secondary = #abefec`
- `secondary-container = #075a58`
- `error = #ff6e84`
- `error-dim = #d73357`
- `text-bright = #f6f3f5`
- `text-primary = #acaaad`
- `text-dim = #767577`
- `text-muted = #48474a`
- `border-hard` / ghost border = `rgba(72, 71, 74, 0.15)`
- `border-soft = rgba(72, 71, 74, 0.10)`
- `border-focus = rgba(197, 196, 255, 0.4)`

**Token-model updates:**
- Preserve existing token keys for backward compatibility
- Add newer semantic keys where helpful:
  - `surface-container-low`
  - `surface-container`
  - `surface-container-high`
  - `surface-container-highest`
  - `surface-bright`
  - `surface-container-lowest`
  - `on-surface`
  - `on-surface-variant`
  - `on-primary-container`
  - `outline-variant`
  - `ghost-border`
- Increase large radius to `12px`
- Add extra-large radius (`16px`) if the token model supports it
- Update `LIGHT_TOKENS` later if needed, but keep the app functional after this phase

### 1C. Rewrite `qss_builder.py`

**File to modify:** `src/ui/theme/qss_builder.py`

**Major rules:**
- Accept `font_headline` in `build_qss()`
- Set global typography to Inter body by default
- Apply the **no-line rule**:
  - Remove visible `1px` borders from most surfaces
  - Use tonal elevation shifts instead of separators
  - Keep only minimal ghost borders where structure needs definition
- Primary buttons use a violet gradient:
  - `qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 primary, stop:1 primary-container)`
- Inputs (`QLineEdit`, `QTextEdit`, `QSpinBox`, `QComboBox`) use black input wells with subtle ghost borders and focus glow
- Sidebar active state uses tonal background + primary text, with no border-left indicator
- Page titles use Manrope, large size, heavy weight
- Tables lose grid lines and gain tonal hover states
- Secondary buttons use ghost-border styling
- Destructive buttons use `error-dim` rather than high-chroma red
- Add selectors for things like `#statCard`, `#statDot`, `#statusDot`, status pills, and CTA roles

### 1D. Update theme engine wiring

**Files to modify:**
- `src/ui/theme/theme_engine.py`
- `src/ui/theme/__init__.py`

**Tasks:**
- Import `FONT_HEADLINE`
- Pass `font_headline` into `build_qss()`
- Keep theme loading resilient if bundled fonts fail to register

---

## Phase 2: Shell Structure — Header Bar, Status Bar, Sidebar

**Goal:** Introduce the new shell frame: a top header, polished sidebar, and bottom status bar.

### 2A. Create `header_bar.py`

**File to create:** `src/ui/components/header_bar.py`

**Component design:**
- `HeaderBar(QWidget)`
- Fixed height around `48px`
- Background matches the base void surface (`#0e0e10`)
- Left: brand label, either app title or “Digital Obsidian”
- Center/left: section tabs such as `Downloads`, `Processing`, `Organization`
- Right: settings/search affordances
- Emit `section_selected(str)` for wiring
- Use object names/properties for QSS targeting

### 2B. Create `status_bar.py`

**File to create:** `src/ui/components/status_bar.py`

**Component design:**
- `StatusBar(QWidget)`
- Fixed height around `28px` to `32px`
- Tonal background with a subtle top ghost border if needed
- Left: status dot + text (`Status: Idle`)
- Center or secondary area: dependency metadata (`yt-dlp`, `ffmpeg`)
- Right: network or system indicator, settings/support metadata
- Small uppercase-styled metadata text
- API such as `set_status()` and `set_metadata()`

### 2C. Restyle `sidebar.py`

**File to modify:** `src/ui/components/sidebar.py`

**Changes:**
- Shift to the Obsidian palette and spacing system
- Branding at top:
  - “Media Core” in primary color
  - small version/status subtitle
- Keep direct tool navigation intact unless a later product decision changes IA
- Active item uses `bg-cell` + primary text, no left indicator bar
- Remove separator lines in favor of spacing
- Add a gradient “New Batch” CTA above bottom utility links
- Add `Logs` and `Support` links near the bottom
- Consider increasing width from about `190px` to about `220px`

### 2D. Update `shell.py`

**File to modify:** `src/ui/shell.py`

**Layout target:**

```text
[Sidebar | HeaderBar]
[       | Content  ]
[       | StatusBar]
```

Use a right-side `QVBoxLayout` containing:
- `HeaderBar`
- central content stack
- `StatusBar`

Expose references for downstream wiring where useful.

### 2E. Update `main_window.py`

**File to modify:** `src/ui/main_window.py`

**Tasks:**
- Feed dependency/runtime info into the new status bar
- Update status text during download/processing events
- Connect header section tabs to sidebar/tool selection logic

---

## Phase 3: Shared Component Refinements

**Goal:** Bring all reusable widgets in line with the design system before reshaping every page.

### 3A. `page_header.py`
- Title uses Manrope headline styling
- Description uses quieter text color
- Stats become cards with rounded surfaces, subtle ghost borders, and status dots

### 3B. `data_panel.py`
- Remove hard borders
- Use tonal panel surface
- Rounded corners (`12px`)
- Stronger header treatment with icon + label support

### 3C. `config_bar.py`
- Remove visual separator lines
- Replace with spacing and compact grouped controls
- Uppercase micro-label treatment where appropriate

### 3D. `collapsible_section.py`
- Tonal header row
- No visible border box around the full section
- Better headline/toggle styling

### 3E. `split_layout.py` or equivalent shared layout helpers
- Support the intended bento split proportions, especially `8/12 + 4/12`
- Increase gaps and card alignment consistency

### 3F. `log_feed.py` and status-tag styling
- Remove hardcoded `setStyleSheet()` usage
- Push visual states into QSS selectors/properties
- Use denser rows with tonal hover handling

### 3G. Hardcoded style audit
- Review `src/ui/components/` for inline styles
- Replace them with object names, dynamic properties, or token-driven helpers
- Update any style utility mappings if token names changed

All Phase 3 tasks are largely independent and can be tackled in parallel once Phase 1 and Phase 2 are stable.

---

## Phase 4: Page-Level Layout Overhauls

**Goal:** Apply the new bento-grid visual system across the main app workflows.

### 4A. `add_urls_page.py` (highest priority)

**Target layout:**
- Two-column bento split
- Left (`8/12`): URL input panel
- Right (`4/12`): destination + parameters + CTA stack

**Details:**
- URL panel has header label/icon, dark textarea well, and helper footer text
- Parameters panel includes:
  - concurrent tasks slider
  - filename format dropdown
  - quality preset toggle controls
- Replace the current start action with a prominent gradient CTA such as `INGEST BATCH`
- Put recent activity below the main split

### 4B. `extract_urls_page.py`
- Left: source URL input + extraction options
- Right: extracted resources/results table with status indicators
- Add compact stat cards such as request rate and memory

### 4C. `convert_page.py`
- Keep or evolve an existing split layout
- Left: file/job list with progress and status chips
- Right: output settings card
- Gradient primary queue/start button

### 4D. `settings_page.py`
- Two-column settings structure:
  - left: settings navigation
  - right: detail/config content
- Add theme selector cards and modern toggle controls where appropriate

### 4E. Other workflow pages

**Files likely impacted:** trim, metadata, sort, rename, match, and related pages under `src/ui/pages/`

**Pattern to apply:**
- Primary content on the left
- Controls/config on the right where it fits
- Reusable card surfaces and page-header treatment
- Consistent CTA hierarchy and spacing

---

## Phase 5: Polish, QA, and Light Theme

**Goal:** Finish the redesign with consistency passes, interaction QA, and light-theme support.

### 5A. Visual polish pass
- Normalize radii, spacing, shadow/contrast levels, and ghost-border usage
- Ensure dialogs, menus, tables, tooltips, and popups align with the same system
- Review icon colors and active/inactive states

### 5B. Hardcoded style cleanup
- Audit remaining `setStyleSheet()` calls across the UI layer
- Replace them unless truly necessary for runtime-only visual state

### 5C. Light theme update
- Create a proper light inversion rather than a token-by-token placeholder
- Ensure theme toggle still works

### 5D. Manual QA
- Launch the app with `python run.py`
- Visit all major pages and dialogs
- Verify hover, focus, pressed, disabled, selected, and progress states
- Test resize behavior and minimum-size constraints
- Compare key pages against redesign references

---

## Dependency Order

```text
Fonts + Tokens
  -> QSS Rewrite
  -> Theme Engine Wiring
  -> Header / Status / Sidebar
  -> Shell + Main Window Integration
  -> Shared Component Cleanup
  -> Page Layout Overhauls
  -> Polish / QA / Light Theme
```

---

## Risk Management

1. Preserve old token keys while introducing new semantic keys to avoid breaking existing widgets mid-migration.
2. Keep font stacks resilient with system fallbacks so missing bundled fonts do not block rendering.
3. Land the redesign incrementally so each phase is runnable and visually reviewable.
4. Centralize style changes in QSS and theme tokens rather than spreading inline style logic across widgets.
5. Audit hardcoded `setStyleSheet()` usage early enough that it does not undermine the new system later.

---

## Verification Checklist

1. Run `python run.py` after each major phase.
2. Navigate through all core pages and confirm the app remains functional.
3. Verify interactive controls still behave correctly:
   - buttons
   - inputs
   - dropdowns
   - spin boxes
   - progress bars
4. Confirm sidebar selection, header navigation, and status-bar updates stay in sync.
5. Test resize behavior and minimum layout stability.
6. Compare the most important screens against the redesign references for spacing, hierarchy, and tone.
