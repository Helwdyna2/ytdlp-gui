# Agent Guide

## Quick Map

- `src/ui/main_window.py`: app orchestration, settings navigation, queue wiring, splitter persistence
- `src/ui/shell.py`: top-level shell
- `src/ui/widgets/ingest_stage_widget.py`: Add Media and Extract URLs stage composition
- `src/ui/widgets/prepare_stage_widget.py`: Convert, Trim, Metadata stage composition
- `src/ui/widgets/organize_stage_widget.py`: Sort, Rename, Match stage composition
- `src/ui/widgets/export_stage_widget.py`: summary, recent activity, settings stage composition
- `src/ui/theme/`: Signal Deck tokens, QSS, icon registry, theme engine
- `src/services/config_service.py`: config defaults and persistence

## Safe Change Patterns

- keep the four stage keys stable: `ingest`, `prepare`, `organize`, `export`
- preserve `ThemeEngine` public usage and `get_icon(name, color=None)`
- preserve auth semantics: one Playwright profile, one Netscape cookie file
- preserve manager/service contracts when changing layout or presentation
- use the existing `window.splitter_sizes` config key for the main workbench splitter state

## High-Risk Areas

- `src/ui/main_window.py`: easy to break signal wiring or session recovery
- `src/ui/widgets/settings_tab_widget.py`: theme persistence, Playwright actions, polite-mode config writes
- `src/core/` workers and managers: do not move widget logic into worker threads
- auth flow: keep the current cookie export and warning semantics intact

## Good Verification Targets

- `pytest -q`
- `pytest tests/test_main_window_workbench.py -v`
- `pytest tests/test_theme_tokens.py tests/test_qss_builder.py -v`
- `python run.py` for a manual smoke pass when UI structure changes
