## 2026-03-17

- Offscreen smoke launch emitted `setHighDpiScaleFactorRoundingPolicy must be called before creating the QGuiApplication instance` during startup.
- Offscreen smoke launch also emitted `This plugin does not support setParent!` after the window came up under `QT_QPA_PLATFORM=offscreen`.
- `gh pr create` initially succeeded but printed shell interpolation errors because backticks in the PR body were evaluated by `zsh` inside double quotes. The PR body was corrected afterward with `gh pr edit`.

## 2026-03-18

- Verification command `python -m compileall ...` failed with `zsh: command not found: python`; this environment needs the repo venv activated or `python3` used explicitly.
- `source .venv/bin/activate && QT_QPA_PLATFORM=offscreen pytest -q tests/test_main_window_workbench.py` crashed with a PyQt/Python 3.14 bus error during teardown (`cleanup_qobject` / `dealloc_QApplication` in the stack), so full UI verification could not be completed in this environment.
