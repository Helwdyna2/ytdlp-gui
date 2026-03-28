# Contributing

Guidelines for contributing to yt-dlp GUI.

## Code Style

### Python Version

- Python 3.10+
- Use type hints for function signatures
- Use `Optional[T]` instead of `T | None`

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `DownloadManager` |
| Methods/Functions | snake_case | `start_downloads()` |
| Variables | snake_case | `concurrent_limit` |
| Constants | UPPER_SNAKE | `DEFAULT_CRF` |
| Private members | _prefix | `_config_lock` |
| Qt Signals | snake_case | `download_started` |
| Qt Slots | snake_case | `_on_download_started()` |

### Imports

Organize imports in this order:
1. Standard library
2. Third-party
3. Local application

```python
# Standard library
import logging
from pathlib import Path
from typing import List, Optional

# Third-party
from PyQt6.QtCore import QObject, pyqtSignal

# Local application
from src.data.models import Download
from src.services.config_service import ConfigService
```

### Docstrings

Use Google-style docstrings:

```python
def start_downloads(self, urls: List[str], config: OutputConfig) -> None:
    """
    Start downloading URLs.

    Args:
        urls: List of URLs to download.
        config: Download configuration.

    Raises:
        ValueError: If urls is empty or config is invalid.
    """
```

## Git Workflow

### Branch Naming

```
feature/add-convert-page
bugfix/fix-download-crash
refactor/sort-manager
docs/update-readme
```

### Commits

Follow conventional commits:

```
feat: add video conversion page
fix: prevent crash on invalid URL
docs: update API documentation
refactor: simplify manager initialization
test: add tests for conversion manager
```

### Pull Requests

1. Create a feature branch
2. Make changes with small, focused commits
3. Add tests for new functionality
4. Ensure all tests pass
5. Update documentation as needed
6. Request review

## Testing Requirements

### Coverage Goals

| Component | Minimum |
|-----------|---------|
| Core (managers, workers) | 80% |
| Services | 90% |
| Data layer | 85% |
| UI | 60% |

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch

def test_manager_action():
    """Test a specific manager action."""
    # Arrange
    mock_repo = Mock()
    manager = MyManager(mock_repo)
    
    # Act
    result = manager.do_action()
    
    # Assert
    assert result.expected_value
```

### PyQt6 Testing

```python
import pytest
from PyQt6.QtWidgets import QApplication

@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

def test_widget(qtbot, qapp):
    """Test widget with qtbot."""
    widget = MyWidget()
    qtbot.addWidget(widget)
    # Test interactions
```

## Code Organization

### New Manager

```python
# src/core/new_feature_manager.py
from PyQt6.QtCore import QObject, pyqtSignal

class NewFeatureManager(QObject):
    """Brief description."""
    
    # Signals
    started = pyqtSignal()
    completed = pyqtSignal(bool)  # success
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
    
    def start(self) -> None:
        """Start the operation."""
        self.started.emit()
        self._worker = NewFeatureWorker()
        self._worker.completed.connect(self._on_completed)
        self._worker.start()
    
    def _on_completed(self, success: bool) -> None:
        """Handle completion."""
        self.completed.emit(success)
```

### New Worker

```python
# src/core/new_feature_worker.py
from PyQt6.QtCore import QThread, pyqtSignal

class NewFeatureWorker(QThread):
    """Worker for background tasks."""
    
    completed = pyqtSignal(bool)
    progress = pyqtSignal(int)  # percent
    
    def run(self) -> None:
        """Execute in worker thread."""
        try:
            # Do work
            self.completed.emit(True)
        except Exception as e:
            self.completed.emit(False)
```

### New Page

```python
# src/ui/pages/new_page.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

class NewPage(QWidget):
    """Brief description."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("New Feature"))
```

### New Widget

```python
# src/ui/widgets/new_widget.py
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton

class NewWidget(QWidget):
    """Brief description."""
    
    action_clicked = pyqtSignal()  # Signal for user actions
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup UI components."""
        layout = QHBoxLayout(self)
        self.button = QPushButton("Action")
        self.button.clicked.connect(self.action_clicked.emit)
        layout.addWidget(self.button)
```

## Documentation

### Docstrings

Required for:
- Public classes
- Public methods
- Complex algorithms

### README Updates

Update when:
- New feature added
- Dependencies change
- Build process changes

### API Documentation

Update `docs/API_REFERENCE.md` when:
- New public API added
- Existing API changes
- New signals added to managers

## File Organization

### Source Files

```
src/
├── main.py              # Main entry point
├── core/                # Business logic
│   ├── *_manager.py    # Managers
│   └── *_worker.py     # Workers
├── data/               # Data layer
│   ├── database.py
│   ├── models.py
│   └── repositories/
├── services/           # Services
├── ui/                 # Interface
│   ├── pages/
│   ├── components/
│   ├── widgets/
│   └── theme/
└── utils/             # Utilities
```

### Test Files

```
tests/
├── conftest.py         # Shared fixtures
└── test_*.py          # One file per module
```

## Performance Considerations

### Threading

- Use QThread for background operations
- Never block the main thread
- Use signals for cross-thread communication

### Database

- Use thread-local connections
- Batch operations when possible
- Use indices for frequently queried columns

### UI

- Debounce rapid updates
- Limit log entries
- Use model/view for large lists

## Error Handling

### Managers

```python
def _on_error(self, error: str) -> None:
    """Handle error from worker."""
    logger.error(f"Operation failed: {error}")
    self.error.emit(error)
```

### Workers

```python
def run(self) -> None:
    try:
        # Do work
        self.completed.emit(True)
    except Exception as e:
        logger.exception("Worker error")
        self.completed.emit(False)
```

### UI

```python
try:
    # Risky operation
except Exception as e:
    QMessageBox.warning(self, "Error", str(e))
```

## Security Considerations

### URL Redaction

Always redact URLs in logs:

```python
from src.utils.url_redaction import redact_url

logger.info(f"Downloading: {redact_url(url)}")
```

### Cookies

Never log cookie contents.

### File Paths

Validate file paths before use.

## Questions

For questions or discussions:
- Open an issue on GitHub
- Check existing issues and documentation

## See Also

- [Architecture Overview](./ARCHITECTURE.md) - System architecture
- [API Reference](./API_REFERENCE.md) - API documentation
- [Testing Guide](./TESTING.md) - Testing documentation
