# Architecture

## Overview

The app is a PyQt6 desktop workbench for yt-dlp workflows. UI code lives in `src/ui/`, business logic in `src/core/`, persistence in `src/data/`, and cross-cutting state/services in `src/services/`.

The top-level runtime flow is:

`UI -> Qt signals/slots -> managers/workers -> services -> database/config/filesystem`

## Entry Points

- `run.py` runs the app from source in development
- `main.py` is the packaging-friendly top-level entry point
- `src/main.py` initializes services, theme, and the Qt application

## Layers

### UI

- `src/ui/main_window.py` owns the main window, shell wiring, stage registration, and app-level orchestration
- `src/ui/shell.py` owns the persistent shell regions: header, stage rail, content stack, footer
- `src/ui/widgets/` contains stage widgets and tool widgets
- `src/ui/components/` contains reusable themed building blocks
- `src/ui/theme/` contains tokens, QSS generation, icon registry, and the theme engine

### Core

- `src/core/download_manager.py` coordinates downloads and emits progress/log signals
- auth, matching, extraction, trimming, and conversion work stays in the core layer and worker classes
- worker threads must talk back to widgets through Qt signals only

### Services

- `ConfigService` persists JSON config and default values
- `SessionService` persists and restores download sessions
- crash recovery and app startup services live here too

### Data

- `src/data/database.py` provides the SQLite database singleton
- repositories in `src/data/repositories/` wrap access patterns
- dataclasses in `src/data/models.py` carry persisted state

## Workbench Structure

The app is organized around four stage keys:

- `ingest`
- `prepare`
- `organize`
- `export`

`MainWindow` registers one widget per stage through `Shell.register_stage()`. Each stage owns its internal tool composition, but the outer navigation contract stays shared.

## Shell Anatomy

- `AppHeader` shows current app/session context, queue stats, and settings access
- `StageRail` provides labeled stage navigation
- the stacked center area swaps stage widgets
- `FooterBar` shows dependency status and app version

Stages use a shared internal pattern:

- `StageContextStrip`
- `WorkspaceSurface`
- `InspectorPanel`
- optional `ActivityDrawer`
- a shared horizontal splitter between primary and inspector content

Splitter state is persisted in `window.splitter_sizes`.

## Auth And Download Invariants

- one persistent Playwright profile directory lives under `auth.profile_dir`
- one Netscape cookie export file lives under `auth.cookies_file_path`
- the app does not create per-site cookie files or `storage_state.json`
- browser close without cookies is treated as a warning path, not a crash path
- anti-ban behavior is limited to polite pacing, rate limits, and retries

## Threading Rules

- never manipulate widgets from worker threads
- worker threads communicate through signals/slots only
- shared state uses thread-safe patterns already established in the repo
- database access stays behind the existing database/repository setup
