## 1. Current codebase summary

- The app is a PyQt6 multi-tool desktop shell rooted in `src/ui/main_window.py` and `src/ui/shell.py`.
- Long-running media work already uses Qt managers plus worker threads in `src/core/`.
- The existing Trim tool is present in navigation, but today it behaves more like a single-range FFmpeg cutter than an editor.
- FFmpeg and ffprobe are already first-class utilities via `src/utils/ffmpeg_utils.py`, `src/core/trim_worker.py`, and `src/core/ffprobe_worker.py`.
- Settings live in JSON through `src/services/config_service.py`; app/session persistence patterns mix JSON config and SQLite-backed repositories.

## 2. Fit analysis against the research handoff

- Playback fits conceptually because the repo already uses mpv for preview, but the current `wid`-embedding approach is not the right long-term base for smooth editor playback.
- Segment editing does not exist yet as a domain model; the repo currently stores only one active start/end range.
- Export can reuse the existing FFmpeg worker pattern, but the old `TrimManager` needed a small extension to support multiple distinct output paths.
- ffprobe reuse is strong for open-time media analysis, but keyframe/thumbnails/waveform work should be layered in later.
- JSON project and quick-session persistence fit the repo better than a new SQLite editor schema.

## 3. Recommended integration strategy

- Keep the feature inside the existing `trim` tool instead of creating a new app or shell section.
- Introduce feature-specific editor logic under `src/core/editor/` so the new segment model does not over-expand `src/data/models.py`.
- Reuse existing page, settings, FFmpeg, ffprobe, logging, and worker patterns where they already fit.
- Defer large-scale package reorganization from the research handoff until playback quality is proven.

## 4. Repo-specific architecture proposal

- `src/ui/pages/trim_page.py` should remain the host page for the editing workflow.
- Playback should evolve behind the current preview widget boundary, with libmpv integration living in `src/core/editor/` and the render surface exposed through `src/ui/widgets/video_preview_widget.py`.
- Segment editing should use a feature-local session model rather than extending the current trim dataclasses directly.
- Separate-output export should be the first real editor export path; merged export should come after copy-safety and boundary warnings are working.
- Quick-session persistence should be stored as JSON in app data, and saved projects should be JSON files chosen by the user.

## 5. File-level plan

Files/modules to modify

- `src/ui/pages/trim_page.py`
- `src/ui/widgets/video_preview_widget.py`
- `src/ui/widgets/trim_timeline_widget.py`
- `src/ui/main_window.py`
- `src/core/trim_manager.py`
- `src/core/ffprobe_worker.py`
- `src/services/config_service.py`

Files/modules to create

- `src/core/editor/__init__.py`
- `src/core/editor/models.py`
- `src/core/editor/mpv_binding.py`
- `src/core/editor/playback_controller.py`
- `src/core/editor/scrub_controller.py`
- `src/core/editor/project_store.py`
- `src/core/editor/quick_session_store.py`
- `src/ui/widgets/segment_list_widget.py`

## 6. Phase plan

Prototype milestone

- Goal: prove smooth playback and responsive seeking inside the existing Trim page.
- Success criteria: one loaded file can play, pause, seek, and scrub without the page freezing.

Editing milestone

- Goal: move Trim from one active range to an ordered segment session model.
- Success criteria: split, select, disable, and label segments in a single source.

Export milestone

- Goal: export enabled segments as separate outputs with lossless copy as the default.
- Success criteria: multiple enabled segments produce separate outputs without filename collisions.

Persistence milestone

- Goal: reopen editing state through quick-session JSON and later saved project JSON.
- Success criteria: active source, segments, selection, and settings survive reopen.

Polish milestone

- Goal: add keyframe-aware warnings, diagnostics, and deeper playback hardening.
- Success criteria: off-keyframe copy risks are visible before export and playback health is observable in-app.

## 7. Risks and unknowns

- Embedded playback quality is still the highest-risk area in this repo.
- The current Trim feature had placeholder-level UI wiring, so part of the work is turning it into a true live tool first.
- macOS/PyQt test stability is weak locally, so GUI verification may need more environment-specific handling than pure unit tests.
- Bundled libmpv and cross-platform packaging should wait until the playback prototype is validated.

## 8. Approval-gated decisions

- Whether to keep the user-facing name as `Trim` or rename it to something closer to `Edit`.
- Whether re-encode fallback stays fully manual, which is the recommended default.
- Whether bundled FFmpeg/libmpv distribution is in scope for the first shipping version of this feature.

## 9. Final recommendation

- Build on the existing Trim tool, prove playback and scrubbing first, and keep the first shipping export path to single-source separate outputs before attempting merged export or deeper analysis features.
