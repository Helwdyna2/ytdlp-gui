# UI Redesign Consolidated Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the UI redesign as one coherent effort by building on the current sidebar/page architecture, aligning it to the March redesign spec, and closing the audit findings without reintroducing the old shell.

**Architecture:** The implementation baseline is the current `src/ui/` rewrite: `Shell` uses `Sidebar + QStackedWidget`, the tool pages live in `src/ui/pages/`, and business logic stays in the existing managers/workers/services. The March design spec remains the source of truth for layout, navigation, tokens, and interaction patterns, while `GUI_AUDIT.md` and `GUI_FIX_PROMPT.md` act as the acceptance checklist for accessibility, copy, hierarchy, spacing, and cleanup. Preserve compatibility shims only where callers still need them; remove them once grep and tests prove they are unused.

**Tech Stack:** Python 3, PyQt6, qtawesome, existing core managers/workers, pytest

---

## Consolidated decisions

- The **current sidebar/page/zinc UI is the baseline**. Do not restart from the pre-redesign stage/tab shell.
- `docs/superpowers/specs/2026-03-18-ui-redesign-design.md` is the authoritative design target for theme, navigation, page structure, and component behavior.
- `GUI_AUDIT.md` is the acceptance criteria for accessibility, hierarchy, layout density, and UX copy.
- `GUI_FIX_PROMPT.md` is a tactical checklist, not the primary architecture document.
- The current "Export summary" surface does **not** come back as a standalone destination. Keep the flat tool navigation; summary information belongs in page headers, queue/progress widgets, and activity surfaces already used by the new UI.
- Prefer the clearer audit copy when the audit and spec differ slightly. Example: app subtitle should be **"Download, convert, and organize media"** rather than the shorter but less explicit "Download, convert, and organize".
- This consolidated plan intentionally supersedes the March spec's earlier breaking token-key rewrite. Preserve the currently landed token vocabulary and align token **values, roles, and selectors** to the spec so the already-landed page code does not absorb an unnecessary second migration.
- Keep the stable backend stage compatibility contract (`ingest`, `prepare`, `organize`, `export`) while live code still depends on it. Shell alias helpers that only exist for compatibility may be removed later, but only after `src/` and `tests/` prove they are unused and the compatibility coverage is updated in the same task.
- Resolve the March spec's older token-term wording through the current landed vocabulary: `bg-active` maps to `bg-cell`, `text-faint` maps to `text-dim`, and button radius uses the current `r-l` token (`6px`).
- Resolve stale IA wording in older docs through the landed tool names: where the March spec says `Download tab`, use the current tool name `Add URLs`.
- Resolve the active-sidebar text ambiguity in favor of the landed higher-contrast treatment: active sidebar items use `text-bright` rather than the older spec wording `text-primary`.

## File structure

### Authoritative references

- Read: `GUI_AUDIT.md`
- Read: `GUI_FIX_PROMPT.md`
- Read: `docs/superpowers/specs/2026-03-18-ui-redesign-design.md`
- Supersede: `docs/superpowers/plans/2026-03-18-ui-redesign.md`

### Theme and styling layer

- Modify: `src/ui/theme/tokens.py` - final token values and token invariants
- Modify: `src/ui/theme/qss_builder.py` - shared selectors, focus styling, button-role contract, sidebar/page/header/config styling
- Modify: `src/ui/theme/theme_engine.py` - only if needed to keep theme application aligned with the token/QSS contract
- Modify: `src/ui/theme/icons.py` - only if icon names or empty-state icons still diverge from the plan

### Shell and shared components

- Modify: `src/ui/shell.py` - tool/stage compatibility rules and selection behavior
- Modify: `src/ui/components/sidebar.py` - title/subtitle copy, active/badge behavior, section structure
- Modify: `src/ui/components/page_header.py` - stats rendering and header semantics
- Modify: `src/ui/components/config_bar.py` - compact settings row behavior
- Modify: `src/ui/components/split_layout.py` - split sizing and minimum widths
- Modify: `src/ui/components/activity_drawer.py` - only if visual hierarchy or spacing still diverges
- Modify: `src/ui/components/data_panel.py` - only if stat/tag styling still leaks old semantics
- Modify: `src/ui/components/log_feed.py` - only if progress/log surfaces need spec alignment

### Page layer

- Modify: `src/ui/pages/add_urls_page.py`
- Modify: `src/ui/pages/extract_urls_page.py`
- Modify: `src/ui/pages/convert_page.py`
- Modify: `src/ui/pages/trim_page.py`
- Modify: `src/ui/pages/metadata_page.py`
- Modify: `src/ui/pages/sort_page.py`
- Modify: `src/ui/pages/rename_page.py`
- Modify: `src/ui/pages/match_page.py`
- Modify: `src/ui/pages/settings_page.py`

### Shared widgets kept under the new pages

- Modify: `src/ui/widgets/url_input_widget.py`
- Modify: `src/ui/widgets/output_config_widget.py`
- Modify: `src/ui/widgets/auth_status_widget.py`
- Modify: `src/ui/widgets/file_picker_widget.py`
- Modify: `src/ui/widgets/queue_progress_widget.py`
- Modify: `src/ui/widgets/progress_widget.py`
- Modify: `src/ui/widgets/download_log_widget.py`
- Modify: `src/ui/widgets/video_preview_widget.py` only if trim-page layout requires small API support
- Modify: `src/ui/widgets/trim_timeline_widget.py` only if trim-page layout requires small API support

### Integration and tests

- Modify: `src/ui/main_window.py`
- Modify: `tests/test_theme_tokens.py`
- Modify: `tests/test_qss_builder.py`
- Modify: `tests/test_theme_engine.py`
- Modify: `tests/test_icons.py`
- Modify: `tests/test_sidebar.py`
- Modify: `tests/test_shell.py`
- Modify: `tests/test_page_header.py`
- Modify: `tests/test_config_bar.py`
- Modify: `tests/test_split_layout.py`
- Modify: `tests/test_pages.py`
- Modify: `tests/test_main_window_workbench.py`
- Delete or replace: `tests/test_convert_tab_widget.py`
- Delete or replace: `tests/test_match_tab_widget.py`

### Documentation follow-up after implementation

- Modify: `docs/ARCHITECTURE.md` if page ownership or shell contracts change
- Modify: `docs/UI_WORKBENCH.md` if the implemented UI behavior differs from the current docs
- Modify: `docs/AGENT_GUIDE.md` if file ownership or testing guidance changes
- Modify: `AGENTS.md` only if repository-level UI/testing instructions need updating

## Chunk 1: Foundations and shared UI contracts

**Deferred from this chunk on purpose:**

- minimum window size (`1000x650`) is owned by Task 8 in `src/ui/main_window.py`
- `src/ui/components/activity_drawer.py` and `src/ui/components/log_feed.py` are treated as already-landed shared surfaces and only move if later verification exposes a regression

### Task 1: Align the theme contract with the consolidated spec

**Files:**
- Modify: `src/ui/theme/tokens.py`
- Modify: `src/ui/theme/qss_builder.py`
- Modify: `src/ui/theme/theme_engine.py`
- Test: `tests/test_theme_tokens.py`
- Test: `tests/test_qss_builder.py`
- Test: `tests/test_theme_engine.py`

- [ ] **Step 1: Update the tests so they describe the final contract**

Add or tighten assertions around the consolidated token/QSS rules:

- dark theme must include `bg-void #09090b`, `bg-surface #0f0f12`, `bg-panel #18181b`, `bg-cell #1c1c21`, `bg-hover #27272a`, `text-primary #a1a1aa`, `text-muted #8a8a94`, `cyan #3b82f6`, `accent-primary #fafafa`
- light theme must include representative checks across surfaces, borders, text, and status colors: `bg-void #fafafa`, `bg-surface #f4f4f5`, `bg-panel #ffffff`, `border-hard #d4d4d8`, `text-primary #3f3f46`, `text-muted #71717a`, `cyan #2563eb`, `red #dc2626`, `accent-primary #18181b`
- token tests must assert `r-l == 6px`
- typography tests must assert the shared font/typography contract: system body font stack, 18px/600 page headings, 12px body text, 11px helper text, and 9px uppercase section-header styling
- QSS must include `QPushButton[button_role="primary"]`, `QPushButton[button_role="secondary"]`, `QPushButton[button_role="destructive"]`
- while compatibility support exists, QSS must also include the legacy object-name selectors `#btnPrimary`, `#btnSecondary`, `#btnDestructive`
- QSS must still include `QWidget#sidebar` and `QPushButton#sidebarItem`
- QSS tests must assert the actual button-role styling contract: primary is filled with `accent-primary` and `text-on-cyan`, secondary is transparent with a `border-hard` outline, destructive uses red text with the agreed destructive treatment, and all button roles keep the exact button paddings (`5px 18px` primary, `5px 14px` secondary/destructive) plus the `r-l` radius contract
- QSS tests must assert the exact secondary/destructive rules: secondary uses transparent background, `border-hard`, and `text-primary`; destructive uses transparent background, `border-hard`, and `red` text
- QSS tests must assert the full focus-selector matrix: `QPushButton`, `QComboBox`, `QLineEdit`, `QTextEdit`, `QPlainTextEdit`, `QSpinBox`, `QDoubleSpinBox`, `QSlider`, `QCheckBox`, `QRadioButton`, and `QTabBar::tab`
- QSS tests must assert the exact focus-ring treatment: `2px` `border-focus` border on the required interactive selectors

- [ ] **Step 2: Run the focused theme tests to capture the current mismatch**

Run: `source .venv/bin/activate && pytest tests/test_theme_tokens.py tests/test_qss_builder.py tests/test_theme_engine.py -v`

Expected: FAIL on token-value, selector, or focus-ring assertions until the theme contract is aligned.

- [ ] **Step 3: Implement the minimal production changes**

Update `src/ui/theme/tokens.py` and `src/ui/theme/qss_builder.py` to match the consolidated plan:

- keep the current token key set intact for this consolidated implementation unless a separate, repo-wide token-key migration is intentionally approved
- move token values to the March redesign palette
- use the current page/button implementation reality as the selector contract: the pages already set `button_role`, so QSS must style `button_role` properties directly
- if any old widget still relies on object names such as `btnPrimary`, support both selectors temporarily rather than breaking in-flight pages
- keep visible focus styling on all interactive widgets
- touch `src/ui/theme/theme_engine.py` only if needed to preserve the current `apply_theme()` / `get_color()` behavior after the token/QSS updates
- align the shared typography selectors in `qss_builder.py` with the consolidated heading/body/helper/section-header contract

- [ ] **Step 4: Re-run the focused theme tests**

Run: `source .venv/bin/activate && pytest tests/test_theme_tokens.py tests/test_qss_builder.py tests/test_theme_engine.py -v`

Expected: PASS for all targeted theme tests.

- [ ] **Step 5: Run the token invariant check**

Run: `source .venv/bin/activate && python -c "from src.ui.theme.tokens import DARK_TOKENS, LIGHT_TOKENS; assert set(DARK_TOKENS) == set(LIGHT_TOKENS); print('token keys match')"`

Expected: prints `token keys match`.

- [ ] **Step 6: Commit**

```bash
git add src/ui/theme/tokens.py src/ui/theme/qss_builder.py src/ui/theme/theme_engine.py \
  tests/test_theme_tokens.py tests/test_qss_builder.py tests/test_theme_engine.py
git commit -m "fix(ui): align theme tokens and button roles with redesign spec"
```

### Task 2: Finish the shell and shared component contract

**Files:**
- Modify: `src/ui/shell.py`
- Modify: `src/ui/components/sidebar.py`
- Modify: `src/ui/components/page_header.py`
- Modify: `src/ui/components/config_bar.py`
- Modify: `src/ui/components/split_layout.py`
- Modify only for component-specific selectors if needed: `src/ui/theme/qss_builder.py`
- Modify if sidebar icon sizing/dimming is not already aligned: `src/ui/theme/icons.py`
- Test: `tests/test_shell.py`
- Test: `tests/test_sidebar.py`
- Test: `tests/test_page_header.py`
- Test: `tests/test_config_bar.py`
- Test: `tests/test_split_layout.py`
- Test: `tests/test_icons.py`

- [ ] **Step 1: Update the shared-component tests**

Extend the tests so they assert the consolidated behavior:

- `Sidebar` title/subtitle copy matches the final wording
- `Sidebar` title is `yt-dlp GUI` and subtitle is `Download, convert, and organize media`
- `Sidebar` keeps the exact `190px` fixed-width flat-nav layout and badge updates without mutating the wrong item
- `Sidebar` section headers remain non-interactive labels and use the consolidated `text-dim` treatment that supersedes the older spec term `text-faint`
- `Sidebar` keeps Settings anchored below the section groups with a separating divider
- `Sidebar` checked/unchecked styling matches the consolidated contract exactly: checked items use `bg-cell`, a `2px` `cyan` left border, and `text-bright`, while non-active items use dimmed icon treatment and `text-dim`
- `Sidebar` icons use the expected qtawesome-backed nav contract, including `14px` sizing and dimmed inactive state
- `Shell` preserves `register_tool()` and the stage-compatibility aliases required by the backend contract
- `Shell` preserves `set_stage_status` while the compatibility surface still exists
- `PageHeader` can add and update stats without inline one-off styling becoming the only way to color them
- `ConfigBar` preserves compact layout responsibilities
- `SplitLayout` preserves the right-panel contract and enforces the spec minimum left-panel width expectation (240px minimum for split tools)

- [ ] **Step 2: Run the focused shared-component tests**

Run: `source .venv/bin/activate && pytest tests/test_shell.py tests/test_sidebar.py tests/test_page_header.py tests/test_config_bar.py tests/test_split_layout.py tests/test_qss_builder.py tests/test_icons.py -v`

Expected: FAIL on sidebar copy, icon/state styling, or shell-compat assertions until the shared contract is aligned.

- [ ] **Step 3: Implement the minimal production changes**

Apply only the changes needed to make the shared contract real:

- update sidebar copy and section behavior
- keep sidebar visual state in shared styling/tests rather than per-page button tweaks
- make `PageHeader` the single reusable home for page stats rather than per-page ad hoc labels
- if stat-color or header-specific styling needs shared selectors, add only those component-specific selectors in `qss_builder.py` instead of re-opening the token/button-role work from Task 1
- keep `ConfigBar` and `SplitLayout` small and focused
- keep `register_stage`, `switch_to_stage`, `active_stage`, `stage_changed`, and `set_stage_status` while the backend stage contract exists; only a separate spec change should remove them

- [ ] **Step 4: Re-run the focused shared-component tests**

Run: `source .venv/bin/activate && pytest tests/test_shell.py tests/test_sidebar.py tests/test_page_header.py tests/test_config_bar.py tests/test_split_layout.py tests/test_qss_builder.py tests/test_icons.py -v`

Expected: PASS for all targeted component tests.

- [ ] **Step 5: Run a targeted legacy-copy audit for shared surfaces**

Run: `source .venv/bin/activate && (rg "Unified media workbench|Browser && Auth|Summary And Utilities|\\bQUEUE\\b|\\bACTIVE\\b|\\bCLOCK\\b" src/ui/components src/ui/shell.py || true)`

Expected: no user-facing matches printed from shared components or `src/ui/shell.py`.

- [ ] **Step 6: Commit**

```bash
git add src/ui/shell.py src/ui/components/sidebar.py src/ui/components/page_header.py \
  src/ui/components/config_bar.py src/ui/components/split_layout.py src/ui/theme/qss_builder.py src/ui/theme/icons.py \
  tests/test_shell.py tests/test_sidebar.py tests/test_page_header.py \
  tests/test_config_bar.py tests/test_split_layout.py tests/test_qss_builder.py tests/test_icons.py
git commit -m "fix(ui): finish shell and shared component contracts"
```

### Task 3: Normalize shared widget copy and action semantics

**Files:**
- Modify: `src/ui/widgets/url_input_widget.py`
- Modify: `src/ui/widgets/output_config_widget.py`
- Modify: `src/ui/widgets/auth_status_widget.py`
- Modify: `src/ui/widgets/file_picker_widget.py`
- Modify: `src/ui/widgets/queue_progress_widget.py`
- Modify: `src/ui/widgets/progress_widget.py`
- Modify: `src/ui/widgets/download_log_widget.py`
- Create or modify: `tests/test_shared_widgets.py`

- [ ] **Step 1: Add or tighten tests around the user-facing shared-widget contract**

Cover the copy and action rules that multiple pages rely on:

- URL placeholder uses `Paste video links here — one per line, or mixed with other text`
- URL helper copy uses `Links are automatically extracted, validated, sorted, and deduplicated.`
- zero-state URL count uses `No links added yet`
- non-zero count uses `{n} links ready`
- auth helper text uses the exact current-IA string `Sign in using Add URLs first to access private content.`
- primary/secondary/destructive button roles are set on shared buttons rather than restyled inline
- shared-widget tests assert recurring action-role mappings explicitly: browse/clear/cancel actions are secondary, load/start actions are primary, and only truly destructive shared actions use the destructive role

- [ ] **Step 2: Run the targeted shared-widget tests**

Run: `source .venv/bin/activate && pytest tests/test_shared_widgets.py -v`

Expected: FAIL on exact copy or button-role assertions until the shared widgets are aligned.

- [ ] **Step 3: Implement the exact copy updates**

Keep logic intact. Update the exact text surfaces first:

- `UrlInputWidget` placeholder/helper/count text
- `AuthStatusWidget` user-facing auth guidance

- [ ] **Step 4: Implement the shared button-role and status-surface updates**

Then update the remaining shared semantics:

- `OutputConfigWidget` labels and button semantics if they still expose old wording or unassigned button roles
- `DownloadLogWidget`/`QueueProgressWidget` button roles and status presentation if they still bypass the shared styling contract
- shared buttons in queue/progress/file-picking widgets so the QSS role contract actually styles them

- [ ] **Step 5: Re-run the targeted shared-widget tests**

Run: `source .venv/bin/activate && pytest tests/test_shared_widgets.py -v`

Expected: PASS for the targeted smoke coverage.

- [ ] **Step 6: Run a targeted legacy-copy audit for shared widgets**

Run: `source .venv/bin/activate && (rg "Unified media workbench|Browser && Auth|Download tab|Playwright profile" src/ui/widgets || true)`

Expected: no user-facing matches printed from shared widgets.

- [ ] **Step 7: Commit**

```bash
git add src/ui/widgets/url_input_widget.py src/ui/widgets/output_config_widget.py \
  src/ui/widgets/auth_status_widget.py src/ui/widgets/file_picker_widget.py \
  src/ui/widgets/queue_progress_widget.py src/ui/widgets/progress_widget.py \
  src/ui/widgets/download_log_widget.py tests/test_shared_widgets.py
git commit -m "fix(ui): normalize shared widget copy and button semantics"
```

## Chunk 2: Page completion and interaction polish

### Task 4: Finish the ingest flow pages

**Files:**
- Modify: `src/ui/pages/add_urls_page.py`
- Modify: `src/ui/pages/extract_urls_page.py`
- Modify: `src/ui/widgets/url_input_widget.py`
- Modify: `src/ui/widgets/auth_status_widget.py`
- Test: `tests/test_pages.py`
- Create or modify: `tests/test_add_urls_page.py`
- Create or modify: `tests/test_extract_urls_page.py`

**Terminology note:** this consolidated plan uses the landed tool name `Add URLs` wherever older March-spec copy said `Download tab`.

- [ ] **Step 1: Write the focused ingest-page tests**

Add assertions for:

- `AddUrlsPage` header copy and exact stat contract (`Queued`, `Active`, `Elapsed`; no `Done` stat in the header)
- count-label behavior for zero vs non-zero URLs
- collapsible login-status/auth section behavior on the Add URLs page
- tests assert the collapsible auth/login surface changes expansion state explicitly
- active download mode replaces or hides the URL-input area instead of merely disabling it
- progress section toggling through `set_download_mode()`
- `ExtractUrlsPage` inline auto-scroll/options row and output-folder row
- `ExtractUrlsPage` extract-action bar and status copy (`Ready to extract.`, `No links found yet.`)
- the extract-flow auth guidance uses the current IA term (`Sign in using Add URLs first to access private content.`) and never reverts to stale wording such as `Download tab` or `Playwright profile`
- Add URLs has exactly one primary action (`Start Download`) and Extract URLs has exactly one primary action (`Extract`)

- [ ] **Step 2: Run the ingest-page tests**

Run: `source .venv/bin/activate && pytest tests/test_add_urls_page.py tests/test_extract_urls_page.py tests/test_pages.py -v`

Expected: failures until the two pages and their shared widgets fully match the final copy/layout contract.

- [ ] **Step 3: Implement the minimal ingest-page changes**

Apply the consolidated decisions:

- keep Add URLs as the landing page
- keep queue/progress/activity surfaces on the Add URLs page rather than reviving a separate summary page
- keep the Add URLs header to `Queued`, `Active`, and `Elapsed` only
- keep the login-status/auth surface collapsible on Add URLs
- make active downloads replace or hide the idle URL-entry surface rather than leaving a disabled input area in place
- left-align any tool-local controls instead of visually centering them
- keep Extract URLs as a full-width tool with inline auto-scroll/options, a dedicated output-folder row, and current-IA auth guidance that points to Add URLs
- make the ingest status row and config row compact, readable, and consistent with the audit

- [ ] **Step 4: Re-run the ingest-page tests**

Run: `source .venv/bin/activate && pytest tests/test_add_urls_page.py tests/test_extract_urls_page.py tests/test_pages.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ui/pages/add_urls_page.py src/ui/pages/extract_urls_page.py \
  src/ui/widgets/url_input_widget.py src/ui/widgets/auth_status_widget.py \
  tests/test_add_urls_page.py tests/test_extract_urls_page.py tests/test_pages.py
git commit -m "fix(ui): finish ingest pages and status copy"
```

### Task 5: Finish convert and trim pages

**Files:**
- Modify: `src/ui/pages/convert_page.py`
- Modify: `src/ui/pages/trim_page.py`
- Modify: `src/ui/widgets/video_preview_widget.py`
- Modify: `src/ui/widgets/trim_timeline_widget.py`
- Delete or replace: `tests/test_convert_tab_widget.py`
- Create or modify: `tests/test_convert_page.py`
- Create or modify: `tests/test_trim_page.py`

- [ ] **Step 1: Replace legacy tab-widget tests with page-focused tests**

Write tests that cover:

- convert page header copy and right-panel settings layout
- convert keeps the spec anatomy: file list on the left, codec/quality/preset controls on the right
- convert uses the shared `SplitLayout` contract, including the shared minimum-width expectations
- `Quality:` label plus CRF tooltip
- convert progress and job-status area rendered below the split layout
- Convert has exactly one primary action (`Start Convert`)
- trim page lossless-copy update
- trim uses a radio-button style mode selector rather than a generic combo box
- trim output section, progress section, and action bar
- trim timeline/video surfaces still instantiate correctly
- Trim has exactly one primary action (`Trim Video`)

- [ ] **Step 2: Run the focused convert/trim tests**

Run: `source .venv/bin/activate && pytest tests/test_convert_page.py tests/test_trim_page.py -v`

Expected: FAIL while the new page contract is not fully asserted or legacy copy/layout remains.

- [ ] **Step 3: Implement the minimal page updates**

Keep worker wiring intact. Limit the work to UI/layout/copy:

- convert uses the split layout cleanly and keeps one primary action
- convert keeps its progress area below the split layout instead of collapsing it into the settings panel
- convert inherits the shared split-layout sizing contract rather than inventing a page-local split rule
- trim keeps the existing preview/timeline integration but uses the new copy, radio-button mode control, mode/output/progress sections, and spacing rules
- no centered floating tab bars or orphan controls remain in these pages

- [ ] **Step 4: Remove or repurpose the obsolete legacy test file**

Delete `tests/test_convert_tab_widget.py` if it no longer covers any real code, or replace its contents with compatibility coverage that still matters.

- [ ] **Step 5: Re-run the focused convert/trim tests**

Run: `source .venv/bin/activate && pytest tests/test_convert_page.py tests/test_trim_page.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add -A src/ui/pages/convert_page.py src/ui/pages/trim_page.py \
  src/ui/widgets/video_preview_widget.py src/ui/widgets/trim_timeline_widget.py \
  tests/test_convert_page.py tests/test_trim_page.py tests/test_convert_tab_widget.py
git commit -m "fix(ui): finish convert and trim pages"
```

### Task 6: Finish metadata, sort, rename, and match pages

**Files:**
- Modify: `src/ui/pages/metadata_page.py`
- Modify: `src/ui/pages/sort_page.py`
- Modify: `src/ui/pages/rename_page.py`
- Modify: `src/ui/pages/match_page.py`
- Modify only if page gaps expose shared-layout bugs: `src/ui/components/split_layout.py`
- Modify if extracted for 2+ pages: `src/ui/components/source_folder_bar.py`
- Delete or replace: `tests/test_match_tab_widget.py`
- Create or modify: `tests/test_metadata_page.py`
- Create or modify: `tests/test_sort_page.py`
- Create or modify: `tests/test_rename_page.py`
- Create or modify: `tests/test_match_page.py`
- Test: `tests/test_split_layout.py`

- [ ] **Step 1: Write the focused organize/metadata page tests**

Cover the audit-specific behaviors:

- split-layout pages use the shared `SplitLayout` contract with a minimum 240px left-side working area
- metadata uses the split structure explicitly: file list/source controls on the left, metadata detail presentation on the right, with any tabs scoped inside that right detail pane rather than replacing the split layout
- Sort keeps the folder-tree preview on the right
- Rename keeps the preview table and selection summary on the right
- Match keeps the results table with status/confidence information on the right
- sort and rename drag surfaces expose visible reorder affordances
- sort and rename expose keyboard reorder controls and reachable focus order
- match options are spaced into readable groups
- match exclusion copy uses `Exclude terms...`
- metadata keeps browse/scan/compare/export controls with a clear primary/secondary hierarchy
- Rename keeps exactly one primary action (`Apply Rename`)
- button-role tests prove there is only one primary action per view; on Match, `Start Matching` is primary and `Scan Folder` is secondary

- [ ] **Step 2: Run the focused organize/metadata page tests**

Run: `source .venv/bin/activate && pytest tests/test_metadata_page.py tests/test_sort_page.py tests/test_rename_page.py tests/test_match_page.py tests/test_split_layout.py -v`

Expected: FAIL until the pages align with the spacing, copy, and button hierarchy requirements.

- [ ] **Step 3: Implement the minimal page changes**

Preserve managers and workers. Only change page composition, copy, and visual semantics:

- add visible drag handles and keyboard-accessible reorder affordances where the spec requires them
- keep the right-hand folder-tree / preview-table / results-table structures intact for Sort, Rename, and Match
- keep one primary action per view
- tighten spacing in match options and organize tools
- use the shared split layout for Metadata, Sort, Rename, and Match with the shared minimum-width contract
- only pull common source-row behavior into `source_folder_bar.py` if at least two pages can share the same row contract cleanly; otherwise keep the row local to the page

- [ ] **Step 4: Remove or repurpose the obsolete legacy match test**

Delete `tests/test_match_tab_widget.py` if it only refers to code that no longer exists, or replace it with coverage that still exercises the current page contract.

- [ ] **Step 5: Re-run the organize/metadata page tests**

Run: `source .venv/bin/activate && pytest tests/test_metadata_page.py tests/test_sort_page.py tests/test_rename_page.py tests/test_match_page.py tests/test_split_layout.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ui/pages/metadata_page.py src/ui/pages/sort_page.py src/ui/pages/rename_page.py \
  src/ui/pages/match_page.py src/ui/components/split_layout.py \
  tests/test_metadata_page.py tests/test_sort_page.py tests/test_rename_page.py tests/test_match_page.py \
  tests/test_split_layout.py tests/test_match_tab_widget.py && \
git diff --quiet -- src/ui/components/source_folder_bar.py || git add src/ui/components/source_folder_bar.py
git commit -m "fix(ui): finish metadata and organize pages"
```

### Task 7: Finish settings and the remaining global UX copy/a11y pass

**Files:**
- Modify: `src/ui/pages/settings_page.py`
- Modify: `src/ui/theme/qss_builder.py`
- Modify: `src/ui/theme/icons.py`
- Modify if summary/tag styling still needs cleanup: `src/ui/components/data_panel.py`
- Modify if final audit finds residual page copy: `src/ui/pages/add_urls_page.py`
- Modify if final audit finds residual page copy: `src/ui/pages/extract_urls_page.py`
- Modify if final audit finds residual page copy: `src/ui/pages/convert_page.py`
- Modify if final audit finds residual page copy: `src/ui/pages/trim_page.py`
- Modify if final audit finds residual page copy: `src/ui/pages/metadata_page.py`
- Modify if final audit finds residual page copy: `src/ui/pages/sort_page.py`
- Modify if final audit finds residual page copy: `src/ui/pages/rename_page.py`
- Modify if final audit finds residual page copy: `src/ui/pages/match_page.py`
- Modify if final audit finds residual widget copy: `src/ui/widgets/url_input_widget.py`
- Modify if final audit finds residual widget copy: `src/ui/widgets/auth_status_widget.py`
- Test: `tests/test_pages.py`
- Test: `tests/test_icons.py`
- Test: `tests/test_qss_builder.py`
- Test: `tests/test_theme_tokens.py`

- [ ] **Step 1: Add or tighten tests for settings and the last global strings**

Assert that:

- settings sections use the final names `Browser & Authentication` and `Advanced Download Options`
- settings includes the full required section set: `Appearance`, `Browser & Authentication`, `Download Defaults`, `Rate Limiting`, `Retry Logic`, and `Advanced Download Options`
- "Force Overwrite" exposes the explanatory tooltip
- settings uses collapsible sections for the major groups called out in the consolidated spec
- empty-state icon choices and summary/status labels no longer use old copy from the audit/fix-prompt
- no standalone UI label still uses `QUEUE`, `ACTIVE`, or `CLOCK` as the user-facing wording

- [ ] **Step 2: Run the focused settings/copy tests**

Run: `source .venv/bin/activate && pytest tests/test_pages.py tests/test_icons.py tests/test_qss_builder.py tests/test_theme_tokens.py -v`

Expected: failures if any last global copy or icon assumptions still leak through.

- [ ] **Step 3: Implement the minimal settings/global changes**

Limit the work to the remaining cross-cutting polish:

- settings naming, collapsible grouping, and tooltips
- any lingering status-label or empty-state icon corrections
- any remaining focus, contrast, or tag styling gaps caught by the audit

- [ ] **Step 4: Re-run the focused settings/copy tests**

Run: `source .venv/bin/activate && pytest tests/test_pages.py tests/test_icons.py tests/test_qss_builder.py tests/test_theme_tokens.py -v`

Expected: PASS.

- [ ] **Step 5: Run a page-polish smoke/audit pass**

Run:

```bash
source .venv/bin/activate && (rg "Download tab|Browser && Auth|Fragment Settings|Search exclusions\\.\\.\\.|Lossless \\(fast, keyframe-limited\\)|Quality \\(CRF\\):|Unsort \\(Flatten\\)|Delete macOS dotfiles|Found: 0 URLs|Ready\\." src/ui/pages src/ui/widgets || true)
source .venv/bin/activate && pytest -q
source .venv/bin/activate && python3 run.py
```

Verify:

- Add URLs auth/login section expands and collapses
- Extract URLs shows inline options/output row and the updated auth guidance
- Sort and Rename expose visible reorder affordances and keyboard-friendly controls
- Trim shows the radio-button mode selector
- focus indicators are visible and keyboard Tab reachability works across the touched pages
- Settings sections collapse/expand, use the full required section set, and appear in the expected order
- the new user-facing copy is present on the touched pages, not just the old copy being absent

- [ ] **Step 6: Commit**

```bash
git add src/ui/pages/settings_page.py src/ui/theme/qss_builder.py src/ui/theme/icons.py \
  src/ui/components/data_panel.py tests/test_pages.py tests/test_icons.py \
  tests/test_qss_builder.py tests/test_theme_tokens.py
git commit -m "fix(ui): complete settings and global accessibility polish"
```

## Chunk 3: Integration, cleanup, and verification

### Stage mapping contract used by compatibility surfaces

Use this exact tool-to-stage map anywhere compatibility APIs or tests need stage-level behavior:

`add_urls` is the currently landed tool key and is the compatibility equivalent of the earlier spec wording `add_media`.

| Tool key | Stage key |
| --- | --- |
| `add_urls` | `ingest` |
| `extract_urls` | `ingest` |
| `convert` | `prepare` |
| `trim` | `prepare` |
| `metadata` | `prepare` |
| `sort` | `organize` |
| `rename` | `organize` |
| `match` | `organize` |
| `settings` | `export` |

### Task 8: Finish main-window integration and retire compatibility leftovers carefully

**Files:**
- Modify: `src/ui/main_window.py`
- Modify: `src/ui/shell.py`
- Modify: `src/ui/pages/__init__.py`
- Modify: `src/ui/components/__init__.py`
- Modify: `src/ui/widgets/__init__.py`
- Create or modify: `tests/test_main_window_workbench.py`
- Test: `tests/test_shell.py`
- Test: `tests/test_pages.py`

- [ ] **Step 1: Add or tighten the integration tests**

Cover the real entry-point behavior:

- create `tests/test_main_window_workbench.py` if it does not already exist
- `MainWindow` starts with exactly nine tool pages registered and Add URLs selected by default
- `MainWindow` registers the nine current tool pages
- shell badge updates still work for the active download flow
- internal stage-key mapping (`ingest`, `prepare`, `organize`, `export`) still behaves correctly where the backend expects it
- `Shell.active_stage()` and `stage_changed` emit/return the expected stage key rather than the raw tool key when compatibility behavior is still supported
- any tool-to-stage translation behavior is tested explicitly in `shell.py`/`main_window.py` coverage
- shell alias APIs are either still covered because live callers need them, or removed in the same task after `src/` and `tests/` prove they are unused
- page imports continue to succeed through `src/ui/pages/__init__.py`

- [ ] **Step 2: Run the focused integration tests**

Run: `source .venv/bin/activate && pytest tests/test_main_window_workbench.py tests/test_shell.py tests/test_pages.py -v`

Expected: FAIL if `MainWindow` still assumes the wrong contract or package exports lag behind the current page set.

- [ ] **Step 3: Implement the stage-compatibility translation behavior**

Use the explicit map above and grep before changing compatibility APIs:

- run `rg "register_stage|switch_to_stage|active_stage|stage_changed|set_stage_status" src/ tests/`
- preserve the internal stage-key mapping because this consolidated plan still honors the backend stage contract from the March spec
- keep the alias APIs in this plan, but make them translate through the exact tool-to-stage map above so compatibility callers observe stage keys rather than raw tool keys
- only consider removing alias APIs in a later plan that also changes the spec/backend contract and updates the compatibility tests together

- [ ] **Step 4: Clean up package exports only after the compatibility behavior is green**

- run `rg "from src.ui.pages|from src.ui.components|from src.ui.widgets|import src.ui.pages|import src.ui.components|import src.ui.widgets" src tests`
- clean up `__init__.py` exports so only real current components/widgets/pages are exported

- [ ] **Step 5: Re-run the focused integration tests**

Run: `source .venv/bin/activate && pytest tests/test_main_window_workbench.py tests/test_shell.py tests/test_pages.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ui/main_window.py src/ui/shell.py src/ui/pages/__init__.py \
  src/ui/components/__init__.py src/ui/widgets/__init__.py \
  tests/test_main_window_workbench.py tests/test_shell.py tests/test_pages.py
git commit -m "fix(ui): finalize main-window integration and compatibility cleanup"
```

### Task 9: Run the full verification pass and update docs that changed in reality

**Files:**
- Modify as needed: `docs/ARCHITECTURE.md`
- Modify as needed: `docs/UI_WORKBENCH.md`
- Modify as needed: `docs/AGENT_GUIDE.md`
- Modify as needed: `AGENTS.md`

- [ ] **Step 1: Run the repository verification suite**

Run:

```bash
source .venv/bin/activate && pytest -q
source .venv/bin/activate && pytest tests/test_main_window_workbench.py -v
source .venv/bin/activate && pytest tests/test_theme_tokens.py tests/test_qss_builder.py tests/test_icons.py -v
```

Expected: PASS for the full suite and the UI-focused targeted suites.

- [ ] **Step 2: Run the string and leftover audit**

Run:

```bash
source .venv/bin/activate && (rg "Browser && Auth|Summary And Utilities|Unified media workbench|Fragment Settings|Check summary or adjust settings" src/ui || true)
source .venv/bin/activate && (rg "Browser && Auth|Summary And Utilities|Unified media workbench|Fragment Settings|Check summary or adjust settings|Playwright profile|Download tab|Search exclusions|Lossless \\(fast, keyframe-limited\\)|Quality \\(CRF\\):|Unsort \\(Flatten\\)|Delete macOS dotfiles|Found: 0 URLs|Ready\\." src/ui || true)
source .venv/bin/activate && (rg "\bQUEUE\b|\bACTIVE\b|\bCLOCK\b" src/ui || true)
source .venv/bin/activate && python -c "from src.ui.theme.tokens import DARK_TOKENS, LIGHT_TOKENS; assert set(DARK_TOKENS) == set(LIGHT_TOKENS); print('token keys match')"
source .venv/bin/activate && python - <<'PY'
from src.ui.theme.tokens import DARK_TOKENS, LIGHT_TOKENS

def hex_to_rgb(value: str):
    value = value.lstrip('#')
    return tuple(int(value[i:i+2], 16) / 255 for i in (0, 2, 4))

def linearize(channel: float) -> float:
    return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4

def luminance(hex_value: str) -> float:
    r, g, b = hex_to_rgb(hex_value)
    r, g, b = linearize(r), linearize(g), linearize(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast(a: str, b: str) -> float:
    l1, l2 = sorted((luminance(a), luminance(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)

pairs = [
    ("dark text-bright", DARK_TOKENS["text-bright"], DARK_TOKENS["bg-void"], 4.5),
    ("dark text-primary", DARK_TOKENS["text-primary"], DARK_TOKENS["bg-void"], 4.5),
    ("dark text-muted", DARK_TOKENS["text-muted"], DARK_TOKENS["bg-void"], 4.5),
    ("dark text-dim", DARK_TOKENS["text-dim"], DARK_TOKENS["bg-void"], 3.0),
    ("light text-bright", LIGHT_TOKENS["text-bright"], LIGHT_TOKENS["bg-void"], 4.5),
    ("light text-primary", LIGHT_TOKENS["text-primary"], LIGHT_TOKENS["bg-void"], 4.5),
    ("light text-muted", LIGHT_TOKENS["text-muted"], LIGHT_TOKENS["bg-void"], 4.5),
    ("light text-dim", LIGHT_TOKENS["text-dim"], LIGHT_TOKENS["bg-void"], 3.0),
]
for label, fg, bg, minimum in pairs:
    ratio = contrast(fg, bg)
    assert ratio >= minimum, f"{label} contrast {ratio:.2f} < {minimum}"
print("contrast checks passed")
PY
```

Expected: no user-facing matches printed from the `src/ui` searches, and the Python commands print `token keys match` and `contrast checks passed`.

- [ ] **Step 3: Do the manual smoke run**

Run: `source .venv/bin/activate && python3 run.py`

Verify:

- the app opens with the sidebar visible
- Add URLs is the default landing page
- click each sidebar item and verify the correct page loads
- each tool loads
- the auth/login surface on Add URLs expands and collapses correctly
- active download badge updates still appear on the sidebar during a live queue/progress flow
- live download progress/status colors reflect the active/in-progress state correctly
- active download mode replaces or hides the idle URL-entry surface
- settings sections are collapsible
- split-layout tools still render with stable left/right sizing
- focus rings are visible by keyboard navigation
- the densest pages (Sort, Rename, Match, Settings) no longer show the specific audit problems around centered controls, cramped checkbox groups, invisible drag affordances, or excessive dead space
- the app closes cleanly after the smoke run

- [ ] **Step 4: Update the docs only if implementation reality changed**

If the final implementation changes the documented shell/page ownership or testing rules, update the affected docs listed above. Do not churn docs that still match reality.

- [ ] **Step 5: Commit**

```bash
git diff --quiet -- docs/ARCHITECTURE.md docs/UI_WORKBENCH.md docs/AGENT_GUIDE.md AGENTS.md || \
  (git add docs/ARCHITECTURE.md docs/UI_WORKBENCH.md docs/AGENT_GUIDE.md AGENTS.md && \
   git commit -m "docs: refresh UI architecture and verification guidance")
```
