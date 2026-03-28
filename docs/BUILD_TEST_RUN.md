# Building, Testing, and Running

Guide for building, testing, and running yt-dlp GUI.

## Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) installed via pip
- [FFmpeg](https://ffmpeg.org/) for conversion/trimming features
- [Playwright](https://playwright.dev/) browsers for URL extraction

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/pb/ytdlp-gui.git
cd ytdlp-gui
```

### 2. Install Dependencies

```bash
# Runtime only
pip install -r requirements.txt

# Runtime + dev/testing
pip install -r requirements-dev.txt
```

### 3. Install Playwright Browsers

```bash
playwright install chromium
```

### 4. Verify FFmpeg Installation

FFmpeg is required for conversion, trimming, and metadata extraction:

```bash
ffmpeg -version
ffprobe -version
```

If FFmpeg is not installed:
- **macOS**: `brew install ffmpeg`
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
- **Linux**: `sudo apt install ffmpeg`

## Running the Application

### Development Mode

```bash
python run.py
```

This runs the application from source code without packaging.

### Production Mode (PyInstaller)

#### Install PyInstaller

```bash
pip install pyinstaller
```

#### Build Executable

```bash
pyinstaller main.py --onefile --name "yt-dlp GUI" --add-data "src:src"
```

#### Run Packaged Application

On Windows:
```cmd
dist\yt-dlp GUI.exe
```

On macOS/Linux:
```bash
./dist/yt-dlp\ GUI
```

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_download_manager.py -v
```

### Run Tests with Coverage

```bash
pytest tests/ --cov=src --cov-report=html
```

### Run Tests Matching Pattern

```bash
pytest tests/ -k "download" -v
```

### Test Directory Structure

```
tests/
├── test_activity_drawer.py
├── test_add_urls_page.py
├── test_auth_domain_suffix.py
├── test_auth_worker.py
├── test_config_bar.py
├── test_config_service.py
├── test_convert_page.py
├── test_data_panel.py
├── test_extract_urls_page.py
├── test_ffmpeg_utils.py
├── test_folder_scan_worker.py
├── test_icons.py
├── test_log_feed.py
├── test_main_window_workbench.py
├── test_match_page.py
├── test_match_scan_worker.py
├── test_metadata_page.py
├── test_netscape_cookies.py
├── test_page_header.py
├── test_pages.py
├── test_qss_builder.py
├── test_rename_page.py
├── test_shared_widgets.py
├── test_shell.py
├── test_sidebar.py
├── test_sort_manager.py
├── test_sort_page.py
├── test_split_layout.py
├── test_theme_engine.py
├── test_theme_tokens.py
├── test_trim_page.py
├── test_url_domains.py
└── test_url_redaction.py
```

## Project Structure

```
ytdlp-gui/
├── main.py                    # PyInstaller entry point
├── run.py                     # Development entry point
├── requirements.txt           # Runtime dependencies
├── src/
│   ├── main.py               # Main module
│   ├── core/                 # Managers and workers
│   ├── data/                 # Database and repositories
│   ├── services/            # Application services
│   ├── ui/                  # User interface
│   └── utils/               # Utilities
├── tests/                    # pytest test suite
└── data/                     # Runtime data (created on first run)
    ├── config.json           # User configuration
    ├── ytdlp_gui.db          # SQLite database
    └── logs/                 # Application logs
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `YTDL_GUI_DATA_DIR` | Override data directory | `data/` subdirectory |

## Troubleshooting

### FFmpeg Not Found

If you see "FFmpeg not found" warnings:
1. Ensure FFmpeg is installed: `ffmpeg -version`
2. Ensure FFmpeg is in your PATH
3. Restart the application

### Playwright Installation Fails

```bash
playwright install --force chromium
```

### Database Errors

Delete `data/ytdlp_gui.db` to reset the database. On next startup, a new database will be created automatically.

### Qt Platform Plugin Error

If you see "Qt platform plugin" errors:
```bash
pip install PyQt6
```

## Development

### Code Style

The project uses:
- Python 3 type hints
- PEP 8 naming conventions
- Qt naming conventions for Qt subclasses

### Adding a New Manager

1. Create `src/core/new_feature_manager.py`
2. Inherit from `QObject`
3. Define signals for communication
4. Create corresponding worker in `src/core/new_feature_worker.py`
5. Register in `MainWindow._setup_ui()`

### Adding a New Page

1. Create `src/ui/pages/new_page.py` inheriting from `QWidget`
2. Implement page UI in `_setup_ui()`
3. Register in `MainWindow._setup_ui()`:
   ```python
   self.new_page = NewPage()
   self.shell.register_tool("new_feature", self.new_page)
   ```

## See Also

- [Testing Guide](./TESTING.md) - Detailed testing documentation
- [Architecture Overview](./ARCHITECTURE.md) - System architecture
- [API Reference](./API_REFERENCE.md) - Manager and service APIs
