# Known Issues and Technical Debt

Documented issues and planned improvements for yt-dlp GUI.

## Known Issues

### Application Issues

#### Type Annotation Incompleteness

**Severity**: Low  
**Status**: Ongoing

The codebase has incomplete type annotations in some areas:
- `src/main.py`: Missing argument for `session_service` in initialization
- Repository methods returning `int` may return `None` in edge cases

**Mitigation**: Runtime validation exists; type checkers report warnings.

#### Event Filter Parameter Naming

**Severity**: Low  
**Status**: Known PyCharm/Qt issue

In `src/ui/main_window.py`, the `eventFilter` method has parameter names that differ from parent class:
- Parent: `a0`, `a1`
- Implementation: `obj`, `event`

This is a known PyQt6 quirk and does not affect functionality.

#### Menu Bar Type Hints

**Severity**: Low  
**Status**: Known PyQt6 limitation

Menu bar methods (`addMenu`, `addAction`, `addSeparator`) may show type checker warnings when called on `menuBar()` return type. This is a PyQt6 type stub limitation and does not affect functionality.

### Download Manager Issues

#### Force Termination Timeout

**Severity**: Medium  
**Description**: When cancelling downloads, workers have a 5-second timeout before force termination. During this time, the UI may appear unresponsive.

**Workaround**: None; this is by design to allow graceful shutdown.

#### Speed Aggregation Edge Case

**Severity**: Low  
**Description**: Aggregate speed calculation may briefly show 0 if all workers complete simultaneously.

**Workaround**: Speed is recalculated on each progress update.

### Conversion Manager Issues

#### Single Conversion at a Time

**Severity**: Low  
**Description**: Conversion manager only processes one conversion at a time (`max_concurrent = 1`) due to FFmpeg resource constraints.

**Mitigation**: Batch operations queue efficiently.

### Session Recovery Issues

#### Session Not Restored on All Crashes

**Severity**: Low  
**Description**: If the application crashes in a way that prevents lock file cleanup, the crash detection may not trigger on next startup.

**Workaround**: Delete `data/.running.lock` to clear stale state.

### FFmpeg Detection

#### FFmpeg Not in PATH

**Severity**: Medium  
**Description**: If FFmpeg is not in the system PATH, the application warns but continues to function for download operations.

**Workaround**: Install FFmpeg and ensure it's in PATH, or install via:
- macOS: `brew install ffmpeg`
- Windows: Download from ffmpeg.org
- Linux: `sudo apt install ffmpeg`

### Platform-Specific Issues

#### Quick Look Only on macOS

**Severity**: Low  
**Description**: Quick Look preview is only available on macOS. On Windows/Linux, pressing space shows a tooltip instead.

**Workaround**: None; this is intentional platform differentiation.

#### Windows Console Window

**Severity**: Low  
**Description**: On Windows, subprocess calls for FFmpeg may briefly show console windows.

**Mitigation**: `get_subprocess_kwargs()` in `platform_utils.py` attempts to minimize this.

## Technical Debt

### Code Quality

#### Qt Designer Not Used

**Priority**: Low  
**Description**: UI code is hand-written rather than using Qt Designer (`.ui` files).

**Rationale**: More flexibility in code-based UI, avoids .ui file versioning issues.

#### Missing Abstract Base Classes

**Priority**: Low  
**Description**: Manager and Worker classes could benefit from abstract base classes to enforce interface contracts.

**Rationale**: Simplicity; interface is well-documented.

#### No Type Checking CI

**Priority**: Medium  
**Description**: No mypy/pytest-ci type checking in CI pipeline.

**Mitigation**: Manual type checking during code review.

### Architecture

#### Singleton Overuse

**Priority**: Low  
**Description**: Singletons used for Database, ConfigService, ThemeEngine make testing more difficult.

**Rationale**: Global state is appropriate for these services.

#### Circular Import Risk

**Priority**: Medium  
**Description**: Some imports between modules may cause circular import issues during testing.

**Mitigation**: Lazy imports where needed (e.g., MatchManager imports MatchWorker dynamically).

#### Worker Thread Safety

**Priority**: Low  
**Description**: Workers modify shared state via signals; the manager layer handles this correctly, but the pattern could be cleaner.

**Rationale**: Qt's signal-slot mechanism is inherently thread-safe.

### Testing

#### UI Test Coverage

**Priority**: Medium  
**Description**: UI component tests have lower coverage (60% target) compared to business logic.

**Mitigation**: Manual testing supplements automated tests.

#### No Integration Tests

**Priority**: Medium  
**Description**: No end-to-end integration tests covering full user workflows.

**Rationale**: PyQt6 testing complexity; manual testing preferred for UI.

#### Mocking yt-dlp

**Priority**: Low  
**Description**: Tests for DownloadWorker would benefit from better yt-dlp mocking.

**Rationale**: Current tests use integration approach where possible.

### Configuration

#### Config Migration Not Implemented

**Priority**: Low  
**Description**: ConfigService has migration infrastructure but no actual migrations have been needed yet.

**Rationale**: Configuration has remained stable.

#### No Config Validation

**Priority**: Medium  
**Description**: ConfigService doesn't validate values (e.g., `concurrent_limit` should be 1-20).

**Mitigation**: UI enforces valid ranges.

### Database

#### No Database Migrations

**Priority**: Low  
**Description**: Database uses a simple version-based migration approach, but migrations are handled manually.

**Rationale**: Simple schema; changes are infrequent.

#### Missing Indices

**Priority**: Low  
**Description**: Some queries may benefit from additional indices.

**Mitigation**: Key queries have appropriate indices.

### Dependencies

#### Unpinned Versions

**Priority**: Medium  
**Description**: `requirements.txt` doesn't pin versions, leading to potential compatibility issues.

**Fix**: Add version pins for reproducibility:
```
PyQt6==6.7.0
yt-dlp==2024.4.9
playwright==1.42.0
send2trash==1.8.2
qtawesome==6.6.0
```

## Planned Improvements

### High Priority

1. **Type Checking CI**: Add mypy to CI pipeline
2. **Dependency Pins**: Add version pins to requirements.txt
3. **Integration Tests**: Add basic end-to-end tests

### Medium Priority

4. **Config Validation**: Add value validation in ConfigService
5. **Better Error Messages**: Improve user-facing error messages
6. **Progress Persistence**: Save conversion/trim progress to database

### Low Priority

7. **Qt Designer Migration**: Consider .ui files for complex widgets
8. **Plugin System**: Allow third-party extensions
9. **Cloud Sync**: Sync config across devices
10. **Portable Mode**: Better support for USB drive deployment

## Reporting Issues

To report issues:
1. Check existing issues on GitHub
2. Include reproduction steps
3. Attach relevant logs from `data/logs/`
4. Specify platform and Python version

## See Also

- [CONTRIBUTING](./CONTRIBUTING.md) - Contribution guidelines
- [Testing Guide](./TESTING.md) - Testing documentation
- [Architecture Overview](./ARCHITECTURE.md) - System architecture
