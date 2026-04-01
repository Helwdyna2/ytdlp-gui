# Trim Editor

This repository now contains a LosslessCut-style editing workflow inside the existing `Trim` tool.

## What It Does

- loads a single video source into the embedded preview player
- plays, pauses, seeks, and scrubs through the file using libmpv render API
- splits the source into ordered segments
- lets you enable or disable segments instead of deleting them
- stores a label and comma-separated tags per segment
- exports enabled segments as separate outputs or as one merged output
- defaults to lossless stream-copy export and warns when copy boundaries are likely off-keyframe
- autosaves the current editing session and can restore it on reopen
- saves and loads explicit project files as JSON

## Main Implementation Areas

- UI host page: `src/ui/pages/trim_page.py`
- Preview widget: `src/ui/widgets/video_preview_widget.py`
- Segment list: `src/ui/widgets/segment_list_widget.py`
- Playback/render layer: `src/core/editor/mpv_binding.py`, `src/core/editor/playback_controller.py`, `src/core/editor/scrub_controller.py`
- Export planning/execution: `src/core/editor/export_planner.py`, `src/core/editor/export_manager.py`
- Persistence: `src/core/editor/project_store.py`, `src/core/editor/quick_session_store.py`
- Diagnostics: `src/core/editor/diagnostics.py`
- Keyframe analysis: `src/core/editor/keyframe_probe_worker.py`

## User Workflow

1. Open `Trim`.
2. Load a video file.
3. Scrub or play to a point of interest.
4. Use `Split at Current` to create segments.
5. Select a segment to edit its range, label, tags, or enabled state.
6. Choose export mode:
   - `Separate Outputs`
   - `Merged Output`
7. Keep `Lossless export` enabled unless you explicitly want re-encoding.
8. Review any warnings shown before export.
9. Export.

## Persistence

- Quick session autosave is stored in `data/trim_quick_session.json`.
- Saved projects are JSON files, typically using the `*.cutproj.json` suffix.
- Project/session data includes source path, duration, ordered segments, selection, export mode, export target, lossless preference, keyframe timestamps, and basic source metadata.

## Important Technical Constraints

- The preview path is libmpv render API inside `QOpenGLWidget`. Do not switch the main path back to `wid`-based embedding.
- `src/main.py` sets a default `QSurfaceFormat` before creating `QApplication`. That is required for the current OpenGL render path.
- Headless tests skip libmpv initialization via `QT_QPA_PLATFORM=offscreen`. That keeps CI/local tests stable, but it means playback still needs manual desktop verification.
- Lossless export is intentionally conservative. Warnings are shown when keyframe safety is unknown or likely risky.

## Current Validation Status

The editor architecture is implemented and the focused model/planner/persistence/page tests pass. The remaining confidence gap is live desktop validation of the real player/export path on macOS, Linux, and Windows builds.
