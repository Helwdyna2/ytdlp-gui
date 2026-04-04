# Repository Guidelines

# Virtual Environment

Use the existing virtual environment always. If you need to create a new one, use `python -m venv .venv` and activate it with `source .venv/bin/activate` (Unix) or `.venv\Scripts\activate` (Windows). Then install dependencies with `pip install -r requirements-dev.txt`. Do not commit the virtual environment directory or any generated files under `data/`.

## Project Structure & Module Organization
The application is a Python desktop GUI built around `PyQt6`. Main entry points are `run.py` for development and `main.py` for packaged runs. Core code lives under `src/`:

- `src/ui/`: windows, pages, widgets, and theme/QSS code
- `src/core/`: download, auth, FFmpeg, matching, and worker logic
- `src/services/`: config, session, and crash recovery services
- `src/data/`: database models and repositories
- `src/utils/`: shared helpers and platform utilities

Saved-task recovery for the current Convert slice spans:

- `src/data/repositories/saved_task_repository.py` for persistence
- `src/services/saved_task_service.py` for orchestration
- `src/core/convert_saved_task.py` for queue-item serialization/detection helpers
- `src/ui/widgets/saved_tasks_dialog.py` and `src/ui/main_window.py` for manual/startup restore entry points
- `src/ui/pages/convert_page.py` for Convert-specific restore/resume behavior

Tests live in `tests/` and follow the source layout with `test_*.py` files. Design references are in `docs/` and `UI/`. Runtime data under `data/` is generated locally and should not be committed.

## Trim Editor Notes
The LosslessCut-style editor work lives inside the existing Trim tool rather than a separate app. Keep new editor-specific logic under `src/core/editor/` and let `src/ui/pages/trim_page.py` orchestrate the workflow.

- Preview playback uses libmpv render API through `QOpenGLWidget` in `src/ui/widgets/video_preview_widget.py`. Do not reintroduce mpv `wid`/native-child embedding as the primary path.
- The Trim timeline is now a custom-painted widget in `src/ui/widgets/trim_timeline_widget.py` that renders segment blocks, a playhead, and draggable selected-segment handles. Extend that widget for timeline UX changes instead of reverting to the older `superqt` range-slider pattern.
- If you touch playback bootstrap, preserve the `QSurfaceFormat.setDefaultFormat(...)` setup in `src/main.py` before `QApplication` creation. This is required for the embedded OpenGL render path, especially on macOS.
- Headless/offscreen tests intentionally skip libmpv initialization in `PlaybackController`. That keeps `pytest` stable under `QT_QPA_PLATFORM=offscreen` while the real app still uses libmpv on desktop runs.
- Decoder-status strings from libmpv property-change events must be decoded from the observed string pointer payload, not from the event data pointer directly, or the UI will show garbled decoder text.
- Editor export/persistence/diagnostics live in `src/core/editor/export_*`, `project_store.py`, `quick_session_store.py`, and `diagnostics.py`. Reuse those instead of extending the legacy one-range trim worker flow for editor features.
- Quick-session autosave writes `data/trim_quick_session.json`. Saved projects are JSON files chosen by the user, typically `*.cutproj.json`.
- Keyframe awareness currently comes from ffprobe via `src/core/editor/keyframe_probe_worker.py`. If you add copy-safety warnings or boundary logic, build on that data instead of inferring from playback alone.
- User-editable Trim bindings and the default scrub-step are configured in Settings under the `Trim & Shortcuts` section and persisted via `trim.shortcuts.*` plus `trim.playback.scrub_step_seconds`.

## Saved Tasks Notes

- The manual unfinished-task browser lives in `src/ui/widgets/saved_tasks_dialog.py`, and the File menu entry is owned by `src/ui/main_window.py`.
- Only Convert currently supports full saved-task restoration. Route saved Convert payloads through `MainWindow.restore_saved_task(...)` into `ConvertPage.restore_saved_task(...)`; other task types should stay on the generic shell-open path until their adapters exist.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate`: create and activate a local virtualenv
- `pip install -r requirements-dev.txt`: install runtime and dev dependencies
- `python run.py`: launch the app in development mode
- `pytest`: run the full test suite
- `pytest --cov=src`: run tests with coverage output
- `mypy src`: run type checks against the application code

`pyinstaller` is listed as a dev dependency, but there is no checked-in spec or build script yet. Add one before documenting a release build workflow.

## Coding Style & Naming Conventions
Follow existing Python style: 4-space indentation, type hints on new code, and short module docstrings. Use `snake_case` for modules, functions, and variables, and `PascalCase` for Qt widgets, managers, and data models. Keep UI code in `src/ui/`, business logic in `src/core/` or `src/services/`, and avoid mixing them. No formatter or linter config is committed; match the surrounding file style closely.

## Testing Guidelines
Use `pytest` and `pytest-qt` for GUI coverage. Name new tests `test_<feature>.py` and keep fixtures in `tests/conftest.py` when shared. Prefer focused unit tests for workers, services, and utility functions, plus page/widget tests for UI regressions. Run `pytest` before opening a PR; use `pytest tests/test_<module>.py` for targeted checks while iterating.

For the Trim editor stack, prefer this focused validation loop while iterating:

- `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/test_editor_models.py tests/test_scrub_controller.py tests/test_export_planner.py tests/test_project_store.py tests/test_trim_page.py tests/test_trim_timeline_widget.py tests/test_video_preview_widget.py -q`
- `python -m py_compile` on touched editor/playback/trim modules when making render-path or signal-flow changes

Passing headless tests is necessary but not sufficient for the player. Live desktop validation in `python run.py` is still required before calling playback/export behavior production-ready.

For the Saved Tasks / Convert recovery stack, prefer this focused validation loop while iterating:

- `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/test_saved_task_repository.py tests/test_convert_saved_task.py tests/test_convert_page.py tests/test_conversion_manager.py tests/test_main_window_workbench.py -q`
- `PYTHONPATH=. .venv/bin/python -m py_compile src/data/models.py src/data/database.py src/data/repositories/saved_task_repository.py src/services/saved_task_service.py src/core/convert_saved_task.py src/core/conversion_manager.py src/core/job_creation_worker.py src/ui/widgets/convert_queue_widget.py src/ui/widgets/saved_tasks_dialog.py src/ui/pages/convert_page.py src/ui/main_window.py src/main.py main.py`

## Architecture Constraints & Gotchas

- `MainWindow.prompt_restore_latest_saved_task()` must only prompt for task types with a real restore implementation. At this stage, only `convert` is restorable through the shared Saved Tasks shell.
- `ConvertPage.restore_saved_task(...)` preserves persisted output paths via `_restored_output_paths`; do not recompute them away during restore/resume work.
- Convert resume is intentionally conservative: only `pending` and `incomplete` items restart automatically. `completed` remain done, `skipped` remain skipped, and `failed` are not auto-rerun on restore.
- `JobCreationWorker` cancellation must still end in a terminal manager callback. If you change async job creation, preserve the path where `ConversionManager` can emit `all_completed` after a cancel/pause during job creation, or the Convert UI will stay wedged in its disabled/running state.

## Commit & Pull Request Guidelines
Recent history mixes short maintenance commits (`Cleanup`, `Redesign`) with conventional messages such as `feat(ui): ...`. Prefer the latter: `feat(area): summary`, `fix(area): summary`, or a concise imperative maintenance message when scope is obvious. PRs should include a short description, linked issue if applicable, test notes, and screenshots for UI changes.
