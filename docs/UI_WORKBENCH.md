# UI Workbench

## Canonical Names

- `workbench` means the four-stage information architecture and shell
- `Signal Deck` means the theme, tokens, icon vocabulary, and styling language

## Shell Anatomy

The persistent shell is:

- `AppHeader`
- `StageRail`
- stacked stage content
- `FooterBar`

Each stage follows the same internal pattern:

- `StageContextStrip`
- `WorkspaceSurface`
- `InspectorPanel`
- optional `ActivityDrawer`
- shared horizontal splitter between primary and inspector content

## Stage Responsibilities

### Ingest

- Add Media
- Extract URLs
- queue and output controls in the inspector
- progress and logs in the activity drawer

### Prepare

- Convert
- Trim
- Metadata
- stage-specific inspector copy based on the active tool

### Organize

- Sort
- Rename
- Match
- stage-specific inspector copy based on the active tool

### Export

- run summary
- recent activity
- settings

## Signal Deck Rules

### Tokens

- `src/ui/theme/tokens.py` is the token source of truth
- keep dark and light token keys in sync
- use semantic surface, border, text, and accent roles instead of one-off widget colors

### Icons

- `src/ui/theme/icons.py` is the icon registry
- keep `get_icon(name, color=None)` stable
- prefer stage-centric names such as `ingest`, `prepare`, `organize`, and `export`

### QSS

- `src/ui/theme/qss_builder.py` is the single stylesheet builder
- workbench selectors should target object names, not ad hoc inline styling

## Legacy Widget Reuse

The workbench intentionally reuses these live widgets instead of rewriting business logic:

- `DataPanel`
- `DataCell`
- `LogFeed`
- `StatusTag`
- `FacilityBar`
- existing tool widgets under `src/ui/widgets/`

The shell and stage composition changed; the underlying managers, workers, auth flow, and settings semantics did not.
