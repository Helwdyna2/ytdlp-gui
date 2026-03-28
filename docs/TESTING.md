# Testing Guide

Comprehensive guide to testing in yt-dlp GUI.

## Testing Overview

The project uses [pytest](https://pytest.org/) with PyQt6 testing support for a test suite covering:
- Unit tests for managers, workers, services, and repositories
- Integration tests for UI components
- 35+ test files

## Test Structure

```
tests/
├── test_activity_drawer.py       # Activity drawer tests
├── test_add_urls_page.py        # Add URLs page tests
├── test_auth_domain_suffix.py   # Auth domain suffix tests
├── test_auth_worker.py          # Auth worker tests
├── test_config_bar.py           # Config bar tests
├── test_config_service.py       # Config service tests
├── test_convert_page.py         # Convert page tests
├── test_data_panel.py           # Data panel tests
├── test_extract_urls_page.py    # Extract URLs page tests
├── test_ffmpeg_utils.py         # FFmpeg utilities tests
├── test_folder_scan_worker.py   # Folder scan worker tests
├── test_icons.py                # Icon utility tests
├── test_log_feed.py             # Log feed tests
├── test_main_window_workbench.py # Main window tests
├── test_match_page.py           # Match page tests
├── test_match_scan_worker.py    # Match scan worker tests
├── test_metadata_page.py         # Metadata page tests
├── test_netscape_cookies.py     # Netscape cookies tests
├── test_page_header.py          # Page header tests
├── test_pages.py                # General page tests
├── test_qss_builder.py          # QSS builder tests
├── test_rename_page.py          # Rename page tests
├── test_shared_widgets.py       # Shared widget tests
├── test_shell.py                # Shell layout tests
├── test_sidebar.py              # Sidebar tests
├── test_sort_manager.py         # Sort manager tests
├── test_sort_page.py            # Sort page tests
├── test_split_layout.py         # Split layout tests
├── test_theme_engine.py         # Theme engine tests
├── test_theme_tokens.py         # Theme tokens tests
├── test_trim_page.py            # Trim page tests
├── test_url_domains.py          # URL domain extraction tests
└── test_url_redaction.py        # URL redaction tests
```

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_config_service.py -v
```

### Run Tests Matching Pattern

```bash
pytest tests/ -k "config" -v
```

### Run with Coverage

```bash
pytest tests/ --cov=src --cov-report=html
```

### Run with Detailed Output

```bash
pytest tests/ -v -s
```

## Testing Patterns

### PyQt6 Testing

Use `pytest-qt` for PyQt6 testing:

```python
import pytest
from PyQt6.QtWidgets import QApplication

@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

def test_widget(qapp):
    """Test widget with QApplication available."""
    widget = MyWidget()
    assert widget.isVisible()
```

### Manager Testing

```python
from unittest.mock import Mock, patch
from src.core.download_manager import DownloadManager

def test_download_manager_start(monkeypatch):
    """Test starting downloads."""
    mock_repo = Mock()
    manager = DownloadManager(mock_repo)
    
    # Mock the worker's start method
    monkeypatch.setattr(manager, '_spawn_workers', lambda: None)
    
    config = OutputConfig(output_dir="/tmp")
    manager.start_downloads(["https://example.com"], config)
    
    assert manager.is_running
    mock_repo.get_downloaded_urls.assert_called_once()
```

### Service Testing

```python
from src.services.config_service import ConfigService

def test_config_get_set(tmp_path):
    """Test config get/set operations."""
    config = ConfigService(config_path=str(tmp_path / "config.json"))
    
    config.set("test.value", 42)
    assert config.get("test.value") == 42
    
    config.set("nested.key", "hello")
    assert config.get("nested.key") == "hello"
```

### Worker Testing

```python
from src.core.download_worker import DownloadWorker

def test_download_worker_cancel(qtbot):
    """Test download worker cancellation."""
    worker = DownloadWorker("https://example.com", config)
    
    with qtbot.waitSignal(worker.completed, timeout=5000):
        worker.cancel()
    
    # Worker should emit completed with cancelled status
```

### Repository Testing

```python
from src.data.repositories.download_repository import DownloadRepository
from src.data.database import Database

def test_download_repository_save(tmp_path):
    """Test saving download records."""
    db = Database(db_path=str(tmp_path / "test.db"))
    repo = DownloadRepository(db)
    
    download = Download(url="https://example.com")
    download_id = repo.save(download)
    
    assert download_id > 0
    
    retrieved = repo.get_by_id(download_id)
    assert retrieved.url == "https://example.com"
```

## Fixtures

### Standard Fixtures

| Fixture | Scope | Description |
|---------|-------|-------------|
| `tmp_path` | function | Temporary directory for test files |
| `qapp` | session | QApplication instance |

### Custom Fixtures

Create fixtures in `tests/conftest.py`:

```python
import pytest
from src.data.database import Database
from src.services.config_service import ConfigService

@pytest.fixture
def test_db(tmp_path):
    """Create test database."""
    Database.reset_instance()
    db = Database(db_path=str(tmp_path / "test.db"))
    yield db
    Database.reset_instance()

@pytest.fixture
def config_service(tmp_path):
    """Create test config service."""
    ConfigService.reset_instance()
    config = ConfigService(config_path=str(tmp_path / "config.json"))
    yield config
    ConfigService.reset_instance()
```

## Mocking

### Mocking yt-dlp

```python
from unittest.mock import patch, MagicMock

def test_download_with_mocked_ytdlp():
    """Test download with mocked yt-dlp."""
    mock_ydl = MagicMock()
    mock_ydl.extract_info.return_value = {"title": "Test Video"}
    
    with patch('yt_dlp.YoutubeDL', return_value=mock_ydl):
        worker = DownloadWorker("https://example.com", config)
        # Test worker behavior
```

### Mocking FFmpeg

```python
from unittest.mock import patch

def test_ffmpeg_conversion():
    """Test FFmpeg conversion with mocked subprocess."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        # Test conversion
```

## Coverage Goals

Target coverage by component:

| Component | Target | Key Files |
|-----------|--------|-----------|
| Core | 80%+ | managers, workers |
| Services | 90%+ | config_service, session_service |
| Data | 85%+ | repositories, models |
| UI | 60%+ | pages, components |

## Continuous Integration

Example GitHub Actions workflow (`.github/workflows/test.yml`):

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov pytest-qt
      - run: pytest tests/ --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## Writing Tests

### Test Naming

Follow pytest conventions:
- `test_<module>_<function>.py` for test files
- `test_<function>_<scenario>` for test functions

```python
def test_config_get_with_default():
    """Test getting config value with default."""

def test_download_manager_cancel_all():
    """Test cancelling all downloads."""
```

### Test Organization

1. Arrange - Set up test fixtures and mocks
2. Act - Execute the functionality under test
3. Assert - Verify expected outcomes

```python
def test_download_completed_signal():
    """Test download completed signal emission."""
    # Arrange
    manager = DownloadManager(mock_repo)
    mock_worker = Mock()
    
    # Act
    manager._on_worker_finished(url)
    
    # Assert
    manager.download_completed.emit.assert_called_once()
```

## See Also

- [Build, Test, Run](./BUILD_TEST_RUN.md) - Build and run procedures
- [API Reference](./API_REFERENCE.md) - Detailed API documentation
- [Architecture Overview](./ARCHITECTURE.md) - System architecture
