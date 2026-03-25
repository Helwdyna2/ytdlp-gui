# Config

Configuration is persisted as JSON by `ConfigService`.

## Important Sections

### `window`

- `width`
- `height`
- `x`
- `y`
- `maximized`
- `splitter_sizes`

### `appearance`

- `theme`

### `download`

- `output_dir`
- `concurrent_limit`
- `force_overwrite`
- `video_only`
- `cookies_path`
- filename template settings

### `extract_urls`

- output directory
- scroll limits
- timing values

### `auth`

- `profile_dir`
- `cookies_file_path`
- `last_login_url`

### `playwright`

- selected browser engine

### `download_polite`

- request pacing
- rate limit
- retry settings

### tool-specific sections

- `convert`
- `trim`
- `rename`
- `sort`
- `match`
- `ffmpeg`

## Defaults

Defaults live in `src/services/config_service.py`.
