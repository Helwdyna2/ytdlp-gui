# Project Memory

## Convert Page

- The Convert page reuses the existing `FFprobeWorker` scan for both source codec filtering and output-resolution orientation detection. Extend that shared metadata path instead of introducing a second probe flow.
- Output resolution presets are stored as `convert.resolution`. Use `"source"` for no resize, and concrete values like `1920x1080` to trigger a scale-and-pad filter in `FFmpegWorker`.

## Trim Editor

- The Trim screen now uses a custom-painted timeline in `src/ui/widgets/trim_timeline_widget.py` instead of the old `superqt` range-slider-first approach. Extend that widget for segment-block, playhead, or handle interactions rather than reintroducing the previous slider UI.
- Trim shortcut bindings and the default scrub-step live in config under `trim.shortcuts.*` and `trim.playback.scrub_step_seconds`, with editing exposed through the `Trim & Shortcuts` settings section.
- libmpv `MPV_FORMAT_STRING` property-change payloads for decoder status need to be dereferenced as `char **` before UTF-8 decoding in `PlaybackController`; treating the event data as a direct `c_char_p` produces garbled decoder labels.
