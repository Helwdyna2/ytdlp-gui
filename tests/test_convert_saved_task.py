"""Tests for Convert saved-task helpers."""

from src.core.convert_saved_task import (
    ConvertQueueItem,
    ConvertQueueItemStatus,
    build_convert_task_payload,
    detect_existing_outputs,
    load_convert_task_payload,
)


def test_build_convert_task_payload_preserves_queue_order():
    items = [
        ConvertQueueItem(
            item_id="one",
            input_path="/tmp/1.mp4",
            output_path="/tmp/out/1.mp4",
            display_name="one.mp4",
        ),
        ConvertQueueItem(
            item_id="two",
            input_path="/tmp/2.mp4",
            output_path="/tmp/out/2.mp4",
            display_name="two.mp4",
            status=ConvertQueueItemStatus.PROCESSING,
            progress_percent=12.5,
        ),
    ]

    payload = build_convert_task_payload(items, {"output_codec": "h264", "output_dir": "/tmp/out"})
    restored = load_convert_task_payload(payload)

    assert [item["item_id"] for item in payload["items"]] == ["one", "two"]
    assert [item.item_id for item in restored] == ["one", "two"]
    assert payload["config"] == {"output_codec": "h264", "output_dir": "/tmp/out"}
    assert restored[1].status == ConvertQueueItemStatus.PROCESSING
    assert restored[1].progress_percent == 12.5


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
    assert updated[0].progress_percent == 100.0
    assert updated[0].detail == "Already processed"


def test_load_convert_task_payload_normalizes_legacy_and_invalid_status_values():
    payload = {
        "items": [
            {"item_id": "legacy-active", "input_path": "/tmp/a.mp4", "output_path": "/tmp/out/a.mp4", "status": "in_progress"},
            {"item_id": "legacy-cancelled", "input_path": "/tmp/b.mp4", "output_path": "/tmp/out/b.mp4", "status": "cancelled"},
            {"item_id": "null-status", "input_path": "/tmp/c.mp4", "output_path": "/tmp/out/c.mp4", "status": None},
            {"item_id": "unknown-status", "input_path": "/tmp/d.mp4", "output_path": "/tmp/out/d.mp4", "status": "mystery"},
        ]
    }

    restored = load_convert_task_payload(payload)

    assert [item.status for item in restored] == [
        ConvertQueueItemStatus.PROCESSING,
        ConvertQueueItemStatus.INCOMPLETE,
        ConvertQueueItemStatus.PENDING,
        ConvertQueueItemStatus.PENDING,
    ]


def test_load_convert_task_payload_normalizes_invalid_progress_percent_values():
    payload = {
        "items": [
            {"item_id": "null-progress", "input_path": "/tmp/a.mp4", "output_path": "/tmp/out/a.mp4", "progress_percent": None},
            {"item_id": "bad-progress", "input_path": "/tmp/b.mp4", "output_path": "/tmp/out/b.mp4", "progress_percent": "not-a-number"},
            {"item_id": "good-progress", "input_path": "/tmp/c.mp4", "output_path": "/tmp/out/c.mp4", "progress_percent": "42.5"},
        ]
    }

    restored = load_convert_task_payload(payload)

    assert [item.progress_percent for item in restored] == [0.0, 0.0, 42.5]


def test_detect_existing_outputs_leaves_missing_and_zero_byte_outputs_unfinished(tmp_path):
    zero_byte_path = tmp_path / "zero.mp4"
    zero_byte_path.write_bytes(b"")
    missing_path = tmp_path / "missing.mp4"

    items = [
        ConvertQueueItem(
            item_id="zero-byte",
            input_path=str(tmp_path / "source-a.mp4"),
            output_path=str(zero_byte_path),
            status=ConvertQueueItemStatus.PENDING,
        ),
        ConvertQueueItem(
            item_id="missing",
            input_path=str(tmp_path / "source-b.mp4"),
            output_path=str(missing_path),
            status=ConvertQueueItemStatus.INCOMPLETE,
        ),
    ]

    updated = detect_existing_outputs(items)

    assert updated[0].status == ConvertQueueItemStatus.PENDING
    assert updated[0].progress_percent == 0.0
    assert updated[1].status == ConvertQueueItemStatus.INCOMPLETE
    assert updated[1].progress_percent == 0.0


def test_detect_existing_outputs_does_not_complete_interrupted_items(tmp_path):
    output_path = tmp_path / "partial.mp4"
    output_path.write_bytes(b"partial-data")

    item = ConvertQueueItem(
        item_id="retry",
        input_path=str(tmp_path / "source.mp4"),
        output_path=str(output_path),
        status=ConvertQueueItemStatus.INCOMPLETE,
        detail="Will restart on resume",
    )

    updated = detect_existing_outputs([item])

    assert updated[0].status == ConvertQueueItemStatus.INCOMPLETE
    assert updated[0].detail == "Will restart on resume"
    assert updated[0].progress_percent == 0.0
