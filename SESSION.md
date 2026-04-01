# Session Log

## 2026-04-01

- Added an output resolution selector to the Convert page with orientation-aware presets, a divider, and opposite-orientation override options.
- Persisted the selected resolution in config, passed it through `ConversionConfig`, and applied it in `FFmpegWorker` with an FFmpeg scale-and-pad filter.
- Added focused tests for the new Convert-page behavior and FFmpeg command generation.
- Mixed-orientation batches currently auto-pick the majority orientation and use the first detected file as the tiebreaker.
- Refreshed the Trim page toward a denser LosslessCut-style editor with a custom segment timeline, compact segment cards, denser preview transport controls, and a new `Remove Video` action.
- Added persisted Trim scrub-step settings plus configurable Trim shortcuts in Settings for split, delete selected segment, label selected segment, and close current video.
- Fixed libmpv decoder-status string handling so observed decoder labels decode cleanly instead of showing garbled text.
- Added Trim dirty-state prompting for close/remove, page-scoped shortcut handling, and focused regression coverage for the preview, timeline, scrub controller, settings, and Trim page flows.
