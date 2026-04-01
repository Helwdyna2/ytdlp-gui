# Session Log

## 2026-04-01

- Added an output resolution selector to the Convert page with orientation-aware presets, a divider, and opposite-orientation override options.
- Persisted the selected resolution in config, passed it through `ConversionConfig`, and applied it in `FFmpegWorker` with an FFmpeg scale-and-pad filter.
- Added focused tests for the new Convert-page behavior and FFmpeg command generation.
- Mixed-orientation batches currently auto-pick the majority orientation and use the first detected file as the tiebreaker.
- Verified PR #1 review comments against the current `fix/convert-preflight-readiness` branch and fixed the valid Convert-page issues only.
- File-list folder scans now emit their loading-state transition as soon as the scan starts, so queue readiness updates immediately instead of waiting for completion/error.
- Skip-matching readiness now refreshes when the checkbox or selected output resolution changes, and the match check now includes selected video resolution for `h264`/`hevc`/`vp9`.
- Added focused Convert-page tests covering the folder-scan busy transition and the skip-status/regression path for resized outputs.
