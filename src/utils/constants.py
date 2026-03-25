"""Application constants."""

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

# File filters
URL_FILE_FILTER = "Text Files (*.txt *.md);;All Files (*)"
VIDEO_FILE_FILTER = (
    "Video Files (*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv *.m4v);;All Files (*)"
)

# Database
DB_VERSION = 3  # Incremented for conversion_jobs table

# Conversion defaults
DEFAULT_CRF = 23
MIN_CRF = 0
MAX_CRF = 51
DEFAULT_PRESET = "medium"
CONVERSION_PRESETS = [
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
]
OUTPUT_CODECS = ["h264", "hevc"]

# Supported video extensions for Sort/Convert
SUPPORTED_VIDEO_EXTENSIONS = [
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".webm",
    ".flv",
    ".wmv",
    ".m4v",
    ".mpeg",
    ".mpg",
    ".3gp",
    ".ogv",
    ".ts",
    ".mts",
    ".m2ts",
]

# Hardware encoder names
HARDWARE_ENCODERS = {
    "nvenc": {"h264": "h264_nvenc", "hevc": "hevc_nvenc"},  # NVIDIA
    "amf": {"h264": "h264_amf", "hevc": "hevc_amf"},  # AMD
    "qsv": {"h264": "h264_qsv", "hevc": "hevc_qsv"},  # Intel
    "videotoolbox": {"h264": "h264_videotoolbox", "hevc": "hevc_videotoolbox"},  # macOS
}

# Trim defaults
DEFAULT_TRIM_SUFFIX = "_trimmed"
TRIM_LOSSLESS_DEFAULT = True
