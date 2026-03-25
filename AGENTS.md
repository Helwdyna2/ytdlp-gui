# AGENTS.md

Single source of truth for AI coding agents working in the `yt-dlp GUI` repository. Keep this file current when setup steps, invariants, architecture, or recurring gotchas change. `CLAUDE.md` and `.github/copilot-instructions.md` should stay as thin pointers to this file, not parallel instruction sets.

## Project Overview

`yt-dlp GUI` is a cross-platform PyQt6 desktop workbench for downloading, preparing, organizing, and exporting media with `yt-dlp`. The app uses a four-stage shell and the Signal Deck visual system.

Canonical stage responsibilities:

- `ingest`: Add Media, Extract URLs, auth state, queue setup, output config
- `prepare`: Convert, Trim, Metadata
- `organize`: Sort, Rename, Match
- `export`: run summary, recent activity, settings

Core behavior includes:

- queue-managed `yt-dlp` downloads with session persistence
- Playwright-based authentication with one persistent browser profile and one Netscape cookie file
- FFmpeg-backed conversion and trimming
- metadata-driven organize tools
- Signal Deck dark and light themes through `ThemeEngine`

## Environment Setup

Always work from the repository root with the project virtual environment active:

```bash
source .venv/bin/activate
```

If the environment does not exist yet:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install
```

Notes:

- all commands below assume the venv is active
- if `python` is missing, the venv is probably not active; use `python3 -m venv .venv` to create it, then reactivate
- `ffmpeg` must already be installed on `PATH`
- Playwright browser binaries are installed separately from Python deps

## Common Commands

```bash
python run.py
pip install -e ".[dev]"
python -m playwright install
pytest -q
pytest tests/test_file.py -v
pytest -k "pattern" -v
pyinstaller ytdlp_gui.spec
```

Focused verification commands:

```bash
pytest tests/test_main_window_workbench.py -v
pytest tests/test_ingest_stage_widget.py tests/test_prepare_stage_widget.py tests/test_organize_stage_widget.py tests/test_export_stage_widget.py -v
pytest tests/test_theme_tokens.py tests/test_qss_builder.py tests/test_icons.py -v
```

Manual smoke pass:

```bash
python run.py
```

## Entry Points And Code Map

Entry points:

- `run.py`: development entry point
- `main.py`: packaging-friendly top-level entry point
- `src/main.py`: initializes Qt application, services, theme, crash recovery, FFmpeg checks, and window restoration

Primary source map:

- `src/ui/main_window.py`: app orchestration, settings navigation, queue wiring, splitter persistence
- `src/ui/shell.py`: `AppHeader`, `StageRail`, stage stack, `FooterBar`
- `src/ui/widgets/ingest_stage_widget.py`: ingest composition
- `src/ui/widgets/prepare_stage_widget.py`: prepare composition
- `src/ui/widgets/organize_stage_widget.py`: organize composition
- `src/ui/widgets/export_stage_widget.py`: export composition
- `src/ui/theme/`: Signal Deck tokens, QSS builder, icon registry, theme engine
- `src/core/`: managers, workers, auth, extraction, organize, conversion logic
- `src/services/config_service.py`: config defaults and persistence
- `src/services/`: config, session restore, crash recovery
- `src/data/`: SQLite database, repositories, dataclasses
- `src/data/models.py`: persisted dataclasses

## Runtime Architecture

Primary flow:

`UI -> Qt signals/slots -> core managers/workers -> services -> database/config/filesystem`

Key layering rules:

- UI code lives in `src/ui/`
- business logic and background work live in `src/core/`
- persisted app state lives in `src/services/` and `src/data/`
- `Database`, `ConfigService`, and `ThemeEngine` use singleton-style access
- repositories wrap database access patterns

## Non-Negotiable Invariants

### Threading

- never manipulate widgets from worker threads
- worker threads must communicate back through Qt signals/slots only
- preserve existing threading boundaries in `src/core/`

### Workbench And UI Contracts

- keep the stage keys stable: `ingest`, `prepare`, `organize`, `export`
- settings stay inside the `export` stage, not top-level navigation
- preserve `ThemeEngine` public usage
- preserve `get_icon(name, color=None)`
- keep shared splitter persistence on `window.splitter_sizes`
- prefer reusing existing tool widgets and business logic over UI rewrites

Signal Deck rules:

- `src/ui/theme/tokens.py` is the token source of truth
- keep dark and light token keys in sync
- use semantic token roles instead of one-off widget colors
- `src/ui/theme/qss_builder.py` is the single stylesheet builder
- target stable object names/selectors in QSS instead of ad hoc inline styling
- prefer stage-centric icon names such as `ingest`, `prepare`, `organize`, and `export`

### Auth And Download Safety

- keep one persistent Playwright profile directory via `auth.profile_dir`
- keep one Netscape cookie file via `auth.cookies_file_path`
- do not add per-site cookie files
- do not add Playwright `storage_state.json` flows to the app
- browser close without cookies is a warning path, not a crash path
- keep auth validation based on exported cookies and registered domain suffixes
- anti-ban behavior is limited to polite pacing, rate limits, and retries
- do not introduce stealth or evasion behavior

Auth source files:

- `src/core/auth_worker.py`
- `src/core/auth_manager.py`
- `src/core/auth_types.py`
- `src/core/netscape_cookies.py`
- `src/core/site_auth.py`
- `src/ui/widgets/auth_status_widget.py`

### Runtime State

- runtime state under `data/` is local-only
- do not reintroduce tracked runtime artifacts such as `data/config.json`, `data/ytdlp_gui.db`, logs, local browser profiles, or generated metadata
- the repo may contain unrelated local media files; do not delete or modify them unless explicitly asked

## Configuration And Persistence

Config is persisted as JSON through `ConfigService`.

Important config sections:

- `window`: geometry, maximized state, `splitter_sizes`
- `appearance`: theme
- `download`: output dir, concurrency, overwrite, video-only, cookies path, filename template
- `extract_urls`: output dir, scroll limits, timing values
- `auth`: profile dir, cookie file path, last login URL
- `playwright`: selected browser engine
- `download_polite`: sleep, rate-limit, retry controls
- tool-specific sections: `convert`, `trim`, `rename`, `sort`, `match`, `ffmpeg`

Version source of truth:

- `pyproject.toml`
- `src/utils/constants.py`

Current version in repo: `1.0.0`

## Code Style And Change Guidance

- imports: stdlib, then third-party, then local
- add type hints on public methods
- use `logger = logging.getLogger(__name__)`
- use `logger.exception()` when preserving tracebacks matters
- PascalCase classes, snake_case functions, `_private` helpers, UPPER_SNAKE constants
- Qt signals use `noun_verb`
- Qt slots use `_on_*`
- preserve manager/service contracts when changing layout or presentation
- there is no configured lint step; do not assume `ruff`, `flake8`, or `mypy`

High-risk areas:

- `src/ui/main_window.py`: signal wiring, session recovery, stage orchestration
- settings UI: theme persistence, Playwright actions, polite-mode writes
- `src/core/` workers and managers: do not move widget logic into worker threads
- auth flow: keep the existing cookie export and warning semantics intact

## Testing And Verification

Minimum expectation before claiming the repo is green:

```bash
pytest -q
```

Run these in addition when relevant:

- shell, theme, or workbench changes: `pytest tests/test_main_window_workbench.py -v` and `pytest tests/test_theme_tokens.py tests/test_qss_builder.py tests/test_icons.py -v`
- stage composition changes: `pytest tests/test_ingest_stage_widget.py tests/test_prepare_stage_widget.py tests/test_organize_stage_widget.py tests/test_export_stage_widget.py -v`
- UI structure changes: do a smoke run with `python run.py` when the environment allows it

Manual smoke checklist:

- workbench minimum size and stage switching
- stage context updates
- shared splitter behavior
- settings navigation inside `export`
- activity drawer behavior
- dark/light Signal Deck switching

Known environment issues worth remembering:

- offscreen smoke launch has emitted `setHighDpiScaleFactorRoundingPolicy must be called before creating the QGuiApplication instance`
- offscreen smoke launch has also emitted `This plugin does not support setParent!`
- `tests/test_main_window_workbench.py` has previously crashed under PyQt with Python 3.14 during teardown in this environment; do not claim that test passed unless you ran it successfully yourself

## Build And Release

Build the packaged app with:

```bash
pyinstaller ytdlp_gui.spec
```

Before a release:

- confirm `pyproject.toml` and `src/utils/constants.py` agree on the version
- run `pytest -q`
- smoke test with `python run.py`
- confirm `ffmpeg` and Playwright flows still work on the target machine

## Troubleshooting

- tests fail immediately: activate the venv and run `pip install -e ".[dev]"`
- auth fails: run `python -m playwright install`, confirm the selected browser in Settings, and verify `auth.profile_dir` and `auth.cookies_file_path`
- convert/trim flows fail: verify `ffmpeg` is on `PATH`
- theme or layout state looks wrong: inspect or reset local `data/config.json`
- build issues: rebuild from a clean venv and rerun `pyinstaller ytdlp_gui.spec`

## Repo-Local Tooling Notes

- `.claude/skills/playwright-cli/` contains browser automation reference material for external tooling workflows
- those docs do not change the application auth model; app code must still use one persistent profile plus one Netscape cookie export file
- do not import multi-session browser management, per-site cookie files, or storage-state JSON patterns into production app behavior

## Documentation And Shared State Files

Keep agent-facing documentation current after significant workflow or architecture changes. `AGENTS.md` is the canonical instruction file. `CLAUDE.md` and `.github/copilot-instructions.md` should only redirect to it.

Reference docs still useful for deeper background:

- `docs/INDEX.md`
- `docs/ARCHITECTURE.md`
- `docs/UI_WORKBENCH.md`
- `docs/AUTH_PLAYWRIGHT.md`
- `docs/TESTING.md`
- `docs/TROUBLESHOOTING.md`
- `docs/BUILD_RELEASE.md`

Shared state files:

- `SESSIONS.md`: concise session history with date, identifier, scope, and outcome
- `MEMORY.md`: durable learnings, conventions, and recurring gotchas
- `ERRORS.md`: important tool, environment, or workflow failures worth follow-up

Rules for these files:

- every written entry must include an identifier such as `codex:YYYY-MM-DD:<topic>`
- prefer durable facts in `MEMORY.md`, not temporary chatter
- if a learning becomes broadly important, promote it into this `AGENTS.md`
- if any of these files grows beyond 200 lines, prune it and archive older material in a repo-appropriate archive location
