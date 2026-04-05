# UI/UX Overhaul Plan

## Summary
Three-part UI overhaul: (1) fix timeline seeking, (2) add drag-and-drop video support, (3) full app redesign with minimal/clean aesthetic (dark mode focused).

## Design Decisions
| Decision | Choice |
|---|---|
| Timeline drag conflict | Seek wins everywhere; handles get dedicated grip UX |
| Segment handle resize | Dedicated visual pill-shaped grips at segment edges |
| Drop target scope | Per-page drop targets (Trim first, then Convert) |
| Drop visual feedback | Full-page semi-transparent overlay with dashed border and icon |
| UI cleanup scope | Full app redesign (all 9 pages) |
| Visual direction | Minimal / clean (Linear/Raycast style) |
| Timeline colors | Integrate with theme tokens (migrate 9 hardcoded hex colors) |
| Theme focus | Dark mode only |

---

## Phase 1: Theme Foundation

### Task 1: Add Timeline Color Tokens and ThemeEngine `color()` Alias

**Files to modify:**
- `src/ui/theme/tokens.py`
- `src/ui/theme/theme_engine.py`

**Steps:**

1. Add 9 new timeline token keys to `REQUIRED_TOKEN_KEYS` in `tokens.py`:
   - `timeline-base-border`, `timeline-base-fill`, `timeline-disabled-fill`
   - `timeline-selected-fill`, `timeline-selected-border`, `timeline-enabled-fill`
   - `timeline-handle-fill`, `timeline-playhead`, `timeline-text`

2. Add corresponding values to `DARK_TOKENS`:
   ```python
   "timeline-base-border": "#30343f",
   "timeline-base-fill": "#191c25",
   "timeline-disabled-fill": "#2b2f39",
   "timeline-selected-fill": "#5e5ad7",
   "timeline-selected-border": "#c6c3ff",
   "timeline-enabled-fill": "#3e546b",
   "timeline-handle-fill": "#f4f1ff",
   "timeline-playhead": "#3bd1ff",
   "timeline-text": "#e7ebf3",
   ```

3. Add corresponding values to `LIGHT_TOKENS`:
   ```python
   "timeline-base-border": "#c0c4cf",
   "timeline-base-fill": "#e8eaef",
   "timeline-disabled-fill": "#d0d3da",
   "timeline-selected-fill": "#6461b3",
   "timeline-selected-border": "#3d3b8e",
   "timeline-enabled-fill": "#7dabc4",
   "timeline-handle-fill": "#1a181b",
   "timeline-playhead": "#0891b2",
   "timeline-text": "#1a181b",
   ```

4. Add `color()` alias to `ThemeEngine`:
   ```python
   def color(self, key: str) -> str:
       """Alias for get_color() — shorter for QPainter code."""
       return self.get_color(key)
   ```

**Verification:**
- `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/test_theme_tokens.py tests/test_theme_engine.py -q`
- `PYTHONPATH=. .venv/bin/python -m py_compile src/ui/theme/tokens.py src/ui/theme/theme_engine.py`

---

### Task 2: Wire Spacing Tokens into QSS Builder + Add Drop Overlay QSS

**Files to modify:**
- `src/ui/theme/qss_builder.py`

**Steps:**

1. In `build_qss()`, replace hardcoded padding/margin pixel values with spacing token references where they align:
   - `4px` → `{t["sp-xs"]}` 
   - `8px` → `{t["sp-s"]}`
   - `12px` → `{t["sp-m"]}`
   - `16px` → `{t["sp-l"]}`
   - `24px` → `{t["sp-xl"]}`
   Only replace values where the semantic meaning matches (padding, margins, spacing). Do NOT replace border-radius, font-size, width/height, or other non-spacing values.

2. Add drop overlay QSS rules at the end of the stylesheet:
   ```css
   /* ----- 48. Drop overlay ----- */
   QWidget#dropOverlay {
       background: rgba(14, 14, 16, 0.85);
       border: 2px dashed {t["primary"]};
       border-radius: {t["r-xl"]};
   }
   
   QLabel#dropOverlayIcon {
       color: {t["primary"]};
       font-size: 48px;
   }
   
   QLabel#dropOverlayText {
       color: {t["text-bright"]};
       font-family: {hl};
       font-size: 18px;
       font-weight: 700;
   }
   
   QLabel#dropOverlayHint {
       color: {t["text-dim"]};
       font-size: 12px;
   }
   ```

**Verification:**
- `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/test_qss_builder.py -q`
- `PYTHONPATH=. .venv/bin/python -m py_compile src/ui/theme/qss_builder.py`

---

## Phase 2: Timeline Interaction

### Task 3: Implement Drag-to-Seek on Timeline

**Files to modify:**
- `src/ui/widgets/trim_timeline_widget.py` (only `_TimelineCanvas` class)

**Context:** Currently `mousePressEvent` emits `seek_requested` on click, but `mouseMoveEvent` only handles handle dragging — there is no seek-while-dragging. Users must click repeatedly to move the playhead.

**Steps:**

1. Add `_seeking: bool = False` instance variable to `_TimelineCanvas.__init__`

2. Modify `mousePressEvent`:
   - After the existing handle-press check returns True (line ~141-142), leave early as before
   - After emitting `seek_requested` (line ~148), set `self._seeking = True`

3. Modify `mouseMoveEvent`:
   - After the existing handle-drag block (lines ~153-159), add a new block BEFORE the cursor logic:
     ```python
     if self._seeking:
         self.seek_requested.emit(self._x_to_time(event.position().x(), track_rect))
         return
     ```

4. Modify `mouseReleaseEvent`:
   - Add `self._seeking = False` alongside the existing `self._drag_mode = None`

5. Update the info label text in `TrimTimelineWidget._setup_ui()`:
   - Change from: `"Click anywhere to seek. Drag the highlighted segment handles to tighten a cut."`
   - Change to: `"Click or drag to seek. Use the handles to adjust segment boundaries."`

**Verification:**
- `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/test_trim_timeline_widget.py -q`
- Write a new test `test_timeline_drag_to_seek_emits_multiple_seeks` that:
  1. Creates a widget with duration 10.0 and one segment
  2. Connects to `seek_requested` signal
  3. Presses at x=100, moves to x=200, then x=300, releases
  4. Asserts multiple seek signals were emitted (at least 2)

---

### Task 4: Dedicated Pill-Shaped Handle Grips

**Files to modify:**
- `src/ui/widgets/trim_timeline_widget.py` (only `_TimelineCanvas.paintEvent`)

**Context:** Currently handles are drawn as 5.5px radius circles. Design calls for pill-shaped grips at segment edges.

**Steps:**

1. Replace the circle handle drawing (lines ~108-114) with pill-shaped grips:
   ```python
   # Draw pill-shaped handle grips for selected segment
   if self._selected_segment_id:
       selected = self._selected_segment()
       if selected is not None:
           pill_width = 6.0
           pill_height = 20.0
           pill_radius = 3.0
           for handle_x in (
               self._time_to_x(selected.start_time, track_rect),
               self._time_to_x(selected.end_time, track_rect),
           ):
               pill_rect = QRectF(
                   handle_x - pill_width / 2,
                   track_rect.center().y() - pill_height / 2,
                   pill_width,
                   pill_height,
               )
               painter.setPen(Qt.PenStyle.NoPen)
               painter.setBrush(handle_fill)
               painter.drawRoundedRect(pill_rect, pill_radius, pill_radius)
   ```

**Verification:**
- `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/test_trim_timeline_widget.py -q`
- Existing tests should still pass (they test click/drag behavior, not paint output)

---

### Task 5: Migrate Timeline Hardcoded Colors to Theme Tokens

**Files to modify:**
- `src/ui/widgets/trim_timeline_widget.py`

**Context:** `_TimelineCanvas.paintEvent` has 9 hardcoded hex color values. These must use `ThemeEngine.get_color()` instead so the timeline respects the active theme. The token keys were added in Task 1.

**Steps:**

1. Add import at top of file:
   ```python
   from ..theme.theme_engine import ThemeEngine
   ```

2. Replace all hardcoded colors in `paintEvent` with token lookups:
   ```python
   engine = ThemeEngine.instance()
   base_border = QColor(engine.get_color("timeline-base-border"))
   base_fill = QColor(engine.get_color("timeline-base-fill"))
   disabled_fill = QColor(engine.get_color("timeline-disabled-fill"))
   selected_fill = QColor(engine.get_color("timeline-selected-fill"))
   selected_border = QColor(engine.get_color("timeline-selected-border"))
   enabled_fill = QColor(engine.get_color("timeline-enabled-fill"))
   handle_fill = QColor(engine.get_color("timeline-handle-fill"))
   playhead_color = QColor(engine.get_color("timeline-playhead"))
   ```

3. Replace the hardcoded `#ffffff` and `#e7ebf3` in segment text drawing:
   ```python
   painter.setPen(QColor(engine.get_color("text-bright")) if is_selected else QColor(engine.get_color("timeline-text")))
   ```

**Verification:**
- `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/test_trim_timeline_widget.py tests/test_theme_tokens.py -q`
- `PYTHONPATH=. .venv/bin/python -m py_compile src/ui/widgets/trim_timeline_widget.py`

---

## Phase 3: Drag-and-Drop

### Task 6: Create DropOverlay Widget

**Files to create:**
- `src/ui/widgets/drop_overlay.py`
- `tests/test_drop_overlay.py`

**Context:** No drag-and-drop exists in the codebase. This creates a reusable overlay widget that pages can embed. The overlay is hidden by default and shown/hidden by the host page's `dragEnterEvent`/`dragLeaveEvent`/`dropEvent`.

**Steps:**

1. Create `src/ui/widgets/drop_overlay.py`:
   ```python
   """Reusable drag-and-drop overlay widget."""
   from PyQt6.QtCore import Qt
   from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


   class DropOverlay(QWidget):
       """Full-page semi-transparent overlay shown during drag-over.
       
       The host page is responsible for showing/hiding this overlay
       by calling show()/hide() in its drag events.
       """

       def __init__(self, parent: QWidget, accepted_extensions: list[str] | None = None):
           super().__init__(parent)
           self.setObjectName("dropOverlay")
           self.accepted_extensions = accepted_extensions or []
           self.hide()
           self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
           self._setup_ui()

       def _setup_ui(self) -> None:
           layout = QVBoxLayout(self)
           layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

           icon = QLabel("\u2b07")  # downward arrow
           icon.setObjectName("dropOverlayIcon")
           icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
           layout.addWidget(icon)

           text = QLabel("Drop files here")
           text.setObjectName("dropOverlayText")
           text.setAlignment(Qt.AlignmentFlag.AlignCenter)
           layout.addWidget(text)

           self._hint = QLabel("")
           self._hint.setObjectName("dropOverlayHint")
           self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
           layout.addWidget(self._hint)

       def set_hint(self, text: str) -> None:
           self._hint.setText(text)

       def resizeToParent(self) -> None:
           if self.parent():
               self.setGeometry(self.parent().rect())
   ```

2. Create `tests/test_drop_overlay.py`:
   - Test construction and initial state (hidden)
   - Test `set_hint` updates label text
   - Test `resizeToParent` matches parent geometry
   - Test accepted_extensions stored correctly

**Verification:**
- `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/test_drop_overlay.py -q`

---

### Task 7: Integrate Drop Overlay into TrimPage

**Files to modify:**
- `src/ui/pages/trim_page.py`

**Context:** TrimPage uses SplitLayout. The drop overlay should cover the entire page. When a video file is dropped, it should load into the trim editor (same as the existing file-open flow).

**Steps:**

1. Add imports:
   ```python
   from src.ui.widgets.drop_overlay import DropOverlay
   from PyQt6.QtCore import QMimeData
   ```

2. In `_setup_ui()` (or `__init__`), after the page root widget is created:
   ```python
   self.setAcceptDrops(True)
   self._drop_overlay = DropOverlay(self, accepted_extensions=[".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".mp3", ".wav", ".flac", ".ogg", ".m4a"])
   self._drop_overlay.set_hint("Video or audio files")
   ```

3. Implement drag events on the page:
   ```python
   def dragEnterEvent(self, event):
       if event.mimeData().hasUrls():
           event.acceptProposedAction()
           self._drop_overlay.resizeToParent()
           self._drop_overlay.raise_()
           self._drop_overlay.show()

   def dragLeaveEvent(self, event):
       self._drop_overlay.hide()

   def dropEvent(self, event):
       self._drop_overlay.hide()
       urls = event.mimeData().urls()
       for url in urls:
           path = url.toLocalFile()
           if path:
               self._load_file(path)  # Use existing file-load method
               break  # Trim works with one file at a time
   ```

4. Override `resizeEvent` to keep overlay sized:
   ```python
   def resizeEvent(self, event):
       super().resizeEvent(event)
       if hasattr(self, '_drop_overlay'):
           self._drop_overlay.resizeToParent()
   ```

**Verification:**
- `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/test_trim_page.py -q`
- `PYTHONPATH=. .venv/bin/python -m py_compile src/ui/pages/trim_page.py`

---

### Task 8: Integrate Drop Overlay into ConvertPage

**Files to modify:**
- `src/ui/pages/convert_page.py`

**Context:** ConvertPage also uses SplitLayout. Drop overlay covers the page. Dropped files should be added to the conversion queue (same as existing file-add flow).

**Steps:**

1. Same pattern as Task 7 but for ConvertPage
2. `accepted_extensions` should include common video/audio formats
3. `dropEvent` should call the existing method that adds files to the conversion queue
4. Multiple files should be supported (unlike Trim which takes one)

**Verification:**
- `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/test_convert_page.py -q`
- `PYTHONPATH=. .venv/bin/python -m py_compile src/ui/pages/convert_page.py`

---

## Phase 4: UI Polish

### Task 9: QSS Minimal/Clean Aesthetic Pass

**Files to modify:**
- `src/ui/theme/qss_builder.py`

**Context:** This is the highest-leverage task — QSS changes cascade to all 9 pages. Target: Linear/Raycast minimal aesthetic.

**Steps:**

1. Reduce visual noise:
   - Remove `ghost-border` from default QPushButton (make truly ghost/borderless)
   - Reduce border-radius on DataPanel from `r-xl` (16px) to `r-l` (12px) for subtlety
   - Make QGroupBox border lighter or remove entirely
   - Tighten QSS padding values where over-generous (e.g. CTA button padding)

2. Improve typography hierarchy:
   - Increase `pageTitle` to 24px and reduce weight to 700
   - Reduce `sidebarSection` letter-spacing from 1px to 0.5px for less "shouting"
   - Ensure consistent font-size scale: 10px (caption), 12px (body), 13px (subtitle), 24px (title)

3. Refine interactive states:
   - Make hover states more subtle (smaller color shift)
   - Ensure disabled states are clearly muted
   - Make focus rings use primary color with lower opacity

4. Polish specific components:
   - QProgressBar: increase to 4px height (from 6px) for slimmer look
   - QScrollBar: make handle slightly wider (8px) for easier grabbing
   - Tab bar: increase selected border-bottom to 2px solid primary

**Verification:**
- `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/test_qss_builder.py -q`
- `PYTHONPATH=. .venv/bin/python -m py_compile src/ui/theme/qss_builder.py`

---

### Task 10: DataPanel Spacing + SplitLayout Standardization

**Files to modify:**
- `src/ui/components/data_panel.py`
- `src/ui/components/split_layout.py`

**Steps:**

1. DataPanel: Tighten internal spacing:
   - Header margins: `(14, 10, 14, 6)` → `(12, 8, 12, 4)`
   - Body margins: `(14, 8, 14, 14)` → `(12, 6, 12, 12)`
   - Body spacing: `8` → `6`

2. SplitLayout: Standardize right panel width:
   - Change default `right_width` from 360 to 340
   - This is the most common width used across pages

**Verification:**
- `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/ -q --timeout=30`

---

### Task 11: Migrate RenamePage to SplitLayout

**Files to modify:**
- `src/ui/pages/rename_page.py`

**Context:** RenamePage is the only page using manual `QHBoxLayout` with `setFixedWidth(260)` instead of the shared `SplitLayout` component. Migrating it ensures visual consistency.

**Steps:**

1. Read the current RenamePage layout code
2. Replace the manual two-column layout with `SplitLayout(right_width=340)`
3. Move existing left-panel content into `split.left_panel`
4. Move existing right-panel content into `split.right_panel`
5. Preserve all existing signal connections and behavior

**Verification:**
- `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/ -q --timeout=30`
- `PYTHONPATH=. .venv/bin/python -m py_compile src/ui/pages/rename_page.py`

---

### Task 12: Sidebar Polish

**Files to modify:**
- `src/ui/components/sidebar.py`

**Steps:**

1. Reduce sidebar width from 220 to 200 for tighter feel
2. Reduce branding spacing: `addSpacing(16)` → `addSpacing(12)`
3. Reduce section gap: `addSpacing(8)` → `addSpacing(6)`
4. Add subtle top border separator above settings button

**Verification:**
- `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/ -q --timeout=30`
- `PYTHONPATH=. .venv/bin/python -m py_compile src/ui/components/sidebar.py`

---

### Task 13: Full Test Suite Verification

**Steps:**
1. Run full test suite: `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/ -q --timeout=60`
2. Run py_compile on all modified files
3. Fix any failures
4. Run mypy if configured: `PYTHONPATH=. .venv/bin/mypy src/ui/theme/ src/ui/widgets/trim_timeline_widget.py src/ui/widgets/drop_overlay.py`

---

## Files Changed Summary

### Modified
- `src/ui/theme/tokens.py` — 9 new timeline color tokens
- `src/ui/theme/theme_engine.py` — `color()` alias
- `src/ui/theme/qss_builder.py` — spacing tokens, drop overlay QSS, aesthetic polish
- `src/ui/widgets/trim_timeline_widget.py` — drag-to-seek, pill handles, theme colors
- `src/ui/pages/trim_page.py` — drop overlay integration
- `src/ui/pages/convert_page.py` — drop overlay integration
- `src/ui/pages/rename_page.py` — SplitLayout migration
- `src/ui/components/data_panel.py` — spacing tightening
- `src/ui/components/split_layout.py` — width standardization
- `src/ui/components/sidebar.py` — visual polish

### Created
- `src/ui/widgets/drop_overlay.py` — reusable drop overlay widget
- `tests/test_drop_overlay.py` — drop overlay tests
