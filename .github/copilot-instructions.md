<!-- See AGENTS.md for the primary agent instructions. This file supplements those. -->

# Copilot Instructions

## Build, test, and run

Use the project virtual environment from the repository root before running commands:

```bash
source .venv/bin/activate
```

If the environment does not exist yet:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python3 -m playwright install
```

Common commands:

```bash
python3 run.py
pytest -q
pytest tests/test_main_window_workbench.py -v
pytest tests/test_file.py -v
pytest -k "pattern" -v
pyinstaller ytdlp_gui.spec
```

There is no configured lint step in this repository. Do not assume `ruff`, `flake8`, or `mypy` are part of the workflow.

When changing shell, theme, or workbench behavior, also run:

```bash
pytest tests/test_main_window_workbench.py -v
pytest tests/test_theme_tokens.py tests/test_qss_builder.py tests/test_icons.py -v
```

When changing UI structure and the environment allows it, do a smoke run with:

```bash
python3 run.py
```

## High-level architecture

This is a PyQt6 desktop workbench for yt-dlp workflows. The runtime flow is:

`UI -> Qt signals/slots -> core managers/workers -> services -> database/config/filesystem`

Key entry points:

- `run.py` runs the app from source in development.
- `main.py` is the packaging-friendly top-level entry point.
- `src/main.py` initializes the Qt application, single-instance behavior, theme application, database/services, crash recovery, FFmpeg checks, and window restoration.

The main layers are:

- `src/ui/` holds the workbench shell, stage widgets, shared components, and theme system.
- `src/core/` implements download/auth/extraction/organize logic and worker classes.
- `src/services/` manages persisted app state such as config, session restore, and crash recovery.
- `src/data/` stores the SQLite database, repositories, and persisted dataclasses.

The app is organized around a four-stage workbench with stable stage keys:

- `ingest`
- `prepare`
- `organize`
- `export`

`src/ui/main_window.py` is the main orchestrator. It creates shared widgets and managers, instantiates one widget per stage, and registers them with `Shell.register_stage()`.

`src/ui/shell.py` defines the persistent outer shell:

- `AppHeader`
- `StageRail`
- stacked stage content
- `FooterBar`

Each stage widget lives in `src/ui/widgets/` and owns its own internal layout. There is no shared `InspectorPanel` — stages compose their content independently using local splitters where needed (e.g., `sort_tab`, `metadata_viewer`, `rename_tab`). The workbench shell changed, but the underlying tool widgets and business logic were intentionally reused rather than rewritten.

## Key conventions

Threading boundaries are strict. Do not manipulate widgets from worker threads; worker code in `src/core/` must communicate back to the UI through Qt signals/slots.

Auth behavior has repository-specific invariants:

- keep one persistent Playwright profile directory via `auth.profile_dir`
- keep one Netscape cookie file via `auth.cookies_file_path`
- do not add per-site cookie files or `storage_state.json`
- treat browser close without cookies as a warning path, not a crash path

Workbench and theme contracts should stay stable:

- preserve the stage keys `ingest`, `prepare`, `organize`, and `export`
- keep `ThemeEngine` public usage stable
- keep `get_icon(name, color=None)` stable
- keep splitter persistence under `window.splitter_sizes`

Signal Deck is the styling system for this app. Follow these repo-specific rules:

- `src/ui/theme/tokens.py` is the source of truth for theme tokens
- keep dark and light token keys in sync
- use semantic token roles instead of one-off widget colors
- `src/ui/theme/qss_builder.py` is the single stylesheet builder
- target stable object names/selectors in QSS instead of ad hoc inline styling
- prefer stage-centric icon names such as `ingest`, `prepare`, `organize`, and `export`

The app depends on runtime state under `data/`, but those artifacts are local-only. Do not reintroduce tracked runtime files such as `data/config.json`.

Anti-ban behavior is intentionally limited to polite pacing, retries, and rate limits. Do not introduce stealth or evasion behavior.
