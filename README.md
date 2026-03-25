# yt-dlp GUI

Cross-platform PyQt6 desktop app for downloading, preparing, organizing, and exporting media with yt-dlp. The app now uses a four-stage workbench shell and the Signal Deck visual system.

Current version: `1.0.0`

## What It Does

- `Ingest` collects URLs, imported lists, auth state, queue setup, and extraction tools.
- `Prepare` groups Convert, Trim, and Metadata workflows in one stage.
- `Organize` groups Sort, Rename, and Match workflows in one stage.
- `Export` holds run summary, recent activity, and app-level settings.

Core behavior stays the same:

- yt-dlp downloads with queue management and session persistence
- Playwright-based authentication with one persistent browser profile and one Netscape cookie file
- FFmpeg-backed conversion and trimming workflows
- metadata-driven organize tools for sorting, renaming, and matching
- dark and light Signal Deck themes through the existing `ThemeEngine`

## Requirements

- Python `3.10+`
- `ffmpeg` installed and available on `PATH`
- Playwright browsers installed after dependency setup

## Setup

Use the project virtual environment from the repo root (POSIX):

```bash
source .venv/bin/activate
```

If it does not exist yet (POSIX):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python3 -m playwright install
```

## Run

Development entry point (POSIX):

```bash
source .venv/bin/activate
python3 run.py
```

Packaged outputs (built with `pyinstaller ytdlp_gui.spec`):

- `yt-dlp-gui` — executable (Windows / Linux)
- `yt-dlp GUI.app` — application bundle (macOS)

## Test

Run the full suite (POSIX):

```bash
source .venv/bin/activate
pytest -q
```

Useful focused commands (POSIX):

```bash
source .venv/bin/activate
pytest tests/test_main_window_workbench.py -v
pytest tests/test_theme_tokens.py tests/test_qss_builder.py -v
```

## Build

Create the packaged app with PyInstaller (POSIX):

```bash
source .venv/bin/activate
pyinstaller ytdlp_gui.spec
```

## Runtime Data

Runtime state is created under `data/` and is not part of the shipped repo. Important examples:

- `data/config.json`
- `data/ytdlp_gui.db`
- `data/logs/`

## Documentation

- [docs/INDEX.md](docs/INDEX.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/UI_WORKBENCH.md](docs/UI_WORKBENCH.md)
- [docs/AUTH_PLAYWRIGHT.md](docs/AUTH_PLAYWRIGHT.md)
- [MEMORY.md](MEMORY.md)
