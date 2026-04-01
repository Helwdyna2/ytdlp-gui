"""Lightweight diagnostics collector for the Trim editor."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DiagnosticEntry:
    """Single diagnostic message for the editor activity feed."""

    level: str
    message: str


class EditorDiagnostics(QObject):
    """In-memory activity log that also forwards to Python logging."""

    entry_added = pyqtSignal(str, str)
    cleared = pyqtSignal()

    def __init__(self, parent=None, max_entries: int = 200):
        super().__init__(parent)
        self._max_entries = max_entries
        self._entries: list[DiagnosticEntry] = []

    def record(self, level: str, message: str) -> None:
        entry = DiagnosticEntry(level=level, message=message)
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]

        log_method = getattr(logger, level, logger.info)
        log_method(message)
        self.entry_added.emit(level, message)

    def clear(self) -> None:
        self._entries.clear()
        self.cleared.emit()

    def entries(self) -> list[DiagnosticEntry]:
        return list(self._entries)

    def warning_count(self) -> int:
        return sum(1 for entry in self._entries if entry.level in {"warning", "error"})
