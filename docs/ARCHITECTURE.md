# Architecture Overview

This document describes the system architecture of yt-dlp GUI, a PyQt6-based desktop application for video downloading.

## High-Level Architecture

```mermaid
graph TB
    subgraph "Entry Point"
        MAIN[main.py / src/main.py]
        RUN[run.py]
    end

    subgraph "UI Layer"
        MW[MainWindow]
        SH[Shell]
        subgraph "Pages"
            ADD[AddUrlsPage]
            EXT[ExtractUrlsPage]
            CON[ConvertPage]
            TRM[TrimPage]
            META[MetadataPage]
            SRT[SortPage]
            REN[RenamePage]
            MAT[MatchPage]
            SET[SettingsPage]
        end
        subgraph "Components"
            SIDEBAR[Sidebar]
            PROG[ProgressWidget]
            LOG[LogFeed]
        end
    end

    subgraph "Service Layer"
        CFG[ConfigService]
        SESS[SessionService]
        CRASH[CrashRecoveryService]
    end

    subgraph "Manager Layer"
        DM[DownloadManager]
        CM[ConversionManager]
        TM[TrimManager]
        SM[SortManager]
        MM[MatchManager]
        EM[ExtractUrlsManager]
        AM[AuthManager]
    end

    subgraph "Worker Layer (QThread)"
        DW[DownloadWorker]
        FW[FFmpegWorker]
        TW[TrimWorker]
        SW[FolderScanWorker]
        MWORKER[MatchWorker]
        EW[ExtractUrlsWorker]
        AW[AuthWorker]
        JW[JobCreationWorker]
    end

    subgraph "Data Layer"
        DB[(SQLite Database)]
        subgraph "Repositories"
            DR[DownloadRepository]
            SR[SessionRepository]
            CR[ConversionRepository]
        end
        subgraph "Models"
            DOWNLOAD[Download]
            SESSION[Session]
            JOB[ConversionJob]
        end
    end

    MAIN --> MW
    RUN --> MAIN
    MW --> SH
    SH --> SIDEBAR
    SH --> PAGES[Pages]
    MW --> MANAGERS[Managers]
    MANAGERS --> WORKERS[Workers]
    MANAGERS --> CFG
    MANAGERS --> SESS
    SESS --> CRASH
    WORKERS --> DB
    DB --> REPOS[Repositories]
    REPOS --> MODELS[Models]
```

## Component Interaction

### Request Flow

```mermaid
sequenceDiagram
    participant UI as UI Layer
    participant Manager as Manager
    participant Worker as QThread Worker
    participant Service as Service Layer
    participant Data as Data Layer

    UI->>Manager: start_downloads(urls, config)
    Manager->>Manager: Validate & setup
    Manager->>Worker: Spawn DownloadWorker
    Worker->>Service: ConfigService.get()
    Worker->>Service: yt_dlp.download()
    Worker-->>Manager: progress/completed signals
    Manager-->>UI: download_progress signal
    Manager->>Data: DownloadRepository.save()
    Data-->>Manager: Download record
```

### Threading Model

```mermaid
graph LR
    subgraph "Main Thread"
        UI[PyQt6 UI]
        MGR[Managers]
        EV[Event Loop]
    end

    subgraph "Worker Threads"
        W1[DownloadWorker 1]
        W2[DownloadWorker 2]
        W3[DownloadWorker N]
    end

    subgraph "Timer Thread"
        AUTO[Auto-save Timer]
    end

    EV --> UI
    EV --> MGR
    MGR --> W1
    MGR --> W2
    MGR --> W3
    AUTO -->|5s interval| MGR
```

## Design Patterns

### Singleton Pattern

Used for:
- `Database` - Single database connection instance
- `ConfigService` - Single configuration instance
- `ThemeEngine` - Single theme instance

```python
class Database:
    _instance: Optional['Database'] = None
    _lock = threading.Lock()

    def __new__(cls, db_path: Optional[str] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
```

### Repository Pattern

Data access abstracted through repositories:

```mermaid
graph LR
    MANAGER[Manager] --> REPO[Repository]
    REPO --> DB[(SQLite)]
    
    subgraph "Repositories"
        DR[DownloadRepository]
        SR[SessionRepository]
        CR[ConversionRepository]
    end
    
    REPO --> DR
    REPO --> SR
    REPO --> CR
```

### QThread Worker Pattern

Long-running operations run in QThread workers:

```python
class DownloadWorker(QThread):
    progress = pyqtSignal(dict)
    completed = pyqtSignal(bool, str, dict)
    log = pyqtSignal(str, str)

    def run(self):
        # Worker thread execution
        self.progress.emit(progress_dict)
        self.completed.emit(True, "Success", metadata)
```

### Signal-Slot Communication

Qt's signal-slot mechanism for thread-safe UI updates:

```mermaid
graph LR
    WORKER[Worker Thread] -->|pyqtSignal| MANAGER[Manager]
    MANAGER -->|pyqtSignal| UI[Main Thread]
    
    subgraph "Signal Types"
        P[progress dict]
        C[completed bool str dict]
        L[log level message]
    end
    
    WORKER --> P
    WORKER --> C
    WORKER --> L
```

## Layer Responsibilities

### UI Layer (`src/ui/`)

- **MainWindow**: Orchestrates all UI components and managers
- **Shell**: Sidebar navigation and content stacking
- **Pages**: Feature-specific UI (AddUrls, Convert, Trim, etc.)
- **Components**: Reusable UI widgets (ProgressWidget, LogFeed, etc.)
- **Theme**: Dark/light theme QSS generation

### Manager Layer (`src/core/`)

Manages business logic and coordinates workers:

| Manager | Responsibility |
|---------|---------------|
| `DownloadManager` | Queue management, concurrent downloads, progress aggregation |
| `ConversionManager` | FFmpeg conversion job queue and processing |
| `TrimManager` | Video trimming job queue |
| `SortManager` | Video sorting by metadata criteria |
| `MatchManager` | Online database matching workflow |
| `ExtractUrlsManager` | Playwright-based URL extraction |
| `AuthManager` | Browser authentication and cookie export |

### Worker Layer (`src/core/`)

QThread-based background workers:

| Worker | Parent Manager | Function |
|--------|---------------|----------|
| `DownloadWorker` | DownloadManager | Single URL yt-dlp download |
| `FFmpegWorker` | ConversionManager | Single file FFmpeg conversion |
| `TrimWorker` | TrimManager | Single file video trimming |
| `FolderScanWorker` | SortManager | Scan folder for video metadata |
| `MatchWorker` | MatchManager | Online database lookups |
| `ExtractUrlsWorker` | ExtractUrlsManager | Playwright page scraping |
| `AuthWorker` | AuthManager | Browser login automation |

### Service Layer (`src/services/`)

Application-wide state management:

| Service | Responsibility |
|---------|---------------|
| `ConfigService` | JSON configuration with atomic saves, migration |
| `SessionService` | Session state tracking with auto-save |
| `CrashRecoveryService` | Lock-file based crash detection |

### Data Layer (`src/data/`)

- **Database**: SQLite connection management with migrations
- **Models**: Dataclasses for business objects
- **Repositories**: CRUD operations for each entity

## State Management

```mermaid
stateDiagram-v2
    [*] --> Starting
    Starting --> Running: start_downloads()
    Running --> Cancelling: cancel_all()
    Cancelling --> Cancelled: workers finished
    Running --> Completed: all workers finished
    Running --> Failed: worker error
    
    Starting --> Recovering: crash detected
    Recovering --> Running: user confirms
    Recovering --> FreshStart: user discards
```

## Configuration Flow

```mermaid
graph LR
    A[config.json] --> B{ConfigService}
    B --> C[DEFAULT_CONFIG]
    B --> D[User Overrides]
    C --> E[Memory Cache]
    D --> E
    
    E --> F[Managers]
    E --> G[UI Components]
```

## Database Schema

```mermaid
erDiagram
    downloads {
        int id PK
        string url
        string title
        string output_path
        int file_size
        string status
        string error_message
        timestamp created_at
        timestamp updated_at
        timestamp completed_at
    }
    
    sessions {
        int id PK
        json pending_urls
        json completed_urls
        string output_dir
        int concurrent_limit
        bool force_overwrite
        bool video_only
        string cookies_path
        bool is_active
        timestamp created_at
        timestamp updated_at
    }
    
    conversion_jobs {
        int id PK
        string input_path
        string output_path
        string status
        string output_codec
        int crf_value
        string preset
        string hardware_encoder
        float progress_percent
        string error_message
        int input_size
        int output_size
        float duration
        timestamp created_at
        timestamp completed_at
    }
    
    config {
        string key PK
        string value
        timestamp updated_at
    }
    
    schema_version {
        int version PK
        timestamp applied_at
        string description
    }
```

## Crash Recovery Flow

```mermaid
graph TD
    A[App Start] --> B{lock file exists?}
    B -->|No| C[Acquire lock]
    B -->|Yes| D{Process running?}
    D -->|No| E[Detect crash]
    E --> F[Offer recovery]
    F --> G{User accepts?}
    G -->|Yes| H[Restore session]
    G -->|No| I[Discard session]
    D -->|Yes| J[Another instance running]
    J --> K[Exit]
    C --> L[Start normally]
    H --> L
    I --> L
    L --> M[App Running]
    M --> N[Clean shutdown]
    N --> O[Release lock]
```

## Entry Points

| File | Purpose |
|------|---------|
| `run.py` | Development entry point |
| `main.py` | PyInstaller production entry |

```python
# run.py (development)
from src.main import main
if __name__ == "__main__":
    main()

# main.py (production with PyInstaller)
def main():
    # SingleApplication, logging, crash recovery
    app = SingleApplication(sys.argv)
    # ...
```

## See Also

- [Module Catalog](./MODULES.md) - Detailed module reference
- [API Reference](./API_REFERENCE.md) - Manager and service APIs
- [Configuration](./CONFIGURATION.md) - Configuration options
