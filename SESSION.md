# Session Log

## 2026-04-01

- Added an output resolution selector to the Convert page with orientation-aware presets, a divider, and opposite-orientation override options.
- Persisted the selected resolution in config, passed it through `ConversionConfig`, and applied it in `FFmpegWorker` with an FFmpeg scale-and-pad filter.
- Added focused tests for the new Convert-page behavior and FFmpeg command generation.
- Mixed-orientation batches currently auto-pick the majority orientation and use the first detected file as the tiebreaker.
