# Design System Specification: High-End Media Processing

## 1. Overview & Creative North Star
**The Creative North Star: "The Digital Obsidian"**
This design system is built for power users who demand precision and focus. Inspired by the architectural clarity of tools like Linear and Raycast, it moves away from the "web-app" aesthetic toward a "native-pro" experience. We prioritize **functional density** over white space, using a monochromatic charcoal base with surgical applications of muted violet and teal. 

The system breaks the standard "boxed" template through **Tonal Layering**. Instead of using lines to separate ideas, we use depth and light. The layout is intentionally asymmetrical, often anchoring heavy data tables against slim, high-density sidebars to create a rhythmic, editorial flow that feels professional and custom-tailored.

---

## 2. Colors & Surface Philosophy
The palette is rooted in a deep charcoal base (`#0e0e10`) to eliminate eye strain during long processing sessions.

### The "No-Line" Rule
**Explicit Instruction:** Traditional 1px solid borders for sectioning are strictly prohibited. Boundaries must be defined through background color shifts or tonal transitions.
- Use `surface-container-low` (`#131315`) for the main canvas.
- Use `surface-container-high` (`#1f1f22`) for secondary panels.
- Content groupings are defined by the contrast between these surfaces, never by a stroke.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers. 
- **Base Level:** `surface` (`#0e0e10`) - The application shell.
- **Level 1 (Panels):** `surface-container` (`#19191c`) - Main functional areas.
- **Level 2 (Cards/Inlays):** `surface-container-highest` (`#262528`) - Active interactive zones or nested data rows.

### The "Glass & Gradient" Rule
To add "soul" to the technical interface:
- **Floating Elements:** Use `surface-bright` (`#2c2c2f`) at 80% opacity with a `20px` backdrop-blur for modals or command menus.
- **CTAs:** Apply a subtle linear gradient from `primary` (`#c5c4ff`) to `primary-container` (`#9c9bd3`) to give buttons a slight metallic sheen rather than a flat fill.

---

## 3. Typography
We utilize a dual-typeface system to balance high-end editorial feel with functional utility.

- **Display & Headlines (Manrope):** Chosen for its geometric precision and modern "tech-boutique" feel. Use `headline-sm` (`1.5rem`) for section headers to provide an authoritative anchor.
- **Interface & Body (Inter):** The workhorse. Inter provides maximum legibility at the small sizes required for dense data processing. 
- **Brand Identity through Scale:** Use extreme contrast between `display-sm` for landing moments and `label-sm` for metadata. This "Big & Small" approach mimics premium magazine layouts.

---

## 4. Elevation & Depth
Hierarchy is achieved through **Tonal Layering**, not structural lines.

- **The Layering Principle:** Place `surface-container-lowest` (`#000000`) elements inside `surface-container-low` areas to create "wells" for input fields. Conversely, use `surface-container-highest` to "lift" active segments.
- **Ambient Shadows:** Shadows are reserved for floating elements only. Use a `32px` blur, `10%` opacity, tinted with `primary-dim` (`#b8b6f0`) to mimic a soft glow from the interface's violet accents.
- **The "Ghost Border" Fallback:** If a divider is mandatory for accessibility (e.g., distinguishing between two similar data columns), use the `outline-variant` (`#48474a`) at **15% opacity**. It should be felt, not seen.

---

## 5. Components

### Buttons
- **Primary:** Gradient fill (`primary` to `primary-container`), `md` (`0.375rem`) roundedness. Label is `on-primary-container`.
- **Secondary:** Surface-only with a "Ghost Border" (15% opacity `outline`). 
- **Tertiary/Ghost:** No container, `primary` text. Use for low-emphasis actions like "Cancel."

### Dense Data Tables
- **Styling:** Forbid horizontal lines. Use a subtle `surface-container-high` hover state to highlight rows.
- **Header:** Use `label-sm` in `on-surface-variant` (`#acaaad`), all-caps with `0.05em` letter spacing.

### Status Indicators & Chips
- **Status:** Use a small 6px dot. `secondary` (`#abefec`) for "Processing," `error` (`#ff6e84`) for "Failed," and `primary` for "Matched."
- **Chips:** `sm` (`0.125rem`) roundedness. Background: `surface-container-highest`. Use for media tags (e.g., "4K", "H.264").

### Form Fields
- **Input Wells:** Background set to `surface-container-lowest` (`#000000`).
- **Focus State:** No thick border. Use a 1px glow using `primary` at 40% opacity and a subtle `surface-tint` inner shadow.

### Media Timeline (Custom)
- **Track:** `surface-container-highest`.
- **Handle:** `primary` solid fill with a 4px `primary_dim` outer glow to indicate "active depth."

---

## 6. Do's and Don'ts

### Do
- **Do** use `2.5` (`0.5rem`) spacing between related data points to maintain high density without clutter.
- **Do** use `secondary` (Teal) for success states and technical data points to provide a cool contrast to the `violet` primary brand color.
- **Do** lean into asymmetry. A wide media player paired with a narrow, dense metadata sidebar creates a professional "workstation" feel.

### Don't
- **Don't** use `#000000` for the background; it feels "dead." Always use the charcoal `surface` (`#0e0e10`) for a premium "ink" depth.
- **Don't** use standard `1px` dividers. Separate content with a `1.1rem` (`5`) gap or a background shift to `surface-container-low`.
- **Don't** use high-saturation reds. Use `error_dim` (`#d73357`) to ensure warnings don't break the muted, sophisticated atmosphere of the app.