# Configuration Reference

Complete reference for all configuration options in yt-dlp GUI.

## Configuration File Location

The configuration is stored in `data/config.json` (relative to the application directory).

## ConfigService API

```python
# Get a value
value = config.get('section.key', default_value)

# Set a value
config.set('section.key', value)

# Get entire section
section = config.get_section('download')

# Set entire section
config.set_section('download', {'output_dir': '/path', ...})

# Save immediately
config.save()

# Queue debounced save (for bursty UI updates)
config.queue_save(delay_ms=150)
```

## Configuration Sections

### window

Window geometry and state.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `width` | int | 1000 | Window width in pixels |
| `height` | int | 700 | Window height in pixels |
| `x` | int? | null | Window X position (null = default) |
| `y` | int? | null | Window Y position (null = default) |
| `splitter_sizes` | list[int] | [450, 550] | Sidebar/content splitter sizes |
| `maximized` | bool | false | Window maximized state |

### dialogs

Dialog state.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `last_dir` | str | "" | Last used directory for file dialogs |

### download

Download settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `output_dir` | str | "" | Default output directory |
| `concurrent_limit` | int | 3 | Max concurrent downloads (1-20) |
| `force_overwrite` | bool | false | Overwrite existing files |
| `video_only` | bool | false | Download video only (no audio) |
| `cookies_path` | str | "" | Path to cookies file |
| `filename_templates` | dict | {} | Domain-specific filename templates |
| `default_template` | str | "%(title)s" | Default yt-dlp filename template |

### behavior

Application behavior settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `auto_save_interval_ms` | int | 5000 | Auto-save interval in milliseconds |
| `debounce_parse_ms` | int | 300 | Debounce delay for URL parsing |
| `log_max_lines` | int | 1000 | Max log entries to display |
| `confirm_on_exit` | bool | true | Confirm before exiting with active downloads |
| `clear_completed_delay_ms` | int | 2000 | Delay before clearing completed items |
| `download_log_auto_scroll` | bool | true | Auto-scroll download log |

### convert

Video conversion settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `output_dir` | str | "" | Default output directory for conversions |
| `codec` | str | "libx264" | Output codec (libx264, libx265) |
| `crf` | int | 23 | Quality (0-51, lower = better) |
| `preset` | str | "medium" | Encoding speed preset |
| `use_hardware_accel` | bool | false | Use hardware acceleration |

### trim

Video trimming settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `mode` | str | "single" | Trim mode ("single" or "batch") |
| `single_lossless` | bool | true | Lossless trim for single mode |
| `single_output_dir` | str | "" | Output directory for single trim |
| `batch_lossless` | bool | true | Lossless trim for batch mode |
| `batch_output_dir` | str | "" | Output directory for batch trim |
| `global_start_offset` | float | 0.0 | Global start offset in seconds |
| `global_end_offset` | float | 0.0 | Global end offset in seconds |

### rename

File renaming settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `last_folder` | str | "" | Last folder used for rename |
| `find_text` | str | "" | Text to find |
| `replace_text` | str | "" | Text to replace with |
| `case_sensitive` | bool | false | Case-sensitive find/replace |
| `use_regex` | bool | false | Use regex for find/replace |

### sort

Video sorting settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `last_source_folder` | str | "" | Last source folder scanned |
| `last_dest_folder` | str | "" | Last destination folder |
| `use_copy` | bool | false | Copy instead of move files |
| `preserve_subfolders` | bool | true | Preserve folder structure |
| `criteria_order` | list[str] | ["fps", "resolution", "orientation", "codec", "bitrate"] | Sort criteria order |
| `criteria_enabled` | dict | See below | Enabled status for each criterion |

Default `criteria_enabled`:
```json
{
    "fps": true,
    "resolution": true,
    "orientation": true,
    "codec": false,
    "bitrate": false
}
```

### match

Database matching settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `last_folder` | str | "" | Last folder scanned |
| `search_porndb` | bool | true | Search ThePornDB |
| `search_stashdb` | bool | true | Search StashDB |
| `porndb_first` | bool | true | Prioritize ThePornDB results |
| `preserve_tags` | bool | true | Preserve position tags in filenames |
| `include_already_named` | bool | false | Include already-named files |
| `custom_studios` | list[str] | [] | Custom studio names |
| `skip_keywords` | list[str] | [] | Keywords to skip in parsing |
| `cookies_dir` | str | "" | Browser profile directory |

### extract_urls

URL extraction settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `output_dir` | str | "" | Output directory for extracted URLs |
| `auto_scroll_enabled` | bool | true | Auto-scroll during extraction |
| `max_scrolls` | int | 200 | Maximum scroll attempts |
| `idle_limit` | int | 5 | Idle timeout in seconds |
| `delay_ms` | int | 800 | Delay between actions in milliseconds |
| `max_bounce_attempts` | int | 3 | Maximum page reloads |

### auth

Authentication settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `profile_dir` | str | "" | Playwright browser profile directory |
| `cookies_file_path` | str | "" | Path to export cookies |
| `last_login_url` | str | "" | Last URL used for login |

### playwright

Playwright settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `browser` | str | "chromium" | Browser to use |

### ffmpeg

FFmpeg settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `warning_dismissed` | bool | false | FFmpeg warning dismissed |

### download_polite

Download politeness settings (rate limiting, retries).

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `sleep_requests_seconds` | float | 0.0 | Sleep between requests |
| `min_sleep_interval_seconds` | float | 0.0 | Minimum sleep interval |
| `max_sleep_interval_seconds` | float | 0.0 | Maximum sleep interval |
| `limit_rate` | str | "" | Rate limit (e.g., "1M") |
| `retries` | int | 10 | Number of retries |

#### retry_sleep_http

HTTP retry sleep configuration.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `mode` | str | "off" | Sleep mode ("off", "linear", "exp") |
| `start` | float | 0.0 | Start value in seconds |
| `end` | float | 0.0 | End value in seconds |
| `step` | float | 1.0 | Step for linear mode |
| `base` | float | 2.0 | Base for exponential mode |

#### retry_sleep_fragment

Fragment retry sleep configuration. Same structure as `retry_sleep_http`.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `retry_sleep_fragment_enabled` | bool | false | Enable fragment retry sleep |

## Constants

Application constants are defined in `src/utils/constants.py`:

```python
# Application info
APP_NAME = "yt-dlp GUI"
APP_VERSION = "1.0.0"

# UI defaults
DEFAULT_WINDOW_WIDTH = 1000
DEFAULT_WINDOW_HEIGHT = 700
DEFAULT_SPLITTER_SIZES = [450, 550]

# Download defaults
DEFAULT_CONCURRENT_LIMIT = 3
MIN_CONCURRENT_LIMIT = 1
MAX_CONCURRENT_LIMIT = 20
DEFAULT_FORCE_OVERWRITE = False
DEFAULT_VIDEO_ONLY = False

# Behavior settings
AUTO_SAVE_INTERVAL_MS = 5000
DEBOUNCE_PARSE_MS = 300
LOG_MAX_LINES = 1000

# yt-dlp defaults
DEFAULT_FORMAT = "bestvideo+bestaudio/best"
VIDEO_ONLY_FORMAT = "bestvideo"
DEFAULT_MERGE_FORMAT = "mp4"

# Conversion defaults
DEFAULT_CRF = 23
MIN_CRF = 0
MAX_CRF = 51
DEFAULT_PRESET = "medium"
CONVERSION_PRESETS = ["ultrafast", "superfast", "veryfast", "faster", "fast",
                      "medium", "slow", "slower", "veryslow"]
OUTPUT_CODECS = ["h264", "hevc"]

# Hardware encoders
HARDWARE_ENCODERS = {
    "nvenc": {"h264": "h264_nvenc", "hevc": "hevc_nvenc"},      # NVIDIA
    "amf": {"h264": "h264_amf", "hevc": "hevc_amf"},            # AMD
    "qsv": {"h264": "h264_qsv", "hevc": "hevc_qsv"},            # Intel
    "videotoolbox": {"h264": "h264_videotoolbox", "hevc": "hevc_videotoolbox"},  # macOS
}

# Trim defaults
DEFAULT_TRIM_SUFFIX = "_trimmed"
TRIM_LOSSLESS_DEFAULT = True

# Supported video extensions
SUPPORTED_VIDEO_EXTENSIONS = [".mp4", ".mkv", ".avi", ".mov", ".webm",
                               ".flv", ".wmv", ".m4v", ".mpeg", ".mpg",
                               ".3gp", ".ogv", ".ts", ".mts", ".m2ts"]
```

## Database Schema Version

```python
DB_VERSION = 3  # Current database schema version
```

## See Also

- [Architecture Overview](./ARCHITECTURE.md) - System architecture
- [Module Catalog](./MODULES.md) - Detailed module reference
- [Data Models](./DATA_MODELS.md) - Database schema and models
