# Agent Guidelines

This document defines roles, skills, and workflows for AI agents working on the yt-dlp GUI project.

## Project Overview

**Project**: yt-dlp GUI  
**Type**: Desktop Application (Python/PyQt6)  
**Purpose**: Cross-platform video downloading GUI using yt-dlp

## Agent Roles

### Backend Developer

**Focus Areas**:
- `src/core/` - Managers and workers
- `src/data/` - Database and repositories
- `src/services/` - Business logic services
- `src/utils/` - Utility functions

**Skills Required**:
- Python 3.10+ with type hints
- PyQt6 signal-slot patterns
- SQLite and threading concepts
- yt-dlp integration

**Key Files**:
- `src/core/download_manager.py` - Download queue orchestration
- `src/core/download_worker.py` - Single URL download worker
- `src/core/conversion_manager.py` - FFmpeg conversion
- `src/data/database.py` - SQLite singleton
- `src/services/config_service.py` - JSON configuration

**Patterns to Follow**:
```python
class MyManager(QObject):
    """Manager docstring."""
    
    # Signals
    started = pyqtSignal()
    completed = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
    
    def start(self) -> None:
        """Start operation."""
        self.started.emit()
        self._worker = MyWorker()
        self._worker.completed.connect(self._on_completed)
        self._worker.start()
    
    def _on_completed(self, success: bool) -> None:
        self.completed.emit(success)
```

### Frontend Developer

**Focus Areas**:
- `src/ui/` - User interface components
- `src/ui/pages/` - Feature pages
- `src/ui/widgets/` - Custom widgets
- `src/ui/theme/` - Theming system

**Skills Required**:
- PyQt6 widget development
- Qt Style Sheets (QSS)
- Signal-slot patterns
- Responsive layout design

**Key Files**:
- `src/ui/main_window.py` - Main window orchestrator
- `src/ui/shell.py` - Shell layout with sidebar
- `src/ui/theme/theme_engine.py` - Theme management
- `src/ui/pages/*.py` - Feature pages

**Patterns to Follow**:
```python
class MyPage(QWidget):
    """Feature page docstring."""
    
    action_requested = pyqtSignal()  # Public signal
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup UI components."""
        layout = QVBoxLayout(self)
        # Add widgets...
```

### Test Engineer

**Focus Areas**:
- `tests/` - Test suite
- pytest fixtures
- PyQt6 testing with qtbot

**Skills Required**:
- pytest framework
- unittest.mock usage
- PyQt6 testing patterns
- Coverage analysis

**Key Files**:
- `tests/conftest.py` - Shared fixtures
- `tests/test_*.py` - Test files

**Patterns to Follow**:
```python
def test_manager_action(monkeypatch):
    """Test manager action."""
    mock_repo = Mock()
    manager = MyManager(mock_repo)
    
    monkeypatch.setattr(manager, '_spawn_workers', lambda: None)
    manager.start()
    
    assert manager.is_running

def test_widget(qtbot):
    """Test widget interaction."""
    widget = MyWidget()
    qtbot.addWidget(widget)
    qtbot.click(widget.button)
```

### Documentation Specialist

**Focus Areas**:
- `docs/` - Documentation files
- `AGENTS.md` - This file
- docstrings
- README files

**Skills Required**:
- Markdown formatting
- Mermaid diagram syntax
- Technical writing

## Skill Matrix

| Skill | Backend | Frontend | Test | Docs |
|-------|---------|----------|------|------|
| Python 3.10+ | Expert | Proficient | Expert | Proficient |
| PyQt6 | Proficient | Expert | Expert | Basic |
| SQLite | Expert | Basic | Proficient | Basic |
| Testing | Proficient | Proficient | Expert | Basic |
| Qt/QSS | Basic | Expert | Proficient | Basic |
| yt-dlp API | Expert | Basic | Proficient | Basic |
| FFmpeg | Proficient | Basic | Proficient | Basic |

## Workflow Guidelines

### Before Making Changes

1. **Read the relevant documentation**:
   - Architecture: `docs/ARCHITECTURE.md`
   - Module details: `docs/MODULES.md`
   - API reference: `docs/API_REFERENCE.md`

2. **Understand the existing code patterns**:
   - Check similar managers/workers for patterns
   - Look at test files for testing patterns
   - Review UI components for styling patterns

3. **Check for related code**:
   - Search for relevant patterns using grep
   - Check if similar functionality exists

### During Development

1. **Follow naming conventions**:
   - Classes: PascalCase (`DownloadManager`)
   - Methods: snake_case (`start_downloads`)
   - Constants: UPPER_SNAKE (`DEFAULT_CONCURRENT_LIMIT`)
   - Private: _prefix (`_config`)

2. **Add appropriate documentation**:
   - Docstrings for public classes and methods
   - Comments for complex logic
   - Update docs for significant changes

3. **Test your changes**:
   - Run relevant tests: `pytest tests/test_file.py -v`
   - Check for type errors
   - Verify UI still works

### After Making Changes

1. **Verify tests pass**:
   ```bash
   pytest tests/ -v
   ```

2. **Run lint/type check** (if configured):
   ```bash
   mypy src/
   ```

3. **Update documentation**:
   - Update relevant docs in `docs/`
   - Add docstrings to new code
   - Update this AGENTS.md if adding new patterns

## File Organization

```
ytdlp-gui/
├── src/
│   ├── main.py              # Entry point
│   ├── core/               # Backend logic
│   │   ├── *_manager.py   # Managers (orchestration)
│   │   └── *_worker.py    # Workers (QThread)
│   ├── data/               # Data layer
│   │   ├── database.py    # SQLite singleton
│   │   ├── models.py      # Dataclasses
│   │   └── repositories/  # Data access
│   ├── services/           # Business services
│   ├── ui/                # Interface
│   │   ├── pages/        # Feature pages
│   │   ├── components/   # Shared components
│   │   ├── widgets/      # Custom widgets
│   │   └── theme/        # Theming
│   └── utils/            # Utilities
├── tests/                 # Test suite
│   ├── conftest.py       # Shared fixtures
│   └── test_*.py        # Test files
├── docs/                 # Documentation
│   ├── README.md         # Project overview
│   ├── ARCHITECTURE.md   # Architecture
│   ├── MODULES.md        # Module catalog
│   ├── API_REFERENCE.md  # API docs
│   └── ...               # Other docs
└── AGENTS.md             # This file
```

## Key Abstractions

### Managers (Orchestrators)

Managers coordinate workers and business logic:
- Inherit from `QObject`
- Define signals for UI communication
- Create and manage worker threads
- Handle business rules and state

### Workers (Background Tasks)

Workers perform operations in QThread:
- Inherit from `QThread`
- Define signals for progress/results
- Implement `run()` method
- Handle cancellation

### Services (Singletons)

Services provide application-wide functionality:
- Singleton pattern via `__new__`
- Thread-safe operations
- State management

### Repositories (Data Access)

Repositories abstract database operations:
- CRUD methods for entities
- Handle database connections
- Return domain objects

## Common Tasks

### Adding a New Manager

1. Create `src/core/new_feature_manager.py`
2. Define signals
3. Implement manager class
4. Add to `MainWindow._setup_ui()`
5. Add tests in `tests/test_new_feature_manager.py`

### Adding a New Page

1. Create `src/ui/pages/new_page.py`
2. Inherit from `QWidget`
3. Implement `_setup_ui()`
4. Register in `MainWindow._setup_ui()`:
   ```python
   self.new_page = NewPage()
   self.shell.register_tool("new_feature", self.new_page)
   ```
5. Add tests

### Adding a New Widget

1. Create `src/ui/widgets/new_widget.py`
2. Inherit from appropriate base class
3. Define public signals
4. Implement widget
5. Import and use in pages

## Testing Strategy

### Unit Tests

Test individual components in isolation:
```python
def test_manager_method():
    manager = Manager(mock_repo)
    result = manager.method()
    assert result == expected
```

### Integration Tests

Test component interactions:
```python
def test_manager_worker_interaction(mocker):
    manager = Manager(mock_repo)
    mocker.patch('Worker.start')
    manager.start()
    assert manager.is_running
```

### UI Tests

Test widget behavior:
```python
def test_widget_click(qtbot):
    widget = MyWidget()
    qtbot.addWidget(widget)
    qtbot.click(widget.button)
    assert widget.clicked
```

## Code Review Checklist

- [ ] Type hints on all public methods
- [ ] Docstrings on classes and public methods
- [ ] Tests for new functionality
- [ ] No obvious bugs or edge cases
- [ ] Follows naming conventions
- [ ] No sensitive data in logs (use URL redaction)
- [ ] Thread safety considered
- [ ] Documentation updated

## Security Considerations

### URL Redaction

Always use URL redaction in logs:
```python
from src.utils.url_redaction import redact_url
logger.info(f"Downloading: {redact_url(url)}")
```

### No Secrets in Code

Never commit:
- API keys
- Passwords
- Cookie contents
- Personal information

## See Also

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Module Catalog](docs/MODULES.md)
- [API Reference](docs/API_REFERENCE.md)
- [Contributing](docs/CONTRIBUTING.md)
- [Testing Guide](docs/TESTING.md)