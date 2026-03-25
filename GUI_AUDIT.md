# yt-dlp GUI — Design Critique, Accessibility Audit & UX Copy Review

**Date:** 2026-03-18 | **Standard:** WCAG 2.1 AA | **Screens reviewed:** 10 (all stages + sub-tabs)

---

## Design Critique

### Overall Impression
The app has a coherent dark "Signal Deck" aesthetic with a warm amber accent, and the four-stage workbench model is a smart information architecture. However, the layouts suffer from excessive empty space, inconsistent alignment patterns, poor visual hierarchy within stages, and controls that feel scattered rather than deliberately composed. The dark theme also creates contrast issues that hurt readability.

### Usability

| # | Finding | Severity | Screens | Recommendation |
|---|---------|----------|---------|----------------|
| 1 | **Tab bar (Summary/Settings, Add Media/Extract URLs, etc.) floats in the center** with no visual connection to the content below it. It looks orphaned. | Major | All stages | Left-align tab bars or anchor them to a content container edge. Add a bottom border or active-tab indicator that connects to the panel below. |
| 2 | **"Check summary or adjust settings" helper text** in top-right competes with the Settings button in the header. Two affordances for the same action. | Moderate | Export | Remove the helper text, or replace it with a contextual status indicator (e.g., "Last export: 2 min ago"). |
| 3 | **Concurrent Downloads slider** has nearly invisible tick marks on dark background. The slider track is barely visible. | Major | Ingest (Add Media) | Increase slider track contrast. Add visible tick labels at min/mid/max. |
| 4 | **"Browser && Auth" label** uses a literal `&&` which looks like a code artifact, not a UI label. | Minor | Export > Settings | Change to "Browser & Auth" or "Browser and Authentication". |
| 5 | **Organize > Match** packs checkboxes and labels on one line with no spacing system. "Search ThePornDB (prioritized)" and "Search StashDB" run together. | Major | Organize > Match | Use a proper form layout with consistent label-input spacing. Group related options in labeled fieldsets. |
| 6 | **Bottom-right thumbnail preview** on every screen is mysterious — no label, no context, very small. | Moderate | All screens | Either make it a purposeful minimap with a label, or remove it. It currently looks like a rendering bug. |
| 7 | **"Recent Activity" button** in the footer feels disconnected from everything. It has an orange border that doesn't match the footer's role. | Minor | All screens | Move activity/log into the Export > Summary tab or make it a slide-up drawer triggered from the footer. |
| 8 | **Sort criteria / Rename tokens lists** have no visual affordance indicating they're draggable/reorderable (the grip dots are nearly invisible). | Major | Organize > Sort, Rename | Add a visible drag handle icon. Consider a hover state that lifts the item. |

### Visual Hierarchy

- **What draws the eye first:** The orange stage heading ("Ingest", "Prepare", etc.) — this is correct.
- **Reading flow problems:** After the heading, the eye jumps to the top-right helper text, then back to the centered tab bar, then down to content. This zigzag is disorienting.
- **Whitespace:** Massive empty areas in the center of most screens (Export Summary, Settings, Ingest empty state). The content doesn't fill the available space or use it purposefully.
- **Typography:** The monospace body font (IBM Plex Mono) at small sizes on dark backgrounds is hard to read. Section headers like "Download Defaults" and "Filename Format" have inconsistent weight/size relative to each other.

### Consistency Issues

| Element | Issue | Recommendation |
|---------|-------|----------------|
| Tab bars | Centered on some screens, left-aligned on none. Different visual treatment per stage. | Standardize position and styling globally. |
| Section headers | "Add Media", "Download Defaults", "Login Status" all use different typography weights. | Use one consistent heading level per nesting depth. |
| Action buttons | "Start Download" is orange-filled, "Trim Video" is orange-filled, but "Scan Folder" and "Start Matching" are also orange-filled at the same level — no primary/secondary distinction. | Define primary (filled orange) vs. secondary (outlined) vs. destructive (red) button hierarchy. |
| Status indicators | "QUEUE —", "ACTIVE —", "CLOCK —" in the header use em-dash for zero, but the Summary tab uses "0" numerals. | Pick one representation for zero/empty state. |
| Form layout | Ingest uses label-left (Output Folder:, Concurrent Downloads:). Prepare > Metadata uses a completely different two-column split. Organize > Sort mixes both. | Standardize form layout patterns across all stages. |

---

## Accessibility Audit

**Issues found:** 14 | **Critical:** 4 | **Major:** 6 | **Minor:** 4

### Perceivable

| # | Issue | WCAG | Severity | Recommendation |
|---|-------|------|----------|----------------|
| 1 | **text-dim (#5a5e6a) on bg-surface (#0e1018)** — contrast ratio ~2.5:1, far below 4.5:1 minimum. Used for helper text, descriptions, and placeholder text throughout. | 1.4.3 | Critical | Brighten text-dim to at least #8a8e9a (~4.6:1). |
| 2 | **text-muted (#3a3e4a) on bg-surface (#0e1018)** — contrast ratio ~1.7:1. Used for disabled states and labels. Virtually invisible. | 1.4.3 | Critical | Raise to at least #6a6e7a for disabled text, or use opacity on text-primary. |
| 3 | **Orange accent (#c4956a) on bg-surface (#0e1018)** — contrast ~4.2:1, just below 4.5:1 for normal-size text. Section headers like "Summary And Utilities" use this at normal text size. | 1.4.3 | Major | Either increase font size to "large text" (18px+ or 14px bold) so 3:1 applies, or brighten to #d4a57a. |
| 4 | **Slider track and tick marks** have insufficient contrast against the dark panel background. Nearly invisible. | 1.4.11 | Major | Ensure slider track and ticks meet 3:1 contrast ratio against their background. |
| 5 | **Checkbox borders** (border-soft #3a3e4a on bg-panel #161820) — ~1.3:1 contrast. Checkboxes are nearly invisible until checked. | 1.4.11 | Critical | Raise checkbox border contrast to at least 3:1. Use border-hard (#2a2c36) minimum, or better, a lighter value. |

### Operable

| # | Issue | WCAG | Severity | Recommendation |
|---|-------|------|----------|----------------|
| 6 | **No visible focus indicators** apparent in any screenshot. Tab navigation likely has no visual ring. | 2.4.7 | Critical | Add a visible focus ring (e.g., 2px solid #c4956a with 2px offset) to all interactive elements. |
| 7 | **Drag-to-reorder lists** (Sort criteria, Rename tokens) have no keyboard alternative visible. | 2.1.1 | Major | Add up/down arrow buttons or keyboard shortcuts for reordering. |
| 8 | **Small touch/click targets** on the trim timeline — the frame thumbnails and scrub handle are tiny. Advisory (WCAG 2.1 AAA target size guidance only; not part of the AA conformance scope for this audit). | 2.5.5 (AAA) | Minor | For AA conformance, keep focus/keyboard access strong; as an AAA improvement, aim for trim handles at least 44x44px. |

### Understandable

| # | Issue | WCAG | Severity | Recommendation |
|---|-------|------|----------|----------------|
| 9 | **"CRF" in Quality slider** — no explanation of what CRF means. Technical jargon. | 3.3.2 | Minor | Add tooltip: "Constant Rate Factor — lower values mean higher quality and larger files." |
| 10 | **"Lossless (fast, keyframe-limited)"** — unclear what "keyframe-limited" means for the user. | 3.3.2 | Minor | Reword: "Lossless trim (fast, may shift start/end to nearest keyframe)" |
| 11 | **No validation feedback visible** — e.g., what happens if you enter an invalid URL? No error state patterns shown. | 3.3.1 | Major | Implement inline validation with error messages below inputs. |
| 12 | **"0,000 s"** in trim start/end fields uses comma as decimal separator inconsistently with other numeric displays. | 3.3.2 | Minor | Use locale-consistent number formatting throughout. |

### Robust

| # | Issue | WCAG | Severity | Recommendation |
|---|-------|------|----------|----------------|
| 13 | **Table headers** (Select, Status, Confidence, etc.) may lack proper accessible names in PyQt. | 4.1.2 | Minor | Ensure QTableWidget has proper header roles and accessible names (`setAccessibleName()` / `setAccessibleDescription()` via `QAccessibleInterface`). |
| 14 | **Tab bar role** — custom tab implementations may not expose the correct tab/tabpanel roles. | 4.1.2 | Major | Use QTabWidget or ensure custom tabs expose proper accessibility roles through `QAccessibleInterface`. |

### Color Contrast Summary (Dark Theme)

| Element | Foreground | Background | Ratio | Required | Pass? |
|---------|-----------|------------|-------|----------|-------|
| Body text (text-primary) | #a0a4b0 | #0e1018 | ~5.2:1 | 4.5:1 | Pass |
| Headings (text-bright) | #e8eaf0 | #0e1018 | ~12:1 | 3:1 | Pass |
| Helper text (text-dim) | #5a5e6a | #0e1018 | ~2.5:1 | 4.5:1 | FAIL |
| Disabled (text-muted) | #3a3e4a | #0e1018 | ~1.7:1 | 4.5:1 | FAIL |
| Orange headers (accent) | #c4956a | #0e1018 | ~4.2:1 | 4.5:1 | FAIL |
| Checkbox borders | #3a3e4a | #161820 | ~1.3:1 | 3:1 | FAIL |
| Slider track | ~#2a2c36 | #161820 | ~1.2:1 | 3:1 | FAIL |

---

## UX Copy Review

### Global Issues

| Current Copy | Problem | Recommended Copy |
|--------------|---------|-----------------|
| "Unified media workbench" (subtitle) | Vague, jargon-heavy. What does "workbench" mean to a user? | "Download, convert, and organize media" |
| "Check summary or adjust settings" | Unclear call to action — check what? adjust what? | Remove entirely, or replace with a contextual status message. |
| "Summary And Utilities" | "Utilities" is developer-speak. And Title Case is inconsistent with other headers. | "Overview" or "Dashboard" |
| "Browser && Auth" | Code artifact leaked into UI | "Browser & Authentication" |
| "QUEUE —", "ACTIVE —", "CLOCK —" | Em-dashes for zero are cryptic. What does CLOCK mean? | "Queued: 0", "Active: 0", "Elapsed: 0:00" |

### Per-Screen Copy

**Ingest > Add Media**

| Element | Current | Recommended | Rationale |
|---------|---------|-------------|-----------|
| Page description | "Add URLs, authenticate when needed, then start the queue." | "Paste video URLs, sign into sites if needed, then download." | Plain language, action-oriented |
| Placeholder text | "Paste URLs here (one per line or mixed with text)..." | "Paste video links here — one per line, or mixed with other text" | Warmer, clearer |
| Helper bullets | "URLs will be automatically: - Extracted from surrounding text..." | "We'll automatically extract, validate, sort, and deduplicate your links." | Single line is friendlier than a bullet list inside a text area |
| "0 URLs ready" | OK but could be warmer | "No links added yet" (empty) / "3 links ready" (populated) | |
| "Filename Format" section | "Saved as: author - id.ext" / "Author uses uploader/creator/channel/artist when available." | "Files saved as: Author - ID.ext" + tooltip for details | Reduce visual noise |

**Ingest > Extract URLs**

| Element | Current | Recommended | Rationale |
|---------|---------|-------------|-----------|
| "Authentication uses the global Playwright profile..." | Too technical for a GUI user | "Sign in using the Download tab first to access private content." | User doesn't need to know about Playwright |
| "Auto-Scroll Options" | Fine as a label | Keep, but expand on hover: "Automatically scroll the page to load more content before extracting" | |
| "Found: 0 URLs" / "Ready." | Robotic | "No links found yet." / "Ready to extract." | |

**Prepare > Convert**

| Element | Current | Recommended | Rationale |
|---------|---------|-------------|-----------|
| "Quality (CRF):" | Jargon | "Quality:" with tooltip "(CRF — lower = better quality, larger file)" | |
| "Lower = better quality, larger file" | Good, keep | Keep | |
| "Slower = better compression" | Good, keep | Keep | |
| "Use Hardware Acceleration" + "Available: Apple VideoToolbox" | Two separate pieces — the "Available" label is oddly placed | "Use hardware acceleration (Apple VideoToolbox detected)" | Single line |
| "Same as input (add _converted suffix)" | Fine, could be clearer | "Same folder as source (adds _converted to filename)" | |

**Prepare > Trim**

| Element | Current | Recommended | Rationale |
|---------|---------|-------------|-----------|
| "Lossless (fast, keyframe-limited)" | Technical | "Lossless (fast — may shift to nearest keyframe)" | Users understand "shift" better than "limited" |
| "Trimmed: 00:00:00.000" | Good | Keep | |
| "0,000 s" in spinboxes | Comma decimal + "s" unit is inconsistent | "0.000s" or locale-aware formatting | |

**Organize > Sort**

| Element | Current | Recommended | Rationale |
|---------|---------|-------------|-----------|
| "Shape media into the structure and naming scheme you want." | Good | Keep, but lowercase "structure" feels right | |
| "Proposed Structure" (placeholder) | Good empty state label | Keep | |
| "Delete macOS dotfiles (__*) during scan" | Technical. What are dotfiles? | "Remove hidden macOS files (._*) during scan" | |
| "Unsort (Flatten)" | Power-user jargon | "Undo sort (move all files back)" | |

**Organize > Match**

| Element | Current | Recommended | Rationale |
|---------|---------|-------------|-----------|
| "Search ThePornDB (prioritized)" | Label is fine for the audience, but the layout is cramped | Keep text, fix layout spacing | |
| "Search exclusions..." | Vague — exclusions of what? | "Skip keywords..." or "Exclude terms..." | |
| "Ready. Select a folder to begin." | Good | Keep | |

**Export > Summary**

| Element | Current | Recommended | Rationale |
|---------|---------|-------------|-----------|
| "No downloads yet" + chart icon | The bar chart icon is misleading — suggests data visualization, not an empty state | Use a download/arrow icon instead, or just the text | |
| "Head to Ingest to queue your first batch." | Good direction, but "Ingest" is jargon outside the app | "Go to Ingest to add your first download." (assuming users learn the nav) | |
| "QUEUED" / "ACTIVE" / "DONE" / "FAILED" counters | ALL CAPS feels aggressive | "Queued" / "Active" / "Done" / "Failed" in sentence case | |

**Export > Settings**

| Element | Current | Recommended | Rationale |
|---------|---------|-------------|-----------|
| "Force Overwrite" | Fine for power users | Add tooltip: "Replace existing files instead of skipping them" | |
| "Video Only (No Audio)" | Clear | Keep | |
| "Fragment Settings" | Most users won't know what fragments are | "Advanced Download Settings" or add explanatory subtitle | |
