# Project Memory

## Convert Page

- The Convert page reuses the existing `FFprobeWorker` scan for both source codec filtering and output-resolution orientation detection. Extend that shared metadata path instead of introducing a second probe flow.
- Output resolution presets are stored as `convert.resolution`. Use `"source"` for no resize, and concrete values like `1920x1080` to trigger a scale-and-pad filter in `FFmpegWorker`.
