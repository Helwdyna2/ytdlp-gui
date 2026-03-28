# Module Catalog

Detailed documentation for each module in yt-dlp GUI.

## Entry Points

### `main.py` (Production Entry)

**Location**: Repository root and `src/main.py`

**Purpose**: PyInstaller production entry point with single-instance support.

**Key Components**:
- `SingleApplication`: Ensures only one instance runs
- `setup_logging()`: Configures file and console logging
- `check_crash_recovery()`: Detects and offers session recovery
- `check_ffmpeg_installation()`: Warns if FFmpeg is missing
- `main()`: Main application initialization

```python
class SingleApplication(QApplication):
    """Single-instance wrapper using QLocalServer/QLocalSocket."""
    
    def is_primary(self) -> bool:
        """Check if this is the primary (first) application instance."""
        
    def cleanup(self):
        """Release the local server lock on shutdown."""
```

### `run.py` (Development Entry)

**Location**: Repository root

**Purpose**: Development entry point that imports from `src.main`.

## Core Module (`src/core/`)

### Download Manager & Worker

#### DownloadManager (`download_manager.py`)

**Responsibility**: Orchestrates download queue, spawns workers, aggregates progress.

**Signals**:
| Signal | Parameters | Description |
|--------|------------|-------------|
| `download_started` | `str url, str title` | Download started |
| `download_progress` | `str url, dict progress` | Progress update |
| `download_completed` | `str url, bool success, str message` | Download finished |
| `queue_progress` | `int completed, int failed, int cancelled, int total` | Queue status |
| `aggregate_speed` | `float bytes_per_second` | Total download speed |
| `all_completed` | - | All downloads finished |

**Public API**:
```python
def start_downloads(self, urls: List[str], config: OutputConfig) -> None
def cancel_all(self) -> None
def cancel_download(self, url: str) -> bool
def get_remaining_urls(self) -> List[str]
def update_concurrent_limit(self, limit: int) -> None
def get_stats(self) -> dict
```

#### DownloadWorker (`download_worker.py`)

**Responsibility**: Single URL download in QThread.

**Signals**:
| Signal | Parameters | Description |
|--------|------------|-------------|
| `progress` | `dict` | Progress info (percent, speed, eta, etc.) |
| `completed` | `bool success, str message, dict metadata` | Download finished |
| `log` | `str level, str message` | Log message |
| `title_found` | `str title` | Video title discovered |

**Key Functions**:
```python
def _build_outtmpl(self, info: Optional[Dict]) -> str
    """Build output template with sequential numbering."""

def _build_options(self, outtmpl: str) -> Dict[str, Any]
    """Build yt-dlp options dictionary."""

def _progress_hook(self, d: Dict[str, Any]) -> None
    """Called by yt-dlp during download."""
```

### Conversion Manager & Worker

#### ConversionManager (`conversion_manager.py`)

**Responsibility**: Batch video conversion using FFmpeg.

**Signals**:
| Signal | Parameters | Description |
|--------|------------|-------------|
| `job_started` | `int job_id` | Conversion started |
| `job_progress` | `int job_id, float percent, str speed, str eta` | Job progress |
| `job_completed` | `int job_id, bool success, str output_path, str error` | Job finished |
| `queue_progress` | `int completed, int total, int in_progress` | Queue status |
| `all_completed` | - | All jobs finished |
| `job_creation_progress` | `int current, int total` | Async job creation |
| `jobs_created` | `List[ConversionJob]` | Jobs ready for processing |

**Public API**:
```python
def set_config(self, config: ConversionConfig) -> None
def add_files(self, input_paths: List[str], output_dir: Optional[str] = None) -> List[ConversionJob]
def add_files_async(self, input_paths: List[str], output_dir: Optional[str] = None) -> None
def start(self) -> None
def cancel_all(self) -> None
def cancel_job(self, job_id: int) -> bool
def get_job(self, job_id: int) -> Optional[ConversionJob]
def get_history(self, limit: int = 50) -> List[ConversionJob]
```

#### FFmpegWorker (`ffmpeg_worker.py`)

**Responsibility**: Single file FFmpeg conversion.

**Features**:
- Hardware acceleration support (NVENC, AMF, QSV, VideoToolbox)
- CRF-based quality control
- Preset-based encoding speed

### Trim Manager & Worker

#### TrimManager (`trim_manager.py`)

**Responsibility**: Video trimming operations.

**Signals**:
| Signal | Parameters | Description |
|--------|------------|-------------|
| `job_started` | `int job_id` | Trim started |
| `job_progress` | `int job_id, float percent` | Job progress |
| `job_completed` | `int job_id, bool success, str output_path, str error` | Job finished |
| `queue_progress` | `int completed, int total, int in_progress` | Queue status |
| `all_completed` | - | All jobs finished |

**Features**:
- Lossless trimming (direct stream copy)
- Re-encoded trimming with quality control

### Sort Manager

#### SortManager (`sort_manager.py`)

**Responsibility**: Sort videos by metadata into folders.

**Sort Criteria**:
- `FPS`: Frame rate (e.g., 24fps, 30fps, 60fps)
- `RESOLUTION`: Video resolution (e.g., 1080p, 4K)
- `ORIENTATION`: Horizontal, vertical, or square
- `CODEC`: Video codec (h264, hevc, etc.)
- `BITRATE`: Video bitrate

**Signals**:
| Signal | Parameters | Description |
|--------|------------|-------------|
| `progress` | `int current, int total, str message` | Scan/progress |
| `file_sorted` | `str original_path, str new_path` | File moved |
| `completed` | `int success_count, int failed_count` | All done |
| `error` | `str message` | Error occurred |

### Match Manager & Workers

#### MatchManager (`match_manager.py`)

**Responsibility**: Match local videos against ThePornDB and StashDB.

**Signals**:
| Signal | Parameters | Description |
|--------|------------|-------------|
| `scan_started` | - | Folder scan began |
| `scan_progress` | `int current, int total` | Scan progress |
| `scan_completed` | `List[MatchResult]` | Scan finished |
| `match_started` | - | Matching began |
| `match_progress` | `int file_index, str status, float percent` | Match progress |
| `match_result` | `int file_index, MatchResult` | Individual result |
| `login_required` | `str database, str url` | Auth needed |
| `match_completed` | - | All matching done |
| `rename_started` | - | Renaming began |
| `rename_progress` | `int current, int total` | Rename progress |
| `rename_completed` | `int success, int failed` | Rename done |
| `error` | `str message` | Error occurred |

**Features**:
- Filename parsing to extract studio/performer/title
- Online database search
- Automatic renaming based on matched metadata

#### MatchScanWorker (`match_scan_worker.py`)

**Responsibility**: Scan folder for video files and parse filenames.

#### MatchWorker (`match_worker.py`)

**Responsibility**: Query online databases for video matches.

### Extract URLs Manager

#### ExtractUrlsManager (`extract_urls_manager.py`)

**Responsibility**: Extract video URLs from web pages using Playwright.

**Signals**:
| Signal | Parameters | Description |
|--------|------------|-------------|
| `extract_started` | - | Extraction began |
| `extract_progress` | `int current, int total, str url` | Page progress |
| `extract_result` | `str url, List[str] video_urls` | URLs found |
| `extract_completed` | `int total_urls` | Extraction done |
| `error` | `str message` | Error occurred |

### Auth Manager

#### AuthManager (`auth_manager.py`)

**Responsibility**: Browser authentication and cookie export.

**Signals**:
| Signal | Parameters | Description |
|--------|------------|-------------|
| `login_started` | - | Login began |
| `login_finished` | `str result, str message` | Login done |
| `cookies_export_started` | - | Export began |
| `cookies_exported` | `str path` | Cookies saved |
| `install_started` | - | Playwright install began |
| `install_progress` | `str message` | Install progress |
| `install_completed` | - | Install done |
| `install_failed` | `str error` | Install failed |
| `error` | `str message` | Error occurred |

## Data Layer (`src/data/`)

### Database (`database.py`)

**Responsibility**: SQLite connection management with thread-safe operations.

**Features**:
- Singleton pattern
- Thread-local connections
- Automatic schema migrations
- Foreign key support

**Schema Tables**:
- `downloads`: Download history
- `sessions`: Session state for recovery
- `config`: Key-value configuration
- `conversion_jobs`: Conversion job records
- `schema_version`: Migration tracking

### Models (`models.py`)

**Download Models**:
```python
class DownloadStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"

@dataclass
class Download:
    url: str
    id: Optional[int] = None
    title: Optional[str] = None
    output_path: Optional[str] = None
    file_size: Optional[int] = None
    status: DownloadStatus = DownloadStatus.COMPLETED
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

@dataclass
class OutputConfig:
    output_dir: str
    concurrent_limit: int = 3
    force_overwrite: bool = False
    video_only: bool = False
    cookies_path: Optional[str] = None
    filename_templates: Dict[str, str] = field(default_factory=dict)
    default_template: str = "%(title)s"

@dataclass
class Session:
    pending_urls: List[str]
    output_dir: str
    concurrent_limit: int = 3
    force_overwrite: bool = False
    video_only: bool = False
    cookies_path: Optional[str] = None
    id: Optional[int] = None
    completed_urls: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
```

**Conversion Models**:
```python
class ConversionStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ConversionConfig:
    output_codec: str = "h264"
    crf_value: int = 23
    preset: str = "medium"
    use_hardware_accel: bool = False
    hardware_encoder: Optional[str] = None
    output_dir: Optional[str] = None

@dataclass
class ConversionJob:
    input_path: str
    output_path: str
    id: Optional[int] = None
    status: ConversionStatus = ConversionStatus.PENDING
    # ... codec, crf, preset settings
    progress_percent: float = 0.0
    error_message: Optional[str] = None
    input_size: int = 0
    output_size: int = 0
    duration: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
```

**Video Metadata**:
```python
@dataclass
class VideoMetadata:
    file_path: str
    width: int = 0
    height: int = 0
    fps: float = 0.0
    codec: str = ""
    bitrate: int = 0
    duration: float = 0.0
    file_size: int = 0
    original_subfolder: str = ""

    @property
    def resolution(self) -> str: ...
    @property
    def resolution_category(self) -> str: ...  # "1080p", "4K", etc.
    @property
    def orientation(self) -> str: ...  # "horizontal", "vertical", "square"
    @property
    def fps_label(self) -> str: ...  # "29.970fps" (exact, 3 decimals)
    @property
    def fps_category(self) -> str: ...  # "30fps" (rounded)
    @property
    def bitrate_label(self) -> str: ...  # "5Mbps"
```

**Match Models**:
```python
class MatchStatus(Enum):
    PENDING = "pending"
    SEARCHING = "searching"
    MATCHED = "matched"
    MULTIPLE_MATCHES = "multiple_matches"
    NO_MATCH = "no_match"
    RENAMED = "renamed"
    SKIPPED = "skipped"
    FAILED = "failed"

@dataclass
class SceneMetadata:
    title: str
    studio: str
    performers: List[str]
    date: Optional[str] = None
    duration: Optional[int] = None
    stashdb_id: Optional[str] = None
    porndb_id: Optional[str] = None
    source_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    source_database: str = ""  # "stashdb" or "porndb"

@dataclass
class ParsedFilename:
    original: str
    studio: Optional[str] = None
    performers: List[str] = field(default_factory=list)
    title: Optional[str] = None
    preserved_tags: List[str] = field(default_factory=list)
    quality_indicators: List[str] = field(default_factory=list)
    search_queries: List[str] = field(default_factory=list)

@dataclass
class MatchResult:
    file_path: str
    original_filename: str
    status: MatchStatus = MatchStatus.PENDING
    parsed: Optional[ParsedFilename] = None
    matches: List[SceneMetadata] = field(default_factory=list)
    selected_match: Optional[SceneMetadata] = None
    confidence: float = 0.0
    new_filename: Optional[str] = None
    error_message: Optional[str] = None
```

### Repositories

#### DownloadRepository (`repositories/download_repository.py`)

```python
class DownloadRepository:
    def save(self, download: Download) -> int
    def get_by_url(self, url: str) -> Optional[Download]
    def get_by_id(self, download_id: int) -> Optional[Download]
    def is_downloaded(self, url: str) -> bool
    def get_downloaded_urls(self, urls: List[str]) -> Set[str]
    def get_all(self, limit: int = 100, offset: int = 0) -> List[Download]
    def get_by_status(self, status: DownloadStatus, limit: int = 100) -> List[Download]
    def delete_all(self) -> int
    def update_status(self, url: str, status: DownloadStatus, error_message: Optional[str] = None) -> bool
    def mark_completed(self, url: str, title: Optional[str] = None, ...) -> bool
```

#### SessionRepository (`repositories/session_repository.py`)

```python
class SessionRepository:
    def save(self, session: Session) -> int
    def get_active(self) -> Optional[Session]
    def mark_inactive(self, session_id: int) -> bool
    def delete(self, session_id: int) -> bool
    def delete_inactive(self) -> int
```

#### ConversionRepository (`repositories/conversion_repository.py`)

```python
class ConversionRepository:
    def create(self, job: ConversionJob) -> ConversionJob
    def get_by_id(self, job_id: int) -> Optional[ConversionJob]
    def get_all(self, limit: int = 50) -> List[ConversionJob]
    def get_by_status(self, status: ConversionStatus) -> List[ConversionJob]
    def update(self, job: ConversionJob) -> bool
    def delete_old(self, days: int = 30) -> int
```

## Services (`src/services/`)

### ConfigService (`config_service.py`)

**Responsibility**: JSON configuration with atomic saves and migration.

**Features**:
- Singleton pattern
- Dot-notation access (`config.get('download.concurrent_limit')`)
- Debounced saves for bursty UI updates
- Atomic file writes (temp file + rename)
- Version-based migration

**Key Methods**:
```python
def get(self, key_path: str, default: Any = None) -> Any
def set(self, key_path: str, value: Any, save: bool = True) -> None
def get_section(self, section: str) -> dict
def set_section(self, section: str, values: dict, save: bool = True) -> None
def queue_save(self, delay_ms: Optional[int] = None) -> None
def save(self) -> None
def reset_to_defaults(self) -> None
```

### SessionService (`session_service.py`)

**Responsibility**: Session state management with auto-save.

**Features**:
- Auto-save every 5 seconds
- Dirty flag for efficient saves
- Session creation/update/completion tracking

**Key Methods**:
```python
def start_auto_save(self, interval_ms: int = 5000) -> None
def stop_auto_save(self) -> None
def create_session(self, urls: List[str], config: OutputConfig) -> Session
def update_pending_urls(self, pending_urls: List[str]) -> None
def complete_session(self) -> None
def get_active_session(self) -> Optional[Session]
def has_active_session(self) -> bool
```

### CrashRecoveryService (`crash_recovery_service.py`)

**Responsibility**: Crash detection and session recovery.

**Features**:
- Lock file with PID tracking
- Cross-platform process detection
- Session recovery offering

## UI Layer (`src/ui/`)

### MainWindow (`main_window.py`)

**Responsibility**: Main application window orchestrating all UI and managers.

**Key Components**:
- Shell layout with sidebar navigation
- Page registration and switching
- Download manager integration
- Keyboard shortcuts
- Quick Look preview (macOS)

**Keyboard Shortcuts**:
| Shortcut | Action |
|----------|--------|
| `Ctrl+Return` | Start downloads |
| `Escape` | Cancel downloads |
| `Ctrl+L` | Focus URL input |
| `Ctrl+Shift+C` | Clear log |
| `Space` (file selected) | Quick Look preview |

### Shell (`shell.py`)

**Responsibility**: Top-level layout with sidebar and content stack.

```python
class Shell(QWidget):
    def register_tool(self, key: str, widget: QWidget) -> None
    def switch_to_tool(self, key: str) -> None
    def active_tool(self) -> str | None
    def set_badge(self, key: str, count: int) -> None
```

### Pages (`src/ui/pages/`)

| Page | File | Purpose |
|------|------|---------|
| Add URLs | `add_urls_page.py` | URL input, download queue |
| Extract URLs | `extract_urls_page.py` | Playwright URL extraction |
| Convert | `convert_page.py` | FFmpeg video conversion |
| Trim | `trim_page.py` | Video trimming |
| Metadata | `metadata_page.py` | Video metadata extraction |
| Sort | `sort_page.py` | Video sorting by criteria |
| Rename | `rename_page.py` | Batch file renaming |
| Match | `match_page.py` | Database matching |
| Settings | `settings_page.py` | Application settings |

### Theme (`src/ui/theme/`)

#### ThemeEngine (`theme_engine.py`)

**Responsibility**: Singleton theme management.

```python
class ThemeEngine(QObject):
    theme_changed = pyqtSignal(str)
    
    def set_theme(self, theme: str) -> None  # "dark" or "light"
    def toggle_theme(self) -> None
    def apply_theme(self, app: QApplication) -> None
    def get_color(self, key: str) -> str
```

#### QSS Builder (`qss_builder.py`)

**Responsibility**: Generate Qt Style Sheets from design tokens.

### Widgets (`src/ui/widgets/`)

| Widget | Purpose |
|--------|---------|
| `UrlInputWidget` | URL text input with validation |
| `FilePickerWidget` | File/folder selection |
| `OutputConfigWidget` | Output directory and options |
| `ProgressWidget` | Individual download progress |
| `QueueProgressWidget` | Overall queue progress |
| `DownloadLogWidget` | Download log display |
| `AuthStatusWidget` | Authentication status |
| `VideoPreviewWidget` | Video preview |
| `TrimTimelineWidget` | Trim point selection |

## Utilities (`src/utils/`)

### Constants (`constants.py`)

```python
APP_NAME = "yt-dlp GUI"
APP_VERSION = "1.0.0"
DEFAULT_CONCURRENT_LIMIT = 3
DEFAULT_CRF = 23
DEFAULT_FORMAT = "bestvideo+bestaudio/best"
SUPPORTED_VIDEO_EXTENSIONS = [".mp4", ".mkv", ".avi", ...]
HARDWARE_ENCODERS = {"nvenc": {...}, "amf": {...}, "qsv": {...}, "videotoolbox": {...}}
```

### Platform Utils (`platform_utils.py`)

```python
def get_platform() -> Platform  # WINDOWS, MACOS, LINUX
def get_data_dir() -> Path
def get_db_path() -> Path
def get_config_path() -> Path
def get_log_dir() -> Path
def get_default_output_dir() -> Path
def quick_look_file(file_path: str) -> bool  # macOS only
def open_file_default_app(file_path: str) -> bool
```

### FFmpeg Utils (`ffmpeg_utils.py`)

```python
def check_ffmpeg_available() -> tuple[bool, bool]  # (ffmpeg, ffprobe)
def get_ffmpeg_version() -> str
def get_video_metadata(file_path: str) -> VideoMetadata
```

## See Also

- [Architecture Overview](./ARCHITECTURE.md) - System architecture diagrams
- [Data Models](./DATA_MODELS.md) - Database schema and models
- [API Reference](./API_REFERENCE.md) - Detailed API documentation
