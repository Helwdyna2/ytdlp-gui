# Decisions

## Workbench Model

- The app uses a four-stage workbench instead of separate peer tabs.
- Canonical stage keys are `ingest`, `prepare`, `organize`, and `export`.
- Settings live inside the `export` stage instead of as top-level navigation.

## Visual System

- Signal Deck is the canonical theme and naming system.
- `src/ui/theme/` remains the single source of truth for tokens, QSS, and icons.
- Dark and light themes are both supported through `ThemeEngine`.

## Persistence

- `pyproject.toml` and `src/utils/constants.py` are the version sources of truth for the app version.
- shared workbench splitter state is persisted in `window.splitter_sizes`
- runtime state such as `data/config.json` is local-only and not tracked in git

## Auth

- one Playwright profile directory
- one Netscape cookie export file
- no per-site cookie files
- no Playwright `storage_state.json`

## Download Safety

- anti-ban behavior stays limited to polite pacing and retry controls
- no stealth or evasion tactics are added to the app
