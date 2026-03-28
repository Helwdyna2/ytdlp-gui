# Glossary

Terminology reference for yt-dlp GUI project.

## Application Terms

### Download Manager
The core manager (`src/core/download_manager.py`) that orchestrates the download queue, spawns worker threads, and aggregates progress from multiple concurrent downloads.

### Download Worker
A QThread worker (`src/core/download_worker.py`) that handles a single URL download using yt-dlp.

### Manager
A QObject subclass in `src/core/` that coordinates business logic and worker threads. Examples: DownloadManager, ConversionManager, MatchManager.

### Worker
A QThread subclass in `src/core/` that performs long-running operations in background threads. Workers communicate via Qt signals.

### Repository
Data access layer classes in `src/data/repositories/` that provide CRUD operations for database entities.

### Session
A recovery mechanism (`Session`, `SessionService`) that tracks download state and allows resumption after crashes.

## Data Model Terms

### Download
A record of a downloaded video, stored in the `downloads` table.

### DownloadStatus
Enum representing download state: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`, `PARTIAL`.

### OutputConfig
Configuration for download operations including output directory, concurrent limit, and overwrite behavior.

### ConversionJob
A video conversion task stored in the `conversion_jobs` table.

### ConversionStatus
Enum for conversion state: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`, `CANCELLED`.

### TrimJob
A video trimming task with start/end times and lossless option.

### MatchResult
Result of matching a local video file against online databases (ThePornDB, StashDB).

### SceneMetadata
Metadata for a matched scene from online databases.

### ParsedFilename
Result of parsing a video filename to extract studio, performer, title, and tags.

### VideoMetadata
Metadata extracted from a video file via ffprobe (resolution, fps, codec, bitrate, etc.).

## UI Terms

### Shell
The main layout widget (`src/ui/shell.py`) containing sidebar navigation and content stack.

### Page
A feature-specific UI in `src/ui/pages/` (e.g., AddUrlsPage, ConvertPage).

### Widget
A reusable PyQt6 widget in `src/ui/widgets/`.

### QSS
Qt Style Sheets - CSS-like styling for PyQt6 widgets.

### Theme Engine
Singleton (`src/ui/theme/theme_engine.py`) that manages dark/light themes and generates QSS.

### Design Tokens
Color and typography values in `src/ui/theme/tokens.py` used for theming.

### Sidebar
Navigation sidebar component (`src/ui/components/sidebar.py`) for switching between pages.

## Technical Terms

### Signal-Slot
Qt's mechanism for communication between objects. Signals are emitted by objects; slots are callback methods.

### QThread
Qt's threading primitive for performing operations in background threads.

### Singleton
Design pattern ensuring only one instance of a class exists (Database, ConfigService).

### Repository Pattern
Pattern abstracting data access through repository classes.

### Atomic Save
File write pattern using temp file + fsync + rename for crash-safe configuration saves.

### Debounced Save
Delayed save triggered after a period of inactivity, for efficient handling of bursty UI updates.

### Crash Recovery
Mechanism using a lock file to detect unclean shutdowns and offer session restoration.

### Lock File
File containing process PID used to detect if a previous instance crashed.

### Sequential Numbering
Automatic numbering for downloaded files (e.g., `video - abc123 - 001.mp4`, `video - abc123 - 002.mp4`).

### URL Redaction
Obfuscation of URLs in logs to protect sensitive information (e.g., `https://example.com/v/12345` becomes `https://example.com/v/*****`).

### Netscape Cookies
Cookie file format used by yt-dlp for authenticated downloads.

### FFprobe
FFmpeg tool for extracting video metadata without encoding.

### CRF
Constant Rate Factor - x264/x265 quality setting (0-51, lower = better).

### Hardware Acceleration
GPU-based video encoding using NVENC (NVIDIA), AMF (AMD), QSV (Intel), or VideoToolbox (macOS).

### ThePornDB
Online adult content database for video matching (porndb.com).

### StashDB
Open adult content database for video matching (stashdb.io).

## Configuration Terms

### ConfigService
Singleton service managing JSON configuration with atomic saves.

### Config Section
A top-level key in the configuration JSON (e.g., `download`, `convert`, `sort`).

### Dot-Notation Path
Configuration access path like `download.concurrent_limit`.

## Page Names

### Add URLs Page
Page for entering URLs and managing download queue.

### Extract URLs Page
Page for extracting video URLs from web pages using Playwright.

### Convert Page
Page for converting videos between formats using FFmpeg.

### Trim Page
Page for trimming video segments.

### Metadata Page
Page for viewing video metadata extracted via ffprobe.

### Sort Page
Page for sorting videos into folders by metadata criteria.

### Rename Page
Page for batch renaming files using patterns.

### Match Page
Page for matching videos against online databases.

### Settings Page
Page for application-wide settings.

## Architecture Patterns

### MVC
Model-View-Controller - pattern used with Qt's signal-slot mechanism.

### Observer
Pattern implemented via Qt signals for UI updates.

### Factory
Pattern for creating worker instances in managers.

### Thread Pool
Pattern of pre-spawned workers for concurrent task execution.

## See Also

- [Architecture Overview](./ARCHITECTURE.md) - System architecture
- [Module Catalog](./MODULES.md) - Detailed module reference
- [Data Models](./DATA_MODELS.md) - Database schema and models
