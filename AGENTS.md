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

Tests live in `tests/` and follow the source layout with `test_*.py` files. Design references are in `docs/` and `UI/`. Runtime data under `data/` is generated locally and should not be committed.

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

## Commit & Pull Request Guidelines
Recent history mixes short maintenance commits (`Cleanup`, `Redesign`) with conventional messages such as `feat(ui): ...`. Prefer the latter: `feat(area): summary`, `fix(area): summary`, or a concise imperative maintenance message when scope is obvious. PRs should include a short description, linked issue if applicable, test notes, and screenshots for UI changes.
