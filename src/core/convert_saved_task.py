"""Helpers for persisting and restoring Convert queue state."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ConvertQueueItemStatus(str, Enum):
    """Supported saved-state statuses for Convert queue items."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    INCOMPLETE = "incomplete"


@dataclass(slots=True)
class ConvertQueueItem:
    """Serializable Convert queue entry."""

    item_id: str
    input_path: str
    output_path: str
    display_name: str = ""
    source_root: Optional[str] = None
    status: ConvertQueueItemStatus = ConvertQueueItemStatus.PENDING
    progress_percent: float = 0.0
    detail: str = ""
    error_message: str = ""

    def to_payload(self) -> dict[str, Any]:
        """Serialize the queue item for task persistence."""
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

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ConvertQueueItem":
        """Restore a queue item from persisted task data."""
        raw_status = payload.get("status", ConvertQueueItemStatus.PENDING)
        if isinstance(raw_status, ConvertQueueItemStatus):
            status = raw_status
        else:
            status = ConvertQueueItemStatus(str(raw_status))

        return cls(
            item_id=str(payload.get("item_id", "")),
            input_path=str(payload.get("input_path", "")),
            output_path=str(payload.get("output_path", "")),
            display_name=str(payload.get("display_name", "")),
            source_root=(
                str(payload.get("source_root"))
                if payload.get("source_root") is not None
                else None
            ),
            status=status,
            progress_percent=float(payload.get("progress_percent", 0.0)),
            detail=str(payload.get("detail", "")),
            error_message=str(payload.get("error_message", "")),
        )


def build_convert_task_payload(
    items: list[ConvertQueueItem],
    config_dict: dict[str, Any],
) -> dict[str, Any]:
    """Build a saved-task payload while preserving the queue order."""
    return {
        "tool": "convert",
        "items": [item.to_payload() for item in items],
        "config": dict(config_dict),
    }


def load_convert_task_payload(payload: dict[str, Any]) -> list[ConvertQueueItem]:
    """Restore saved Convert queue items from a persisted payload."""
    items: list[ConvertQueueItem] = []
    for raw_item in payload.get("items", []):
        items.append(ConvertQueueItem.from_payload(raw_item))
    return items


def detect_existing_outputs(items: list[ConvertQueueItem]) -> list[ConvertQueueItem]:
    """Mark queue items complete when their expected output already exists."""
    updated: list[ConvertQueueItem] = []
    for item in items:
        output_file = Path(item.output_path)
        if output_file.exists() and output_file.is_file() and output_file.stat().st_size > 0:
            updated.append(
                replace(
                    item,
                    status=ConvertQueueItemStatus.COMPLETED,
                    progress_percent=100.0,
                    detail="Already processed",
                )
            )
            continue

        updated.append(item)
    return updated
