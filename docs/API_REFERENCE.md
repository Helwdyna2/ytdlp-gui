# API Reference

Complete API reference for managers, workers, services, and repositories.

## Managers

Managers orchestrate business logic and coordinate QThread workers. All managers inherit from `QObject` and communicate via Qt signals.

### DownloadManager

**File**: `src/core/download_manager.py`

**Responsibility**: Download queue management, concurrent worker spawning, progress aggregation.

#### Signals

```python
download_started = pyqtSignal(str, str)      # url, title
download_progress = pyqtSignal(str, dict)   # url, progress_dict
download_completed = pyqtSignal(str, bool, str)  # url, success, message
download_title_found = pyqtSignal(str, str)  # url, title
queue_progress = pyqtSignal(int, int, int, int)  # completed, failed, cancelled, total
aggregate_speed = pyqtSignal(float)          # total bytes/sec
log_message = pyqtSignal(str, str)           # level, message
all_completed = pyqtSignal()
downloads_started = pyqtSignal()
download_cancelling = pyqtSignal(str)        # url
download_force_terminated = pyqtSignal(str)  # url
```

#### Public API

```python
def __init__(self, download_repository: DownloadRepository, parent=None)

@property
def is_running(self) -> bool

@property
def pending_urls(self) -> List[str]

@property
def active_urls(self) -> List[str]

def start_downloads(self, urls: List[str], config: OutputConfig) -> None
    """Start downloading URLs with given config."""

def cancel_all(self) -> None
    """Cancel all downloads gracefully with force-terminate timeout."""

def cancel_download(self, url: str) -> bool
    """Cancel a specific download. Returns True if found."""

def get_remaining_urls(self) -> List[str]
    """Get all remaining URLs (queued + active)."""

def update_concurrent_limit(self, limit: int) -> None
    """Update concurrent download limit."""

def get_stats(self) -> dict
    """Get current download statistics."""
    # Returns: {'total', 'completed', 'failed', 'cancelled', 'queued', 'active', 'skipped', 'is_running'}
```

#### Usage Example

```python
download_manager = DownloadManager(download_repository)

# Connect signals
download_manager.download_progress.connect(lambda url, p: print(f"{url}: {p['percent']:.1f}%"))
download_manager.all_completed.connect(lambda: print("All done!"))

# Start downloads
config = OutputConfig(output_dir="/path/to/output", concurrent_limit=3)
download_manager.start_downloads(["https://example.com/video"], config)

# Cancel all
download_manager.cancel_all()
```

---

### ConversionManager

**File**: `src/core/conversion_manager.py`

**Responsibility**: Batch video conversion job queue and FFmpeg worker management.

#### Signals

```python
job_started = pyqtSignal(int)                                           # job_id
job_progress = pyqtSignal(int, float, str, str)                        # job_id, percent, speed, eta
job_completed = pyqtSignal(int, bool, str, str)                          # job_id, success, output_path, error
queue_progress = pyqtSignal(int, int, int)                             # completed, total, in_progress
all_completed = pyqtSignal()
job_creation_progress = pyqtSignal(int, int)                            # current, total
jobs_created = pyqtSignal(list)                                        # List[ConversionJob]
log = pyqtSignal(str, str)                                              # level, message
files_deleted = pyqtSignal(int, list)                                   # count, paths
```

#### Public API

```python
def __init__(self, repository: Optional[ConversionRepository] = None, parent=None)

@property
def is_running(self) -> bool

@property
def pending_count(self) -> int

@property
def active_count(self) -> int

@property
def completed_count(self) -> int

@property
def failed_count(self) -> int

def set_config(self, config: ConversionConfig) -> None

def add_files(self, input_paths: List[str], output_dir: Optional[str] = None) -> List[ConversionJob]
    """Add files synchronously. Returns created jobs."""

def add_files_async(self, input_paths: List[str], output_dir: Optional[str] = None) -> None
    """Add files asynchronously. Jobs created in background thread."""

def start(self) -> None
    """Start processing the conversion queue."""

def cancel_all(self) -> None
    """Cancel all pending and active conversions."""

def cancel_job(self, job_id: int) -> bool
    """Cancel a specific job. Returns True if found."""

def get_job(self, job_id: int) -> Optional[ConversionJob]

def get_history(self, limit: int = 50) -> List[ConversionJob]

def clear_history(self, days: int = 30) -> int
    """Delete jobs older than specified days. Returns count deleted."""

def reset_counts(self) -> None
```

---

### TrimManager

**File**: `src/core/trim_manager.py`

**Responsibility**: Video trimming job queue and processing.

#### Signals

```python
job_started = pyqtSignal(int)
job_progress = pyqtSignal(int, float)
job_completed = pyqtSignal(int, bool, str, str)
queue_progress = pyqtSignal(int, int, int)
all_completed = pyqtSignal()
log = pyqtSignal(str, str)
```

#### Public API

```python
def set_config(self, config: TrimConfig) -> None

def add_jobs(self, jobs: List[TrimJob]) -> None

def start(self) -> None

def cancel_all(self) -> None

def cancel_job(self, job_id: int) -> bool

def get_job(self, job_id: int) -> Optional[TrimJob]
```

---

### SortManager

**File**: `src/core/sort_manager.py`

**Responsibility**: Sort videos by metadata into folders.

#### Signals

```python
progress = pyqtSignal(int, int, str)   # current, total, message
file_sorted = pyqtSignal(str, str)     # original_path, new_path
completed = pyqtSignal(int, int)      # success_count, failed_count
error = pyqtSignal(str)
```

#### Public API

```python
def set_config(self, config: SortConfig) -> None

def scan_folder(self, folder_path: str) -> None
    """Scan folder for videos. Emits progress signals."""

def sort_files(self, video_metadata: List[VideoMetadata]) -> None
    """Sort scanned files based on criteria."""

def cancel(self) -> None
```

---

### MatchManager

**File**: `src/core/match_manager.py`

**Responsibility**: Match local videos against ThePornDB and StashDB.

#### Signals

```python
scan_started = pyqtSignal()
scan_progress = pyqtSignal(int, int)              # current, total
scan_completed = pyqtSignal(list)                 # List[MatchResult]
match_started = pyqtSignal()
match_progress = pyqtSignal(int, str, float)       # file_index, status, percent
match_result = pyqtSignal(int, object)            # file_index, MatchResult
login_required = pyqtSignal(str, str)             # database, url
match_completed = pyqtSignal()
rename_started = pyqtSignal()
rename_progress = pyqtSignal(int, int)            # current, total
rename_completed = pyqtSignal(int, int)          # success, failed
error = pyqtSignal(str)
```

#### Public API

```python
def set_config(self, config: MatchConfig) -> None

def scan_folder(self, folder_path: str) -> None
    """Scan folder for video files."""

def start_matching(self) -> None
    """Start matching process for scanned files."""

def stop_matching(self) -> None

def confirm_login(self, database: str) -> None
    """Confirm user has logged in to database."""

def select_match(self, file_index: int, match: SceneMetadata) -> None
    """Select a specific match for a file."""

def rename_files(self, file_indices: List[int]) -> None
    """Rename selected files to matched names."""

def generate_new_filename(self, result: MatchResult) -> Optional[str]
    """Generate new filename from match result."""

def get_files(self) -> List[MatchResult]

def set_scan_results(self, files: List[MatchResult]) -> None
```

---

### ExtractUrlsManager

**File**: `src/core/extract_urls_manager.py`

**Responsibility**: Extract video URLs from web pages using Playwright.

#### Signals

```python
extract_started = pyqtSignal()
extract_progress = pyqtSignal(int, int, str)    # current, total, url
extract_result = pyqtSignal(str, list)         # page_url, video_urls
extract_completed = pyqtSignal(int)            # total_urls
error = pyqtSignal(str)
```

#### Public API

```python
def set_config(self, config: ExtractUrlsConfig) -> None

def add_urls(self, page_urls: List[str]) -> None

def start_extraction(self) -> None

def cancel(self) -> None
```

---

### AuthManager

**File**: `src/core/auth_manager.py`

**Responsibility**: Browser authentication and cookie export for site access.

#### Signals

```python
login_started = pyqtSignal()
login_finished = pyqtSignal(str, str)           # result, message
cookies_export_started = pyqtSignal()
cookies_exported = pyqtSignal(str)             # path
install_started = pyqtSignal()
install_progress = pyqtSignal(str)             # message
install_completed = pyqtSignal()
install_failed = pyqtSignal(str)               # error
error = pyqtSignal(str)
```

#### Public API

```python
def open_login(self, url: str, target_cookie_suffixes: List[str] = None) -> None
    """Open browser for login."""

def export_cookies(self) -> None
    """Export cookies from browser profile to Netscape format."""

def get_cookies_file_path(self) -> str
    """Get path to cookies file."""

def install_playwright(self) -> None
    """Install Playwright browsers."""
```

---

## Workers

Workers are QThread subclasses that perform operations in background threads.

### DownloadWorker

**File**: `src/core/download_worker.py`

```python
class DownloadWorker(QThread):
    progress = pyqtSignal(dict)
    completed = pyqtSignal(bool, str, dict)   # success, message, metadata
    log = pyqtSignal(str, str)                 # level, message
    title_found = pyqtSignal(str)              # title

    def __init__(self, url: str, config: OutputConfig, parent=None)

    def run(self) -> None:
        """Execute download in worker thread."""

    def cancel(self) -> None:
        """Request cancellation."""
```

---

### FFmpegWorker

**File**: `src/core/ffmpeg_worker.py`

```python
class FFmpegWorker(QThread):
    progress = pyqtSignal(float, str, str)     # percent, speed, eta
    completed = pyqtSignal(bool, str, str)     # success, output_path, error
    log = pyqtSignal(str, str)                 # level, message

    def __init__(self, input_path: str, output_path: str, config: ConversionConfig, parent=None)

    def run(self) -> None

    def cancel(self) -> None
```

---

### TrimWorker

**File**: `src/core/trim_worker.py`

```python
class TrimWorker(QThread):
    progress = pyqtSignal(float)               # percent
    completed = pyqtSignal(bool, str, str)     # success, output_path, error
    log = pyqtSignal(str, str)

    def __init__(self, job: TrimJob, config: TrimConfig, parent=None)
```

---

### FolderScanWorker

**File**: `src/core/folder_scan_worker.py`

```python
class FolderScanWorker(QThread):
    progress = pyqtSignal(int, int, str)       # current, total, current_file
    metadata_found = pyqtSignal(object)       # VideoMetadata
    completed = pyqtSignal(list)              # List[VideoMetadata]
    error = pyqtSignal(str)

    def __init__(self, folder_path: str, recursive: bool = True, parent=None)
```

---

### MatchWorker

**File**: `src/core/match_worker.py`

```python
class MatchWorker(QThread):
    progress = pyqtSignal(int, str)            # file_index, status_message
    match_found = pyqtSignal(int, object)     # file_index, MatchResult
    login_required = pyqtSignal(str, str)     # database_name, url
    login_completed = pyqtSignal(str)         # database_name
    error = pyqtSignal(int, str)              # file_index, error_message
    completed = pyqtSignal()

    def __init__(self, files: List[MatchResult], config: MatchConfig, cookies_dir: str, parent=None)

    def run(self) -> None

    def cancel(self) -> None

    def confirm_login(self, database: str) -> None
```

---

### ExtractUrlsWorker

**File**: `src/core/extract_urls_worker.py`

```python
class ExtractUrlsWorker(QThread):
    progress = pyqtSignal(int, int, str)      # current, total, url
    result = pyqtSignal(str, list)            # page_url, video_urls
    completed = pyqtSignal(int)               # total_urls
    error = pyqtSignal(str)

    def __init__(self, page_urls: List[str], config: ExtractUrlsConfig, parent=None)
```

---

### AuthWorker

**File**: `src/core/auth_worker.py`

```python
class AuthWorker(QThread):
    login_started = pyqtSignal()
    login_finished = pyqtSignal(str, str)     # result, message
    cookies_export_started = pyqtSignal()
    cookies_exported = pyqtSignal(str)        # path
    install_started = pyqtSignal()
    install_progress = pyqtSignal(str)         # message
    install_completed = pyqtSignal()
    install_failed = pyqtSignal(str)           # error
    error = pyqtSignal(str)

    def __init__(self, login_url: str, target_suffixes: List[str], profile_dir: str, parent=None)
```

---

## Services

### ConfigService

**File**: `src/services/config_service.py`

Singleton service for JSON configuration management.

```python
class ConfigService:
    _instance: Optional["ConfigService"] = None

    def __init__(self, config_path: Optional[str] = None)

    # Configuration Access
    def get(self, key_path: str, default: Any = None) -> Any
        """Get config value by dot-notation path.
        # Examples:
        #   config.get('download.concurrent_limit')
        #   config.get('window.width')
        #   config.get('nonexistent', 'default')
        """

    def set(self, key_path: str, value: Any, save: bool = True) -> None
        """Set config value by dot-notation path."""

    def get_section(self, section: str) -> dict
        """Get entire config section as dict."""

    def set_section(self, section: str, values: dict, save: bool = True) -> None
        """Set entire config section."""

    # Persistence
    def save(self) -> None
        """Save configuration to file atomically."""

    def queue_save(self, delay_ms: Optional[int] = None) -> None
        """Debounced save for bursty UI updates."""

    def reset_to_defaults(self) -> None
        """Reset all configuration to defaults."""

    # Singleton management
    @classmethod
    def reset_instance(cls) -> None
```

#### Configuration Sections

```python
DEFAULT_CONFIG = {
    "version": 1,
    "window": {
        "width": 1000,
        "height": 700,
        "x": None,
        "y": None,
        "splitter_sizes": [450, 550],
        "maximized": False,
    },
    "dialogs": {"last_dir": ""},
    "download": {
        "output_dir": "",
        "concurrent_limit": 3,
        "force_overwrite": False,
        "video_only": False,
        "cookies_path": "",
        "filename_templates": {},
        "default_template": "%(title)s",
    },
    "behavior": {
        "auto_save_interval_ms": 5000,
        "debounce_parse_ms": 300,
        "log_max_lines": 1000,
        "confirm_on_exit": True,
    },
    "convert": {
        "output_dir": "",
        "codec": "libx264",
        "crf": 23,
        "preset": "medium",
        "use_hardware_accel": False,
    },
    "trim": {...},
    "rename": {...},
    "sort": {...},
    "match": {...},
    "extract_urls": {...},
    "auth": {...},
    "playwright": {"browser": "chromium"},
    "ffmpeg": {"warning_dismissed": False},
    "download_polite": {...},
}
```

---

### SessionService

**File**: `src/services/session_service.py`

Session state management with auto-save.

```python
class SessionService(QObject):
    def __init__(self, session_repository: SessionRepository, parent=None)

    # Auto-save
    def start_auto_save(self, interval_ms: int = 5000) -> None
    def stop_auto_save(self) -> None
    def mark_dirty(self) -> None

    # Session lifecycle
    def create_session(self, urls: List[str], config: OutputConfig) -> Session
    def update_pending_urls(self, pending_urls: List[str]) -> None
    def complete_session(self) -> None
    def save_if_dirty(self) -> None

    # Session queries
    def get_active_session(self) -> Optional[Session]
    def get_recoverable_session(self) -> Optional[Session]
    def clear_session(self, session_id: int) -> None
    def cleanup_old_sessions(self) -> None

    # Properties
    @property
    def current_session(self) -> Optional[Session]
    @property
    def has_active_session(self) -> bool
    @property
    def is_dirty(self) -> bool
```

---

### CrashRecoveryService

**File**: `src/services/crash_recovery_service.py`

Crash detection and recovery.

```python
class CrashRecoveryService:
    def __init__(self, session_repository: SessionRepository)

    def check_crash(self) -> bool
        """Check if last session crashed. Returns True if crash detected."""

    def acquire_lock(self) -> bool
        """Acquire lock file on startup."""

    def release_lock(self) -> None
        """Release lock file on clean shutdown."""

    def get_recoverable_session(self) -> Optional[Session]
    def mark_recovered(self, session: Session) -> None
    def discard_session(self, session: Session) -> None
```

---

## Repositories

### DownloadRepository

**File**: `src/data/repositories/download_repository.py`

```python
class DownloadRepository:
    def __init__(self, database: Database)

    def save(self, download: Download) -> int
    def get_by_url(self, url: str) -> Optional[Download]
    def get_by_id(self, download_id: int) -> Optional[Download]
    def is_downloaded(self, url: str) -> bool
    def get_downloaded_urls(self, urls: List[str]) -> Set[str]
    def get_all(self, limit: int = 100, offset: int = 0) -> List[Download]
    def get_by_status(self, status: DownloadStatus, limit: int = 100) -> List[Download]
    def get_count(self) -> int
    def get_count_by_status(self, status: DownloadStatus) -> int
    def delete_by_id(self, download_id: int) -> bool
    def delete_by_url(self, url: str) -> bool
    def delete_all(self) -> int
    def update_status(self, url: str, status: DownloadStatus, error_message: Optional[str] = None) -> bool
    def mark_completed(self, url: str, title: Optional[str] = None, output_path: Optional[str] = None, file_size: Optional[int] = None) -> bool
```

---

### SessionRepository

**File**: `src/data/repositories/session_repository.py`

```python
class SessionRepository:
    def __init__(self, database: Database)

    def save(self, session: Session) -> int
    def get_active(self) -> Optional[Session]
    def mark_inactive(self, session_id: int) -> bool
    def delete(self, session_id: int) -> bool
    def delete_inactive(self) -> int
```

---

### ConversionRepository

**File**: `src/data/repositories/conversion_repository.py`

```python
class ConversionRepository:
    def __init__(self, database: Database)

    def create(self, job: ConversionJob) -> ConversionJob
    def get_by_id(self, job_id: int) -> Optional[ConversionJob]
    def get_all(self, limit: int = 50) -> List[ConversionJob]
    def get_by_status(self, status: ConversionStatus) -> List[ConversionJob]
    def update(self, job: ConversionJob) -> bool
    def delete_old(self, days: int = 30) -> int
```

---

## Database

**File**: `src/data/database.py`

SQLite connection management.

```python
class Database:
    _instance: Optional['Database'] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[str] = None)

    def _get_connection(self) -> sqlite3.Connection
        """Get thread-local database connection."""

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor
    def executemany(self, query: str, params_list: list) -> None
    def fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]
    def fetchall(self, query: str, params: tuple = ()) -> list

    def initialize(self) -> None
    def close(self) -> None

    @classmethod
    def reset_instance(cls) -> None
```

---

## See Also

- [Architecture Overview](./ARCHITECTURE.md) - System architecture
- [Module Catalog](./MODULES.md) - Detailed module reference
- [Data Models](./DATA_MODELS.md) - Database schema and models
