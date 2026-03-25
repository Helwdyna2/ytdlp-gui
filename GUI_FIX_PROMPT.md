# GUI Fix Prompt — For GitHub Copilot Autopilot Mode

> Paste everything below the line into Copilot. It is designed for autonomous execution — no confirmation stops.

---

Read `AGENTS.md` first for project conventions. Then read `GUI_AUDIT.md` for full context on every issue referenced below. This is a PyQt6 app with a token-based theme system (`src/ui/theme/tokens.py` → `src/ui/theme/qss_builder.py`). UI strings live in widget files under `src/ui/widgets/` and `src/ui/components/`.

Implement ALL of the following changes autonomously. Do not stop to ask for confirmation — work through everything end to end. Use subagents / parallel tool calls wherever independent changes can be made simultaneously. Run the following at the end to verify nothing is broken:

```bash
pytest -q
pytest tests/test_main_window_workbench.py -v
pytest tests/test_theme_tokens.py tests/test_qss_builder.py tests/test_icons.py -v
```

---

## 1. Critical Accessibility — Theme Token Contrast Fixes

**File:** `src/ui/theme/tokens.py`

In `DARK_TOKENS`, make these exact changes:

| Token | Old Value | New Value | Reason |
|-------|-----------|-----------|--------|
| `text-dim` | `#5a5e6a` | `#8a8e9a` | ~2.5:1 → ~4.6:1 on bg-surface (WCAG 1.4.3) |
| `text-muted` | `#3a3e4a` | `#6a6e7a` | ~1.7:1 → ~3.5:1 on bg-surface (WCAG 1.4.3) |
| `border-soft` | `#3a3e4a` | `#5a5e6a` | Checkbox/input borders invisible at ~1.3:1 on bg-panel (WCAG 1.4.11) |
| `border-hard` | `#2a2c36` | `#4a4e5a` | Slider tracks/dividers invisible at ~1.2:1 on bg-panel (WCAG 1.4.11) |
| `orange` | `#c4956a` | `#d4a57a` | Just below 4.5:1 for normal text on bg-surface (WCAG 1.4.3) |
| `accent-primary` | `#c4956a` | `#d4a57a` | Same — accent-primary should match orange |
| `text-strong` | `#c4956a` | `#d4a57a` | Same — text-strong should match orange |
| `border-focus` | `#c4956a` | `#d4a57a` | Keep focus ring consistent with updated orange |

Also update `LIGHT_TOKENS` — verify each of orange, accent-primary, text-strong, and border-focus using a 4.5:1 WCAG AA contrast check and only keep `#a07040` if all checks pass, otherwise adjust.

---

## 2. Focus Indicators

**File:** `src/ui/theme/qss_builder.py`

Add visible `:focus` styles for all interactive widget types. Every focusable element needs a visible ring when navigated via keyboard. Add QSS rules like:

```qss
QPushButton:focus,
QComboBox:focus,
QLineEdit:focus,
QTextEdit:focus,
QPlainTextEdit:focus,
QSpinBox:focus,
QDoubleSpinBox:focus,
QSlider:focus,
QCheckBox:focus,
QRadioButton:focus,
QTabBar::tab:focus {
    border: 2px solid {border-focus};
}
```

Integrate this into the existing QSS builder pattern — don't create a separate stylesheet. Make sure the focus ring is visible against both `bg-surface` and `bg-panel` backgrounds.

---

## 3. UX Copy — String Replacements

Search for each old string in the source files and replace it. Use `grep -r` to locate the exact files if needed. Many of these are in widget files under `src/ui/widgets/` and `src/ui/components/`.

### 3a. Global / Shell (`src/ui/components/`)

| Find (old string) | Replace with | File hint |
|--------------------|-------------|-----------|
| `"Unified media workbench"` | `"Download, convert, and organize media"` | `app_header.py` |
| `"QUEUE"` (as a header stat label) | `"Queued"` | `app_header.py` |
| `"ACTIVE"` (as a header stat label) | `"Active"` | `app_header.py` |
| `"CLOCK"` (as a header stat label) | `"Elapsed"` | `app_header.py` |

For the header stats, also change the em-dash (`—`) zero placeholder to show the actual numeric value (e.g., `"0"` instead of `"—"`). Search for where the em-dash is set as a default/zero value.

### 3b. Export Stage

| Find | Replace | File hint |
|------|---------|-----------|
| `"Summary And Utilities"` | `"Overview"` | `export_stage_widget.py` |
| `"Check summary or adjust settings"` | Remove this string/label entirely | `export_stage_widget.py` |
| `"QUEUED"` (counter label in summary) | `"Queued"` | `export_stage_widget.py` |
| `"ACTIVE"` (counter label in summary) | `"Active"` | `export_stage_widget.py` |
| `"DONE"` (counter label in summary) | `"Done"` | `export_stage_widget.py` |
| `"FAILED"` (counter label in summary) | `"Failed"` | `export_stage_widget.py` |
| `"Head to Ingest to queue your first batch."` | `"Go to Ingest to add your first download."` | `export_stage_widget.py` |

For the empty state icon — if it currently uses a bar chart icon (e.g., `"mdi.chart-bar"` or similar), replace it with a download icon (e.g., `"mdi.download"` or `"mdi.cloud-download"`). Search the export widget for the icon reference.

### 3c. Settings

| Find | Replace | File hint |
|------|---------|-----------|
| `"Browser && Auth"` | `"Browser & Authentication"` | `settings_tab_widget.py` |
| `"Fragment Settings"` | `"Advanced Download Options"` | `settings_tab_widget.py` |

Add a tooltip to the "Force Overwrite" checkbox: `"Replace existing files instead of skipping them"`. Find the QCheckBox for force overwrite and call `.setToolTip(...)` on it.

### 3d. Ingest Stage

| Find | Replace | File hint |
|------|---------|-----------|
| `"Add URLs, authenticate when needed, then start the queue."` | `"Paste video URLs, sign in if needed, then download."` | `ingest_stage_widget.py` or `stage_definitions.py` |
| `"Paste URLs here (one per line or mixed with text)..."` | `"Paste video links here — one per line, or mixed with other text"` | `url_input_widget.py` |
| `"0 URLs ready"` (when count is 0) | `"No links added yet"` | `url_input_widget.py` or `ingest_stage_widget.py` |

For the helper bullets inside the URL text area placeholder (`"URLs will be automatically:\n- Extracted from surrounding text\n- Validated for proper format\n- Sorted alphabetically\n- Deduplicated"`), replace the entire multi-line string with: `"Links are automatically extracted, validated, sorted, and deduplicated."` — keep it as a single line.

Also look for where the `"{n} URLs ready"` count label is set. Change the zero case to `"No links added yet"` and the non-zero case to `"{n} links ready"`.

### 3e. Extract URLs Tab

| Find | Replace | File hint |
|------|---------|-----------|
| Any string mentioning `"Playwright profile"` or `"global Playwright profile"` in user-visible text | `"Sign in using the Download tab first to access private content."` | `extract_urls_tab_widget.py` |
| `"Found: 0 URLs"` (zero state) | `"No links found yet."` | `extract_urls_tab_widget.py` |
| `"Ready."` (status label in extract tab) | `"Ready to extract."` | `extract_urls_tab_widget.py` |

### 3f. Prepare > Convert

| Find | Replace | File hint |
|------|---------|-----------|
| `"Quality (CRF):"` | `"Quality:"` | `convert_tab_widget.py` |

Add a tooltip to the Quality label or slider: `"CRF (Constant Rate Factor) — lower values mean higher quality and larger files"`.

For the hardware acceleration line, combine `"Use Hardware Acceleration"` and `"Available: ..."` into a single label pattern like: `"Use hardware acceleration ({backend} available)"` where `{backend}` is dynamically inserted. Look at how the available backend string is currently set and merge them.

### 3g. Prepare > Trim

| Find | Replace | File hint |
|------|---------|-----------|
| `"Lossless (fast, keyframe-limited)"` | `"Lossless (fast — may shift to nearest keyframe)"` | `trim_tab_widget.py` |

### 3h. Organize > Sort

| Find | Replace | File hint |
|------|---------|-----------|
| Any string matching `"Delete macOS dotfiles"` or similar | `"Remove hidden macOS files (._*) during scan"` | `sort_tab_widget.py` |
| `"Unsort (Flatten)"` | `"Undo sort (move files back)"` | `sort_tab_widget.py` |

### 3i. Organize > Match

| Find | Replace | File hint |
|------|---------|-----------|
| `"Search exclusions"` (button or placeholder text) | `"Exclude terms..."` | `match_tab_widget.py` |

---

## 4. Layout & Visual Hierarchy

### 4a. Left-align tab bars

In every stage widget that creates a tab bar or button group for sub-tools (Summary/Settings, Add Media/Extract URLs, Convert/Trim/Metadata, Sort/Rename/Match), change the alignment from centered to left-aligned.

Look for `QHBoxLayout` patterns that add stretch on both sides of the tab buttons, or `setAlignment(Qt.AlignCenter)`. Change to `Qt.AlignLeft` or remove the leading stretch. The tab bar should align with the left edge of the content area (below the stage heading), not float in the center.

Files to check: `export_stage_widget.py`, `ingest_stage_widget.py`, `prepare_stage_widget.py`, `organize_stage_widget.py`, and any shared tab/toolbar component.

### 4b. Compact Export Summary layout

In the Export > Summary view, the four stat counters (Queued/Active/Done/Failed) should be laid out as a tight horizontal strip rather than four large separated boxes. Reduce the spacing between them and bring the empty state message closer vertically. Look for the layout in `export_stage_widget.py` and reduce margins/spacing.

### 4c. Drag handle visibility

In Sort criteria and Rename tokens drag lists (`sort_tab_widget.py`, `rename_tab_widget.py`), find the drag handle elements (grip dots or icons). Change their color to use `text-dim` (which is now `#8a8e9a` after the token fix) instead of whatever dim value they currently use. If there's a hover state, make the background lighten to `bg-hover` on mouseover.

### 4d. Match tab checkbox spacing

In `match_tab_widget.py`, the checkboxes for "Search ThePornDB (prioritized)" and "Search StashDB" plus "Preserve position tags" and "Include already-named files" are all crammed together. Add proper spacing between the checkbox groups. Use the spacing tokens (`sp-m` = 12px between items within a group, `sp-l` = 16px between groups).

---

## 5. Button Hierarchy

Establish three button tiers across the app by updating QSS classes or inline styles:

**Primary action** (one per screen max) — filled with `accent-primary` background, `text-on-cyan` (dark) text:
- "Start Download" (Ingest)
- "Extract" (Extract URLs)
- "Trim Video" (Trim)
- "Start Matching" (Match)
- "Scan" (Sort, Rename, Metadata)

**Secondary action** — outlined with `border-soft` border, `text-primary` text, transparent background:
- "Browse..."
- "Clear"
- "Cancel"
- "Load"
- "Scan Folder" (if Scan is already primary)
- "Refresh Preview"
- "View Match Details"
- "Manual Search..."
- "Set to Current"
- "Compare"
- "Export to CSV"

**Destructive action** — filled with `red` background, white text:
- "Remove"
- "Stop"
- "Clear History"

Look at how buttons are currently styled. If the app uses a class/property system (e.g., `setProperty("class", "primary")`), update the QSS to define `.primary`, `.secondary`, `.destructive` classes. If buttons are styled inline or by widget name, add the appropriate property to each button and define the QSS rules.

If there's no existing class system, add `setProperty("button_role", "primary")` (etc.) to the relevant buttons and add QSS selectors like:

```qss
QPushButton[button_role="primary"] { background: {accent-primary}; color: {text-on-cyan}; border: none; }
QPushButton[button_role="secondary"] { background: transparent; color: {text-primary}; border: 1px solid {border-soft}; }
QPushButton[button_role="destructive"] { background: {red}; color: #ffffff; border: none; }
```

---

## 6. Final Verification

After all changes are complete:

1. Run the full verification suite and fix any failures:
   ```bash
   pytest -q
   pytest tests/test_main_window_workbench.py -v
   pytest tests/test_theme_tokens.py tests/test_qss_builder.py tests/test_icons.py -v
   ```
2. Grep across the codebase for any remaining instances of old strings that should have been replaced (especially `"Browser && Auth"`, `"Summary And Utilities"`, `"QUEUE"` as a standalone label, `"Unified media workbench"`).
3. Verify that the DARK_TOKENS and LIGHT_TOKENS dicts still have identical key sets (this is a project invariant — see tokens.py docstring).
4. If any test specifically asserts on old string values or old token hex codes, update those test assertions to match the new values.
