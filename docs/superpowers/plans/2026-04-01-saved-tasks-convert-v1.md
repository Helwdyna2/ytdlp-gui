# Saved Tasks Convert V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first shippable Saved Tasks slice: shared task persistence, startup/manual recovery UI, and full Convert pause/resume queue recovery with processed-file detection.

**Architecture:** Add a generic `saved_tasks` persistence layer plus a small service for listing, saving, recovering, and deleting tasks. Keep Convert's runtime in `ConversionManager`, but move its queue state into durable models/helpers so `ConvertPage` can persist, restore, reorder, skip, and resume batches without assuming mid-file FFmpeg resume.

**Tech Stack:** Python, PyQt6, SQLite, pytest, pytest-qt, FFmpeg worker flow already present in `src/core`

---

## Scope Check

The approved design covers future Trim, Match, Rename, and Download adapters too, but this implementation plan deliberately stops at the first independently shippable slice:

- shared Saved Tasks storage and listing
- startup recovery prompt and manual Saved Tasks dialog
- Convert queue persistence, pause/put-aside, restore, reorder, skip, force-start-next, and processed-file detection

Trim and other tool adapters should be planned separately after this slice ships.

## File Structure

- Modify: `src/data/models.py`
  Add `SavedTaskStatus`, `SavedTask`, and JSON-backed row parsing helpers.

- Modify: `src/data/database.py`
  Add schema migration v4 for the `saved_tasks` table and indexes.

- Create: `src/data/repositories/saved_task_repository.py`
  CRUD and listing operations for saved tasks.

- Modify: `src/data/repositories/__init__.py`
  Export the new repository.

- Create: `src/services/saved_task_service.py`
  Small orchestration service for save/update/delete/latest-recoverable/list-unfinished operations.

- Create: `src/core/convert_saved_task.py`
  Convert queue item dataclasses, serialization helpers, and expected-output detection.

- Modify: `src/core/conversion_manager.py`
  Add pause semantics, queue ordering hooks, and persistence-friendly signals/state access.

- Create: `src/ui/widgets/convert_queue_widget.py`
  Render queue rows with status styling and emit reorder/skip/prioritize actions.

- Create: `src/ui/widgets/saved_tasks_dialog.py`
  Manual Saved Tasks list dialog for restore/delete/open actions.

- Modify: `src/ui/pages/convert_page.py`
  Replace transient list/job handling with durable queue state and Saved Task syncing.

- Modify: `src/ui/main_window.py`
  Add Saved Tasks menu entry and startup restore path for saved convert tasks.

- Modify: `src/main.py`
  Initialize `SavedTaskService` and route startup recovery to the new flow.

- Test: `tests/test_saved_task_repository.py`
  Repository and migration coverage.

- Test: `tests/test_convert_saved_task.py`
  Queue serialization and processed-file detection coverage.

- Modify: `tests/test_convert_page.py`
  Convert pause/resume/reorder/skip/status coverage.

- Modify: `tests/test_main_window_workbench.py`
  Saved Tasks dialog/menu and startup restore coverage.

### Task 1: Add Saved Task Persistence

**Files:**
- Modify: `src/data/models.py`
- Modify: `src/data/database.py`
- Create: `src/data/repositories/saved_task_repository.py`
- Modify: `src/data/repositories/__init__.py`
- Test: `tests/test_saved_task_repository.py`

- [ ] **Step 1: Write the failing repository tests**

```python
from src.data.database import Database
from src.data.models import SavedTask, SavedTaskStatus
from src.data.repositories.saved_task_repository import SavedTaskRepository


def test_saved_task_repository_round_trips_payload(tmp_path):
    Database.reset_instance()
    db = Database(str(tmp_path / "saved_tasks.db"))
    repo = SavedTaskRepository(db)

    task = SavedTask(
        task_type="convert",
        title="Batch convert",
        status=SavedTaskStatus.PAUSED,
        payload={"items": [{"input_path": "/tmp/a.mp4"}]},
        summary={"completed": 1, "total": 3},
    )

    created = repo.create(task)
    fetched = repo.get_by_id(created.id)

    assert fetched is not None
    assert fetched.payload["items"][0]["input_path"] == "/tmp/a.mp4"
    assert fetched.summary == {"completed": 1, "total": 3}


def test_saved_task_repository_returns_latest_unfinished(tmp_path):
    Database.reset_instance()
    db = Database(str(tmp_path / "saved_tasks.db"))
    repo = SavedTaskRepository(db)

    repo.create(SavedTask(task_type="convert", title="Done", status=SavedTaskStatus.COMPLETED))
    repo.create(SavedTask(task_type="convert", title="Paused", status=SavedTaskStatus.PAUSED))

    latest = repo.get_latest_unfinished()

    assert latest is not None
    assert latest.title == "Paused"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_saved_task_repository.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.data.repositories.saved_task_repository'`

- [ ] **Step 3: Add the model, migration, and repository**

```python
class SavedTaskStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"


@dataclass
class SavedTask:
    task_type: str
    title: str
    id: Optional[int] = None
    status: SavedTaskStatus = SavedTaskStatus.PAUSED
    summary: Dict[str, Any] = field(default_factory=dict)
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_row(cls, row) -> "SavedTask":
        import json

        return cls(
            id=row["id"],
            task_type=row["task_type"],
            title=row["title"],
            status=SavedTaskStatus(row["status"]),
            summary=json.loads(row["summary_json"] or "{}"),
            payload=json.loads(row["payload_json"] or "{}"),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
```

```python
def _migrate_to_v4(self) -> None:
    self.execute(
        """
        CREATE TABLE IF NOT EXISTS saved_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'paused',
            summary_json TEXT NOT NULL DEFAULT '{}',
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT chk_saved_task_status
                CHECK (status IN ('active', 'paused', 'completed', 'failed', 'deleted'))
        )
        """
    )
```

```python
class SavedTaskRepository:
    def __init__(self, db: Optional[Database] = None):
        self._db = db or Database()

    def create(self, task: SavedTask) -> SavedTask:
        payload_json = json.dumps(task.payload)
        summary_json = json.dumps(task.summary)
        cursor = self._db.execute(
            """
            INSERT INTO saved_tasks (task_type, title, status, summary_json, payload_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.task_type,
                task.title,
                task.status.value,
                summary_json,
                payload_json,
                task.created_at.isoformat(),
                task.updated_at.isoformat(),
            ),
        )
        task.id = cursor.lastrowid
        return task

    def update(self, task: SavedTask) -> None:
        self._db.execute(
            """
            UPDATE saved_tasks
            SET title = ?, status = ?, summary_json = ?, payload_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                task.title,
                task.status.value,
                json.dumps(task.summary),
                json.dumps(task.payload),
                datetime.now().isoformat(),
                task.id,
            ),
        )

    def get_by_id(self, task_id: int) -> Optional[SavedTask]:
        row = self._db.fetchone("SELECT * FROM saved_tasks WHERE id = ?", (task_id,))
        return SavedTask.from_row(row) if row else None

    def get_latest_unfinished(self) -> Optional[SavedTask]:
        row = self._db.fetchone(
            """
            SELECT * FROM saved_tasks
            WHERE status IN ('active', 'paused', 'failed')
            ORDER BY updated_at DESC
            LIMIT 1
            """
        )
        return SavedTask.from_row(row) if row else None

    def list_unfinished(self) -> list[SavedTask]:
        rows = self._db.fetchall(
            """
            SELECT * FROM saved_tasks
            WHERE status IN ('active', 'paused', 'failed')
            ORDER BY updated_at DESC
            """
        )
        return [SavedTask.from_row(row) for row in rows]

    def mark_deleted(self, task_id: int) -> bool:
        cursor = self._db.execute(
            """
            UPDATE saved_tasks
            SET status = 'deleted', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (task_id,),
        )
        return cursor.rowcount > 0
```

- [ ] **Step 4: Run the repository tests again**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_saved_task_repository.py -q`
Expected: PASS with `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/data/models.py src/data/database.py src/data/repositories/__init__.py src/data/repositories/saved_task_repository.py tests/test_saved_task_repository.py
git commit -m "feat(data): add saved task persistence"
```

### Task 2: Add Saved Task Service and Recovery Selection

**Files:**
- Create: `src/services/saved_task_service.py`
- Modify: `src/main.py`
- Test: `tests/test_saved_task_repository.py`

- [ ] **Step 1: Write the failing service and startup selection tests**

```python
from src.data.models import SavedTask, SavedTaskStatus
from src.services.saved_task_service import SavedTaskService


def test_saved_task_service_prefers_latest_unfinished_convert(tmp_path):
    Database.reset_instance()
    db = Database(str(tmp_path / "saved_tasks.db"))
    repo = SavedTaskRepository(db)
    service = SavedTaskService(repo)

    repo.create(SavedTask(task_type="convert", title="older", status=SavedTaskStatus.PAUSED))
    repo.create(SavedTask(task_type="convert", title="newer", status=SavedTaskStatus.ACTIVE))

    latest = service.get_latest_recoverable_task()

    assert latest is not None
    assert latest.title == "newer"
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_saved_task_repository.py -q`
Expected: FAIL because `SavedTaskService` does not exist yet

- [ ] **Step 3: Implement the service and wire startup creation**

```python
class SavedTaskService:
    def __init__(self, repository: SavedTaskRepository):
        self._repository = repository

    def save_task(self, task: SavedTask) -> SavedTask:
        if task.id is None:
            return self._repository.create(task)
        self._repository.update(task)
        return task

    def get_latest_recoverable_task(self) -> Optional[SavedTask]:
        return self._repository.get_latest_unfinished()

    def list_unfinished_tasks(self) -> list[SavedTask]:
        return self._repository.list_unfinished()

    def delete_task(self, task_id: int) -> bool:
        return self._repository.mark_deleted(task_id)
```

```python
saved_task_repo = SavedTaskRepository(database)
saved_task_service = SavedTaskService(saved_task_repo)
main_window = MainWindow(
    database,
    session_service,
    saved_task_service=saved_task_service,
)
```

```python
def __init__(
    self,
    database: Database,
    session_service: SessionService,
    saved_task_service: Optional[SavedTaskService] = None,
    parent=None,
):
    super().__init__(parent)
    self.database = database
    self.session_service = session_service
    self.saved_task_service = saved_task_service
```

- [ ] **Step 4: Run the service and workbench tests again**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_saved_task_repository.py -q`
Expected: PASS for the new service assertions

- [ ] **Step 5: Commit**

```bash
git add src/services/saved_task_service.py src/main.py tests/test_saved_task_repository.py
git commit -m "feat(core): add saved task service"
```

### Task 3: Build Convert Queue Serialization and Processed-File Detection

**Files:**
- Create: `src/core/convert_saved_task.py`
- Test: `tests/test_convert_saved_task.py`

- [ ] **Step 1: Write the failing Convert payload tests**

```python
from src.core.convert_saved_task import (
    ConvertQueueItem,
    ConvertQueueItemStatus,
    build_convert_task_payload,
    detect_existing_outputs,
)


def test_build_convert_task_payload_preserves_queue_order():
    items = [
        ConvertQueueItem(item_id="one", input_path="/tmp/1.mp4", output_path="/tmp/out/1.mp4"),
        ConvertQueueItem(item_id="two", input_path="/tmp/2.mp4", output_path="/tmp/out/2.mp4"),
    ]

    payload = build_convert_task_payload(items, {"output_codec": "h264"})

    assert [item["item_id"] for item in payload["items"]] == ["one", "two"]


def test_detect_existing_outputs_marks_non_zero_files_complete(tmp_path):
    output_path = tmp_path / "done.mp4"
    output_path.write_bytes(b"video-bytes")

    item = ConvertQueueItem(
        item_id="done",
        input_path=str(tmp_path / "source.mp4"),
        output_path=str(output_path),
        status=ConvertQueueItemStatus.PENDING,
    )

    updated = detect_existing_outputs([item])

    assert updated[0].status == ConvertQueueItemStatus.COMPLETED
    assert updated[0].detail == "Already processed"
```

- [ ] **Step 2: Run the Convert payload tests to verify they fail**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_convert_saved_task.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.core.convert_saved_task'`

- [ ] **Step 3: Implement the queue item helpers**

```python
class ConvertQueueItemStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    INCOMPLETE = "incomplete"


@dataclass
class ConvertQueueItem:
    item_id: str
    input_path: str
    output_path: str
    display_name: str = ""
    source_root: Optional[str] = None
    status: ConvertQueueItemStatus = ConvertQueueItemStatus.PENDING
    progress_percent: float = 0.0
    detail: str = ""
    error_message: str = ""

    def to_payload(self) -> dict:
        return {
            "item_id": self.item_id,
            "input_path": self.input_path,
            "output_path": self.output_path,
            "display_name": self.display_name,
            "source_root": self.source_root,
            "status": self.status.value,
            "progress_percent": self.progress_percent,
            "detail": self.detail,
            "error_message": self.error_message,
        }
```

```python
def detect_existing_outputs(items: list[ConvertQueueItem]) -> list[ConvertQueueItem]:
    updated: list[ConvertQueueItem] = []
    for item in items:
        output_file = Path(item.output_path)
        if output_file.exists() and output_file.stat().st_size > 0:
            updated.append(
                replace(
                    item,
                    status=ConvertQueueItemStatus.COMPLETED,
                    detail="Already processed",
                    progress_percent=100.0,
                )
            )
        else:
            updated.append(item)
    return updated
```

```python
def load_convert_task_payload(payload: dict) -> list[ConvertQueueItem]:
    items: list[ConvertQueueItem] = []
    for raw_item in payload.get("items", []):
        items.append(
            ConvertQueueItem(
                item_id=raw_item["item_id"],
                input_path=raw_item["input_path"],
                output_path=raw_item["output_path"],
                display_name=raw_item.get("display_name", ""),
                source_root=raw_item.get("source_root"),
                status=ConvertQueueItemStatus(raw_item.get("status", "pending")),
                progress_percent=raw_item.get("progress_percent", 0.0),
                detail=raw_item.get("detail", ""),
                error_message=raw_item.get("error_message", ""),
            )
        )
    return items
```

- [ ] **Step 4: Run the Convert payload tests again**

Run: `PYTHONPATH=. .venv/bin/pytest tests/test_convert_saved_task.py -q`
Expected: PASS with `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/core/convert_saved_task.py tests/test_convert_saved_task.py
git commit -m "feat(convert): add saved task queue payload helpers"
```

### Task 4: Replace Convert's Transient List with a Queue Widget

**Files:**
- Create: `src/ui/widgets/convert_queue_widget.py`
- Modify: `src/ui/pages/convert_page.py`
- Modify: `tests/test_convert_page.py`

- [ ] **Step 1: Write the failing UI tests for queue status and actions**

```python
def test_convert_page_shows_completed_item_status(qapp, fake_config_service, fake_ffprobe_worker):
    from src.ui.pages.convert_page import ConvertPage

    page = ConvertPage()
    page._queue_widget.set_items(
        [
            ConvertQueueItem(
                item_id="done",
                input_path="/tmp/a.mp4",
                output_path="/tmp/out/a.mp4",
                display_name="a.mp4",
                status=ConvertQueueItemStatus.COMPLETED,
                detail="Already processed",
            )
        ]
    )

    assert page._queue_widget.item_status_text("done") == "Already processed"


def test_convert_page_prioritize_selected_item_moves_it_first(qapp, fake_config_service, fake_ffprobe_worker):
    from src.ui.pages.convert_page import ConvertPage

    page = ConvertPage()
    page._queue_widget.set_items(
        [
            ConvertQueueItem(
                item_id="one",
                input_path="/tmp/1.mp4",
                output_path="/tmp/out/1.mp4",
                display_name="1.mp4",
            ),
            ConvertQueueItem(
                item_id="two",
                input_path="/tmp/2.mp4",
                output_path="/tmp/out/2.mp4",
                display_name="2.mp4",
            ),
        ]
    )

    page._queue_widget.select_item("two")
    page._queue_widget.prioritize_selected()

    assert [item.item_id for item in page._queue_widget.items()] == ["two", "one"]
```

- [ ] **Step 2: Run the Convert page tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/test_convert_page.py -q`
Expected: FAIL because `ConvertPage` still uses the old transient file/job widgets

- [ ] **Step 3: Create the queue widget and swap it into `ConvertPage`**

```python
class ConvertQueueWidget(QWidget):
    reorder_requested = pyqtSignal(list)
    skip_requested = pyqtSignal(str)
    prioritize_requested = pyqtSignal(str)

    def set_items(self, items: list[ConvertQueueItem]) -> None:
        self._items = list(items)
        self._list_widget.clear()
        for item in self._items:
            row = QListWidgetItem(f"{item.display_name} — {item.detail or item.status.value.title()}")
            row.setData(Qt.ItemDataRole.UserRole, item.item_id)
            if item.status == ConvertQueueItemStatus.COMPLETED:
                row.setForeground(QColor("#2e7d32"))
            self._list_widget.addItem(row)

    def items(self) -> list[ConvertQueueItem]:
        return list(self._items)

    def select_item(self, item_id: str) -> None:
        for row_index in range(self._list_widget.count()):
            row = self._list_widget.item(row_index)
            if row.data(Qt.ItemDataRole.UserRole) == item_id:
                self._list_widget.setCurrentRow(row_index)
                return

    def prioritize_selected(self) -> None:
        current = self._list_widget.currentItem()
        if current is None:
            return
        item_id = current.data(Qt.ItemDataRole.UserRole)
        self.prioritize_requested.emit(item_id)

    def item_status_text(self, item_id: str) -> str:
        for row_index in range(self._list_widget.count()):
            row = self._list_widget.item(row_index)
            if row.data(Qt.ItemDataRole.UserRole) == item_id:
                return row.text().split(" — ", 1)[1]
        return ""
```

```python
self._queue_widget = ConvertQueueWidget()
files_panel.body_layout.addWidget(self._queue_widget)
self._queue_items: list[ConvertQueueItem] = []
self._queue_widget.reorder_requested.connect(self._on_queue_reordered)
self._queue_widget.skip_requested.connect(self._on_queue_item_skipped)
self._queue_widget.prioritize_requested.connect(self._on_queue_item_prioritized)

def _on_queue_reordered(self, item_ids: list[str]) -> None:
    by_id = {item.item_id: item for item in self._queue_items}
    self._queue_items = [by_id[item_id] for item_id in item_ids if item_id in by_id]
    self._queue_widget.set_items(self._queue_items)

def _on_queue_item_skipped(self, item_id: str) -> None:
    for item in self._queue_items:
        if item.item_id == item_id and item.status == ConvertQueueItemStatus.PENDING:
            item.status = ConvertQueueItemStatus.SKIPPED
            item.detail = "Skipped by user"
    self._queue_widget.set_items(self._queue_items)

def _on_queue_item_prioritized(self, item_id: str) -> None:
    prioritized = [item for item in self._queue_items if item.item_id == item_id]
    remaining = [item for item in self._queue_items if item.item_id != item_id]
    self._queue_items = prioritized + remaining
    self._queue_widget.set_items(self._queue_items)
```

- [ ] **Step 4: Run the Convert page tests again**

Run: `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/test_convert_page.py -q`
Expected: PASS for the new queue status and prioritize cases, with existing Convert-page tests still green

- [ ] **Step 5: Commit**

```bash
git add src/ui/widgets/convert_queue_widget.py src/ui/pages/convert_page.py tests/test_convert_page.py
git commit -m "feat(convert): add editable queue widget"
```

### Task 5: Persist Convert State Through Pause, Resume, and Completion

**Files:**
- Modify: `src/core/conversion_manager.py`
- Modify: `src/ui/pages/convert_page.py`
- Modify: `tests/test_convert_page.py`

- [ ] **Step 1: Write the failing pause/resume tests**

```python
def test_convert_page_pause_marks_active_item_incomplete(
    qapp, fake_config_service, fake_ffprobe_worker, fake_conversion_manager
):
    from src.ui.pages.convert_page import ConvertPage

    page = ConvertPage()
    page.restore_saved_task(
        {"tool": "convert", "items": [
                {"item_id": "active", "input_path": "/tmp/a.mp4", "output_path": "/tmp/out/a.mp4", "display_name": "a.mp4", "status": "processing"},
                {"item_id": "next", "input_path": "/tmp/b.mp4", "output_path": "/tmp/out/b.mp4", "display_name": "b.mp4", "status": "pending"},
            ], "config": {"output_codec": "h264", "output_dir": "/tmp/out"}}
    )

    page._active_queue_item_id = "active"
    page._on_pause_put_aside()

    assert page._queue_items[0].status.value == "incomplete"


def test_convert_page_resume_skips_completed_and_restarts_incomplete(
    qapp, fake_config_service, fake_ffprobe_worker, fake_conversion_manager
):
    from src.ui.pages.convert_page import ConvertPage

    page = ConvertPage()
    page.restore_saved_task(
        {"tool": "convert", "items": [
                {"item_id": "done", "input_path": "/tmp/a.mp4", "output_path": "/tmp/out/a.mp4", "display_name": "a.mp4", "status": "completed"},
                {"item_id": "retry", "input_path": "/tmp/b.mp4", "output_path": "/tmp/out/b.mp4", "display_name": "b.mp4", "status": "incomplete"},
            ], "config": {"output_codec": "h264", "output_dir": "/tmp/out"}}
    )

    page._resume_saved_task()

    manager = fake_conversion_manager.instances[-1]
    assert manager.added_files == ["/tmp/b.mp4"]
```

- [ ] **Step 2: Run the focused Convert tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/test_convert_page.py -q`
Expected: FAIL because pause/put-aside and resume are not implemented

- [ ] **Step 3: Implement persistence-aware pause/resume flow**

```python
def pause_all(self) -> None:
    with QMutexLocker(self._mutex):
        for worker in list(self._active_workers.values()):
            worker.cancel()
        for job in self._pending_jobs:
            if job.status == ConversionStatus.PENDING:
                job.status = ConversionStatus.CANCELLED
                self._repository.update(job)
```

```python
def _on_pause_put_aside(self) -> None:
    if self._conversion_manager:
        self._conversion_manager.cancel_all()

    for item in self._queue_items:
        if item.item_id == self._active_queue_item_id:
            item.status = ConvertQueueItemStatus.INCOMPLETE
            item.detail = "Will restart on resume"
            item.progress_percent = 0.0

    self._persist_saved_task(status="paused")
    self._restore_controls_after_stop()
```

```python
def _resume_saved_task(self) -> None:
    files_to_convert = [
        item.input_path
        for item in self._queue_items
        if item.status in {ConvertQueueItemStatus.PENDING, ConvertQueueItemStatus.INCOMPLETE}
    ]
    self._start_conversion_with_files(files_to_convert)
```

```python
def restore_saved_task(self, payload: dict) -> None:
    self._queue_items = load_convert_task_payload(payload)
    self._queue_widget.set_items(self._queue_items)
    config = payload.get("config", {})
    self._apply_saved_config(config)
```

```python
def _start_conversion_with_files(self, files_to_convert: list[str]) -> None:
    config = self._build_config()
    output_paths = self._build_output_paths(files_to_convert, config.output_dir)
    self._conversion_manager = ConversionManager()
    self._conversion_manager.set_config(config)
    self._conversion_manager.add_files_async(
        files_to_convert,
        config.output_dir,
        output_paths=output_paths,
    )

def _restore_controls_after_stop(self) -> None:
    self._file_list.set_enabled(True)
    self._cancel_btn.setVisible(False)
    self._start_btn.setEnabled(True)

def _apply_saved_config(self, config: dict) -> None:
    self._set_selected_output_codec(config.get("output_codec", "h264"))
    self._output_input.setText(config.get("output_dir", ""))
```

- [ ] **Step 4: Run Convert-page verification**

Run: `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/test_convert_page.py -q`
Expected: PASS with new pause/resume coverage and no regressions in existing Convert tests

- [ ] **Step 5: Commit**

```bash
git add src/core/conversion_manager.py src/ui/pages/convert_page.py tests/test_convert_page.py
git commit -m "feat(convert): persist pause and resume state"
```

### Task 6: Add Startup Restore and Saved Tasks Dialog

**Files:**
- Create: `src/ui/widgets/saved_tasks_dialog.py`
- Modify: `src/ui/main_window.py`
- Modify: `src/main.py`
- Modify: `tests/test_main_window_workbench.py`

- [ ] **Step 1: Write the failing workbench tests for restore flow**

```python
def test_main_window_exposes_saved_tasks_action(qapp):
    win = _make_window(qapp)
    action_texts = [action.text() for action in win.menuBar().actions()[0].menu().actions()]
    assert "Saved Tasks" in action_texts


def test_main_window_restore_saved_convert_task(qapp):
    win = _make_window(qapp)
    payload = {
        "tool": "convert",
        "items": [{"item_id": "one", "input_path": "/tmp/1.mp4", "output_path": "/tmp/out/1.mp4", "status": "pending"}],
        "config": {"output_codec": "h264", "output_dir": "/tmp/out"},
    }

    win.restore_saved_task(payload)

    assert win.shell.active_tool() == "convert"
```

- [ ] **Step 2: Run the workbench tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/test_main_window_workbench.py -q`
Expected: FAIL because the dialog and `restore_saved_task()` entry point do not exist

- [ ] **Step 3: Implement the dialog and restore entry point**

```python
class SavedTasksDialog(QDialog):
    task_open_requested = pyqtSignal(int)
    task_delete_requested = pyqtSignal(int)

    def set_tasks(self, tasks: list[SavedTask]) -> None:
        self._tasks_by_id = {task.id: task for task in tasks if task.id is not None}
        self._list.clear()
        for task in tasks:
            item = QListWidgetItem(f"{task.title} — {task.summary.get('completed', 0)}/{task.summary.get('total', 0)}")
            item.setData(Qt.ItemDataRole.UserRole, task.id)
            self._list.addItem(item)

    def selected_task(self) -> Optional[SavedTask]:
        current = self._list.currentItem()
        if current is None:
            return None
        return self._tasks_by_id.get(current.data(Qt.ItemDataRole.UserRole))
```

```python
saved_tasks_action = QAction("Saved Tasks", self)
saved_tasks_action.triggered.connect(self._show_saved_tasks_dialog)
file_menu.addAction(saved_tasks_action)
```

```python
def restore_saved_task(self, payload: dict) -> None:
    if payload.get("tool") == "convert":
        self.shell.switch_to_tool("convert")
        self.convert_page.restore_saved_task(payload)
```

```python
def _show_saved_tasks_dialog(self) -> None:
    dialog = SavedTasksDialog(self)
    dialog.set_tasks(self.saved_task_service.list_unfinished_tasks())
    if dialog.exec():
        selected_task = dialog.selected_task()
        if selected_task is not None:
            self.restore_saved_task(
                {"tool": selected_task.task_type, **selected_task.payload}
            )
```

- [ ] **Step 4: Run the workbench tests again**

Run: `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/test_main_window_workbench.py -q`
Expected: PASS with the File menu action and convert restore path covered

- [ ] **Step 5: Commit**

```bash
git add src/ui/widgets/saved_tasks_dialog.py src/ui/main_window.py src/main.py tests/test_main_window_workbench.py
git commit -m "feat(ui): add saved tasks recovery surfaces"
```

### Task 7: End-to-End Verification and Session Docs

**Files:**
- Modify: `SESSION.md`
- Modify: `MEMORY.md` if implementation reveals durable gotchas

- [ ] **Step 1: Run focused regression coverage**

Run: `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/pytest tests/test_saved_task_repository.py tests/test_convert_saved_task.py tests/test_convert_page.py tests/test_main_window_workbench.py -q`
Expected: PASS across the new persistence, Convert queue, and restore flows

- [ ] **Step 2: Run syntax verification for touched modules**

Run: `python -m py_compile src/data/models.py src/data/database.py src/data/repositories/saved_task_repository.py src/services/saved_task_service.py src/core/convert_saved_task.py src/core/conversion_manager.py src/ui/widgets/convert_queue_widget.py src/ui/widgets/saved_tasks_dialog.py src/ui/pages/convert_page.py src/ui/main_window.py src/main.py`
Expected: no output

- [ ] **Step 3: Smoke-test the desktop flow manually**

Run: `python run.py`
Expected: app starts, a Convert batch can be paused, reopened from Saved Tasks, and resumed with completed items preserved

- [ ] **Step 4: Update session memory**

```markdown
- Added shared Saved Tasks persistence and a recovery dialog for unfinished Convert batches.
- Convert now stores queue item state, supports pause/put-aside, and restarts interrupted files from the beginning on resume.
- Processed-file detection uses expected output path plus non-zero file existence; it does not compare source/output file size.
```

- [ ] **Step 5: Commit**

```bash
git add SESSION.md MEMORY.md
git commit -m "docs: record saved tasks rollout"
```

## Self-Review

- Spec coverage: this plan covers shared task persistence, startup/manual recovery, Convert queue durability, immediate-pause semantics, processed-file detection, queue editing, and verification. It intentionally excludes Trim and other adapters because the approved spec already phases them later.
- Placeholder scan: no `TBD`, `TODO`, or "implement later" markers remain. Each task names concrete files, tests, commands, and method shapes.
- Type consistency: the plan consistently uses `SavedTask`, `SavedTaskStatus`, `SavedTaskService`, `ConvertQueueItem`, and `ConvertQueueItemStatus` across repository, service, page, and UI tasks.
