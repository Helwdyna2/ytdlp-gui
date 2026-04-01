# Session Log

## 2026-04-01

- Added `SavedTaskService` as a thin orchestration layer over `SavedTaskRepository` with save, recoverable-list, unfinished-list, and delete helpers.
- Wired startup to build the saved-task repository/service alongside the existing session services and passed the service into `MainWindow` via an optional constructor argument.
- Kept Task 2 scoped to wiring only; the Saved Tasks UI surfaces remain for Task 6.
- Reworked the focused window test to assert constructor compatibility without instantiating the full trim/settings UI stack, which was crashing in headless Qt teardown.
- Verified the saved-task repository/service path and the startup wiring helper with the focused pytest slice.
- Added an output resolution selector to the Convert page with orientation-aware presets, a divider, and opposite-orientation override options.
- Persisted the selected resolution in config, passed it through `ConversionConfig`, and applied it in `FFmpegWorker` with an FFmpeg scale-and-pad filter.
- Added focused tests for the new Convert-page behavior and FFmpeg command generation.
- Mixed-orientation batches currently auto-pick the majority orientation and use the first detected file as the tiebreaker.
- Verified the pasted PR #2 CodeRabbit findings against the current `codex/trim-refresh-scrub-controls` branch and fixed only the live `.gitignore` issue.
- Removed the malformed `+pytest-of-*/` diff marker, kept a single valid `pytest-of-*/` ignore entry, and preserved `trim_quick_session.json` as its own ignore line.
- The remaining pasted comments referenced shortcut/timeline/test code paths that are not present on this branch, so no additional code changes were needed.
- Refreshed the Trim page toward a denser LosslessCut-style editor with a custom segment timeline, compact segment cards, denser preview transport controls, and a new `Remove Video` action.
- Added persisted Trim scrub-step settings plus configurable Trim shortcuts in Settings for split, delete selected segment, label selected segment, and close current video.
- Fixed libmpv decoder-status string handling so observed decoder labels decode cleanly instead of showing garbled text.
- Added Trim dirty-state prompting for close/remove, page-scoped shortcut handling, and focused regression coverage for the preview, timeline, scrub controller, settings, and Trim page flows.
- Verified PR #1 review comments against the current `fix/convert-preflight-readiness` branch and fixed the valid Convert-page issues only.
- File-list folder scans now emit their loading-state transition as soon as the scan starts, so queue readiness updates immediately instead of waiting for completion/error.
- Skip-matching readiness now refreshes when the checkbox or selected output resolution changes, and the match check now includes selected video resolution for `h264`/`hevc`/`vp9`.
- Added focused Convert-page tests covering the folder-scan busy transition and the skip-status/regression path for resized outputs.
- Wrote the Saved Tasks design spec in `docs/superpowers/specs/2026-04-01-saved-tasks-design.md` covering unified task persistence, Convert-first queue recovery, immediate pause behavior, and phased adapter rollout for other tools.
- Chose a shared Saved Tasks shell with per-tool adapters rather than a universal runtime engine, so Convert can ship first without rewriting Trim and Download internals.
- Wrote the implementation plan in `docs/superpowers/plans/2026-04-01-saved-tasks-convert-v1.md`, scoping the first delivery to shared Saved Tasks infrastructure plus Convert pause/resume, queue editing, startup restore, and processed-file detection.
