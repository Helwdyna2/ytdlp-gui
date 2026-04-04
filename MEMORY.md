# Project Memory

## Convert Page

- The Convert page reuses the existing `FFprobeWorker` scan for both source codec filtering and output-resolution orientation detection. Extend that shared metadata path instead of introducing a second probe flow.
- Output resolution presets are stored as `convert.resolution`. Use `"source"` for no resize, and concrete values like `1920x1080` to trigger a scale-and-pad filter in `FFmpegWorker`.
- Skip-matching output checks for `h264`, `hevc`, and `vp9` must compare the selected target resolution as well as codec/extension. Otherwise resized transcodes can be incorrectly treated as already matching and skipped.

## Saved Tasks

- Saved-task persistence is split between `src/data/repositories/saved_task_repository.py` and `src/services/saved_task_service.py`; UI entry points live in `src/ui/widgets/saved_tasks_dialog.py` and `src/ui/main_window.py`.
- `MainWindow.prompt_restore_latest_saved_task()` must only prompt for task types with a real restore implementation. Today that means `convert` only; prompting for other unfinished tasks creates a dead-end UX.
- `ConvertPage.restore_saved_task(...)` preserves persisted output paths via `_restored_output_paths`, so resumed Convert batches keep the saved output destinations instead of recomputing them from the current output-folder field.
- Resume semantics for Convert are intentionally conservative: only `pending` and `incomplete` queue items restart; `completed` stay done, `skipped` stay skipped, and `failed` items are not auto-rerun during restore.
- `JobCreationWorker` must emit `completed(jobs)` even when cancelled so `ConversionManager` can discard partial jobs, emit `all_completed`, and avoid wedging the Convert page during cancel/pause in the async job-creation phase.

## Saved Tasks

- Manual unfinished-task browsing lives in `src/ui/widgets/saved_tasks_dialog.py`, and `MainWindow` owns the File-menu entry plus dialog action handling.
- Only Convert currently has a full restore path. `MainWindow.restore_saved_task(...)` should route Convert payloads into `ConvertPage.restore_saved_task(...)`; other task types can switch tools in the shell, but they are not restored yet.
