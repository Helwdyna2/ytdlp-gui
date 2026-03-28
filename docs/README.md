# yt-dlp GUI

A cross-platform PyQt6 desktop application for downloading videos from YouTube and 1000+ other sites using yt-dlp, with queue management, progress tracking, session persistence, and advanced features like video conversion, trimming, and matching against online databases.

## Features

- **Video Downloading**: Download videos from YouTube, Vimeo, Pornhub, and 1000+ other sites
- **Queue Management**: Concurrent downloads with configurable limits
- **Progress Tracking**: Real-time progress bars, speed indicators, and ETA
- **Session Persistence**: Auto-save and crash recovery for interrupted sessions
- **Video Conversion**: Convert videos between formats using FFmpeg
- **Video Trimming**: Cut video segments without re-encoding (or with re-encoding)
- **Video Sorting**: Organize videos by FPS, resolution, codec, bitrate, or orientation
- **Batch Renaming**: Rename videos based on metadata patterns
- **Database Matching**: Match videos against ThePornDB and StashDB for metadata
- **URL Extraction**: Extract video URLs from web pages using Playwright
- **Cookie Authentication**: Support for site authentication via browser cookies
- **Dark/Light Themes**: Customizable UI with Signal Deck-inspired design

## Quick Start

### Prerequisites

- Python 3.10+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) (installed via pip)
- [FFmpeg](https://ffmpeg.org/) (for conversion/trimming features)
- [Playwright](https://playwright.dev/) browsers (for URL extraction and auth)

### Installation

```bash
# Clone the repository
git clone https://github.com/pb/ytdlp-gui.git
cd ytdlp-gui

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (first time only)
playwright install chromium

# Run the application
python run.py
```

### Building for Distribution

```bash
# Install PyInstaller
pip install pyinstaller

# Create executable
pyinstaller main.py --onefile --name "yt-dlp GUI"
```

## Project Structure

```
ytdlp-gui/
├── main.py                    # PyInstaller entry point
├── run.py                     # Development entry point
├── requirements.txt           # Python dependencies
├── src/
│   ├── main.py               # Main module (SingleApplication, logging)
│   ├── core/                 # Business logic & QThread workers
│   ├── data/                 # Data layer (SQLite, models, repositories)
│   ├── services/             # Application services
│   ├── ui/                   # User interface
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/            # Main tab pages
│   │   ├── theme/            # Theming system
│   │   └── widgets/          # Custom widgets
│   └── utils/                # Utility functions
├── tests/                    # pytest test suite (35+ test files)
└── data/                     # Runtime data (gitignored)
    ├── config.json           # User configuration
    ├── ytdlp_gui.db          # SQLite database
    └── logs/                 # Application logs
```

## Documentation

- [Architecture Overview](./ARCHITECTURE.md) - System architecture and design patterns
- [Module Catalog](./MODULES.md) - Detailed module reference
- [Data Models](./DATA_MODELS.md) - Database schema and data models
- [API Reference](./API_REFERENCE.md) - Manager and service APIs
- [Configuration](./CONFIGURATION.md) - Configuration options
- [Building & Testing](./BUILD_TEST_RUN.md) - Build, test, and run procedures
- [Testing Guide](./TESTING.md) - Testing strategy and coverage
- [Glossary](./GLOSSARY.md) - Project terminology
- [Contributing](./CONTRIBUTING.md) - Coding standards and contribution guidelines
- [Issues & Technical Debt](./ISSUES_DEBT.md) - Known issues and technical debt
- [Dependencies](./DEPENDENCIES.md) - Dependency documentation

## Key Technologies

- **PyQt6**: Qt-based GUI framework
- **yt-dlp**: Video downloading engine
- **SQLite**: Local database for persistence
- **FFmpeg**: Video conversion and processing
- **Playwright**: Browser automation for URL extraction and auth

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Return` | Start downloads |
| `Escape` | Cancel downloads |
| `Ctrl+L` | Focus URL input |
| `Ctrl+Shift+C` | Clear download log |
| `Space` (macOS) | Quick Look preview on selected file |

## License

See LICENSE file in repository root.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for coding standards and contribution guidelines.
