# AGENTS.md

Instructions for AI coding agents working in the `yt-dlp GUI` repository.

# Important Notes

- Always update relevant documentation after significant changes. `AGENTS.md`, `CLAUDE.md`, `copilot-instructions.md` especially. Prefer to use `AGENTS.md` as the primary source of instructions. 

## Environment Setup

Always use the project virtual environment from the repository root:

```bash
source .venv/bin/activate
```

If it does not exist yet:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install
```

All commands below assume the virtual environment is active.

## Quick Reference

```bash
python run.py                  # Run from source
pip install -e ".[dev]"        # Install runtime + dev dependencies
python -m playwright install   # Install Playwright browsers
pytest -q                      # Run the full test suite
pytest tests/test_file.py -v   # Run one test file
pytest -k "pattern" -v         # Run a focused subset
pyinstaller ytdlp_gui.spec     # Build the packaged app
```

## Project Overview

Cross-platform PyQt6 desktop GUI for yt-dlp with a four-stage workbench shell and the Signal Deck visual system.

### Workbench Stages

- `Ingest`: Add Media, Extract URLs, auth state, queue setup, output config
- `Prepare`: Convert, Trim, Metadata
- `Organize`: Sort, Rename, Match
- `Export`: run summary, recent activity, settings

### Entry Points

- `run.py` for development
- `main.py` for packaging-friendly startup
- `src/main.py` for application initialization

## Project Structure

```text
src/
├── core/           # Business logic, managers, and workers
├── data/           # SQLite database, models, repositories
├── services/       # ConfigService, SessionService, CrashRecoveryService
├── ui/
│   ├── shell.py        # AppHeader + StageRail + stage stack + FooterBar
│   ├── main_window.py  # Main orchestration, stage wiring, splitter persistence
│   ├── theme/          # ThemeEngine, tokens, QSS builder, icons
│   ├── components/     # Shared workbench widgets
│   └── widgets/        # Stage widgets and tool widgets
└── utils/          # Constants, formatters, platform helpers
```

Runtime state is created under `data/` and is local-only. Do not reintroduce tracked runtime artifacts such as `data/config.json`.

## Architecture

```text
UI -> Qt signals/slots -> Core managers/workers -> Services -> Data/filesystem
```

- `Database`, `ConfigService`, and `ThemeEngine` use singleton-style access
- dataclasses live in `src/data/models.py`
- background work happens in worker classes and reports back via Qt signals

## Non-Negotiable Invariants

### Threading

- never manipulate widgets from worker threads
- worker threads communicate with the UI through Qt signals/slots only
- preserve the existing threading boundaries in `src/core/`

### Auth

- one persistent Playwright profile directory via `auth.profile_dir`
- one Netscape cookie file via `auth.cookies_file_path`
- do not introduce per-site cookie files or `storage_state.json`
- browser close without cookies is a warning path, not a crash path

### Workbench Contracts

- keep the stage keys stable: `ingest`, `prepare`, `organize`, `export`
- keep `ThemeEngine` public usage stable
- keep `get_icon(name, color=None)` stable
- keep shared splitter persistence on `window.splitter_sizes`

### Anti-Ban

- only polite pacing, retry, and rate-limit controls
- no stealth or evasion tactics

## Code Style

- imports: stdlib -> third-party -> local
- type hints on public methods
- `logger = logging.getLogger(__name__)`
- use `logger.exception()` when preserving tracebacks matters
- PascalCase classes, snake_case functions, `_private` helpers, UPPER_SNAKE constants
- Qt signals use `noun_verb`
- Qt slots use `_on_*`

## Testing And Verification

- run `pytest -q` before claiming the repo is green
- when changing shell or theme behavior, also run:

```bash
pytest tests/test_main_window_workbench.py -v
pytest tests/test_theme_tokens.py tests/test_qss_builder.py tests/test_icons.py -v
```

- when changing UI structure, do a smoke run with `python run.py` when the environment allows it

## Gotchas

- no linter is configured; do not assume `ruff`, `flake8`, or `mypy` are part of the workflow
- `ffmpeg` is required for Convert, Trim, and some organize flows
- Playwright browser binaries must be installed separately
- the repo may contain unrelated local media files; do not delete or modify them unless explicitly asked

## Documentation

- `docs/INDEX.md` is the docs entry point
- `docs/ARCHITECTURE.md` explains the current runtime structure
- `docs/UI_WORKBENCH.md` is the source of truth for shell anatomy and Signal Deck rules
- `docs/AGENT_GUIDE.md` is the quick map for common code changes
- `MEMORY.md` is the working memory file
- `ERRORS.md` is the running incident log
