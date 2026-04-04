"""Dialog for browsing and restoring saved tasks."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ...data.models import SavedTask
from ...services.saved_task_service import SavedTaskService


class SavedTasksDialog(QDialog):
    """Simple modal list for unfinished saved tasks."""

    def __init__(
        self,
        saved_task_service: SavedTaskService,
        parent=None,
    ):
        super().__init__(parent)
        self.saved_task_service = saved_task_service
        self._tasks_by_id: dict[int, SavedTask] = {}
        self._setup_ui()
        self._load_tasks()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Saved Tasks")
        self.resize(520, 360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        intro = QLabel("Pick an unfinished task to restore or delete.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self._list = QListWidget()
        layout.addWidget(self._list, stretch=1)

        button_row = QHBoxLayout()
        button_row.addStretch()

        self._delete_btn = QPushButton("Delete")
        self._open_btn = QPushButton("Open")
        self._close_btn = QPushButton("Close")

        button_row.addWidget(self._delete_btn)
        button_row.addWidget(self._open_btn)
        button_row.addWidget(self._close_btn)
        layout.addLayout(button_row)

        self._list.itemDoubleClicked.connect(lambda _item: self.accept())
        self._delete_btn.clicked.connect(self._delete_selected_task)
        self._open_btn.clicked.connect(self.accept)
        self._close_btn.clicked.connect(self.reject)

    def _load_tasks(self) -> None:
        tasks = self.saved_task_service.list_unfinished_tasks()
        self._tasks_by_id = {task.id: task for task in tasks if task.id is not None}

        self._list.clear()
        for task in tasks:
            summary = task.summary or {}
            completed = summary.get("completed", 0)
            total = summary.get("total", 0)
            label = f"{task.title} - {completed}/{total}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, task.id)
            self._list.addItem(item)

        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def selected_task(self) -> Optional[SavedTask]:
        """Return the currently selected saved task."""
        current = self._list.currentItem()
        if current is None:
            return None

        task_id = current.data(Qt.ItemDataRole.UserRole)
        if task_id is None:
            return None
        return self._tasks_by_id.get(task_id)

    def _delete_selected_task(self) -> None:
        task = self.selected_task()
        if task is None or task.id is None:
            return

        result = QMessageBox.question(
            self,
            "Delete Saved Task",
            f'Delete "{task.title}" from Saved Tasks?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        self.saved_task_service.delete_task(task.id)
        self._load_tasks()
